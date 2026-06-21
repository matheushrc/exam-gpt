from unittest import mock

from django.test import Client, TestCase
from django.urls import reverse

from apps.rag_ingestion.models import Prova, Questao
from apps.upload import session as wizard_session
from apps.upload.forms import MetaForm


class WizardSessionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.request = mock.Mock()
        self.request.session = self.client.session

    def test_get_wizard_data_returns_empty_dict_when_missing(self):
        self.assertEqual(wizard_session.get_wizard_data(self.request, "missing"), {})

    def test_set_then_get_round_trips_data(self):
        wizard_session.set_wizard_data(self.request, "abc", {"prova": {"materia": "Redes"}})

        self.assertEqual(
            wizard_session.get_wizard_data(self.request, "abc"),
            {"prova": {"materia": "Redes"}},
        )

    def test_clear_removes_only_target_session(self):
        wizard_session.set_wizard_data(self.request, "abc", {"prova": {}})
        wizard_session.set_wizard_data(self.request, "def", {"prova": {}})

        wizard_session.clear_wizard_data(self.request, "abc")

        self.assertEqual(wizard_session.get_wizard_data(self.request, "abc"), {})
        self.assertEqual(wizard_session.get_wizard_data(self.request, "def"), {"prova": {}})

    def test_new_session_id_is_unique(self):
        self.assertNotEqual(wizard_session.new_session_id(), wizard_session.new_session_id())


class MetaFormTests(TestCase):
    def test_valid_data_with_professor_choice(self):
        form = MetaForm(
            data={
                "professor": "joao.silva",
                "cursos": "Engenharia Civil, Arquitetura",
                "ano_semestre": "2026.1",
                "materia": "Calculo",
                "numero_avaliacao": "1",
                "recuperacao": "",
                "nota_final": "8.5",
                "data_aplicacao": "2026-03-15",
            },
            professores=[{"username": "joao.silva", "name": "Joao Silva"}],
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["professor"], "joao.silva")
        self.assertEqual(form.cleaned_data["numero_avaliacao"], 1)
        self.assertFalse(form.cleaned_data["recuperacao"])

    def test_invalid_ano_semestre_pattern_rejected(self):
        form = MetaForm(
            data={
                "professor": "",
                "cursos": "",
                "ano_semestre": "2026-1",
                "materia": "Calculo",
                "numero_avaliacao": "1",
                "data_aplicacao": "2026-03-15",
            },
            professores=[],
        )

        self.assertFalse(form.is_valid())
        self.assertIn("ano_semestre", form.errors)

    def test_professor_choices_built_from_kwarg(self):
        form = MetaForm(professores=[{"username": "a.b", "name": "A B"}])

        self.assertIn(("a.b", "A B"), form.fields["professor"].choices)
        self.assertIn(("", "---"), form.fields["professor"].choices)


class UploadViewTests(TestCase):
    def test_get_renders_step1_template(self):
        response = self.client.get(reverse("upload"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "upload/step1_upload.html")

    def test_post_without_files_shows_error(self):
        response = self.client.post(reverse("upload"), data={})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "upload/step1_upload.html")
        self.assertTrue(response.context["error"])

    def test_post_with_single_pdf_calls_extract_from_pdf(self):
        fake_exam = mock.Mock()
        fake_exam.model_dump.return_value = {"materia": "Redes", "questoes": []}

        async def fake_extract(*args, **kwargs):
            return fake_exam

        with mock.patch(
            "apps.upload.views.extract_exam_from_pdf", side_effect=fake_extract
        ) as extract_mock:
            pdf_file = self._make_upload_file("prova.pdf", b"%PDF-1.4 fake")
            response = self.client.post(
                reverse("upload"), data={"files": pdf_file}, format="multipart"
            )

        extract_mock.assert_called_once()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/upload/"))
        self.assertTrue(response.url.endswith("/meta/"))

    def test_post_with_images_calls_extract_from_images(self):
        fake_exam = mock.Mock()
        fake_exam.model_dump.return_value = {"materia": "Redes", "questoes": []}

        async def fake_extract(*args, **kwargs):
            return fake_exam

        with mock.patch(
            "apps.upload.views.extract_exam_from_images", side_effect=fake_extract
        ) as extract_mock:
            img1 = self._make_upload_file("p1.jpg", b"\xff\xd8fake1")
            img2 = self._make_upload_file("p2.jpg", b"\xff\xd8fake2")
            response = self.client.post(
                reverse("upload"), data={"files": [img1, img2]}, format="multipart"
            )

        extract_mock.assert_called_once()
        self.assertEqual(response.status_code, 302)

    def test_post_extraction_failure_renders_error_without_500(self):
        async def failing_extract(*args, **kwargs):
            raise RuntimeError("boom")

        with mock.patch(
            "apps.upload.views.extract_exam_from_images", side_effect=failing_extract
        ):
            img = self._make_upload_file("p1.jpg", b"\xff\xd8fake")
            response = self.client.post(
                reverse("upload"), data={"files": img}, format="multipart"
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("boom", response.context["error"])

    @staticmethod
    def _make_upload_file(name: str, content: bytes):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile(name, content)


class MetaViewTests(TestCase):
    def setUp(self):
        self.session_id = "session-1"
        session = self.client.session
        session["upload_wizard"] = {
            self.session_id: {
                "prova": {
                    "professor": "Jane Doe",
                    "cursos": ["Engenharia Civil"],
                    "materia": "Calculo",
                    "ano_semestre": "2026.1",
                    "data_aplicacao": "2026-03-15",
                    "numero_avaliacao": 1,
                    "recuperacao": False,
                    "nota_final": None,
                    "questoes": [],
                },
                "file_names": ["test.pdf"],
            }
        }
        session.save()

    def test_get_404s_for_unknown_session(self):
        response = self.client.get(reverse("upload-meta", args=["unknown"]))

        self.assertEqual(response.status_code, 404)

    def test_get_prefills_form_from_session(self):
        response = self.client.get(reverse("upload-meta", args=[self.session_id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calculo")
        self.assertContains(response, "Engenharia Civil")

    def test_post_valid_data_updates_session_and_redirects(self):
        response = self.client.post(
            reverse("upload-meta", args=[self.session_id]),
            data={
                "professor": "",
                "cursos": "Engenharia Civil, Arquitetura",
                "ano_semestre": "2026.2",
                "materia": "Calculo II",
                "numero_avaliacao": "2",
                "recuperacao": "on",
                "nota_final": "7.0",
                "data_aplicacao": "2026-06-01",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/review/"))

        session = self.client.session
        prova = session["upload_wizard"][self.session_id]["prova"]
        self.assertEqual(prova["materia"], "Calculo II")
        self.assertEqual(prova["ano_semestre"], "2026.2")
        self.assertEqual(prova["cursos"], ["Engenharia Civil", "Arquitetura"])
        self.assertTrue(prova["recuperacao"])

    def test_post_invalid_data_rerenders_form_with_errors(self):
        response = self.client.post(
            reverse("upload-meta", args=[self.session_id]),
            data={
                "professor": "",
                "cursos": "",
                "ano_semestre": "not-a-semester",
                "materia": "",
                "numero_avaliacao": "",
                "data_aplicacao": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())


class ReviewViewTests(TestCase):
    def setUp(self):
        self.session_id = "session-review"
        session = self.client.session
        session["upload_wizard"] = {
            self.session_id: {
                "prova": {
                    "professor": "Jane Doe",
                    "cursos": ["Engenharia Civil"],
                    "materia": "Calculo",
                    "ano_semestre": "2026.1",
                    "data_aplicacao": "2026-03-15",
                    "numero_avaliacao": 1,
                    "recuperacao": False,
                    "nota_final": None,
                    "questoes": [
                        {
                            "numero": 1,
                            "enunciado": "Original enunciado",
                            "pontuacao": 2.0,
                            "resposta": None,
                            "nota_recebida": None,
                            "subquestoes": None,
                        },
                        {
                            "numero": 2,
                            "enunciado": "Questao com sub",
                            "pontuacao": 3.0,
                            "resposta": None,
                            "nota_recebida": None,
                            "subquestoes": [
                                {
                                    "label": "(a)",
                                    "enunciado": "Sub original",
                                    "pontuacao": 1.5,
                                    "resposta": None,
                                    "nota_recebida": None,
                                },
                            ],
                        },
                    ],
                },
                "file_names": ["test.pdf"],
            }
        }
        session.save()

    def test_get_404s_for_unknown_session(self):
        response = self.client.get(reverse("upload-review", args=["unknown"]))

        self.assertEqual(response.status_code, 404)

    def test_get_renders_questions_from_session(self):
        response = self.client.get(reverse("upload-review", args=[self.session_id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Original enunciado")
        self.assertContains(response, "Sub original")

    def test_post_saves_edits_and_redirects_home(self):
        with (
            mock.patch("apps.upload.views.get_client", return_value=mock.Mock()),
            mock.patch("apps.upload.views.get_embeddings_batch", return_value=[[0.1], [0.2]]),
            mock.patch("apps.upload.views.rebuild_vector_index", return_value=2),
        ):
            response = self.client.post(
                reverse("upload-review", args=[self.session_id]),
                data={
                    "q1_enunciado": "Enunciado editado",
                    "q1_resposta": "Resposta do aluno",
                    "q1_nota_recebida": "1.5",
                    "q2_sub1_enunciado": "Sub editado",
                    "q2_sub1_resposta": "Resposta sub",
                    "q2_sub1_nota_recebida": "1.0",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

        prova = Prova.objects.get(materia="Calculo", ano_semestre="2026.1", numero_avaliacao=1)
        self.assertEqual(prova.professor, "Jane Doe")

        questao = Questao.objects.get(numero=1, enunciado="Enunciado editado")
        self.assertEqual(questao.resposta, "Resposta do aluno")
        self.assertEqual(questao.nota_recebida, 1.5)

        questao_sub = Questao.objects.get(numero=2)
        self.assertEqual(questao_sub.subquestoes[0]["enunciado"], "Sub editado")
        self.assertEqual(questao_sub.subquestoes[0]["nota_recebida"], 1.0)

        # session cleared after successful save
        session = self.client.session
        self.assertNotIn(self.session_id, session.get("upload_wizard", {}))

    def test_post_continues_and_warns_when_embedding_step_fails(self):
        with (
            mock.patch("apps.upload.views.get_client", side_effect=RuntimeError("no api key")),
        ):
            response = self.client.post(
                reverse("upload-review", args=[self.session_id]),
                data={
                    "q1_enunciado": "Original enunciado",
                    "q1_resposta": "",
                    "q1_nota_recebida": "",
                    "q2_sub1_enunciado": "Sub original",
                    "q2_sub1_resposta": "",
                    "q2_sub1_nota_recebida": "",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Prova.objects.filter(
                materia="Calculo", ano_semestre="2026.1", numero_avaliacao=1
            ).exists()
        )


class ProfessorsPartialViewTests(TestCase):
    def test_returns_empty_options_without_semester(self):
        response = self.client.get(reverse("upload-professors"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["professores"], [])

    def test_filters_by_materia_when_provided(self):
        fake_professors = [{"username": "a.b", "name": "A B"}]
        with mock.patch(
            "apps.upload.views.get_professors_for_materia", return_value=fake_professors
        ) as materia_mock:
            response = self.client.get(
                reverse("upload-professors"), {"semester": "2026.1", "materia": "Calculo"}
            )

        materia_mock.assert_called_once_with("2026.1", "Calculo")
        self.assertEqual(response.context["professores"], fake_professors)

    def test_falls_back_to_semester_only_lookup(self):
        fake_professors = [{"username": "c.d", "name": "C D"}]
        with mock.patch(
            "apps.upload.views.get_professors_for_semester", return_value=fake_professors
        ) as semester_mock:
            response = self.client.get(reverse("upload-professors"), {"semester": "2026.1"})

        semester_mock.assert_called_once_with("2026.1")
        self.assertEqual(response.context["professores"], fake_professors)
