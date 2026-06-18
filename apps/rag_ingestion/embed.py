# ruff: noqa: E402
import json
import os
import sys
from pathlib import Path

import django
import numpy as np
from turbovec import IdMapIndex

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
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

JSON_PATH = BASE_DIR / "data" / "provas" / "redes" / "redes.json"
INDEX_PATH = embeddings_settings.INDEX_PATH
MAPPING_PATH = embeddings_settings.MAPPING_PATH
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

    # 3. Salva os embeddings associados aos chunks no banco de dados Django (MongoDB)
    for questao, embedding in zip(questoes_objs, embeddings):
        Chunks.objects.update_or_create(
            id_questao=questao,
            defaults={"question_embedding": embedding},
        )

    # 4. Reconstrói o índice Turbovec usando IdMapIndex para permitir "allowlist"
    # Mapeamos o índice com chaves numéricas sequenciais de 0 a N (uint64)
    # e salvamos a correspondência de ObjectIds no JSON
    todos_chunks = list(Chunks.objects.exclude(question_embedding=None))

    if todos_chunks:
        all_vectors = np.array(
            [c.question_embedding for c in todos_chunks], dtype=np.float32
        )
        all_ids = [str(c.id_questao_id) for c in todos_chunks]

        # Sequencial de chaves para compatibilidade com allowlists no IdMapIndex
        sequential_keys = np.arange(len(all_vectors), dtype=np.uint64)

        # Usando IdMapIndex em vez de TurboQuantIndex para liberar suporte ao parâmetro allowlist
        index = IdMapIndex(dim=EMBEDDING_DIMS, bit_width=4)
        index.add_with_ids(all_vectors, sequential_keys)

        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        index.write(str(INDEX_PATH))

        with MAPPING_PATH.open("w", encoding="utf-8") as f:
            json.dump(all_ids, f, indent=4)

        print("Índice vetorial e mapeamento salvos com sucesso!")

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
