"""Константы путей API Tasks."""

HEALTH = "/health"
ISSUES = "/api/issues"
ISSUE_BY_ID = "/api/issues/{issue_id}"
ISSUE_CHILDREN = "/api/issues/{issue_id}/children"
ISSUE_RELATED = "/api/issues/{issue_id}/related"
AUTH_LOGIN = "/api/auth/login"
ADMIN_STATE = "/__admin/state"
ADMIN_RESET = "/__admin/reset"
ADMIN_RESET_EMPTY = "/__admin/reset?empty=true"
ADMIN_CONFIG = "/__admin/config"


def admin_config_path(require_auth: bool) -> str:
    """Путь служебного эндпоинта переключения проверки токена."""
    value = "true" if require_auth else "false"
    return f"{ADMIN_CONFIG}?require_auth={value}"
