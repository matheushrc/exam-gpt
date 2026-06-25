# Exam GPT

Projeto Django para extrair dados estruturados de provas e usar embeddings para
busca e apoio ao estudo.

As ideias de produto e notas de funcionamento ficam em [IDEAS.md](IDEAS.md).

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
