# Fluxo de Ingestão: do Input ao Vetor no TurboVec

Existem dois caminhos de entrada, mas ambos convergem para o mesmo núcleo de persistência e indexação.

---

## Caminho 1 — Upload pelo SPA (tempo real)

```
Usuário faz upload (PDF ou fotos)
        │
        ▼
POST /api/provas/extract/   (ProvaExtractAPIView)
        │
        ├─ PDF único ──────► extract_exam_from_pdf(pdf_bytes)
        │                           │
        │                    convert_pdf(pdf_bytes)          [pdf_convert.py]
        │                           │
        │                    PDFBodyAnalyzer.has_body()
        │                     ├─ texto usável? → retorna ("TEXT", texto_extraído)
        │                     └─ escaneado?    → renderiza páginas como JPEG 300dpi
        │                           │
        │                    extract_exam_from_content(content, inference_type)
        │
        └─ fotos/imagens ──► extract_exam_from_images(images)
                                    │
                             extract_exam_from_content(images, "IMAGE")

                                    │
                             GoogleAgent + Gemini (pydantic-ai)     [agents/Google.py]
                             System prompt: EXAM_PROMPT + FILE_NAME_PROMPT
                             Output type: ProvaComNome (schema Pydantic)
                                    │
                             Retorna JSON com prova extraída para o frontend
                             (ainda não salvo no banco)
        │
        ▼
Usuário revisa/edita no frontend
        │
        ▼
POST /api/provas/           (ProvaSaveAPIView)
        │
        ▼
   [núcleo de persistência + indexação]  ← ver abaixo
```

---

## Caminho 2 — Seeding em lote (linha de comando)

```
input/provas/
  └─ <pasta ou PDF>
        │
        ▼
manage.py extract_exams                 [management/commands/extract_exams.py]
  Para cada arquivo/pasta:
    └─ extract_exam_from_pdf() ou extract_exam_from_images()
       (mesmo fluxo do Caminho 1 até o Gemini)
    └─ Salva resultado em input/converted_provas/<nome>.json
        │
        ▼
seed_exams.py  (ou manage.py seed_exams)
  seed_exam_jsons(json_root)            [embed.py]
    └─ find_exam_json_files()  → lista todos os .json
    └─ load_exam_json()        → valida estrutura
    └─ upsert_exam()           → persiste no banco  ← núcleo abaixo
    └─ get_embeddings_batch()  → gera todos os embeddings de uma vez
    └─ rebuild_vector_index()  → reconstrói o índice inteiro
```

---

## Núcleo: Persistência + Indexação

```
upsert_exam(data)                       [embed.py]
  │
  ├─ Prova.objects.update_or_create(materia, ano_semestre, numero_avaliacao)
  │    └─ professor: email → nome via datasets/docentes.csv (_resolve_professor)
  │
  ├─ Para cada questão:
  │    └─ Questao.objects.update_or_create(ordem, enunciado)
  │    └─ build_chunk(materia, ordem, enunciado, subquestoes, resposta)
  │         → monta texto: "task: search result | title: <materia> - Questão N | text: ..."
  │
  └─ prova.questoes.set(questoes)       → popula rag_ingestion_prova_questoes
  │
  └─ retorna (prova, questoes, chunk_texts)

get_embeddings_batch(client, chunk_texts)
  └─ genai.Client.models.embed_content(model="text-embedding-004", dim=768)
  └─ retorna lista de vetores float32

rebuild_vector_index(questoes, embeddings)     [embed.py]
  │
  ├─ Chunks.objects.all().delete()      → limpa mapeamento antigo
  ├─ np.array(embeddings, dtype=float32)
  ├─ turbo_ids = [0, 1, 2, ...]        → índices sequenciais
  │
  ├─ IdMapIndex(dim=768, bit_width=4)   → cria índice TurboVec (quantizado 4-bit)
  ├─ index.add_with_ids(vetores, turbo_ids)
  ├─ index.write("indexes/index.tvim") → persiste o índice em disco
  │
  └─ Para cada (questao, turbo_id):
       Chunks.objects.update_or_create(id_questao=questao, turbo_id=turbo_id)
       → salva o mapeamento turbo_id ↔ Questao no banco
```

---

## Deleção (signal)

Quando uma `Prova` é deletada (`pre_delete`):

```
signals.py → clear_chunks_for_deleted_prova
  ├─ Encontra Questões que só pertencem a esta Prova
  ├─ Busca os turbo_ids correspondentes em Chunks
  ├─ vector_index.remove_turbo_ids(turbo_ids)
  │    └─ IdMapIndex.load() → index.remove(id) → index.write()
  ├─ Chunks.objects.filter(...).delete()
  └─ Questao.objects.filter(...).delete()
```

---

## Resumo das tabelas envolvidas

| Tabela                         | O que armazena                                         |
| ------------------------------ | ------------------------------------------------------ |
| `rag_ingestion_prova`          | Metadados da prova (matéria, professor, semestre)      |
| `rag_ingestion_questao`        | Enunciado, resposta, pontuação de cada questão         |
| `rag_ingestion_prova_questoes` | Join M2M entre Prova e Questão                         |
| `rag_ingestion_chunks`         | Mapeamento `questao_id ↔ turbo_id` (posição no índice) |
| `indexes/index.tvim`           | Índice TurboVec em disco com os vetores embedados      |
