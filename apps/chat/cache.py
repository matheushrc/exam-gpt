import json
from pathlib import Path

from apps.chat.settings import chat_settings

CACHE_ROOT = Path(chat_settings.CACHE_ROOT)


def get_semesters() -> list[str]:
    path = CACHE_ROOT / "semesters.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_groups(semester: str) -> list[dict]:
    path = CACHE_ROOT / semester / "groups.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_schedule(semester: str, group: int | None = None) -> list[dict]:
    path = CACHE_ROOT / semester / "schedule.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        entries = json.load(f)
    if group is not None:
        entries = [entry for entry in entries if entry.get("group") == group]
    return entries


def get_professors_for_semester(semester: str) -> list[dict]:
    usernames = set()
    for entry in get_schedule(semester):
        usernames.update(entry.get("members", []))
    return sorted(
        (
            {"username": username, "name": username.replace(".", " ").title()}
            for username in usernames
        ),
        key=lambda professor: professor["name"],
    )


def get_professors_for_materia(semester: str, materia: str) -> list[dict]:
    usernames = set()
    materia_lower = materia.lower()
    for entry in get_schedule(semester):
        if materia_lower in entry.get("name", "").lower():
            usernames.update(entry.get("members", []))
    return sorted(
        (
            {"username": username, "name": username.replace(".", " ").title()}
            for username in usernames
        ),
        key=lambda professor: professor["name"],
    )


def get_materias_for_semester(semester: str) -> list[str]:
    names = {entry["name"] for entry in get_schedule(semester) if entry.get("name")}
    return sorted(names)
