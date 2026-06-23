import asyncio
import base64

from loguru import logger
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rag_ingestion.embed import (
    get_client,
    get_embeddings_batch,
    rebuild_vector_index,
    upsert_exam,
)
from apps.rag_ingestion.extract import extract_exam_from_images, extract_exam_from_pdf


class ProvaExtractAPIView(APIView):
    """POST /api/provas/extract/ -- extraction endpoint for the SPA upload flow.

    Accepts multipart files or base64 camera images and returns the extracted
    Prova+Questões as JSON for the client-side review screen to edit before
    saving via ProvaSaveAPIView.
    """

    def post(self, request):
        try:
            files = request.FILES.getlist("files")
            if files:
                if len(files) == 1 and files[0].name.lower().endswith(".pdf"):
                    pdf_file = files[0]
                    exam = asyncio.run(
                        extract_exam_from_pdf(
                            pdf_file.read(), source_hint=pdf_file.name
                        )
                    )
                    file_names = [pdf_file.name]
                else:
                    images = [f.read() for f in files]
                    file_names = [f.name for f in files]
                    exam = asyncio.run(
                        extract_exam_from_images(
                            images, source_hint=", ".join(file_names)
                        )
                    )
            elif request.content_type == "application/json":
                camera_images = request.data.get("camera_images") or []
                if not camera_images:
                    raise ValueError("No files or camera images provided.")
                images = [base64.b64decode(img) for img in camera_images]
                file_names = [f"camera_{i + 1}.jpg" for i in range(len(images))]
                exam = asyncio.run(
                    extract_exam_from_images(images, source_hint="camera capture")
                )
            else:
                raise ValueError("No files or camera images provided.")
        except (ValueError, RuntimeError) as exc:
            logger.warning(f"Exam extraction failed: {exc}")
            return Response({"detail": str(exc)}, status=400)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error during exam extraction")
            return Response(
                {"detail": f"Erro inesperado ao extrair a prova: {exc}"}, status=500
            )

        return Response(
            {"prova": exam.model_dump(mode="json"), "file_names": file_names}
        )


class ProvaSaveAPIView(APIView):
    """POST /api/provas/ -- persist a (possibly user-edited) Prova+Questões payload
    and rebuild the vector index. This is the SPA upload flow's save step.
    """

    def post(self, request):
        prova = request.data.get("prova")
        if not prova:
            return Response({"detail": "O campo 'prova' é obrigatório."}, status=400)

        try:
            prova_obj, questao_objs, chunk_texts = upsert_exam(prova)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to persist exam")
            return Response({"detail": f"Erro ao salvar a prova: {exc}"}, status=400)

        warning = None
        try:
            client = get_client()
            embeddings = get_embeddings_batch(client, chunk_texts)
            rebuild_vector_index(questao_objs, embeddings)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Embedding/indexing step failed after saving exam")
            warning = str(exc)

        return Response(
            {
                "id": str(prova_obj.id),
                "materia": prova_obj.materia,
                "ano_semestre": prova_obj.ano_semestre,
                "numero_avaliacao": prova_obj.numero_avaliacao,
                "warning": warning,
            }
        )
