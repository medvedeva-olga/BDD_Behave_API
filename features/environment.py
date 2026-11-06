"""Окружение behave для тестов мокового Tasks API."""

import logging
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.client import ApiClient  # noqa: E402
from support.cleanup import cleanup_created_issues  # noqa: E402

# Кириллица в консоли Windows (cp1251/cp1252) ломает print() и логи.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger("tasks.environment")

DEFAULT_BASE_URL = "http://127.0.0.1:8090"

START_HINT = (
    "Мок не запущен. Запустите его из корня проекта:\n"
    "  docker compose up -d --wait\n"
    "или без Docker:\n"
    "  python tools/mock_tasks_api.py"
)


def _base_url(context):
    """Приоритет: -D base_url=... > API_BASE_URL > behave.ini > константа."""
    return (
        context.config.userdata.get("base_url")
        or os.getenv("API_BASE_URL")
        or DEFAULT_BASE_URL
    )


def _ensure_service_available(context):
    try:
        response = context.api.health()
    except Exception as error:  # noqa: BLE001 - нужен понятный текст для тестов
        raise RuntimeError(
            f"{START_HINT}\nАдрес: {context.api.base_url}\nОшибка: {error}"
        ) from error

    if response.status_code != 200:
        raise RuntimeError(
            f"{START_HINT}\nАдрес: {context.api.base_url}\n"
            f"GET /health вернул {response.status_code}: {response.text}"
        )


def before_all(context):
    """Настроить логи и проверить, что мок доступен."""
    context.config.setup_logging()

    context.api = ApiClient(_base_url(context))
    logger.info("Базовый URL: %s", context.api.base_url)

    _ensure_service_available(context)


def before_scenario(context, scenario):
    """Изолировать сценарии: начальные данные и выключенная проверка токена."""
    context.api.clear_token()
    context.api.reset()
    context.api.set_auth_required(False)

    context.created_issue_id = None
    context.created_issue_ids = []
    context.created_issues_map = {}
    context.last_count = None


def after_scenario(context, scenario):
    """Удалить всё, что сценарий создал через API (даже если он упал)."""
    cleanup_created_issues(context)


def after_all(context):
    context.api.close()
