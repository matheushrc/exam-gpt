# ruff: noqa: E402
import json
import os
import sys
from pathlib import Path

import django
import numpy as np
from turbovec import IdMapIndex

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.settings")
django.setup()

from google import genai
from google.genai import types

from apps.rag_ingestion.models import Chunks, Prova, Questao
from apps.rag_ingestion.settings import embeddings_settings

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

client = genai.Client(api_key=GOOGLE_API_KEY)

JSON_PATH = PROJECT_ROOT / "input" / "provas" / "redes-de-computadores" / "redes.json"
INDEX_PATH = Path(embeddings_settings.INDEX_PATH)
EMBEDDING_MODEL = embeddings_settings.EMBEDDING_MODEL
EMBEDDING_DIMS = embeddings_settings.EMBEDDING_DIMS


def format_subquestoes(subquestoes: list | None) -> str:
    if not subquestoes:
        return ""
    return "\n".join(f"{s['label']}) {s['enunciado']} " for s in subquestoes)


def build_chunk(
    materia: str,
    numero: int,
    enunciado: str,
    subquestoes: list | None,
    resposta: str | None,
) -> str:
    parts = [f"task: search result | title: {materia} - Questão {numero} | text:"]
    parts.append(enunciado)
    sub_text = format_subquestoes(subquestoes)
    if sub_text:
        parts.append(sub_text)
    # Inclui a resposta/gabarito se disponível para melhorar a semântica na busca
    if resposta:
        parts.append(f"Gabarito/Resposta esperada: {resposta}")
    return "\n".join(parts)


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
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


def main() -> None:
    with JSON_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    questoes_criadas = []
    chunk_texts = []
    questoes_objs = []

    # 1. Cria ou atualiza as questões no Django
    for q_data in data["questoes"]:
        questao, q_created = Questao.objects.update_or_create(
            numero=q_data["numero"],
            enunciado=q_data["enunciado"],
            defaults={
                "subquestoes": q_data["subquestoes"] or [],
                "resposta": q_data.get("resposta"),
                "pontuacao": q_data.get("pontuacao"),
            },
        )
        questoes_criadas.append(questao)
        questoes_objs.append(questao)

        chunk_text = build_chunk(
            materia=data["materia"],
            numero=q_data["numero"],
            enunciado=q_data["enunciado"],
            subquestoes=q_data["subquestoes"],
            resposta=q_data.get("resposta"),
        )
        chunk_texts.append(chunk_text)

    # 2. Ingestão paralela/lote: Uma única requisição HTTP para a API de embeddings
    print(
        f"Gerando embeddings em lote para {len(chunk_texts)} questões...",
        end=" ",
        flush=True,
    )
    embeddings = get_embeddings_batch(chunk_texts)
    print("ok")

    # 3. Reconstrói o índice Turbovec e salva em Mongo apenas o ID numérico do vetor.
    if embeddings:
        all_vectors = np.array(embeddings, dtype=np.float32)
        turbo_ids = np.arange(len(all_vectors), dtype=np.uint64)

        index = IdMapIndex(dim=EMBEDDING_DIMS, bit_width=4)
        index.add_with_ids(all_vectors, turbo_ids)

        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        index.write(str(INDEX_PATH))

        for questao, turbo_id in zip(questoes_objs, turbo_ids):
            Chunks.objects.update_or_create(
                id_questao=questao,
                defaults={"turbo_id": int(turbo_id)},
            )

        print("Índice vetorial salvo e chunks vinculados aos IDs Turbovec!")

    # Prova.questoes logic
    prova, p_created = Prova.objects.update_or_create(
        materia=data["materia"],
        ano=data["ano"],
        semestre=str(data["semestre"]),
        numero_avaliacao=data["numero_avaliacao"],
        defaults={
            "professor": data["professor"],
            "cursos": data["cursos"],
            "data_aplicacao": data["data_aplicacao"],
            "questoes": questoes_criadas[0],
        },
    )

    p_action = "criada" if p_created else "atualizada"
    print(
        f"\nProva {p_action}: {prova.materia} {prova.ano}.{prova.semestre} (id={prova.pk})"
    )
    print(f"Concluído: {len(questoes_criadas)} questões processadas.")


if __name__ == "__main__":
    main()
