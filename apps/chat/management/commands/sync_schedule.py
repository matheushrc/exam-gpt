import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

HORARIO_ENDPOINT = "https://cc.uffs.edu.br/horario/"
GROUPS_ENDPOINT = "https://cc.uffs.edu.br/horario/data/{semester}/groups.json"
SCHEDULE_ENDPOINT = "https://cc.uffs.edu.br/horario/data/{semester}/schedule.json"

CACHE_ROOT = Path("cache/schedule")


class Command(BaseCommand):
    help = "Download and cache UFFS schedule data locally."

    def add_arguments(self, parser):
        parser.add_argument(
            "--semester",
            type=str,
            default=None,
            help="Sync only this semester (e.g. 2024.1). Defaults to all semesters.",
        )

    def handle(self, *args, **options):
        semester = options.get("semester")

        semesters = self._fetch_semesters()
        CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        with (CACHE_ROOT / "semesters.json").open("w", encoding="utf-8") as f:
            json.dump(semesters, f, ensure_ascii=False)
        self.stdout.write(f"Saved {len(semesters)} semesters to {CACHE_ROOT / 'semesters.json'}")

        target_semesters = [semester] if semester else semesters

        for sem in target_semesters:
            self._sync_semester(sem)

    def _fetch_semesters(self) -> list[str]:
        self.stdout.write(f"Fetching semesters from {HORARIO_ENDPOINT}")
        response = requests.get(HORARIO_ENDPOINT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        select = soup.find("select", id="semester")
        if select is None:
            return []
        return [
            option.get("value") or option.text.strip()
            for option in select.find_all("option")
        ]

    def _sync_semester(self, semester: str) -> None:
        semester_dir = CACHE_ROOT / semester
        semester_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"Syncing semester {semester}")

        groups_url = GROUPS_ENDPOINT.format(semester=semester)
        groups_response = requests.get(groups_url)
        groups_response.raise_for_status()
        groups = groups_response.json()
        with (semester_dir / "groups.json").open("w", encoding="utf-8") as f:
            json.dump(groups, f, ensure_ascii=False)
        self.stdout.write(f"  Saved {len(groups)} groups to {semester_dir / 'groups.json'}")

        schedule_url = SCHEDULE_ENDPOINT.format(semester=semester)
        schedule_response = requests.get(schedule_url)
        schedule_response.raise_for_status()
        schedule = schedule_response.json()
        with (semester_dir / "schedule.json").open("w", encoding="utf-8") as f:
            json.dump(schedule, f, ensure_ascii=False)
        self.stdout.write(f"  Saved {len(schedule)} schedule entries to {semester_dir / 'schedule.json'}")
