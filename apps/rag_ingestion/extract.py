"""
Async exam extraction service.

Called by:
- The upload wizard view (real-time, single folder/file)
- The `extract_exams` management command (batch)
"""

import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_ai.agent import Agent

from apps.rag_ingestion.agents.Google import GoogleAgent
from apps.rag_ingestion.pdf_convert import InferenceType
from apps.rag_ingestion.prompts import EXAM_PROMPT
from apps.rag_ingestion.schemas.prova import Prova
from settings.settings import BASE_DIR

NAMING_PROMPT_PATH = Path(BASE_DIR) / "prompts" / "files" / "naming_pattern.prompt.md"

DEFAULT_EXTRACTION_MODEL = "gemini-3.5-flash"


class ExamFileName(BaseModel):
    disciplina: str = Field(
        description="Pasta da disciplina, sem acento, em kebab-case."
    )
    nome_arquivo: str = Field(
        description="Nome do arquivo JSON no padrão de nomes da prova.",
        pattern=r"^\d{4}-\d{2}-\d{2}_np\d+(?:_rec)?(?:_p\d+)?_[a-z0-9]+(?:[._-][a-z0-9]+)*\.json$",
    )

    @field_validator("disciplina", "nome_arquivo")
    @classmethod
    def reject_path_separators(cls, value: str) -> str:
        if "/" in value or "\\" in value:
            raise ValueError("Use apenas um segmento de caminho, sem separadores.")
        return value


class ProvaComNome(Prova):
    arquivo: ExamFileName = Field(
        description="Destino sugerido para salvar a prova extraída em JSON."
    )


FILE_NAME_PROMPT = """
## Saída de nome de arquivo
- Preencha `arquivo.disciplina` e `arquivo.nome_arquivo` usando a convenção de nomes acima.
- A extensão do arquivo gerado deve ser `.json`.
- Use o usuário institucional do professor quando aparecer no documento; caso contrário,
  derive um identificador curto e estável do nome do professor, em minúsculas, sem acentos.
- Se a prova for recuperação, inclua `_rec`; se for parte específica, inclua `_p<n>`.
- Retorne somente dados extraídos ou inferidos a partir da prova.
"""


def _build_system_prompt() -> str:
    naming = NAMING_PROMPT_PATH.read_text(encoding="utf-8")
    return f"{EXAM_PROMPT.strip()}\n\n{naming.strip()}\n\n{FILE_NAME_PROMPT.strip()}"


def _make_agent(google_client: GoogleAgent, model_name: str) -> Agent:
    return google_client.create_agent(
        model_name=model_name,
        retries=10,
        output_type=ProvaComNome,
        model_settings={"max_tokens": 64000, "temperature": 0.0},
        system_prompt=_build_system_prompt(),
    )


async def extract_exam_from_content(
    content: str | list[bytes],
    inference_type: InferenceType = "IMAGE",
    *,
    source_hint: str = "",
    model_name: str = DEFAULT_EXTRACTION_MODEL,
    api_key: str | None = None,
) -> ProvaComNome:
    """
    Extract structured exam data from whatever `pdf_convert.convert_pdf()` (or a raw
    image upload) produced -- a text body, or a list of page images. Same call site
    regardless of what kind of PDF the user uploaded.

    Args:
        content: Document text (TEXT) or page/photo image bytes (IMAGE).
        inference_type: "TEXT" or "IMAGE" -- matches `pdf_convert.convert_pdf()`'s return.
        source_hint: Human-readable label for logging (e.g. folder or file name).
        model_name: Gemini model to use.
        api_key: Google API key; defaults to GOOGLE_API_KEY env var.

    Returns:
        ProvaComNome with all fields filled by the model.
        nota_final, nota_recebida, recuperacao will be None/False -- user fills these in the wizard.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is required.")
    client = GoogleAgent(api_key=key)
    agent = _make_agent(client, model_name)

    base_prompt = f"Extraia a prova completa do material anexo. Origem: {source_hint}"
    if inference_type == "TEXT":
        user_prompt = f"{base_prompt}\n\n## Conteúdo extraído do PDF\n\n{content}"
        result = await client.get_inference_async(agent=agent, user_prompt=user_prompt)
    else:
        images = content if isinstance(content, list) else [content]
        result = await client.get_inference_async(
            agent=agent, user_prompt=base_prompt, image_content=images
        )
    return result.output


async def extract_exam_from_pdf(
    pdf_bytes: bytes,
    *,
    source_hint: str = "",
    model_name: str = DEFAULT_EXTRACTION_MODEL,
    api_key: str | None = None,
) -> ProvaComNome:
    """
    Single entry point for "user uploaded a PDF of unknown kind". Runs
    `pdf_convert.convert_pdf()` to decide TEXT vs IMAGE, then delegates to
    `extract_exam_from_content()`. This is what the upload wizard and the
    `extract_exams` management command should call for PDF input.
    """
    from apps.rag_ingestion.pdf_convert import convert_pdf

    inference_type, content = convert_pdf(pdf_bytes)
    return await extract_exam_from_content(
        content,
        inference_type,
        source_hint=source_hint,
        model_name=model_name,
        api_key=api_key,
    )


async def extract_exam_from_images(
    images: list[bytes],
    *,
    source_hint: str = "",
    model_name: str = DEFAULT_EXTRACTION_MODEL,
    api_key: str | None = None,
) -> ProvaComNome:
    """Back-compat wrapper for callers that already have a flat list of image bytes
    (e.g. a folder of photographed pages, or the wizard's camera-capture flow)."""
    return await extract_exam_from_content(
        images, "IMAGE", source_hint=source_hint, model_name=model_name, api_key=api_key
    )
