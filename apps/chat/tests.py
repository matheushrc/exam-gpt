import json
import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.chat import cache


class CacheTests(TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.cache_root = Path(self._tmpdir.name)
        self._patcher = mock.patch.object(cache, "CACHE_ROOT", self.cache_root)
        self._patcher.start()
        self.addCleanup(self._patcher.stop)
        self.addCleanup(self._tmpdir.cleanup)

    def test_get_semesters_returns_empty_list_when_cache_file_missing(self):
        self.assertEqual(cache.get_semesters(), [])

    def test_get_professors_for_materia_filters_correctly(self):
        semester = "2024.1"
        semester_dir = self.cache_root / semester
        semester_dir.mkdir(parents=True, exist_ok=True)

        schedule = [
            {
                "name": "Algoritmos e Programacao",
                "group": 1,
                "members": ["joao.silva", "maria.souza"],
            },
            {
                "name": "Banco de Dados",
                "group": 1,
                "members": ["pedro.santos"],
            },
            {
                "name": "Algoritmos Avancados",
                "group": 2,
                "members": ["maria.souza"],
            },
        ]
        with (semester_dir / "schedule.json").open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        professors = cache.get_professors_for_materia(semester, "algoritmos")

        usernames = {professor["username"] for professor in professors}
        self.assertEqual(usernames, {"joao.silva", "maria.souza"})
        # banco de dados professor must not be included
        self.assertNotIn("pedro.santos", usernames)
        # results sorted by name
        self.assertEqual(
            [professor["name"] for professor in professors],
            sorted(professor["name"] for professor in professors),
        )


class SyncScheduleCommandTests(TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.cache_root = Path(self._tmpdir.name) / "cache" / "schedule"
        self.addCleanup(self._tmpdir.cleanup)

    def test_sync_schedule_writes_expected_files(self):
        from apps.chat.management.commands import sync_schedule

        semesters_html = """
        <html>
        <body>
            <select name="semester" id="semester">
                <option value="2024.1">2024.1</option>
                <option value="2024.2">2024.2</option>
            </select>
        </body>
        </html>
        """

        groups_payload = [{"group": 1, "name": "Group 1"}]
        schedule_payload = [
            {"name": "Algoritmos", "group": 1, "members": ["joao.silva"]},
        ]

        def fake_get(url, *args, **kwargs):
            response = mock.Mock()
            response.raise_for_status = mock.Mock()
            if url == sync_schedule.HORARIO_ENDPOINT:
                response.text = semesters_html
            elif url == sync_schedule.GROUPS_ENDPOINT.format(semester="2024.1"):
                response.json = mock.Mock(return_value=groups_payload)
            elif url == sync_schedule.SCHEDULE_ENDPOINT.format(semester="2024.1"):
                response.json = mock.Mock(return_value=schedule_payload)
            else:
                response.json = mock.Mock(return_value=[])
            return response

        with mock.patch.object(sync_schedule, "CACHE_ROOT", self.cache_root):
            with mock.patch.object(sync_schedule, "requests") as requests_mock:
                requests_mock.get.side_effect = fake_get
                call_command("sync_schedule", "--semester", "2024.1")

            semesters_file = self.cache_root / "semesters.json"
            self.assertTrue(semesters_file.exists())
            with semesters_file.open(encoding="utf-8") as f:
                self.assertEqual(json.load(f), ["2024.1", "2024.2"])

            groups_file = self.cache_root / "2024.1" / "groups.json"
            self.assertTrue(groups_file.exists())
            with groups_file.open(encoding="utf-8") as f:
                self.assertEqual(json.load(f), groups_payload)

            schedule_file = self.cache_root / "2024.1" / "schedule.json"
            self.assertTrue(schedule_file.exists())
            with schedule_file.open(encoding="utf-8") as f:
                self.assertEqual(json.load(f), schedule_payload)
