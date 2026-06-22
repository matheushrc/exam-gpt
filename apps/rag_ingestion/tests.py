import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase
from django.test import TestCase
import numpy as np
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel
from turbovec import IdMapIndex

from apps.rag_ingestion.agents.Google import GoogleAgent
from apps.rag_ingestion.extract import _make_agent
from apps.rag_ingestion.models import Chunks, Prova, Questao
from apps.rag_ingestion.embed import (
    DEFAULT_JSON_ROOT,
    build_chunk,
    find_exam_json_files,
    load_exam_json,
)
from apps.rag_ingestion.settings import embeddings_settings
from apps.rag_ingestion.vector_index import remove_turbo_ids


class ExamJsonDiscoveryTests(SimpleTestCase):
    def test_find_exam_json_files_recursively(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "redes-de-computadores"
            nested.mkdir()
            expected = nested / "2026-05-04_np1_professor.json"
            expected.write_text("{}", encoding="utf-8")
            (nested / "ignored.txt").write_text("ignored", encoding="utf-8")

            self.assertEqual(find_exam_json_files(root), [expected])

    def test_default_json_root_uses_converted_provas(self):
        self.assertEqual(DEFAULT_JSON_ROOT.name, "converted_provas")

    def test_load_exam_json_requires_questoes_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "invalid.json"
            json_path.write_text(json.dumps({"materia": "Redes"}), encoding="utf-8")

            with self.assertRaisesMessage(ValueError, "has no questoes list"):
                load_exam_json(json_path)


class ChunkFormattingTests(SimpleTestCase):
    def test_build_chunk_includes_subquestions_and_answer(self):
        chunk = build_chunk(
            materia="Redes de Computadores",
            numero=1,
            enunciado="Explique roteamento.",
            subquestoes=[{"label": "(a)", "enunciado": "Defina rota."}],
            resposta="Roteamento escolhe caminhos.",
        )

        self.assertIn("Redes de Computadores - Questão 1", chunk)
        self.assertIn("(a) Defina rota.", chunk)
        self.assertIn("Gabarito/Resposta esperada: Roteamento escolhe caminhos.", chunk)


class VectorIndexRemovalTests(SimpleTestCase):
    def test_remove_turbo_ids_is_noop_without_index_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            remove_turbo_ids([1, 2], index_path=Path(tmpdir) / "missing.tvim")

    def test_remove_turbo_ids_removes_ids_from_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "index.tvim"
            index = IdMapIndex(dim=8, bit_width=4)
            index.add_with_ids(
                np.ones((2, 8), dtype=np.float32),
                np.array([10, 11], dtype=np.uint64),
            )
            index.write(str(index_path))

            remove_turbo_ids([10], index_path=index_path)

            updated_index = IdMapIndex.load(str(index_path))
            self.assertFalse(updated_index.contains(10))
            self.assertTrue(updated_index.contains(11))


class ProvaDeleteCleanupTests(TestCase):
    @patch("apps.rag_ingestion.signals.remove_turbo_ids")
    def test_delete_prova_removes_orphan_questions_and_chunks(self, remove_mock):
        questao = Questao.objects.create(
            numero=1,
            enunciado="Explique DNS.",
            subquestoes=[],
            resposta=None,
            pontuacao=1.0,
        )
        prova = Prova.objects.create(
            professor="Professor",
            cursos=[],
            materia="Redes de Computadores",
            ano_semestre="2026.1",
            data_aplicacao="2026-05-04",
            numero_avaliacao=1,
        )
        prova.questoes.add(questao)
        Chunks.objects.create(id_questao=questao, turbo_id=42)

        prova.delete()

        self.assertEqual(Prova.objects.count(), 0)
        self.assertEqual(Questao.objects.count(), 0)
        self.assertEqual(Chunks.objects.count(), 0)
        remove_mock.assert_called_once_with([42])


class ProvaQuestaoNovosCamposTests(TestCase):
    def test_prova_nota_final_defaults_to_none(self):
        prova = Prova.objects.create(
            professor="Prof",
            cursos=[],
            materia="Redes",
            ano_semestre="2026.1",
            data_aplicacao="2026-05-04",
            numero_avaliacao=1,
        )
        self.assertIsNone(prova.nota_final)

    def test_prova_recuperacao_defaults_to_false(self):
        prova = Prova.objects.create(
            professor="Prof",
            cursos=[],
            materia="Redes",
            ano_semestre="2026.1",
            data_aplicacao="2026-05-04",
            numero_avaliacao=1,
        )
        self.assertFalse(prova.recuperacao)

    def test_questao_nota_recebida_defaults_to_none(self):
        questao = Questao.objects.create(numero=1, enunciado="X", pontuacao=2.0)
        self.assertIsNone(questao.nota_recebida)

    def test_ano_semestre_schema_validation(self):
        from apps.rag_ingestion.schemas.prova import Prova as ProvaSchema
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            ProvaSchema(
                professor="P",
                materia="M",
                ano_semestre="1",
                data_aplicacao="2026-01-01",
                numero_avaliacao=1,
                questoes=[],
            )

        p = ProvaSchema(
            professor="P",
            materia="M",
            ano_semestre="2026.1",
            data_aplicacao="2026-01-01",
            numero_avaliacao=1,
            questoes=[],
        )
        self.assertEqual(p.ano_semestre, "2026.1")


class GoogleAgentFallbackTests(SimpleTestCase):
    def test_create_agent_without_fallback_uses_plain_google_model(self):
        client = GoogleAgent(api_key="fake-key")
        agent = client.create_agent(model_name="gemini-3.5-flash")
        self.assertIsInstance(agent.model, GoogleModel)
        self.assertEqual(agent.model.model_name, "gemini-3.5-flash")

    def test_create_agent_with_fallback_wraps_in_fallback_model(self):
        client = GoogleAgent(api_key="fake-key")
        agent = client.create_agent(
            model_name="gemini-3.5-flash",
            fallback_model_names=["gemini-3.1-flash-lite"],
        )
        self.assertIsInstance(agent.model, FallbackModel)
        model_names = [m.model_name for m in agent.model.models]
        self.assertEqual(model_names, ["gemini-3.5-flash", "gemini-3.1-flash-lite"])


class ExtractionAgentFallbackTests(SimpleTestCase):
    def test_make_agent_falls_back_to_flash_lite(self):
        client = GoogleAgent(api_key="fake-key")
        agent = _make_agent(client, "gemini-3.5-flash")
        self.assertIsInstance(agent.model, FallbackModel)
        model_names = [m.model_name for m in agent.model.models]
        self.assertEqual(
            model_names,
            ["gemini-3.5-flash", embeddings_settings.EXTRACTION_FALLBACK_MODEL],
        )

    def test_extraction_fallback_model_setting_defaults_to_flash_lite(self):
        self.assertEqual(
            embeddings_settings.EXTRACTION_FALLBACK_MODEL, "gemini-3.1-flash-lite"
        )
