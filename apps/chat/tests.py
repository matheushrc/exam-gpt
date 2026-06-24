import json
import os
import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

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


class ChatMessageViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_post_with_empty_message_returns_400(self):
        response = self.client.post("/api/chat/", {"message": ""}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_with_missing_message_returns_400(self):
        response = self.client.post("/api/chat/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    @mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @mock.patch("apps.chat.views.GoogleAgent")
    @mock.patch("apps.chat.views.search")
    def test_post_with_grounding_calls_retrieve_tool(
        self, mock_search, mock_google_agent
    ):
        mock_search.return_value = []

        mock_result = mock.Mock()
        mock_result.output = "Resposta gerada pelo modelo."
        mock_result.all_messages_json.return_value = b"[]"

        async def fake_get_inference_async(agent, user_prompt, **kwargs):
            # Simulate the model deciding to call the retrieve_exams tool.
            for tool in agent.kwargs.get("tools") or []:
                tool.function("O que é recursão?")
            return mock_result

        mock_client = mock.Mock()
        mock_client.get_inference_async = fake_get_inference_async

        def fake_create_agent(**kwargs):
            agent = mock.Mock()
            agent.kwargs = kwargs
            return agent

        mock_client.create_agent = fake_create_agent
        mock_google_agent.return_value = mock_client

        response = self.client.post(
            "/api/chat/", {"message": "O que é recursão?"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["query"], "O que é recursão?")
        self.assertEqual(response.data["answer"], "Resposta gerada pelo modelo.")
        self.assertEqual(response.data["sources"], [])
        mock_search.assert_called_once()

    @mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @mock.patch("apps.chat.views.GoogleAgent")
    @mock.patch("apps.chat.views.search")
    def test_post_without_grounding_never_calls_search(
        self, mock_search, mock_google_agent
    ):
        mock_result = mock.Mock()
        mock_result.output = "Resposta gerada pelo modelo."
        mock_result.all_messages_json.return_value = b"[]"

        async def fake_get_inference_async(**kwargs):
            return mock_result

        mock_client = mock.Mock()
        mock_client.get_inference_async = fake_get_inference_async
        mock_client.create_agent = mock.Mock(return_value=mock.Mock())
        mock_google_agent.return_value = mock_client

        response = self.client.post(
            "/api/chat/",
            {"message": "O que é recursão?", "grounding": False},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sources"], [])
        mock_search.assert_not_called()


class ChatShellResponsiveTests(TestCase):
    def test_chat_page_renders_mobile_sidebar_and_panel_hooks(self):
        response = self.client.get("/")
        html = response.content.decode("utf-8")

        self.assertIn('id="sidebar-mobile-toggle"', html)
        self.assertIn('aria-label="Abrir menu"', html)
        self.assertIn('id="sidebar-mobile-close"', html)
        self.assertIn('aria-label="Fechar menu"', html)
        self.assertIn('aria-controls="sidebar"', html)

    def test_transcript_script_treats_chat_header_as_optional(self):
        response = self.client.get("/")
        html = response.content.decode("utf-8")
        transcript = Path("apps/chat/static/chat/js/transcript.js").read_text()

        self.assertNotIn('id="chat-title"', html)
        self.assertNotIn('id="chat-subtitle"', html)
        self.assertNotIn("function setChatHeader()", transcript)
        self.assertNotIn("chat-title", transcript)
        self.assertNotIn("chat-subtitle", transcript)

    def test_right_panel_close_button_is_removed(self):
        response = self.client.get("/")
        html = response.content.decode("utf-8")
        self.assertNotIn('id="right-panel-close"', html)

    def test_references_js_exposes_build_sources_section(self):
        references = Path("apps/chat/static/chat/js/references.js").read_text()
        self.assertIn("buildSourcesSection", references)
        self.assertIn("window.PGReferences", references)

    def test_transcript_js_delegates_card_building_to_references(self):
        transcript = Path("apps/chat/static/chat/js/transcript.js").read_text()
        self.assertNotIn("buildQuestaoCard", transcript)
        self.assertIn("PGReferences.buildSourcesSection", transcript)

    def test_serialize_sources_includes_similarity_tier(self):
        from apps.chat.views import _serialize_sources
        from unittest.mock import Mock
        questao = Mock()
        questao.id = "60a8f8888888888888888888"
        questao.ordem = 1
        questao.enunciado = "Teste"
        questao.subquestoes = []
        questao.resposta = "Teste resposta"
        questao.pontuacao = 1.0
        questao.nota_recebida = 1.0
        questao.provas_resolved = []
        
        res_high = _serialize_sources([(0.90, questao)])
        res_medium = _serialize_sources([(0.75, questao)])
        res_low = _serialize_sources([(0.50, questao)])
        
        self.assertEqual(res_high[0]["similarity_tier"], "high")
        self.assertEqual(res_medium[0]["similarity_tier"], "medium")
        self.assertEqual(res_low[0]["similarity_tier"], "low")

