import base64
import json

from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from loguru import logger

from apps.chat.cache import get_professors_for_materia, get_professors_for_semester
from apps.rag_ingestion.embed import (
    get_client,
    get_embeddings_batch,
    rebuild_vector_index,
    upsert_exam,
)
from apps.rag_ingestion.extract import extract_exam_from_images, extract_exam_from_pdf
from apps.upload.forms import MetaForm
from apps.upload.session import (
    clear_wizard_data,
    get_wizard_data,
    new_session_id,
    set_wizard_data,
)


class UploadView(View):
    async def get(self, request):
        # DC "Enviar prova" screen. The empty -> processing -> review flow is
        # driven client-side against the JSON endpoints (/api/provas/extract/,
        # /api/provas/); the session wizard below remains as a no-JS fallback.
        return render(request, "upload/upload.html")

    async def post(self, request):
        try:
            files = request.FILES.getlist("files")
            if files:
                if len(files) == 1 and files[0].name.lower().endswith(".pdf"):
                    pdf_file = files[0]
                    exam = await extract_exam_from_pdf(
                        pdf_file.read(), source_hint=pdf_file.name
                    )
                    file_names = [pdf_file.name]
                else:
                    images = [f.read() for f in files]
                    file_names = [f.name for f in files]
                    exam = await extract_exam_from_images(
                        images, source_hint=", ".join(file_names)
                    )
            elif request.content_type == "application/json":
                payload = json.loads(request.body)
                camera_images = payload.get("camera_images", [])
                if not camera_images:
                    raise ValueError("No files or camera images provided.")
                images = [base64.b64decode(img) for img in camera_images]
                file_names = [f"camera_{i + 1}.jpg" for i in range(len(images))]
                exam = await extract_exam_from_images(
                    images, source_hint="camera capture"
                )
            else:
                raise ValueError("No files or camera images provided.")
        except (ValueError, RuntimeError) as exc:
            logger.warning(f"Exam extraction failed: {exc}")
            return render(
                request,
                "upload/step1_upload.html",
                {"error": str(exc)},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error during exam extraction")
            return render(
                request,
                "upload/step1_upload.html",
                {"error": f"Erro inesperado ao extrair a prova: {exc}"},
            )

        session_id = new_session_id()
        set_wizard_data(
            request,
            session_id,
            {"prova": exam.model_dump(mode="json"), "file_names": file_names},
        )
        return redirect(reverse("upload-meta", args=[session_id]))


class MetaView(View):
    def get(self, request, session_id: str):
        data = get_wizard_data(request, session_id)
        if not data:
            raise Http404("Upload session not found or expired.")

        prova = data["prova"]
        semester = prova.get("ano_semestre", "")
        materia = prova.get("materia", "")
        professores = (
            get_professors_for_materia(semester, materia)
            if semester and materia
            else get_professors_for_semester(semester)
            if semester
            else []
        )

        initial = {
            "professor": prova.get("professor", ""),
            "cursos": ", ".join(prova.get("cursos") or []),
            "ano_semestre": prova.get("ano_semestre", ""),
            "materia": prova.get("materia", ""),
            "numero_avaliacao": prova.get("numero_avaliacao"),
            "recuperacao": prova.get("recuperacao", False),
            "nota_final": prova.get("nota_final"),
            "data_aplicacao": prova.get("data_aplicacao"),
        }
        form = MetaForm(initial=initial, professores=professores)
        return render(
            request,
            "upload/step2_meta.html",
            {"form": form, "session_id": session_id, "prova": prova},
        )

    def post(self, request, session_id: str):
        data = get_wizard_data(request, session_id)
        if not data:
            raise Http404("Upload session not found or expired.")

        prova = data["prova"]
        semester = request.POST.get("ano_semestre") or prova.get("ano_semestre", "")
        materia = request.POST.get("materia") or prova.get("materia", "")
        professores = (
            get_professors_for_materia(semester, materia)
            if semester and materia
            else get_professors_for_semester(semester)
            if semester
            else []
        )

        form = MetaForm(request.POST, professores=professores)
        if not form.is_valid():
            return render(
                request,
                "upload/step2_meta.html",
                {"form": form, "session_id": session_id, "prova": prova},
            )

        cleaned = form.cleaned_data
        prova["professor"] = cleaned["professor"]
        prova["cursos"] = [
            curso.strip() for curso in cleaned["cursos"].split(",") if curso.strip()
        ]
        prova["ano_semestre"] = cleaned["ano_semestre"]
        prova["materia"] = cleaned["materia"]
        prova["numero_avaliacao"] = cleaned["numero_avaliacao"]
        prova["recuperacao"] = cleaned["recuperacao"]
        prova["nota_final"] = cleaned["nota_final"]
        prova["data_aplicacao"] = cleaned["data_aplicacao"].isoformat()

        data["prova"] = prova
        set_wizard_data(request, session_id, data)
        return redirect(reverse("upload-review", args=[session_id]))


class ReviewView(View):
    def get(self, request, session_id: str):
        data = get_wizard_data(request, session_id)
        if not data:
            raise Http404("Upload session not found or expired.")

        prova = data["prova"]
        return render(
            request,
            "upload/step3_review.html",
            {"session_id": session_id, "questoes": prova["questoes"], "prova": prova},
        )

    def post(self, request, session_id: str):
        data = get_wizard_data(request, session_id)
        if not data:
            raise Http404("Upload session not found or expired.")

        prova = data["prova"]
        for i, questao in enumerate(prova["questoes"], start=1):
            enunciado_key = f"q{i}_enunciado"
            resposta_key = f"q{i}_resposta"
            nota_key = f"q{i}_nota_recebida"
            if enunciado_key in request.POST:
                questao["enunciado"] = request.POST[enunciado_key]
            if resposta_key in request.POST:
                questao["resposta"] = request.POST[resposta_key] or None
            if nota_key in request.POST:
                nota_value = request.POST[nota_key]
                questao["nota_recebida"] = float(nota_value) if nota_value else None

            for j, subquestao in enumerate(questao.get("subquestoes") or [], start=1):
                sub_enunciado_key = f"q{i}_sub{j}_enunciado"
                sub_resposta_key = f"q{i}_sub{j}_resposta"
                sub_nota_key = f"q{i}_sub{j}_nota_recebida"
                if sub_enunciado_key in request.POST:
                    subquestao["enunciado"] = request.POST[sub_enunciado_key]
                if sub_resposta_key in request.POST:
                    subquestao["resposta"] = request.POST[sub_resposta_key] or None
                if sub_nota_key in request.POST:
                    sub_nota_value = request.POST[sub_nota_key]
                    subquestao["nota_recebida"] = (
                        float(sub_nota_value) if sub_nota_value else None
                    )

        data["prova"] = prova
        set_wizard_data(request, session_id, data)

        prova_obj, questao_objs, chunk_texts = upsert_exam(prova)
        warning = None
        try:
            client = get_client()
            embeddings = get_embeddings_batch(client, chunk_texts)
            rebuild_vector_index(questao_objs, embeddings)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Embedding/indexing step failed after saving exam")
            warning = str(exc)

        clear_wizard_data(request, session_id)
        if warning:
            from django.contrib import messages

            messages.warning(
                request,
                f"Prova salva, mas houve um erro ao gerar embeddings: {warning}",
            )
        return redirect("/")


class ProfessorsPartialView(View):
    def get(self, request):
        semester = request.GET.get("semester", "")
        materia = request.GET.get("materia", "")
        if not semester:
            professores = []
        elif materia:
            professores = get_professors_for_materia(semester, materia)
        else:
            professores = get_professors_for_semester(semester)
        return render(
            request,
            "upload/_professor_options.html",
            {"professores": professores},
        )
