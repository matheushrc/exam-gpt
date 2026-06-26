import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.test import TestCase
import numpy as np
from loguru import logger
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel
from turbovec import IdMapIndex

from apps.rag_ingestion.agents.Google import GoogleAgent
from apps.rag_ingestion.extract import _make_agent
from apps.rag_ingestion.markdown_normalize import normalize_extracted_markdown
from apps.rag_ingestion.prompts.prova import EXAM_PROMPT
from apps.rag_ingestion.schemas.prova import Questao as SchemaQuestao
from apps.rag_ingestion.models import Chunks, Prova, Questao
from apps.rag_ingestion.embed import (
    DEFAULT_JSON_ROOT,
    _resolve_professor,
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
            ordem=1,
            enunciado="Explique roteamento.",
            subquestoes=[{"enunciado": "Defina rota."}],
            resposta="Roteamento escolhe caminhos.",
        )

        self.assertIn("Redes de Computadores - Questão 1", chunk)
        self.assertIn("Defina rota.", chunk)
        self.assertIn("Gabarito/Resposta esperada: Roteamento escolhe caminhos.", chunk)


class MarkdownNormalizeTests(SimpleTestCase):
    def test_preserves_brazilian_currency_markers(self):
        text = "A media amostral e de R$ 250,00, com desvio padrao de R$ 55,00."

        self.assertEqual(normalize_extracted_markdown(text), text)

    def test_converts_obvious_single_dollar_inline_math(self):
        text = "Calcule $x^2 + y$ e justifique."

        self.assertEqual(
            normalize_extracted_markdown(text),
            r"Calcule \(x^2 + y\) e justifique.",
        )

    def test_does_not_convert_display_math_blocks(self):
        text = "Use:\n$$\nx^2 + y\n$$\nDepois responda."

        self.assertEqual(normalize_extracted_markdown(text), text)

    def test_preserves_inline_code_spans(self):
        text = "Use o caminho `$HOME` antes de calcular $x+1$."

        self.assertEqual(
            normalize_extracted_markdown(text),
            r"Use o caminho `$HOME` antes de calcular \(x+1\).",
        )

    def test_preserves_fenced_code_blocks_with_dollar_pairs(self):
        text = "Exemplo:\n```bash\nexport PATH=\"$HOME/bin:$PATH\"\n```\nDepois calcule $x+1$."

        self.assertEqual(
            normalize_extracted_markdown(text),
            "Exemplo:\n```bash\nexport PATH=\"$HOME/bin:$PATH\"\n```\nDepois calcule \\(x+1\\).",
        )

    def test_schema_normalizes_enunciado_and_resposta(self):
        questao = SchemaQuestao(
            enunciado="Resolva $x+1$ e considere R$ 10,00.",
            pontuacao=1.0,
            resposta="Resultado: $x=-1$.",
            nota_recebida=None,
            subquestoes=None,
        )

        self.assertEqual(questao.enunciado, r"Resolva \(x+1\) e considere R$ 10,00.")
        self.assertEqual(questao.resposta, r"Resultado: \(x=-1\).")


class ExtractionPromptMarkdownContractTests(SimpleTestCase):
    def test_prompt_requires_parenthesized_inline_latex(self):
        self.assertIn("\\(...\\)", EXAM_PROMPT)
        self.assertIn("nunca use $...$ para matemática inline", EXAM_PROMPT)

    def test_prompt_preserves_brazilian_currency_as_plain_text(self):
        self.assertIn("R$ 250,00", EXAM_PROMPT)
        self.assertIn("valor monetário", EXAM_PROMPT)


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
            ordem=1,
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
        questao = Questao.objects.create(ordem=1, enunciado="X", pontuacao=2.0)
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


class SeedExamJsonsLoggingTests(SimpleTestCase):
    @patch("apps.rag_ingestion.embed.rebuild_vector_index", return_value=2)
    @patch(
        "apps.rag_ingestion.embed.get_embeddings_batch",
        return_value=[[0.1], [0.2]],
    )
    @patch("apps.rag_ingestion.embed.upsert_exam")
    @patch("apps.rag_ingestion.embed.load_exam_json", return_value={"questoes": []})
    @patch("apps.rag_ingestion.embed.find_exam_json_files")
    def test_seed_exam_jsons_logs_via_loguru_not_print(
        self,
        find_mock,
        load_mock,
        upsert_mock,
        embeddings_mock,
        rebuild_mock,
    ):
        from apps.rag_ingestion.embed import seed_exam_jsons
        from settings.settings import BASE_DIR

        json_file = BASE_DIR / "input" / "converted_provas" / "calc.json"
        find_mock.return_value = [json_file]
        fake_prova = Mock(materia="CÁLCULO")
        upsert_mock.return_value = (fake_prova, ["q1"], ["chunk text"])

        records = []
        sink_id = logger.add(records.append, format="{message}")
        try:
            result = seed_exam_jsons(json_root=Path("unused"), client=Mock())
        finally:
            logger.remove(sink_id)

        messages = [r.record["message"] for r in records]
        self.assertIn(
            "Loaded input/converted_provas/calc.json -> CÁLCULO", messages
        )
        self.assertIn("Generating embeddings for 1 questions...", messages)
        self.assertEqual(result.chunks, 2)


class ProvaExtractAPIViewLoggingTests(TestCase):
    def test_post_extraction_failure_logs_via_loguru(self):
        async def failing_extract(*args, **kwargs):
            raise RuntimeError("boom")

        records = []
        sink_id = logger.add(records.append, format="{message}")
        try:
            with patch(
                "apps.rag_ingestion.views.extract_exam_from_images",
                side_effect=failing_extract,
            ):
                response = self.client.post(
                    "/api/provas/extract/",
                    data={"camera_images": ["aGVsbG8="]},
                    content_type="application/json",
                )
        finally:
            logger.remove(sink_id)

        self.assertEqual(response.status_code, 400)
        messages = [r.record["message"] for r in records]
        self.assertIn("Exam extraction failed: boom", messages)

        from apps.rag_ingestion import views as rag_views

        self.assertIs(rag_views.logger, logger)


class ResolveProfessorTests(SimpleTestCase):
    def test_email_resolved_from_docentes_csv(self):
        from apps.rag_ingestion.embed import _EMAIL_TO_NAME
        if _EMAIL_TO_NAME:
            email, name = next(iter(_EMAIL_TO_NAME.items()))
            self.assertEqual(_resolve_professor([email]), name)

    def test_unknown_email_falls_back_to_title_cased_username(self):
        self.assertEqual(_resolve_professor(["joao.silva@uffs.edu.br"]), "Joao Silva")

    def test_plain_string_is_returned_unchanged(self):
        self.assertEqual(_resolve_professor("Leandro Bordin"), "Leandro Bordin")

    def test_multiple_emails_joined_with_comma(self):
        result = _resolve_professor(["joao.silva@uffs.edu.br", "maria.souza@uffs.edu.br"])
        self.assertEqual(result, "Joao Silva, Maria Souza")

    def test_email_without_at_sign_treated_as_username(self):
        self.assertEqual(_resolve_professor(["joao.silva"]), "Joao Silva")

    def test_list_repr_string_does_not_appear_in_output(self):
        result = _resolve_professor(["lbordin@uffs.edu.br"])
        self.assertNotIn("[", result)
        self.assertNotIn("]", result)
        self.assertNotIn("@", result)


class AdminRegistrationTests(SimpleTestCase):
    def test_questao_is_registered(self):
        from django.contrib import admin
        self.assertIn(Questao, admin.site._registry)

    def test_chunks_is_registered(self):
        from django.contrib import admin
        self.assertIn(Chunks, admin.site._registry)

    def test_prova_is_registered(self):
        from django.contrib import admin
        self.assertIn(Prova, admin.site._registry)

    def test_questao_admin_list_display(self):
        from django.contrib import admin
        model_admin = admin.site._registry[Questao]
        self.assertIn("ordem", model_admin.list_display)
        self.assertIn("pontuacao", model_admin.list_display)

    def test_prova_admin_list_display(self):
        from django.contrib import admin
        model_admin = admin.site._registry[Prova]
        self.assertIn("materia", model_admin.list_display)
        self.assertIn("professor", model_admin.list_display)
        self.assertIn("ano_semestre", model_admin.list_display)

    def test_chunks_admin_raw_id_fields(self):
        from django.contrib import admin
        model_admin = admin.site._registry[Chunks]
        self.assertIn("id_questao", model_admin.raw_id_fields)
