"""Шаги для авторизации и режима проверки токена."""

from behave import given, when

from support.data import json_body


@given("сервис требует токен")
def step_require_auth(context):
    context.api.set_auth_required(True)


@given("сервис не требует токен")
def step_do_not_require_auth(context):
    context.api.set_auth_required(False)


@when('я авторизуюсь с логином "{username}" и паролем "{password}"')
def step_login(context, username, password):
    context.api.login(username, password)
    if context.api.last_response.status_code == 200:
        context.api.token = json_body(context)["access_token"]


@when('я авторизуюсь с логином "{username}" и пустым паролем')
def step_login_with_empty_password(context, username):
    context.api.login(username, "")
