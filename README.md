# Exam GPT

Projeto Django para extrair dados estruturados de provas e usar embeddings
para busca e apoio ao estudo (RAG). O aluno faz upload de uma prova (PDF ou
fotos), o sistema extrai as questões estruturadas via Gemini e o chat responde
perguntas sobre o conteúdo das provas já enviadas, citando as fontes.

## Pré-requisitos

- Docker e Docker Compose

## Setup

1. Copie o arquivo de exemplo de variáveis de ambiente:

   ```bash
   cp .env.example .env
   ```

2. Gere um `SECRET_KEY` e cole no `.env`:

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

3. Gere uma `GOOGLE_API_KEY` própria em
   [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys) e cole
   no `.env`. Sem essa chave, o upload de provas e o chat não respondem —
   isso é esperado, não um bug: o projeto não distribui uma chave
   compartilhada.

## Rodando

```bash
docker compose up --build
```

Acesse `http://localhost:8000` (ou a porta configurada em `PORT` no `.env`).

## Testando de verdade (golden path)

1. Abra a tela de upload e envie uma prova de exemplo (PDF ou fotos).
2. Aguarde a extração terminar — a prova aparece com as questões estruturadas.
3. Abra o chat e pergunte sobre o conteúdo da prova enviada.

Esse fluxo não depende de rodar `seed_exams`/`extract_exams` nem de ter dados
pré-carregados — é a forma mais rápida de comprovar a integração com a IA.

## Avançado (opcional)

Para processar um lote de provas já salvas localmente em `input/provas/`
(imagens ou PDFs, com ou sem texto extraível):

```bash
uv run python manage.py extract_exams
uv run python manage.py seed_exams
```

Essas duas rotinas usam a `GOOGLE_API_KEY` de verdade e consomem cota real da
API — evite rodá-las repetidamente sem necessidade.

O comando abaixo baixa e cacheia localmente os dados de horário/professores
da UFFS. Hoje isso alimenta só a API (`/api/semesters/`, `/api/professors/`),
usada para preparar uma futura filtragem por professor/semestre no chat —
ainda não há nenhum seletor na UI que dependa disso, então pular este passo
não afeta o uso atual do app:

```bash
docker compose exec provas-gpt python manage.py sync_schedule
```

## Troubleshooting

- **Porta já em uso:** mude `PORT` no `.env` antes de subir o compose, ou pare
  o processo que já está usando a porta configurada.
- **Mongo "connection refused" no primeiro `up`:** o container do app pode
  subir antes do Mongo ficar pronto para aceitar conexões; rode
  `docker compose up --build` novamente ou aguarde alguns segundos e recarregue
  a página.
- **Upload/chat não respondem ou retornam erro silencioso:** confira se
  `GOOGLE_API_KEY` está preenchida no `.env` e é uma chave válida gerada em
  [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys) — sem
  ela, as chamadas ao Gemini falham.
- **`.env` não é lido pelo compose:** confirme que o arquivo `.env` existe na
  raiz do repo (não só o `.env.example`) antes de rodar `docker compose up`.

## Mais documentação

- [`docs/IDEAS.md`](docs/IDEAS.md) — backlog e ideias de produto
- [`docs/CONCERNS.md`](docs/CONCERNS.md) — questões em aberto conhecidas
- [`DESIGN.md`](DESIGN.md) — sistema de design e tokens de UI
- [`docs/FLUXO_INGESTION.md`](docs/FLUXO_INGESTION.md) — fluxo completo de
  ingestão, do input ao vetor indexado
