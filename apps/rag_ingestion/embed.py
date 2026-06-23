# ruff: noqa: E402
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import django
import numpy as np
from turbovec import IdMapIndex

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.settings")
django.setup()

from google import genai
from google.genai import types
from loguru import logger

from apps.rag_ingestion.models import Chunks, Prova, Questao
from apps.rag_ingestion.settings import embeddings_settings

DEFAULT_JSON_ROOT = PROJECT_ROOT / "input" / "converted_provas"
INDEX_PATH = Path(embeddings_settings.INDEX_PATH)
EMBEDDING_MODEL = embeddings_settings.EMBEDDING_MODEL
EMBEDDING_DIMS = embeddings_settings.EMBEDDING_DIMS


@dataclass(frozen=True)
class IngestionResult:
    provas: int
    questoes: int
    chunks: int
    index_path: Path


def get_client() -> genai.Client:
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    return genai.Client(api_key=google_api_key)


def find_exam_json_files(json_root: Path) -> list[Path]:
    if json_root.is_file():
        return [json_root]
    if not json_root.exists():
        raise FileNotFoundError(f"JSON root does not exist: {json_root}")
    return sorted(path for path in json_root.rglob("*.json") if path.is_file())


def load_exam_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if "questoes" not in data or not isinstance(data["questoes"], list):
        raise ValueError(f"Exam JSON has no questoes list: {path}")
    return data


def format_subquestoes(subquestoes: list | None) -> str:
    if not subquestoes:
        return ""
    return "\n".join(s["enunciado"] for s in subquestoes)


def build_chunk(
    materia: str,
    ordem: int,
    enunciado: str,
    subquestoes: list | None,
    resposta: str | None,
) -> str:
    parts = [f"task: search result | title: {materia} - Questão {ordem} | text:"]
    parts.append(enunciado)
    sub_text = format_subquestoes(subquestoes)
    if sub_text:
        parts.append(sub_text)
    if resposta:
        parts.append(f"Gabarito/Resposta esperada: {resposta}")
    return "\n".join(parts)


def get_embeddings_batch(client: genai.Client, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in texts]
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=contents,
        config={"output_dimensionality": EMBEDDING_DIMS},
    )
    embeddings = []
    for emb in response.embeddings:
        values = emb.values
        if values is None:
            raise ValueError("Gemini returned no embedding values.")
        embeddings.append([float(v) for v in values])
    return embeddings


def upsert_exam(data: dict[str, Any]) -> tuple[Prova, list[Questao], list[str]]:
    prova, _ = Prova.objects.update_or_create(
        materia=data["materia"],
        ano_semestre=data["ano_semestre"],
        numero_avaliacao=data["numero_avaliacao"],
        defaults={
            "professor": data["professor"],
            "cursos": data.get("cursos") or [],
            "data_aplicacao": data["data_aplicacao"],
            "nota_final": data.get("nota_final"),
            "recuperacao": data.get("recuperacao", False),
        },
    )

    questoes: list[Questao] = []
    chunk_texts: list[str] = []
    for ordem, q_data in enumerate(data["questoes"], start=1):
        subquestoes = q_data.get("subquestoes") or []
        # A question with subquestões carries no standalone answer/grade — the
        # answer lives in the subquestões. Null those here so the persisted row
        # and the embedded chunk text agree (no stale parent answer leaks into
        # search-match text).
        resposta = None if subquestoes else q_data.get("resposta")
        nota_recebida = None if subquestoes else q_data.get("nota_recebida")
        defaults = {
            "subquestoes": subquestoes,
            "resposta": resposta,
            "pontuacao": q_data.get("pontuacao"),
            "nota_recebida": nota_recebida,
        }

        questao, _ = Questao.objects.update_or_create(
            ordem=ordem,
            enunciado=q_data["enunciado"],
            defaults=defaults,
        )
        questoes.append(questao)
        chunk_texts.append(
            build_chunk(
                materia=data["materia"],
                ordem=ordem,
                enunciado=q_data["enunciado"],
                subquestoes=subquestoes,
                resposta=resposta,
            )
        )

    prova.questoes.set(questoes)
    return prova, questoes, chunk_texts


def rebuild_vector_index(
    questoes: list[Questao],
    embeddings: list[list[float]],
    *,
    index_path: Path = INDEX_PATH,
) -> int:
    Chunks.objects.all().delete()
    if not embeddings:
        if index_path.exists():
            index_path.unlink()
        return 0

    all_vectors = np.array(embeddings, dtype=np.float32)
    turbo_ids = np.arange(len(all_vectors), dtype=np.uint64)

    index = IdMapIndex(dim=EMBEDDING_DIMS, bit_width=4)
    index.add_with_ids(all_vectors, turbo_ids)

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index.write(str(index_path))

    for questao, turbo_id in zip(questoes, turbo_ids):
        Chunks.objects.update_or_create(
            id_questao=questao,
            defaults={"turbo_id": int(turbo_id)},
        )

    return len(turbo_ids)


def seed_exam_jsons(
    json_root: Path = DEFAULT_JSON_ROOT,
    *,
    client: genai.Client | None = None,
) -> IngestionResult:
    json_files = find_exam_json_files(json_root)
    if not json_files:
        raise ValueError(f"No exam JSON files found under {json_root}")

    embedding_client = client or get_client()
    all_questoes: list[Questao] = []
    all_chunk_texts: list[str] = []

    for json_file in json_files:
        data = load_exam_json(json_file)
        prova, questoes, chunk_texts = upsert_exam(data)
        all_questoes.extend(questoes)
        all_chunk_texts.extend(chunk_texts)
        logger.info(f"Loaded {json_file.relative_to(PROJECT_ROOT)} -> {prova.materia}")

    logger.info(f"Generating embeddings for {len(all_chunk_texts)} questions...")
    embeddings = get_embeddings_batch(embedding_client, all_chunk_texts)
    chunks = rebuild_vector_index(all_questoes, embeddings)

    return IngestionResult(
        provas=len(json_files),
        questoes=len(all_questoes),
        chunks=chunks,
        index_path=INDEX_PATH,
    )
