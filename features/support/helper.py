def _find_issue(context, subject):
    response = context.api.get_issues()
    assert response.status_code == 200, (
        f"Не удалось получить список задач: {response.status_code}: {response.text}"
    )
    body = response.json()
    issues = body.get("issues") or []
    for issue in issues:
        if issue.get("subject") == subject:
            return issue
    return None


def _find_issue_id(context, subject):
    issue = _find_issue(context, subject)
    assert issue is not None, f"Задача с названием '{subject}' не найдена"
    return issue["id"]
