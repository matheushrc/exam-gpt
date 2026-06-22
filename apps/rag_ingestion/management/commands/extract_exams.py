"""
Batch-extract exam material from input/provas -> input/converted_provas.
Replaces the root-level get_exam_json.py script.

Accepts, mixed together under input/provas: folders of photographed pages
(.jpg/.jpeg/.png) AND standalone PDFs of any kind -- digital/text-based,
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
    DEFAULT_EXTRACTION_MODEL,
    ProvaComNome,
    extract_exam_from_images,
    extract_exam_from_pdf,
)
from apps.rag_ingestion.settings import embeddings_settings
from apps.rag_ingestion.utils import load_images_from_folder

INPUT_ROOT = Path(embeddings_settings.INPUT_ROOT)
OUTPUT_ROOT = Path(embeddings_settings.OUTPUT_ROOT)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSION = ".pdf"


def safe_segment(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    normalized = re.sub(r"[^a-z0-9._-]+", "-", normalized).strip(".-_")
    if not normalized or normalized in {".", ".."}:
        raise ValueError(f"Invalid path segment: {value!r}")
    return normalized


def write_exam_json(exam: ProvaComNome, output_root: Path) -> Path:
    disciplina = safe_segment(exam.arquivo.disciplina)
    file_name = safe_segment(exam.arquivo.nome_arquivo)
    if not file_name.endswith(".json"):
        file_name = f"{Path(file_name).stem}.json"

    output_path = (output_root / disciplina / file_name).resolve()
    output_root_resolved = output_root.resolve()
    if output_root_resolved not in output_path.parents:
        raise ValueError(f"Resolved output path escapes OUTPUT_ROOT: {output_path}")

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
    """Standalone PDFs anywhere under input_root -- any kind: text-based or scanned."""
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
        stdout.write(f"  Extracting {folder.name}...")
        exam = await extract_exam_from_images(
            images,
            source_hint=folder.relative_to(INPUT_ROOT).as_posix(),
            model_name=model_name,
        )
        out = write_exam_json(exam, OUTPUT_ROOT)
        stdout.write(f"  -> {out}")
        return out


async def _process_pdf(
    pdf_path: Path,
    model_name: str,
    semaphore: asyncio.Semaphore,
    stdout,
) -> Path:
    async with semaphore:
        stdout.write(f"  Extracting {pdf_path.name}...")
        exam = await extract_exam_from_pdf(
            pdf_path.read_bytes(),
            source_hint=pdf_path.relative_to(INPUT_ROOT).as_posix(),
            model_name=model_name,
        )
        out = write_exam_json(exam, OUTPUT_ROOT)
        stdout.write(f"  -> {out}")
        return out


class Command(BaseCommand):
    help = (
        "Batch-extract exam material (photo folders or PDFs of any kind) "
        "from input/provas to input/converted_provas."
    )

    def add_arguments(self, parser):
        parser.add_argument("--model", default=DEFAULT_EXTRACTION_MODEL)
        parser.add_argument("--concurrency", type=int, default=2)

    def handle(self, *args, **options):
        if not os.environ.get("GOOGLE_API_KEY"):
            self.stderr.write("GOOGLE_API_KEY is required.")
            return

        folders = find_exam_folders(INPUT_ROOT)
        pdfs = find_exam_pdfs(INPUT_ROOT)
        if not folders and not pdfs:
            self.stderr.write(f"No exam material found under {INPUT_ROOT}.")
            return

        self.stdout.write(f"Found {len(folders)} folder(s) and {len(pdfs)} PDF(s).")
        semaphore = asyncio.Semaphore(options["concurrency"])
        tasks = [
            _process_folder(f, options["model"], semaphore, self.stdout)
            for f in folders
        ] + [_process_pdf(p, options["model"], semaphore, self.stdout) for p in pdfs]
        results = asyncio.run(asyncio.gather(*tasks))
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(results)} JSON file(s)."))
