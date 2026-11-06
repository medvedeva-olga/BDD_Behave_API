"""Шаги для служебных эндпоинтов мока."""

from behave import then, when

from support.data import json_body


@when("я запрашиваю здоровье сервиса")
def step_health(context):
    context.api.health()


@when("я запрашиваю состояние мока")
def step_state(context):
    context.api.state()


@when("я сбрасываю состояние мока")
def step_reset(context):
    context.api.reset()


@when("я очищаю состояние мока")
def step_clear(context):
    context.api.clear_state()


@then("количество задач в состоянии мока равно {count:d}")
def step_state_issues_count(context, count):
    body = json_body(context)
    assert len(body["issues"]) == count, (
        f"В состоянии {len(body['issues'])} задач, ожидалось {count}"
    )


@then("состояние мока содержит задачу с ID {issue_id:d}")
def step_state_has_issue(context, issue_id):
    body = json_body(context)
    issue_ids = [issue["id"] for issue in body["issues"]]

    assert issue_id in issue_ids, f"В состоянии мока нет задачи {issue_id}: {issue_ids}"


@then("количество связей в состоянии мока равно {count:d}")
def step_state_relations_count(context, count):
    body = json_body(context)
    assert len(body["relations"]) == count, (
        f"В состоянии {len(body['relations'])} связей, ожидалось {count}"
    )
