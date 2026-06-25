import asyncio
import json
import os
import queue
import threading

from django.http import JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from pydantic_ai import Tool
from pydantic_ai.agent import Agent
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.cache import (
    get_all_professors,
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
        context["chat_model_presets"] = chat_settings.CHAT_MODEL_PRESETS
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
            return Response(get_all_professors(), status=200)
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
        provas = getattr(questao, "provas_resolved", [])
        prova = provas[0] if provas else None
        if prova:
            header = (
                f"[{prova.materia} Q{questao.ordem}] "
                f"(professor: {prova.professor}, "
                f"semestre: {prova.ano_semestre}, "
                f"avaliação: {prova.numero_avaliacao}, "
                f"score: {score:.3f})"
            )
        else:
            header = f"[Questão {questao.ordem}] (score: {score:.3f})"

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
    message_history: list[ModelMessage] | None = None,
):
    client = GoogleAgent(api_key=api_key)
    agent = _make_chat_agent(client, model_name, temperature, max_tokens, tools)
    return await client.get_inference_async(
        agent=agent, user_prompt=user_prompt, message_history=message_history
    )


def _get_similarity_tier(score: float) -> str:
    if score >= chat_settings.SIMILARITY_THRESHOLD_HIGH:
        return "high"
    elif score >= chat_settings.SIMILARITY_THRESHOLD_MEDIUM:
        return "medium"
    return "low"


def _serialize_sources(collected: list) -> list[dict]:
    return [
        {
            "score": score,
            "similarity_tier": _get_similarity_tier(score),
            "questao": {
                "id": str(questao.id),
                "ordem": questao.ordem,
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
                for prova in getattr(questao, "provas_resolved", [])
            ],
        }
        for score, questao in collected
    ]


def _parse_chat_request(data: dict) -> dict | None:
    """Returns parsed/validated chat params, or None if the message is empty."""
    message = (data.get("message") or "").strip()
    if not message:
        return None

    return {
        "message": message,
        "materia": data.get("materia") or None,
        "top_k": int(data.get("top_k") or chat_settings.DEFAULT_TOP_K),
        "similarity_threshold": float(
            data.get("similarity_threshold")
            or chat_settings.DEFAULT_SIMILARITY_THRESHOLD
        ),
        "model_name": data.get("model") or chat_settings.DEFAULT_CHAT_MODEL,
        "temperature": float(data.get("temperature") or chat_settings.DEFAULT_TEMPERATURE),
        "max_tokens": int(data.get("max_tokens") or chat_settings.DEFAULT_MAX_TOKENS),
        "grounding": bool(data.get("grounding", True)),
        "message_history": _deserialize_message_history(data.get("message_history")),
    }


def _deserialize_message_history(raw: list | None) -> list[ModelMessage] | None:
    """Rebuilds pydantic-ai's message history from the JSON list the client
    echoes back. The client holds this in memory only (no server-side
    conversation storage), so on malformed input we just drop the history
    instead of failing the request."""
    if not raw:
        return None
    try:
        return ModelMessagesTypeAdapter.validate_json(json.dumps(raw))
    except Exception:
        return None


def _serialize_message_history(result) -> list:
    return json.loads(result.all_messages_json())


def _resolve_api_key(request, data: dict) -> str | None:
    return (
        request.headers.get("X-Google-Api-Key")
        or data.get("api_key")
        or os.environ.get("GOOGLE_API_KEY")
    )


def _run_async_generator_sync(async_gen_factory):
    """Drives an async generator to completion on a background thread,
    yielding each item back to sync code via a queue.

    StreamingHttpResponse under WSGI needs a sync iterable, but pydantic-ai's
    streaming API (and the anyio task groups inside it) require the whole
    `async with agent.run_stream(...)` block to run within a single task.
    Calling `loop.run_until_complete()` per chunk from the WSGI thread breaks
    that invariant ("cancel scope in a different task"), so instead we run
    the entire async generator inside one `asyncio.run()` call on a separate
    thread and relay items through a thread-safe queue.
    """
    q: queue.Queue = queue.Queue()

    def runner():
        async def consume():
            try:
                async for item in async_gen_factory():
                    q.put(("item", item))
            except Exception as exc:
                q.put(("error", exc))
            finally:
                q.put(("done", None))

        asyncio.run(consume())

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()

    while True:
        kind, payload = q.get()
        if kind == "item":
            yield payload
        elif kind == "error":
            raise payload
        else:
            break

    thread.join()


def _stream_chat_events(
    *,
    message: str,
    api_key: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    tools: list[Tool] | None,
    collected: list,
    message_history: list[ModelMessage] | None = None,
):
    history_holder: list = []

    async def agen():
        client = GoogleAgent(api_key=api_key)
        agent = _make_chat_agent(client, model_name, temperature, max_tokens, tools)
        async with client.run_stream(
            agent=agent, user_prompt=message, message_history=message_history
        ) as result:
            async for delta in result.stream_text(delta=True):
                yield delta
            history_holder.append(_serialize_message_history(result))

    try:
        for delta in _run_async_generator_sync(agen):
            yield f"data: {json.dumps({'type': 'delta', 'text': delta})}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
        return

    sources = _serialize_sources(collected)
    history = history_holder[0] if history_holder else []
    yield f"data: {json.dumps({'type': 'done', 'sources': sources, 'message_history': history})}\n\n"


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
        params = _parse_chat_request(request.data)
        if params is None:
            return Response({"detail": "O campo 'message' é obrigatório."}, status=400)

        api_key = _resolve_api_key(request, request.data)
        if not api_key:
            return Response(
                {"detail": "Nenhuma chave de API do Google foi configurada."},
                status=400,
            )

        collected: list = []
        tools = None
        if params["grounding"]:
            tools = [
                _build_retrieve_tool(
                    params["materia"], params["top_k"], params["similarity_threshold"], collected
                )
            ]

        history = params["message_history"] or []
        try:
            result = asyncio.run(
                _generate_answer(
                    params["message"],
                    api_key=api_key,
                    model_name=params["model_name"],
                    temperature=params["temperature"],
                    max_tokens=params["max_tokens"],
                    tools=tools,
                    message_history=params["message_history"],
                )
            )
            answer = result.output
            history = _serialize_message_history(result)
        except Exception as exc:
            answer = f"Ocorreu um erro ao gerar a resposta: {exc}"

        sources = _serialize_sources(collected)

        return Response(
            {
                "query": params["message"],
                "answer": answer,
                "sources": sources,
                "message_history": history,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class ChatStreamView(View):
    """Streams the chat answer as SSE text deltas, ending with a `done` event
    carrying the sources. Plain Django View (not DRF) so we can return a
    StreamingHttpResponse without DRF's response/renderer machinery. CSRF is
    exempted here the same way DRF's APIView exempts ChatMessageView."""

    def post(self, request):
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido."}, status=400)

        params = _parse_chat_request(data)
        if params is None:
            return JsonResponse(
                {"detail": "O campo 'message' é obrigatório."}, status=400
            )

        api_key = _resolve_api_key(request, data)
        if not api_key:
            return JsonResponse(
                {"detail": "Nenhuma chave de API do Google foi configurada."},
                status=400,
            )

        collected: list = []
        tools = None
        if params["grounding"]:
            tools = [
                _build_retrieve_tool(
                    params["materia"], params["top_k"], params["similarity_threshold"], collected
                )
            ]

        response = StreamingHttpResponse(
            _stream_chat_events(
                message=params["message"],
                api_key=api_key,
                model_name=params["model_name"],
                temperature=params["temperature"],
                max_tokens=params["max_tokens"],
                tools=tools,
                collected=collected,
                message_history=params["message_history"],
            ),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
