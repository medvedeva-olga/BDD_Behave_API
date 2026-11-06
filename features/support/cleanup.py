"""Уборка созданных сущностей после сценария."""

import logging

logger = logging.getLogger("tasks.cleanup")


def register_created_issue(context, issue_id, subject = None):
    """Запомнить ID задачи, созданной сценарием, для удаления в after_scenario + связывание subject  с id"""
    if not isinstance(issue_id, int) or isinstance(issue_id, bool) or issue_id <= 0:
        return

    if not hasattr(context, "created_issues_map"):
        context.created_issues_map = {}

    issue_ids = getattr(context, "created_issue_ids", None)
    if issue_ids is None:
        issue_ids = context.created_issue_ids = []

    if issue_id not in issue_ids:
        issue_ids.append(issue_id)
        logger.debug("Создана задача %s: добавлена в очередь на очистку", issue_id)

    # Запоминаем связь с именем (если имя передано)
    if subject:
        context.created_issues_map[subject] = issue_id
        logger.debug("Связь сохранена: '%s' <-> ID %s", subject, issue_id)

def find_created_issue(context, subject):
    """Получить id созданной задачи по ее subject  из памяти теста"""
    try:
        issue_id = context.created_issues_map[subject]
    except (AttributeError, KeyError) as exc:
        raise KeyError(f"Задача '{subject}' не найдена в памяти теста!") from exc
    return issue_id

def cleanup_created_issues(context):
    """Удалить задачи, созданные сценарием.

    Уборка не должна ронять прогон: 404 (задачу уже удалили или сбросили
    состояние) считается нормой, остальные ошибки только логируются.
    Задачи удаляются в обратном порядке — сначала дочерние, потом родитель.
    """
    api = getattr(context, "api", None)
    issue_ids = list(getattr(context, "created_issue_ids", None) or [])
    context.created_issue_ids = []

    if api is None or not issue_ids:
        return

    # Сценарий мог оставить включённой проверку токена и без валидного токена.
    # Для уборки это не важно, поэтому принудительно выключаем режим.
    try:
        api.set_auth_required(False)
    except Exception as error:  # noqa: BLE001 - уборка не должна падать
        logger.warning("Не удалось выключить проверку токена перед очисткой: %s", error)

    for issue_id in reversed(issue_ids):
        try:
            response = api.delete_issue(issue_id, force=True)
        except Exception as error:  # noqa: BLE001 - уборка не должна падать
            logger.warning("Не удалось удалить задачу %s: %s", issue_id, error)
            continue

        if response.status_code == 200:
            logger.info("Очистка: задача %s удалена", issue_id)
        elif response.status_code == 404:
            logger.debug("Очистка: задача %s уже удалена", issue_id)
        else:
            logger.warning(
                "Очистка: задачу %s удалить не удалось (%s): %s",
                issue_id,
                response.status_code,
                response.text,
            )
