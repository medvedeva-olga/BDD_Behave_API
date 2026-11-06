"""Разбор таблиц Gherkin и доступ к JSON-ответу."""

import json


def convert(value):
    """Привести строку из таблицы Gherkin к JSON-типу."""
    text = value.strip()
    lowered = text.lower()

    if lowered in ("null", "none"):
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def table_to_dict(table):
    """Таблица «поле → значение»: первая строка — заголовки, далее пары.

    Ожидается формат::

        | поле      | значение |
        | subject   | Задача   |
        | priority  | 185      |
    """
    if table is None or not table.rows:
        raise AssertionError(
            "Ожидалась таблица «поле → значение» с хотя бы одной строкой данных"
        )

    pairs = {}
    for row in table.rows:
        if len(row) != 2:
            raise AssertionError(
                "Каждая строка таблицы должна содержать ровно две ячейки: "
                f"поле и значение, получено {len(row)}: {list(row)}"
            )
        pairs[row[0].strip()] = convert(row[1])
    return pairs


def last_response(context):
    response = context.api.last_response
    if response is None:
        raise AssertionError("Запрос ещё не выполнялся: нет last_response")
    return response


def json_body(context):
    response = last_response(context)
    try:
        return response.json()
    except ValueError as error:
        raise AssertionError(
            f"Ответ не является JSON ({response.status_code}): {response.text}"
        ) from error


def resolve(data, path):
    """Достать значение по пути вида "issue.standards.0.valueId"."""
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    return current


def pretty(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def get_issue_dates(issue):
    standards = {item["fieldId"]: item["valueId"] for item in issue.get("standards") or []}
    return standards.get("startDate"), standards.get("endDate")


def create_task_payload(subject, start, end, parent_id=None):
    payload = {
        "projectId": 854,
        "trackerId": 34,
        "statusId": 13,
        "priority": 185,
        "subject": subject,
        "startDate": start,
        "endDate": end,
    }
    if parent_id is not None:
        payload["parentIssue"] = parent_id
    return payload

