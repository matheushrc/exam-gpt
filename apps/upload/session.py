"""Helpers to read/write upload wizard state in Django sessions."""

import uuid
from typing import Any

SESSION_KEY = "upload_wizard"


def new_session_id() -> str:
    return str(uuid.uuid4())


def get_wizard_data(request, session_id: str) -> dict[str, Any]:
    wizard = request.session.get(SESSION_KEY, {})
    return wizard.get(session_id, {})


def set_wizard_data(request, session_id: str, data: dict[str, Any]) -> None:
    wizard = request.session.get(SESSION_KEY, {})
    wizard[session_id] = data
    request.session[SESSION_KEY] = wizard
    request.session.modified = True


def clear_wizard_data(request, session_id: str) -> None:
    wizard = request.session.get(SESSION_KEY, {})
    wizard.pop(session_id, None)
    request.session[SESSION_KEY] = wizard
    request.session.modified = True
