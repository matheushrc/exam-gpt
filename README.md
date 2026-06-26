# Exam GPT

Projeto Django para extrair dados estruturados de provas e usar embeddings para
busca e apoio ao estudo.

As ideias de produto e notas de funcionamento ficam em [IDEAS.md](IDEAS.md).

## Configuração e Seed do Banco

### Pré-requisitos

- MongoDB rodando em `localhost:27017` (via `docker compose up mongo -d`)
- `GOOGLE_API_KEY` definida no ambiente (ou no arquivo `.env`)

### Seed das provas (a partir do terminal local)

```bash
# 1. Suba somente o MongoDB (se ainda não estiver rodando)
docker compose up mongo -d

# 2. Execute o seed — lê os JSONs em input/converted_provas/ e reconstrói o índice
GOOGLE_API_KEY="sua-chave" uv run python manage.py seed_exams
```

Se a chave já estiver no `.env`, você pode carregá-la antes:

```bash
set -a && source .env && set +a
uv run python manage.py seed_exams
```

O script conecta ao MongoDB em `localhost:27017` (padrão, configurável via `MONGO_HOST`/`MONGO_PORT` no `.env`) e regrava o índice vetorial em `indexes/index.tvim`.

---

## Checklist — Requisitos do Projeto

- ⚠️ Banco de Dados (≥ 4 entidades + CRUD) — 3 entidades ativas: `Questao`, `Chunks`, `Prova` (`Aluno`/`RespostaAluno` comentados)
- ✅ Metodologia ágil (SCRUM) — sprints em `docs/`, backlog em `IDEAS.md`
- ✅ Controle de versão (GitHub) — repositório git com commits convencionais
- ✅ Páginas de erro personalizadas (404/500) — `templates/404.html` e `500.html`
- ✅ Testes automatizados (≥ 1) — testes em `rag_search`, `chat` e `rag_ingestion`
- ✅ Integração com API externa — Google Gemini + horários UFFS (`HORARIO_ENDPOINT`)
- ✅ Upload de provas dos alunos — `apps/upload/`
- ✅ Chatbot com RAG utilizando as questões dos alunos — `apps/chat/` + `apps/rag_search/`

**Pendente:** descomentar `Aluno`/`RespostaAluno` (ou criar outra entidade) para atingir ≥ 4 entidades
