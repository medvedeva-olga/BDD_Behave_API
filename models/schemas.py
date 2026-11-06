"""JSON Schema ответов мокового Tasks API."""

ISSUE_SCHEMA = {
    "type": "object",
    "required": [
        "id",
        "projectId",
        "trackerId",
        "statusId",
        "priority",
        "subject",
        "parentIssue",
        "standards",
    ],
    "properties": {
        "id": {"type": "integer"},
        "projectId": {"type": "integer"},
        "trackerId": {"type": "integer"},
        "statusId": {"type": "integer"},
        "priority": {"type": "integer"},
        "subject": {"type": "string"},
        "parentIssue": {"type": ["integer", "null"]},
        "standards": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["fieldId", "valueId"],
                "properties": {
                    "fieldId": {"enum": ["startDate", "endDate"]},
                    "valueId": {"type": ["string", "null"]},
                },
            },
        },
    },
}

ISSUE_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["issue"],
    "properties": {"issue": ISSUE_SCHEMA},
}

CHILD_ROW_SCHEMA = {
    "type": "object",
    "required": ["rowId", "subject"],
    "properties": {
        "rowId": {"type": "integer"},
        "subject": {"type": "string"},
    },
}

CHILDREN_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["rows", "count"],
    "properties": {
        "rows": {"type": "array", "items": CHILD_ROW_SCHEMA},
        "count": {"type": "integer"},
    },
}

RELATION_SCHEMA = {
    "type": "object",
    "required": ["id", "issueId", "relatedIssueId", "relationType", "delay"],
    "properties": {
        "id": {"type": "integer"},
        "issueId": {"type": "integer"},
        "relatedIssueId": {"type": "integer"},
        "relationType": {"type": "string"},
        "delay": {"type": "integer"},
    },
}

ERROR_SCHEMA = {
    "type": "object",
    "required": ["statusCode", "message"],
    "properties": {
        "statusCode": {"type": "integer"},
        "message": {"type": "string"},
    },
}

LOGIN_SCHEMA = {
    "type": "object",
    "required": ["access_token", "token_type", "expires_in"],
    "properties": {
        "access_token": {"type": "string"},
        "token_type": {"type": "string"},
        "expires_in": {"type": "integer"},
    },
}

HEALTH_SCHEMA = {
    "type": "object",
    "required": ["status"],
    "properties": {"status": {"const": "ok"}},
}

STATE_SCHEMA = {
    "type": "object",
    "required": ["issues", "relations"],
    "properties": {
        "issues": {"type": "array", "items": ISSUE_SCHEMA},
        "relations": {"type": "array", "items": RELATION_SCHEMA},
    },
}

SCHEMAS = {
    "issue": ISSUE_SCHEMA,
    "issue_response": ISSUE_RESPONSE_SCHEMA,
    "children_response": CHILDREN_RESPONSE_SCHEMA,
    "relation": RELATION_SCHEMA,
    "error": ERROR_SCHEMA,
    "login": LOGIN_SCHEMA,
    "health": HEALTH_SCHEMA,
    "state": STATE_SCHEMA,
}
