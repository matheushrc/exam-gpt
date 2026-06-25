import csv
import json
from pathlib import Path

from apps.chat.settings import chat_settings

CACHE_ROOT = Path(chat_settings.CACHE_ROOT)
DOCENTES_CSV = Path(__file__).resolve().parents[2] / "datasets" / "docentes.csv"


def _load_docentes_mapping() -> dict[str, str]:
    mapping = {}
    csv_path = DOCENTES_CSV
    if not csv_path.exists():
        return mapping
    try:
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # Pula o cabeçalho
            for row in reader:
                if len(row) >= 2:
                    nome = row[0].strip()
                    email = row[1].strip()
                    if email and nome:
                        username = email.split("@")[0].lower()
                        mapping[username] = nome.title()
    except Exception:
        pass
    return mapping

DOCENTES_NAMES = _load_docentes_mapping()


def _professor_option(username: str) -> dict:
    return {
        "username": username,
        "name": DOCENTES_NAMES.get(username, username.replace(".", " ").title()),
    }


def get_all_professors() -> list[dict]:
    return sorted(
        (
            {"username": username, "name": name}
            for username, name in DOCENTES_NAMES.items()
        ),
        key=lambda professor: professor["name"],
    )


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
        (_professor_option(username) for username in usernames),
        key=lambda professor: professor["name"],
    )


def get_professors_for_materia(semester: str, materia: str) -> list[dict]:
    usernames = set()
    materia_lower = materia.lower()
    for entry in get_schedule(semester):
        if materia_lower in entry.get("name", "").lower():
            usernames.update(entry.get("members", []))
    return sorted(
        (_professor_option(username) for username in usernames),
        key=lambda professor: professor["name"],
    )


def get_materias_for_semester(semester: str) -> list[str]:
    names = {entry["name"] for entry in get_schedule(semester) if entry.get("name")}
    return sorted(names)
