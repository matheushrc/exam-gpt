import asyncio
import os

from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from pydantic_ai.agent import Agent
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.cache import (
    get_groups,
    get_professors_for_materia,
    get_professors_for_semester,
    get_schedule,
    get_semesters,
)
from apps.rag_ingestion.agents.Google import GoogleAgent
from apps.rag_search.search import search

CHAT_MODEL = "gemini-3.1-flash-lite"

CHAT_SYSTEM_PROMPT = """
Você é um assistente que ajuda estudantes a tirar dúvidas sobre questões de
provas anteriores. Use o contexto fornecido, composto por questões e
respostas de provas passadas, para responder à pergunta do estudante.

Ao citar uma questão, use o formato [Matéria QN], onde N é o número da
questão (ex: [Cálculo I Q3]).

Se a pergunta do estudante não tiver relação com as questões fornecidas no
contexto, diga isso diretamente ao estudante em vez de tentar inventar uma
resposta.
"""


class ChatView(TemplateView):
    template_name = "chat/chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["conversation_id"] = self.request.GET.get("c", "")
        return context


class SemestersView(APIView):
    @extend_schema(responses={200: {"type": "array", "items": {"type": "string"}}})
    def get(self, request):
        return Response(get_semesters())


class GroupsView(APIView):
    @extend_schema(responses={200: {"type": "array", "items": {"type": "object"}}})
    def get(self, request, semester: str):
        return Response(get_groups(semester))


class ScheduleView(APIView):
    @extend_schema(responses={200: {"type": "array", "items": {"type": "object"}}})
    def get(self, request, semester: str, group: int):
        return Response(get_schedule(semester, group))


class ProfessorsView(APIView):
    @extend_schema(responses={200: {"type": "array", "items": {"type": "object"}}})
    def get(self, request):
        semester = request.query_params.get("semester", "")
        materia = request.query_params.get("materia", "")
        if not semester:
            return Response([], status=200)
        if materia:
            professors = get_professors_for_materia(semester, materia)
        else:
            professors = get_professors_for_semester(semester)
        return Response(professors)


def _make_chat_agent(google_client: GoogleAgent) -> Agent:
    return google_client.create_agent(
        output_type=str,
        model_name=CHAT_MODEL,
        retries=3,
        model_settings={"temperature": 0.0},
        system_prompt=CHAT_SYSTEM_PROMPT.strip(),
    )


async def _generate_answer(user_prompt: str) -> str:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable not set.")
    client = GoogleAgent(api_key=api_key)
    agent = _make_chat_agent(client)
    result = await client.get_inference_async(agent=agent, user_prompt=user_prompt)
    return result.output


def _format_context(results):
    if not results:
        return (
            "Nenhuma questão relevante foi encontrada nas provas anteriores "
            "para esta pergunta."
        )

    blocks = []
    for score, questao in results:
        prova = questao.provas.first()
        if prova:
            header = (
                f"[{prova.materia} Q{questao.numero}] "
                f"(professor: {prova.professor}, "
                f"semestre: {prova.ano_semestre}, "
                f"avaliação: {prova.numero_avaliacao}, "
                f"score: {score:.3f})"
            )
        else:
            header = f"[Questão {questao.numero}] (score: {score:.3f})"

        block = f"{header}\nEnunciado: {questao.enunciado}"
        if questao.resposta:
            block += f"\nResposta: {questao.resposta}"
        blocks.append(block)

    return "\n\n".join(blocks)


class ChatMessageView(APIView):
    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "answer": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "object"}},
                },
            }
        }
    )
    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response(
                {"detail": "O campo 'message' é obrigatório."}, status=400
            )

        materia = request.data.get("materia") or None
        top_k = int(request.data.get("top_k") or 5)

        results = search(query=message, materia=materia, top_k=top_k)
        context_text = _format_context(results)

        user_prompt = (
            f"Contexto:\n{context_text}\n\nPergunta do estudante: {message}"
        )

        try:
            answer = asyncio.run(_generate_answer(user_prompt))
        except Exception as exc:
            answer = f"Ocorreu um erro ao gerar a resposta: {exc}"

        sources = [
            {
                "score": score,
                "questao": {
                    "id": questao.id,
                    "numero": questao.numero,
                    "enunciado": questao.enunciado,
                    "subquestoes": questao.subquestoes,
                    "resposta": questao.resposta,
                    "pontuacao": questao.pontuacao,
                    "nota_recebida": questao.nota_recebida,
                },
                "provas": [
                    {
                        "materia": prova.materia,
                        "professor": prova.professor,
                        "ano_semestre": prova.ano_semestre,
                        "numero_avaliacao": prova.numero_avaliacao,
                    }
                    for prova in questao.provas.all()
                ],
            }
            for score, questao in results
        ]

        return Response({"query": message, "answer": answer, "sources": sources})
