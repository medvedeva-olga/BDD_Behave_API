"""Шаги для дочерних задач и связей между задачами."""

from behave import then, when

from support.data import json_body
from support.cleanup import find_created_issue


@when("я запрашиваю дочерние задачи для ID {issue_id:d}")
def step_get_children(context, issue_id):
    context.api.get_children(issue_id)


@then("количество детей равно {count:d}")
def step_children_count(context, count):
    body = json_body(context)
    assert body["count"] == count, (
        f"count: ожидалось {count}, получено {body['count']} ({body['rows']})"
    )
    assert len(body["rows"]) == count, (
        f"В rows {len(body['rows'])} элементов, а count={count}"
    )


@then("список детей содержит ID {child_id:d}")
def step_children_contains(context, child_id):
    rows = json_body(context)["rows"]
    row_ids = [row["rowId"] for row in rows]

    assert child_id in row_ids, f"В списке детей нет ID {child_id}: {row_ids}"


@then("список детей содержит созданную задачу")
def step_children_contains_created(context):
    created = getattr(context, "created_issue_id", None)
    assert created is not None, "Сценарий ещё не создал задачу"

    rows = json_body(context)["rows"]
    row_ids = [row["rowId"] for row in rows]

    assert created in row_ids, f"Созданной задачи {created} нет среди детей: {row_ids}"


@when('я связываю задачу {issue_id:d} с задачей {related_id:d} как "{relation_type}"')
def step_create_relation(context, issue_id, related_id, relation_type):
    context.api.create_relation(issue_id, related_id, relation_type)


@then("связь соединяет задачи {issue_id:d} и {related_id:d}")
def step_relation_links(context, issue_id, related_id):
    body = json_body(context)
    assert body["issueId"] == issue_id, (
        f"issueId: ожидалось {issue_id}, получено {body['issueId']}"
    )
    assert body["relatedIssueId"] == related_id, (
        f"relatedIssueId: ожидалось {related_id}, получено {body['relatedIssueId']}"
    )


@when('я связываю задачу "{a}" с задачей "{b}" как "{relation_type}"')
def step_link_tasks(context, a, b, relation_type):
    issue_id = find_created_issue(context, a)
    related_id = find_created_issue(context, b)
    context.api.create_relation(issue_id, related_id, relation_type)