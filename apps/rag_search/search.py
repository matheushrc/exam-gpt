import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from google import genai
from turbovec import IdMapIndex

from apps.rag_ingestion.models import Chunks, Questao
from apps.rag_search.settings import search_settings


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    return genai.Client(api_key=google_api_key)


@lru_cache(maxsize=1)
def load_index() -> IdMapIndex | None:
    index_path = Path(search_settings.INDEX_PATH)

    if not index_path.exists():
        return None

    return IdMapIndex.load(str(index_path))


def get_query_embedding(query: str) -> list[float]:
    text = f"task: search result | query: {query}"
    response = get_client().models.embed_content(
        model=search_settings.EMBEDDING_MODEL,
        contents=text,
        config={"output_dimensionality": search_settings.EMBEDDING_DIMS},
    )
    values = response.embeddings[0].values or []
    return [float(v) for v in values]


def search(
    query: str,
    materia: str | None = None,
    top_k: int = search_settings.TOP_K,
    similarity_threshold: float = search_settings.MIN_SIMILARITY_SCORE,
) -> list[tuple[float, Questao]]:
    vector_index = load_index()
    if vector_index is None:
        return []

    query_embedding = get_query_embedding(query)
    query_arr = np.array([query_embedding], dtype=np.float32)

    allowlist_arr = None
    if materia:
        allowed_indices = list(
            Chunks.objects.filter(id_questao__provas__materia=materia)
            .exclude(turbo_id=None)
            .values_list("turbo_id", flat=True)
        )

        if not allowed_indices:
            return []

        allowlist_arr = np.array(allowed_indices, dtype=np.uint64)

    scores, indices = vector_index.search(query_arr, k=top_k, allowlist=allowlist_arr)

    target_turbo_ids = []
    id_scores = {}
    for score, idx in zip(scores[0], indices[0]):
        if score >= similarity_threshold:
            turbo_id = int(idx)
            target_turbo_ids.append(turbo_id)
            id_scores[turbo_id] = float(score)

    if not target_turbo_ids:
        return []

    chunks = {
        chunk.turbo_id: chunk
        for chunk in Chunks.objects.select_related("id_questao").filter(
            turbo_id__in=target_turbo_ids,
        )
    }
    return [
        (id_scores[turbo_id], chunks[turbo_id].id_questao)
        for turbo_id in target_turbo_ids
        if turbo_id in chunks
    ]
