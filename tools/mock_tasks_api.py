"""Моковый сервис Tasks API для интеграционных тестов задач.

Повторяет эндпоинты, которые использует TasksService (Node.js):

    POST   /api/auth/login                 -> {"access_token": "..."}
    POST   /api/issues                     -> <id>            (голое число)
    GET    /api/issues/<id>                -> {"issue": {..., "standards": [...]}}
    DELETE /api/issues/<id>?force=true     -> <id>            (голое число)
    POST   /api/issues/<id>/related        -> {"id": ..., ...}
    GET    /api/issues/<id>/children       -> {"rows": [{"rowId": ...}], "count": N}

Служебные эндпоинты для тестов:

    GET    /health                         -> {"status": "ok"}
    POST   /__admin/reset                  -> {"reset": true}   (начальные данные)
    POST   /__admin/reset?empty=true       -> {"reset": true}   (полностью очистить)
    POST   /__admin/config?require_auth=1  -> {"require_auth": true}
    GET    /__admin/state                  -> {"issues": [...], "relations": [...]}

Начальные данные: 4 задачи (id 1..4). У задачи 1 есть дети 2 и 3, поэтому
GET /api/issues/1 и POST /api/issues с parentIssue=1 работают сразу после
запуска. Первая созданная задача получит id 5.

Запуск:
    python tools/mock_tasks_api.py
    python tools/mock_tasks_api.py --port 8091
    python tools/mock_tasks_api.py --require-auth

Переменные окружения: API_HOST (по умолчанию 127.0.0.1), API_PORT (8090),
MOCK_REQUIRE_AUTH=1.

Авторизация по умолчанию не проверяется: в тестируемом коде TasksService.auth()
сразу возвращает true и не выставляет заголовок Authorization, поэтому все
запросы идут без токена. Включайте --require-auth, чтобы проверять обработку 401.
"""

import argparse
import json
import os
import threading
import traceback
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ACCESS_TOKEN = "mock-access-token"
DATE_FIELDS = ("startDate", "endDate")
REQUIRED_ISSUE_FIELDS = ("projectId", "trackerId", "statusId", "priority", "subject")

# Начальные данные: с ними GET сразу отдаёт задачи, а parentIssue=1 валиден.
# Даты — строки, как их присылает клиент; id уникальны и идут подряд.
SEED_ISSUES = (
    {
        "id": 1,
        "projectId": 854,
        "trackerId": 34,
        "statusId": 13,
        "priority": 185,
        "subject": "Project management",
        "parentIssue": None,
        "startDate": "2026-01-01",
        "endDate": "2026-12-31",
    },
    {
        "id": 2,
        "projectId": 854,
        "trackerId": 34,
        "statusId": 13,
        "priority": 185,
        "subject": "Requirements",
        "parentIssue": 1,
        "startDate": "2026-01-01",
        "endDate": "2026-01-31",
    },
    {
        "id": 3,
        "projectId": 854,
        "trackerId": 34,
        "statusId": 13,
        "priority": 185,
        "subject": "API development",
        "parentIssue": 1,
        "startDate": "2026-02-01",
        "endDate": "2026-03-31",
    },
    {
        "id": 4,
        "projectId": 854,
        "trackerId": 34,
        "statusId": 13,
        "priority": 185,
        "subject": "Release 1.0",
        "parentIssue": None,
        "startDate": "2026-04-01",
        "endDate": "2026-04-30",
    },
)


class BadRequest(Exception):
    """Некорректный запрос: клиенту уходит 400 с текстом ошибки."""


class TasksState:
    """Состояние мока в памяти. Сбрасывается через POST /__admin/reset."""

    def __init__(self):
        self.lock = threading.Lock()
        self.seed()

    def seed(self):
        """Начальные данные: задача 1 существует, поэтому parentIssue=1 валиден."""
        self.issues = {issue["id"]: dict(issue) for issue in SEED_ISSUES}
        self.relations = []
        self.next_issue_id = max(self.issues) + 1
        self.next_relation_id = 1
        self.tokens = set()

    def clear(self):
        """Полностью пустое состояние (POST /__admin/reset?empty=true)."""
        self.issues = {}
        self.relations = []
        self.next_issue_id = 1
        self.next_relation_id = 1
        self.tokens = set()


class TasksHandler(BaseHTTPRequestHandler):
    state = TasksState()
    require_auth = False
    # Значение, заданное при запуске: /__admin/reset возвращает его обратно.
    require_auth_default = False

    # ---------------------------------------------------------------- HTTP

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def _dispatch(self, method):
        try:
            status, payload = self._route(method)
        except BadRequest as error:
            status, payload = 400, {"statusCode": 400, "message": str(error)}
        except Exception:  # noqa: BLE001 - мок не должен молча падать
            traceback.print_exc()
            status, payload = 500, {"statusCode": 500, "message": "Internal mock error"}

        self._send_json(status, payload)

    def _route(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        parts = [part for part in path.split("/") if part]
        query = parse_qs(parsed.query)

        if (
            self.require_auth
            and path.startswith("/api/")
            and path != "/api/auth/login"
            and not self._authorized()
        ):
            return 401, {"statusCode": 401, "message": "Unauthorized"}

        if method == "GET" and path == "/health":
            return 200, {"status": "ok"}

        if method == "POST" and path == "/api/auth/login":
            return self._login()

        if method == "POST" and path == "/api/issues":
            return self._create_issue()

        if method == "POST" and path == "/__admin/reset":
            empty = query.get("empty", ["0"])[0].lower() in ("1", "true", "yes")
            with self.state.lock:
                if empty:
                    self.state.clear()
                else:
                    self.state.seed()
            # Сброс возвращает режим авторизации, с которым мок запустили.
            type(self).require_auth = type(self).require_auth_default
            return 200, {"reset": True}

        if method == "POST" and path == "/__admin/config":
            require_auth = query.get("require_auth", ["0"])[0].lower() in (
                "1",
                "true",
                "yes",
            )
            type(self).require_auth = require_auth
            return 200, {"require_auth": require_auth}

        if method == "GET" and path == "/__admin/state":
            return self._admin_state()

        if method == "GET" and path == "/api/issues":
            return self._list_issues(query)

        if (
            len(parts) == 3
            and parts[0] == "api"
            and parts[1] == "issues"
            and parts[2].isdigit()
        ):
            issue_id = int(parts[2])
            if method == "GET":
                return self._get_issue(issue_id)
            if method == "DELETE":
                return self._delete_issue(issue_id, query)

        if (
            len(parts) == 4
            and parts[0] == "api"
            and parts[1] == "issues"
            and parts[2].isdigit()
        ):
            issue_id = int(parts[2])
            if method == "POST" and parts[3] == "related":
                return self._create_relation(issue_id)
            if method == "GET" and parts[3] == "children":
                return self._get_children(issue_id)

        return 404, {"statusCode": 404, "message": f"Not found: {method} {path}"}

    # ------------------------------------------------------------ Эндпоинты

    def _login(self):
        data = self._read_json()
        username = data.get("username")
        password = data.get("password")
        if not _non_empty_string(username) or not _non_empty_string(password):
            raise BadRequest("Fields 'username' and 'password' are required")

        with self.state.lock:
            self.state.tokens.add(ACCESS_TOKEN)

        return 200, {
            "access_token": ACCESS_TOKEN,
            "token_type": "Bearer",
            "expires_in": 3600,
        }

    def _create_issue(self):
        data = self._read_json()

        missing = [name for name in REQUIRED_ISSUE_FIELDS if name not in data]
        if missing:
            raise BadRequest("Missing required fields: " + ", ".join(missing))

        subject = data["subject"]
        if not _non_empty_string(subject):
            raise BadRequest("Field 'subject' must be a non-empty string")

        for name in ("projectId", "trackerId", "statusId", "priority"):
            if not _is_int(data[name]):
                raise BadRequest(f"Field '{name}' must be an integer")

        parent = data.get("parentIssue")
        if parent is not None and not _is_int(parent):
            raise BadRequest("Field 'parentIssue' must be an integer or null")

        dates = {}
        for name in DATE_FIELDS:
            value = data.get(name)
            if value is not None and not isinstance(value, str):
                raise BadRequest(f"Field '{name}' must be a string or null")
            dates[name] = value

        with self.state.lock:
            # Родитель должен существовать, иначе в GET /children будет мусор.
            if parent is not None and parent not in self.state.issues:
                return 404, {
                    "statusCode": 404,
                    "message": f"Parent issue {parent} not found",
                }

            issue_id = self.state.next_issue_id
            self.state.next_issue_id += 1
            self.state.issues[issue_id] = {
                "id": issue_id,
                "projectId": data["projectId"],
                "trackerId": data["trackerId"],
                "statusId": data["statusId"],
                "priority": data["priority"],
                "subject": subject,
                "parentIssue": parent,
                "startDate": dates["startDate"],
                "endDate": dates["endDate"],
            }

        # TasksService.createTask() ждёт в теле именно id, а не объект.
        return 201, issue_id

    def _get_issue(self, issue_id):
        with self.state.lock:
            issue = self.state.issues.get(issue_id)
            if issue is None:
                return 404, {
                    "statusCode": 404,
                    "message": f"Issue {issue_id} not found",
                }
            body = self._issue_body(issue)

        return 200, {"issue": body}

    def _list_issues(self, query=None):
        subject = ""
        if query:
            subject = (query.get("subject", [""])[0] or "").strip()
        with self.state.lock:
            issues = [
                self._issue_body(issue)
                for issue in self.state.issues.values()
                if not subject or issue["subject"] == subject
            ]
        return 200, {"issues": issues}

    def _delete_issue(self, issue_id, query):
        force = query.get("force", ["false"])[0].lower() == "true"

        with self.state.lock:
            issue = self.state.issues.get(issue_id)
            if issue is None:
                return 404, {
                    "statusCode": 404,
                    "message": f"Issue {issue_id} not found",
                }

            children = [
                child_id
                for child_id, item in self.state.issues.items()
                if item["parentIssue"] == issue_id
            ]
            if children and not force:
                return 409, {
                    "statusCode": 409,
                    "message": (
                        f"Issue {issue_id} has children {children}. "
                        "Use force=true to delete the whole branch."
                    ),
                }

            # Дети остаются, но без ссылки на удалённого родителя.
            for child_id in children:
                self.state.issues[child_id]["parentIssue"] = None

            del self.state.issues[issue_id]
            self.state.relations = [
                relation
                for relation in self.state.relations
                if issue_id not in (relation["issueId"], relation["relatedIssueId"])
            ]

        # TasksService.deleteTask() тоже ждёт id в теле ответа.
        return 200, issue_id

    def _create_relation(self, issue_id):
        data = self._read_json()

        related_issue_id = data.get("relatedIssueId")
        if not _is_int(related_issue_id):
            raise BadRequest("Field 'relatedIssueId' must be an integer")

        relation_type = data.get("relationType", "")
        if not isinstance(relation_type, str):
            raise BadRequest("Field 'relationType' must be a string")

        delay = data.get("delay", 0)
        if not _is_int(delay):
            raise BadRequest("Field 'delay' must be an integer")

        with self.state.lock:
            if issue_id not in self.state.issues:
                return 404, {
                    "statusCode": 404,
                    "message": f"Issue {issue_id} not found",
                }
            if related_issue_id not in self.state.issues:
                return 404, {
                    "statusCode": 404,
                    "message": f"Related issue {related_issue_id} not found",
                }

            relation_id = self.state.next_relation_id
            self.state.next_relation_id += 1
            relation = {
                "id": relation_id,
                "issueId": issue_id,
                "relatedIssueId": related_issue_id,
                "relationType": relation_type,
                "delay": delay,
            }
            self.state.relations.append(relation)

            # FinishStart: задача-источник завершает работу, задача-наследник
            # начинается в следующий рабочий день и сохраняет свою длительность,
            # посчитанную в рабочих днях (выходные не входят в длительность).
            if relation_type == "FinishStart":
                source = self.state.issues.get(issue_id)
                target = self.state.issues.get(related_issue_id)
                if source is not None and target is not None:
                    source_end = _parse_date(source.get("endDate"))
                    target_old_start = _parse_date(target.get("startDate"))
                    target_old_end = _parse_date(target.get("endDate"))
                    if (
                        source_end is not None
                        and target_old_start is not None
                        and target_old_end is not None
                    ):
                        new_start = _business_day_on_or_after(
                            source_end + timedelta(days=1)
                        )
                        duration = _business_days(target_old_start, target_old_end)
                        new_end = _add_business_days(new_start, duration)
                        target["startDate"] = new_start.isoformat()
                        target["endDate"] = new_end.isoformat()

                        # Дочерние задачи, которые целиком лежали внутри старого
                        # диапазона задачи, «едут» вместе с ней. Длительность
                        # каждой дочерней задачи тоже сохраняется в рабочих днях.
                        shift = new_start - target_old_start
                        for child in self.state.issues.values():
                            if child.get("parentIssue") != related_issue_id:
                                continue
                            child_old_start = _parse_date(child.get("startDate"))
                            child_old_end = _parse_date(child.get("endDate"))
                            if child_old_start is None or child_old_end is None:
                                continue
                            if (
                                child_old_start < target_old_start
                                or child_old_end > target_old_end
                            ):
                                # Ребёнок вне диапазона родителя — независим.
                                continue
                            child_new_start = _business_day_on_or_after(
                                child_old_start + shift
                            )
                            child_duration = _business_days(
                                child_old_start, child_old_end
                            )
                            child["startDate"] = child_new_start.isoformat()
                            child["endDate"] = _add_business_days(
                                child_new_start, child_duration
                            ).isoformat()

                        # Родитель (и его родители) должен покрывать дочерние
                        # задачи по датам, иначе итоговый диапазон будет неверным.
                        self._fit_to_children(related_issue_id)
                        self._refresh_ancestors(related_issue_id)

        return 201, dict(relation)

    def _fit_to_children(self, issue_id):
        """Расширить диапазон задачи, чтобы он покрывал всех её детей."""
        issue = self.state.issues.get(issue_id)
        if issue is None:
            return

        child_starts = []
        child_ends = []
        for child in self.state.issues.values():
            if child.get("parentIssue") != issue_id:
                continue
            child_start = _parse_date(child.get("startDate"))
            child_end = _parse_date(child.get("endDate"))
            if child_start is not None:
                child_starts.append(child_start)
            if child_end is not None:
                child_ends.append(child_end)

        if not child_starts or not child_ends:
            return

        issue_start = _parse_date(issue.get("startDate"))
        issue_end = _parse_date(issue.get("endDate"))
        min_start = min(child_starts)
        max_end = max(child_ends)

        if issue_start is None or min_start < issue_start:
            issue["startDate"] = min_start.isoformat()
        if issue_end is None or max_end > issue_end:
            issue["endDate"] = max_end.isoformat()

    def _refresh_ancestors(self, issue_id):
        """Подниматься по цепочке родителей, расширяя их диапазон до детей."""
        current = self.state.issues.get(issue_id)
        seen = set()
        while current is not None:
            parent_id = current.get("parentIssue")
            if parent_id is None or parent_id in seen:
                break
            parent = self.state.issues.get(parent_id)
            if parent is None:
                break
            seen.add(parent_id)

            child_start = _parse_date(current.get("startDate"))
            child_end = _parse_date(current.get("endDate"))
            parent_start = _parse_date(parent.get("startDate"))
            parent_end = _parse_date(parent.get("endDate"))

            if child_start is not None and (
                parent_start is None or child_start < parent_start
            ):
                parent["startDate"] = child_start.isoformat()
            if child_end is not None and (parent_end is None or child_end > parent_end):
                parent["endDate"] = child_end.isoformat()

            current = parent

    def _get_children(self, issue_id):
        with self.state.lock:
            if issue_id not in self.state.issues:
                return 404, {
                    "statusCode": 404,
                    "message": f"Issue {issue_id} not found",
                }

            child_ids = sorted(
                child_id
                for child_id, item in self.state.issues.items()
                if item["parentIssue"] == issue_id
            )
            rows = [
                {
                    "rowId": child_id,
                    "subject": self.state.issues[child_id]["subject"],
                }
                for child_id in child_ids
            ]

        return 200, {"rows": rows, "count": len(rows)}

    def _admin_state(self):
        with self.state.lock:
            issues = [
                self._issue_body(issue) for issue in self.state.issues.values()
            ]
            relations = [dict(relation) for relation in self.state.relations]

        return 200, {"issues": issues, "relations": relations}

    # ------------------------------------------------------------- Помощники

    def _issue_body(self, issue):
        """Форма ответа GET /api/issues/<id>: даты живут в standards."""
        return {
            "id": issue["id"],
            "projectId": issue["projectId"],
            "trackerId": issue["trackerId"],
            "statusId": issue["statusId"],
            "priority": issue["priority"],
            "subject": issue["subject"],
            "parentIssue": issue["parentIssue"],
            "standards": [
                {"fieldId": "startDate", "valueId": issue["startDate"]},
                {"fieldId": "endDate", "valueId": issue["endDate"]},
            ],
        }

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}

        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BadRequest("Request body must be valid UTF-8 JSON") from None

        if not isinstance(data, dict):
            raise BadRequest("Request body must be a JSON object")
        return data

    def _authorized(self):
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        token = header[len(prefix):].strip()
        with self.state.lock:
            return token in self.state.tokens

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def log_message(self, fmt, *args):
        print(f"[tasks-mock] {self.address_string()} {fmt % args}")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _non_empty_string(value):
    return isinstance(value, str) and bool(value.strip())


def _parse_date(value):
    """Привести строку вида YYYY-MM-DD к datetime.date (None, если не удалось)."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _next_business_day(value):
    """Следующий день после value, пропуская выходные (Sat=5, Sun=6)."""
    parsed = _parse_date(value)
    if parsed is None:
        return value
    return _business_day_on_or_after(parsed + timedelta(days=1)).isoformat()


def _business_day_on_or_after(value):
    """Ближайший рабочий день, не раньше value."""
    current = value
    while current.weekday() >= 5:
        current = current + timedelta(days=1)
    return current


def _business_days(start, end):
    """Количество рабочих дней (Mon-Fri) в диапазоне [start, end] включительно."""
    if start is None or end is None or end < start:
        return 0
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current = current + timedelta(days=1)
    return days


def _add_business_days(start, duration):
    """Дата последнего рабочего дня для duration рабочих дней, начиная с start.

    start должен быть рабочим днём; duration >= 1. Выходные при подсчёте
    пропускаются, поэтому диапазон может «удлиняться» в календарных днях.
    """
    current = start
    remaining = max(duration, 1)
    while True:
        if current.weekday() < 5:
            remaining -= 1
            if remaining == 0:
                return current
        current = current + timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description="Mock Tasks API")
    parser.add_argument(
        "--host", default=os.getenv("API_HOST", "127.0.0.1"), help="bind address"
    )
    parser.add_argument(
        "--port", type=int, default=int(os.getenv("API_PORT", "8090")), help="port"
    )
    parser.add_argument(
        "--require-auth",
        action="store_true",
        default=os.getenv("MOCK_REQUIRE_AUTH") == "1",
        help="require a Bearer token for /api/* (except login)",
    )
    args = parser.parse_args()

    TasksHandler.require_auth = args.require_auth
    TasksHandler.require_auth_default = args.require_auth

    server = ThreadingHTTPServer((args.host, args.port), TasksHandler)
    print(f"Tasks mock API: http://{args.host}:{args.port}")
    print("Seed: 4 issues (ids 1..4); POST /__admin/reset restores them")
    print("  POST   /api/auth/login")
    print("  POST   /api/issues")
    print("  GET    /api/issues/<id>")
    print("  DELETE /api/issues/<id>?force=true")
    print("  POST   /api/issues/<id>/related")
    print("  GET    /api/issues/<id>/children")
    print("  POST   /__admin/reset")
    print("  POST   /__admin/config?require_auth=true")
    print("  GET    /__admin/state")
    print("  GET    /health")
    if args.require_auth:
        print("Auth: Bearer token required for /api/* (use POST /api/auth/login)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
