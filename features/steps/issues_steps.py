"""Шаги для задач (issues)."""

from behave import given, when, then

from support.cleanup import register_created_issue, find_created_issue
from support.data import json_body, table_to_dict, create_task_payload, get_issue_dates


DEFAULT_ISSUE = {
    "projectId": 854,
    "trackerId": 34,
    "statusId": 13,
    "priority": 185,
    "subject": "Тестовая задача",
    "startDate": "2026-05-01",
    "endDate": "2026-05-10",
}


def _payload(context, extra=None):
    payload = dict(DEFAULT_ISSUE)
    if getattr(context, "table", None):
        payload.update(table_to_dict(context.table))
    if extra:
        payload.update(extra)
    return payload


def _post_issue(context, payload):
    """Создать задачу и запомнить её ID для очистки в after_scenario."""
    response = context.api.create_issue(payload)
    if response.status_code == 201:
        try:
            issue_id = response.json()
        except ValueError:
            return response
        context.created_issue_id = issue_id
        register_created_issue(context, issue_id, payload.get("subject"))
    return response

def _check_response_status(response, status_code):
    assert response.status_code == status_code, (
    f"Неверный статус ответа: {response.status_code}: {response.text}"
)


@when("я запрашиваю задачу с ID {issue_id:d}")
def step_get_issue(context, issue_id):
    context.api.get_issue(issue_id)


@when("я запрашиваю созданную задачу")
def step_get_created_issue(context):
    issue_id = getattr(context, "created_issue_id", None)
    assert issue_id is not None, "Сценарий ещё не создал задачу"

    context.api.get_issue(issue_id)


@when("я создаю задачу")
def step_create_issue(context):
    _post_issue(context, _payload(context))


@when("я создаю задачу с родителем {parent_id:d}")
def step_create_child_issue(context, parent_id):
    payload = _payload(context)
    payload["parentIssue"] = parent_id
    _post_issue(context, payload)


@when('я создаю задачу без поля "{field}"')
def step_create_issue_without_field(context, field):
    payload = _payload(context)
    payload.pop(field, None)
    _post_issue(context, payload)


@when("я создаю задачу без дат")
def step_create_issue_without_dates(context):
    payload = _payload(context, extra={"startDate": None, "endDate": None})
    _post_issue(context, payload)

@when("я создаю задачу с пустым subject")
def step_create_issue_with_empty_subject(context):
    payload = _payload(context, extra={"subject": ""})
    _post_issue(context, payload)

@given('cоздана задача "{subject}" c датами "{start}", "{end}"')
@given('создана задача "{subject}" с датами "{start}", "{end}"')
@when('я создаю задачу "{subject}" с датами "{start}", "{end}"')
@when('я создаю задачу "{subject}" c датами "{start}", "{end}"')
def step_create_task_with_dates(context, subject, start, end):
    payload = _payload(context, extra={"startDate": start, "endDate": end, "subject": subject})
    response = _post_issue(context, payload)
    _check_response_status(response, 201)

@given('cоздана подзадача "{subject}" c датами "{start}", "{end}", родительская: "{parent}"')
@given('создана подзадача "{subject}" с датами "{start}", "{end}", родительская: "{parent}"')
@when('я создаю подзадачу "{subject}" с датами "{start}", "{end}", родительская: "{parent}"')
@when('я создаю подзадачу "{subject}" c датами "{start}", "{end}", родительская: "{parent}"')
def step_create_subtask(context, subject, start, end, parent):
    parent_id = find_created_issue(context, parent)
    payload = create_task_payload(subject, start, end, parent_id)
    response = _post_issue(context, payload)
    _check_response_status(response, 201)


@then('задача "{subject}" имеет дату начала:"{start}", дату окончания:"{end}"')
def step_check_task_dates(context, subject, start, end):
    issue_id = find_created_issue(context, subject)
    context.api.get_issue(issue_id)
    issue = json_body(context)["issue"]
    assert issue is not None, f"Задача с id '{issue_id}' не найдена"
    issue_start, issue_end = get_issue_dates(issue)
    assert str(issue_start) == start, (
        f"startDate задачи '{subject}': ожидалось {start}, получено {issue_start}"
    )
    assert str(issue_end) == end, (
        f"endDate задачи '{subject}': ожидалось {end}, получено {issue_end}"
    )

@then('даты задачи равны "{start}" и "{end}"')
def step_check_last_issue_dates(context, start, end):
    issue = json_body(context)["issue"]
    issue_start, issue_end = get_issue_dates(issue)
    assert str(issue_start) == start, (
        f"startDate: ожидалось {start}, получено {issue_start}"
    )
    assert str(issue_end) == end, (
        f"endDate: ожидалось {end}, получено {issue_end}"
    )


@then('поле "issue.id" равно ID созданной задачи')
def step_created_issue_id(context):
    issue = json_body(context)["issue"]
    expected = getattr(context, "created_issue_id", None)

    assert expected is not None, "Сценарий ещё не создал задачу"
    assert issue["id"] == expected, (
        f"issue.id: ожидалось {expected}, получено {issue['id']}"
    )


@when("я удаляю задачу с ID {issue_id:d} с force")
def step_delete_issue_force(context, issue_id):
    context.api.delete_issue(issue_id, force=True)


@when("я удаляю задачу с ID {issue_id:d} без force")
def step_delete_issue_without_force(context, issue_id):
    context.api.delete_issue(issue_id, force=False)
