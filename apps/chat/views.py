import asyncio
import os

from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from pydantic_ai import Tool
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
from apps.chat.prompts import CHAT_SYSTEM_PROMPT
from apps.chat.settings import chat_settings
from apps.rag_ingestion.agents.Google import GoogleAgent
from apps.rag_search.search import search


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


def _format_context(results):
    if not results:
        return (
            "Nenhuma questão relevante foi encontrada nas provas anteriores "
            "para esta pergunta."
        )

    blocks = []
    for score, questao in results:
        prova = questao.prova
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


def _build_retrieve_tool(
    materia: str | None,
    top_k: int,
    similarity_threshold: float,
    collected: list,
) -> Tool:
    def retrieve_exams(query: str) -> str:
        """Busca questões e respostas de provas anteriores relacionadas à query.

        Use esta ferramenta quando a resposta depender de questões de provas
        anteriores. Retorna um bloco de texto com as questões encontradas, ou
        avisa quando nada relevante foi encontrado.
        """
        results = search(
            query=query,
            materia=materia,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        collected.extend(results)
        return _format_context(results)

    return Tool(retrieve_exams, name="retrieve_exams")


def _make_chat_agent(
    google_client: GoogleAgent,
    model_name: str,
    temperature: float,
    max_tokens: int,
    tools: list[Tool] | None,
) -> Agent:
    return google_client.create_agent(
        output_type=str,
        model_name=model_name,
        retries=3,
        model_settings={"temperature": temperature, "max_tokens": max_tokens},
        system_prompt=CHAT_SYSTEM_PROMPT.strip(),
        tools=tools,
    )


async def _generate_answer(
    user_prompt: str,
    *,
    api_key: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    tools: list[Tool] | None,
) -> str:
    client = GoogleAgent(api_key=api_key)
    agent = _make_chat_agent(client, model_name, temperature, max_tokens, tools)
    result = await client.get_inference_async(agent=agent, user_prompt=user_prompt)
    return result.output


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
            return Response({"detail": "O campo 'message' é obrigatório."}, status=400)

        materia = request.data.get("materia") or None
        top_k = int(request.data.get("top_k") or chat_settings.DEFAULT_TOP_K)
        similarity_threshold = float(
            request.data.get("similarity_threshold")
            or chat_settings.DEFAULT_SIMILARITY_THRESHOLD
        )
        model_name = request.data.get("model") or chat_settings.DEFAULT_CHAT_MODEL
        temperature = float(
            request.data.get("temperature") or chat_settings.DEFAULT_TEMPERATURE
        )
        max_tokens = int(
            request.data.get("max_tokens") or chat_settings.DEFAULT_MAX_TOKENS
        )
        grounding = bool(request.data.get("grounding", True))

        api_key = (
            request.headers.get("X-Google-Api-Key")
            or request.data.get("api_key")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not api_key:
            return Response(
                {"detail": "Nenhuma chave de API do Google foi configurada."},
                status=400,
            )

        collected: list = []
        tools = None
        if grounding:
            tools = [
                _build_retrieve_tool(materia, top_k, similarity_threshold, collected)
            ]

        try:
            answer = asyncio.run(
                _generate_answer(
                    message,
                    api_key=api_key,
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                )
            )
        except Exception as exc:
            answer = f"Ocorreu um erro ao gerar a resposta: {exc}"

        sources = [
            {
                "score": score,
                "questao": {
                    "id": str(questao.id),
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
            for score, questao in collected
        ]

        return Response({"query": message, "answer": answer, "sources": sources})
