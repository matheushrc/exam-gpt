"""
Async exam extraction service.

Called by:
- The SPA upload extraction endpoint (real-time, single folder/file)
- The `extract_exams` management command (batch)
"""

import os

from pydantic_ai.agent import Agent

from apps.rag_ingestion.agents.Google import GoogleAgent
from apps.rag_ingestion.pdf_convert import InferenceType
from apps.rag_ingestion.prompts import (
    EXAM_PROMPT,
    EXTRACTION_USER_PROMPT,
    FILE_NAME_PROMPT,
)
from apps.rag_ingestion.schemas.exam_file_name import ProvaComNome
from apps.rag_ingestion.settings import embeddings_settings

DEFAULT_EXTRACTION_MODEL = embeddings_settings.EXTRACTION_MODEL


def _build_system_prompt() -> str:
    return f"{EXAM_PROMPT.strip()}\n\n{FILE_NAME_PROMPT.strip()}"


def _make_agent(google_client: GoogleAgent, model_name: str) -> Agent:
    return google_client.create_agent(
        model_name=model_name,
        fallback_model_names=[embeddings_settings.EXTRACTION_FALLBACK_MODEL],
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
        nota_final, nota_recebida, recuperacao will be None/False -- the user fills these in on the review screen.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is required.")
    client = GoogleAgent(api_key=key)
    agent = _make_agent(client, model_name)

    base_prompt = EXTRACTION_USER_PROMPT.format(source_hint=source_hint)
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
    `extract_exam_from_content()`. This is what the SPA upload endpoint and
    the `extract_exams` management command should call for PDF input.
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
    (e.g. a folder of photographed pages, or the camera-capture upload flow)."""
    return await extract_exam_from_content(
        images, "IMAGE", source_hint=source_hint, model_name=model_name, api_key=api_key
    )
