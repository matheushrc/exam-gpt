# Step 04 — Migrate `get_exam_json.py` → `rag_ingestion`

> **Context:** see [context.md](context.md) for the overall plan, wave execution order, and dependency graph.
> **Prerequisite:** Step 01 (models updated, new fields exist in schema).
> **Touches:** `get_exam_json.py` (root), `apps/rag_ingestion/`.
> **One agent handles this entire step.**

---

## Rationale

`get_exam_json.py` currently lives at the project root and runs as a standalone script.  
It needs to:

1. Become callable from the upload wizard (step 05) as an async Django service
2. Reflect the new model fields (`nota_final`, `nota_recebida`, `recuperacao`, `ano_semestre`)
3. Still work as a batch CLI tool (management command)
4. **Accept any uploaded PDF** — not just pre-converted image folders. A user may upload a
   text-based PDF (digital exam, exported doc), a scanned/photographed PDF (image-based,
   no extractable text layer), or loose photos. All three must converge on the same
   extraction call.

`src/lambdas/split_n_convert_pdf` already solves the "what kind of PDF is this and how do I
turn it into model-ready input" problem for the geogis-ai pipeline (it inspects the PDF body,
decides `TEXT` vs `IMAGE` inference, and renders pages to JPEG when there's no usable text
layer). Step 4.0 ports that logic into this project, stripped of anything AWS-specific
(no S3, no SQS, no DynamoDB job table) so it runs synchronously inside a Django request or
management command.

---

## 4.0 — Port PDF conversion: `apps/rag_ingestion/pdf_convert.py`

Ported from `src/lambdas/split_n_convert_pdf/pdf_analyzer.py` and `lambda_function.py`.
Same body-detection heuristic (`RefinedDocument` + uniqueness ratio) and same
extract-dominant-image-or-render-page strategy, but synchronous and S3-free: it takes raw
PDF bytes in, returns text or image bytes out.

```python
"""
PDF intake: decide whether a PDF has a usable text layer or must be rendered as images,
then produce model-ready content either way.

Ported from src/lambdas/split_n_convert_pdf (pdf_analyzer.py + lambda_function.py),
stripped of S3/SQS/DynamoDB — this runs synchronously in-process.
"""
import collections
import io
import re
from typing import Literal

import fitz
from PIL import Image
from refinedoc.refined_document import RefinedDocument

InferenceType = Literal["TEXT", "IMAGE"]


class PDFBodyAnalyzer:
    """Decides whether a PDF has a substantial, non-boilerplate text body."""

    def __init__(self, doc: fitz.Document):
        self.document_text = [page.get_text().split("\n") for page in doc]  # type: ignore
        self.refined_doc = RefinedDocument(content=self.document_text, win=5)

    def _evaluate_text_uniqueness(
        self, repetition_threshold: float = 0.5, min_unique_words: int = 20
    ) -> dict:
        boilerplate = collections.Counter()
        page_words = []
        for t in self.document_text:
            page_text = " ".join(t) if t else ""
            words = [w.lower() for w in re.findall(r"\w+", page_text)]
            page_words.append(words)
            boilerplate.update(set(words))

        num_pages = len(page_words)
        rpt_cut = repetition_threshold * num_pages
        boilerplate = {w for w, cnt in boilerplate.items() if cnt > rpt_cut}

        scores = [len(set(words) - boilerplate) for words in page_words]
        substantial_pages = sum(1 for s in scores if s >= min_unique_words)
        return {
            "total_pages": num_pages,
            "ratio": substantial_pages / num_pages if num_pages else 0,
        }

    def has_body(
        self,
        repetition_threshold: float = 0.5,
        min_unique_words: int = 20,
        uniqueness_ratio: float = 0.7,
    ) -> tuple[bool, str, InferenceType]:
        try:
            bodies = self.refined_doc.body
            document_text = "\n".join(line for body in bodies for line in body)
            analysis = self._evaluate_text_uniqueness(
                repetition_threshold=repetition_threshold,
                min_unique_words=min_unique_words,
            )
            if (
                len(bodies) > 0
                and any(len(line.strip()) > 0 for body in bodies for line in body)
                and analysis["ratio"] > uniqueness_ratio
            ):
                return True, document_text, "TEXT"
        except (OSError, ValueError, AttributeError):
            return False, "", "IMAGE"
        return False, "", "IMAGE"


def _save_image_optimized(image: Image.Image, quality: int, grayscale: bool) -> bytes:
    if grayscale:
        image = image.convert("L")
    buf = io.BytesIO()
    image.save(buf, quality=quality, format="JPEG")
    return buf.getvalue()


def _render_page(page: "fitz.Page", quality: int, grayscale: bool) -> bytes:
    pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
    mode = "RGB" if pix.n < 4 else "RGBA"
    pil_image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    return _save_image_optimized(pil_image, quality, grayscale)


def _extract_or_render_page(
    fitz_doc: "fitz.Document",
    page: "fitz.Page",
    image_list: list,
    quality: int,
    grayscale: bool,
) -> bytes:
    """Single dominant image on the page → extract it as-is. Otherwise render the page."""
    if not image_list:
        return _render_page(page, quality, grayscale)

    img_areas = sorted(
        ((img[2] * img[3], img) for img in image_list), key=lambda x: x[0], reverse=True
    )
    largest_area, largest_img = img_areas[0]
    is_dominant = len(img_areas) == 1 or largest_area > img_areas[1][0] * 3
    if is_dominant:
        base_image = fitz_doc.extract_image(largest_img[0])
        if base_image:
            try:
                image = Image.open(io.BytesIO(base_image["image"]))
                return _save_image_optimized(image, quality, grayscale)
            except (OSError, ValueError):
                pass
    return _render_page(page, quality, grayscale)


def convert_pdf(pdf_bytes: bytes) -> tuple[InferenceType, str | list[bytes]]:
    """
    Convert any uploaded PDF into model-ready content.

    Returns:
        ("TEXT", document_text)        — PDF has a real text layer (digital exam/doc).
        ("IMAGE", [page_jpeg, ...])     — PDF is scanned/photographed; one JPEG per page.
    """
    fitz_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    has_body, document_text, inference_type = PDFBodyAnalyzer(fitz_doc).has_body()
    if has_body:
        fitz_doc.close()
        return "TEXT", document_text

    pages: list[bytes] = []
    for page in fitz_doc:  # type: ignore
        image_list = page.get_images(full=True)
        pages.append(_extract_or_render_page(fitz_doc, page, image_list, quality=85, grayscale=False))
    fitz_doc.close()
    return inference_type, pages
```

`refinedoc` and `pymupdf` (`fitz`) are already project dependencies (`pyproject.toml`), so no
new packages are needed.

---

## 4.1 — Create the extraction service module

**`apps/rag_ingestion/extract.py`** — pure async extraction logic, no Django management command scaffolding:

```python
"""
Async exam extraction service.

Called by:
- The upload wizard view (real-time, single folder)
- The `extract_exams` management command (batch)
"""
import asyncio
import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_ai.agent import Agent

from apps.rag_ingestion.agents.Google import GoogleAgent
from apps.rag_ingestion.prompts import EXAM_PROMPT
from apps.rag_ingestion.schemas.prova import Prova
from apps.rag_ingestion.utils import load_images_from_folder

NAMING_PROMPT_PATH = Path("prompts/naming_pattern.prompt.md")

# Modelo confirmado: gemini-3.5-flash (mesmo valor que já está em get_exam_json.py)
DEFAULT_EXTRACTION_MODEL = "gemini-3.5-flash"


class ExamFileName(BaseModel):
    disciplina: str = Field(description="Pasta da disciplina, sem acento, em kebab-case.")
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
    image upload) produced — a text body, or a list of page images. Same call site
    regardless of what kind of PDF the user uploaded.

    Args:
        content: Document text (TEXT) or page/photo image bytes (IMAGE).
        inference_type: "TEXT" or "IMAGE" — matches `pdf_convert.convert_pdf()`'s return.
        source_hint: Human-readable label for logging (e.g. folder or file name).
        model_name: Gemini model to use. Default: gemini-3.5-flash.
        api_key: Google API key; defaults to GOOGLE_API_KEY env var.

    Returns:
        ProvaComNome with all fields filled by the model.
        nota_final, nota_recebida, recuperacao will be None/False — user fills these in the wizard.
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
    `extract_exam_from_content()`. This is what the upload wizard (step 05) and the
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
    (e.g. a folder of photographed pages, or step 05's camera-capture flow)."""
    return await extract_exam_from_content(
        images, "IMAGE", source_hint=source_hint, model_name=model_name, api_key=api_key
    )
```

Add `from apps.rag_ingestion.pdf_convert import InferenceType` to the import block at the top
of `extract.py` (defined in step 4.0).

---

## 4.2 — Management command: `extract_exams` (batch CLI replacement)

**`apps/rag_ingestion/management/commands/extract_exams.py`**

```python
"""
Batch-extract exam material from input/provas → input/converted_provas.
Replaces the root-level get_exam_json.py script.

Accepts, mixed together under input/provas: folders of photographed pages
(.jpg/.jpeg/.png) AND standalone PDFs of any kind — digital/text-based,
scanned/image-based, or single/multi-page. Each item is routed to the right
extraction path automatically; the model-facing call is identical either way.

Usage:
  uv run python manage.py extract_exams
  uv run python manage.py extract_exams --concurrency 4
  uv run python manage.py extract_exams --model gemini-2.5-flash
"""
import asyncio
import json
import os
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.rag_ingestion.extract import (
    ProvaComNome,
    extract_exam_from_images,
    extract_exam_from_pdf,
)
from apps.rag_ingestion.utils import load_images_from_folder

INPUT_ROOT = Path("input/provas")
OUTPUT_ROOT = Path("input/converted_provas")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSION = ".pdf"


def safe_segment(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    )
    normalized = re.sub(r"[^a-z0-9._-]+", "-", normalized).strip(".-_")
    if not normalized:
        raise ValueError(f"Invalid path segment: {value!r}")
    return normalized


def write_exam_json(exam: ProvaComNome, output_root: Path) -> Path:
    disciplina = safe_segment(exam.arquivo.disciplina)
    file_name = safe_segment(exam.arquivo.nome_arquivo)
    if not file_name.endswith(".json"):
        file_name = f"{Path(file_name).stem}.json"
    output_path = output_root / disciplina / file_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(exam.model_dump(mode="json"), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def find_exam_folders(input_root: Path) -> list[Path]:
    """Folders that contain loose page photos (not PDFs)."""
    folders: list[Path] = []
    for folder, _, files in os.walk(input_root):
        path = Path(folder)
        if any(Path(f).suffix.lower() in IMAGE_EXTENSIONS for f in files):
            folders.append(path)
    return sorted(folders, key=lambda p: p.relative_to(input_root).as_posix())


def find_exam_pdfs(input_root: Path) -> list[Path]:
    """Standalone PDFs anywhere under input_root — any kind: text-based or scanned."""
    pdfs = [
        Path(folder) / f
        for folder, _, files in os.walk(input_root)
        for f in files
        if Path(f).suffix.lower() == PDF_EXTENSION
    ]
    return sorted(pdfs, key=lambda p: p.relative_to(input_root).as_posix())


async def _process_folder(
    folder: Path,
    model_name: str,
    semaphore: asyncio.Semaphore,
    stdout,
) -> Path:
    async with semaphore:
        images = load_images_from_folder(str(folder))
        stdout.write(f"  Extracting {folder.name}…")
        exam = await extract_exam_from_images(
            images,
            source_hint=folder.relative_to(INPUT_ROOT).as_posix(),
            model_name=model_name,
        )
        out = write_exam_json(exam, OUTPUT_ROOT)
        stdout.write(f"  → {out}")
        return out


async def _process_pdf(
    pdf_path: Path,
    model_name: str,
    semaphore: asyncio.Semaphore,
    stdout,
) -> Path:
    async with semaphore:
        stdout.write(f"  Extracting {pdf_path.name}…")
        exam = await extract_exam_from_pdf(
            pdf_path.read_bytes(),
            source_hint=pdf_path.relative_to(INPUT_ROOT).as_posix(),
            model_name=model_name,
        )
        out = write_exam_json(exam, OUTPUT_ROOT)
        stdout.write(f"  → {out}")
        return out


class Command(BaseCommand):
    help = (
        "Batch-extract exam material (photo folders or PDFs of any kind) "
        "from input/provas to input/converted_provas."
    )

    def add_arguments(self, parser):
        parser.add_argument("--model", default="gemini-3.5-flash")
        parser.add_argument("--concurrency", type=int, default=2)

    def handle(self, *args, **options):
        folders = find_exam_folders(INPUT_ROOT)
        pdfs = find_exam_pdfs(INPUT_ROOT)
        if not folders and not pdfs:
            self.stderr.write(f"No exam material found under {INPUT_ROOT}.")
            return
        self.stdout.write(f"Found {len(folders)} folder(s) and {len(pdfs)} PDF(s).")
        semaphore = asyncio.Semaphore(options["concurrency"])
        tasks = [
            _process_folder(f, options["model"], semaphore, self.stdout) for f in folders
        ] + [_process_pdf(p, options["model"], semaphore, self.stdout) for p in pdfs]
        results = asyncio.run(asyncio.gather(*tasks))
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(results)} JSON file(s)."))
```

---

## 4.3 — Delete root `get_exam_json.py`

This is not a production system and there's no need for backwards compatibility. Delete
`get_exam_json.py` outright — `manage.py extract_exams` fully replaces it.

---

## 4.4 — Update `AGENTS.md`

Replace:

```
- `PYTHONPATH=... uv run python get_exam_json.py`: convert raw exam images…
```

With:

```
- `uv run python manage.py extract_exams`: batch-extract exam material (photo folders or PDFs of any kind —
  text-based or scanned) from `input/provas` → `input/converted_provas`.
  Options: `--model gemini-3.5-flash` (default), `--concurrency 2`.
```

---

## 4.5 — Verify

```bash
# Smoke test: runs on first folder found under input/provas if any exist
uv run python manage.py extract_exams --concurrency 1
uv run python manage.py test apps.rag_ingestion
uv run ruff check .
```

---

## Completion Checklist

- [ ] `apps/rag_ingestion/pdf_convert.py` created with `convert_pdf()`, ported from
      `src/lambdas/split_n_convert_pdf` (no S3/SQS/DynamoDB)
- [ ] `apps/rag_ingestion/extract.py` created with `extract_exam_from_content()`,
      `extract_exam_from_pdf()`, and the `extract_exam_from_images()` back-compat wrapper
- [ ] `apps/rag_ingestion/management/commands/extract_exams.py` created and handles
      both photo folders and standalone PDFs (text-based or scanned) under `input/provas`
- [ ] Root `get_exam_json.py` deleted
- [ ] `AGENTS.md` updated
- [ ] `uv run python manage.py check` passes
- [ ] `ruff check .` clean
