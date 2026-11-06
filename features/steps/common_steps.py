"""Универсальные проверки ответов Tasks API."""

import logging

from behave import given, then
from jsonschema import ValidationError, validate

from models.schemas import SCHEMAS
from support.data import json_body, pretty, resolve

logger = logging.getLogger("tasks.steps.common")


@given("мок находится в начальном состоянии")
def step_initial_state(context):
    """Явный сброс: сценарий не зависит от предыдущих."""
    context.api.reset()
    context.api.set_auth_required(False)


@then("статус ответа равен {status:d}")
def step_status(context, status):
    response = context.api.last_response
    assert response is not None, "Запрос ещё не выполнялся"

    assert response.status_code == status, (
        f"Ожидался статус {status}, получен {response.status_code}. "
        f"Тело: {response.text}"
    )


@then('ответ соответствует схеме "{name}"')
def step_schema(context, name):
    schema = SCHEMAS.get(name)
    assert schema is not None, f"Неизвестная схема: {name}"

    body = json_body(context)
    try:
        validate(instance=body, schema=schema)
    except ValidationError as error:
        path = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise AssertionError(
            f"Ответ не соответствует схеме '{name}' "
            f"(поле {path}): {error.message}\n{pretty(body)}"
        ) from error


@then('поле "{path}" равно "{expected}"')
def step_field_string(context, path, expected):
    body = json_body(context)
    try:
        actual = resolve(body, path)
    except (KeyError, IndexError, TypeError) as error:
        raise AssertionError(
            f"В ответе нет поля '{path}': {error}\n{pretty(body)}"
        ) from error

    assert actual == expected, (
        f"Поле '{path}': ожидалось {expected!r}, получено {actual!r}"
    )


@then('поле "{path}" равно null')
def step_field_null(context, path):
    body = json_body(context)
    try:
        actual = resolve(body, path)
    except (KeyError, IndexError, TypeError) as error:
        raise AssertionError(
            f"В ответе нет поля '{path}': {error}\n{pretty(body)}"
        ) from error

    assert actual is None, f"Поле '{path}': ожидался null, получено {actual!r}"


@then('поле "{path}" равно числу {expected:d}')
def step_field_int(context, path, expected):
    body = json_body(context)
    try:
        actual = resolve(body, path)
    except (KeyError, IndexError, TypeError) as error:
        raise AssertionError(
            f"В ответе нет поля '{path}': {error}\n{pretty(body)}"
        ) from error

    assert actual == expected, (
        f"Поле '{path}': ожидалось {expected}, получено {actual!r}"
    )


@then('сообщение об ошибке содержит "{text}"')
def step_error_message(context, text):
    body = json_body(context)
    message = body.get("message", "")
    assert text in message, (
        f"В сообщении об ошибке нет подстроки {text!r}: {message!r}"
    )


@then("тело ответа содержит ID новой задачи")
def step_new_issue_id(context):
    body = json_body(context)
    assert isinstance(body, int), (
        "Ожидалось голое число (id) в теле ответа, "
        f"получено {type(body).__name__}: {body!r}"
    )
    assert body > 0, f"ID новой задачи должен быть положительным: {body}"

    context.created_issue_id = body


@then("тело ответа содержит ID {expected:d}")
def step_body_id(context, expected):
    body = json_body(context)
    assert body == expected, f"Ожидался id {expected} в теле ответа, получено {body!r}"
