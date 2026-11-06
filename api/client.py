"""HTTP-клиент для Tasks API: сессия, базовый URL, ретраи, токен, логирование."""

import logging
import time

import requests

from api import endpoints

logger = logging.getLogger("tasks.api")

DEFAULT_TIMEOUT = 10
RETRIES = 3
RETRY_DELAY = 0.3


class ApiClient:
    """Тонкая обёртка над requests.Session.

    Шаги не знают про URL и заголовки: адрес добавляет клиент, а Bearer-токен
    подставляется автоматически после успешного логина.
    """

    def __init__(self, base_url, timeout=DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.last_response = None
        self.token = None

    # ---------------------------------------------------------------- запросы

    def request(self, method, path, **kwargs):
        url = self.base_url + path
        kwargs.setdefault("timeout", self.timeout)

        headers = dict(kwargs.pop("headers", None) or {})
        if self.token:
            headers.setdefault("Authorization", f"Bearer {self.token}")
        if headers:
            kwargs["headers"] = headers

        logger.debug("%s %s params=%s json=%s", method, url, kwargs.get("params"), kwargs.get("json"))

        response = self._request_with_retries(method, url, **kwargs)
        self.last_response = response

        logger.info("%s %s -> %s", method, url, response.status_code)
        logger.debug("ответ: %s", response.text)
        return response

    def _request_with_retries(self, method, url, **kwargs):
        last_error = None
        for attempt in range(1, RETRIES + 1):
            try:
                return self.session.request(method, url, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as error:
                last_error = error
                if attempt < RETRIES:
                    logger.warning(
                        "Повтор %s/%s после сетевой ошибки: %s",
                        attempt,
                        RETRIES,
                        error,
                    )
                    time.sleep(RETRY_DELAY)
        raise last_error

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    # ------------------------------------------------------- служебные эндпоинты

    def health(self):
        """GET /health — проверка доступности мокового сервиса."""
        return self.get(endpoints.HEALTH)

    def state(self):
        """GET /__admin/state — текущее состояние мока."""
        return self.get(endpoints.ADMIN_STATE)

    def reset(self):
        """Вернуть мок к начальным данным (POST /__admin/reset)."""
        return self.post(endpoints.ADMIN_RESET)

    def clear_state(self):
        """Полная очистка состояния мока (POST /__admin/reset?empty=true)."""
        return self.post(endpoints.ADMIN_RESET_EMPTY)

    def set_auth_required(self, required: bool):
        """Включить/выключить проверку Bearer-токена (только для моки)."""
        return self.post(endpoints.admin_config_path(required))

    def clear_token(self):
        self.token = None

    def close(self):
        self.session.close()

    # --------------------------------------------------------------- issues

    def get_issue(self, issue_id: int):
        """GET /api/issues/{issue_id} — получить задачу."""
        return self.get(endpoints.ISSUE_BY_ID.format(issue_id=issue_id))

    def get_issues(self, params=None):
        """GET /api/issues — список задач (опционально с фильтром ?subject=...)."""
        return self.get(endpoints.ISSUES, params=params)

    def create_issue(self, payload: dict):
        """POST /api/issues — создать задачу (ответ: голый id)."""
        return self.post(endpoints.ISSUES, json=payload)

    def delete_issue(self, issue_id: int, force: bool = False):
        """DELETE /api/issues/{issue_id}[?force=true] — удалить задачу."""
        path = endpoints.ISSUE_BY_ID.format(issue_id=issue_id)
        if force:
            path += "?force=true"
        return self.delete(path)

    def get_children(self, issue_id: int):
        """GET /api/issues/{issue_id}/children — дочерние задачи."""
        return self.get(endpoints.ISSUE_CHILDREN.format(issue_id=issue_id))

    def create_relation(self, issue_id: int, related_id: int, relation_type: str):
        """POST /api/issues/{issue_id}/related — связать задачи."""
        return self.post(
            endpoints.ISSUE_RELATED.format(issue_id=issue_id),
            json={
                "relatedIssueId": related_id,
                "relationType": relation_type,
                "delay": 0,
            },
        )

    # ------------------------------------------------------------------ auth

    def login(self, username: str, password: str):
        """POST /api/auth/login — получить Bearer-токен."""
        return self.post(
            endpoints.AUTH_LOGIN,
            json={"username": username, "password": password},
        )
