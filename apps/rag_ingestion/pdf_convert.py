"""
PDF intake: decide whether a PDF has a usable text layer or must be rendered as images,
then produce model-ready content either way.

Ported from src/lambdas/split_n_convert_pdf (pdf_analyzer.py + lambda_function.py),
stripped of S3/SQS/DynamoDB -- this runs synchronously in-process.
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
        boilerplate_set = {w for w, cnt in boilerplate.items() if cnt > rpt_cut}

        scores = [len(set(words) - boilerplate_set) for words in page_words]
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


def _render_page(page: fitz.Page, quality: int, grayscale: bool) -> bytes:
    pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
    mode = "RGB" if pix.n < 4 else "RGBA"
    pil_image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    return _save_image_optimized(pil_image, quality, grayscale)


def _extract_or_render_page(
    fitz_doc: fitz.Document,
    page: fitz.Page,
    image_list: list,
    quality: int,
    grayscale: bool,
) -> bytes:
    """Single dominant image on the page -> extract it as-is. Otherwise render the page."""
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
        ("TEXT", document_text)        -- PDF has a real text layer (digital exam/doc).
        ("IMAGE", [page_jpeg, ...])    -- PDF is scanned/photographed; one JPEG per page.
    """
    fitz_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    has_body, document_text, inference_type = PDFBodyAnalyzer(fitz_doc).has_body()
    if has_body:
        fitz_doc.close()
        return "TEXT", document_text

    pages: list[bytes] = []
    for page in fitz_doc:  # type: ignore
        image_list = page.get_images(full=True)
        pages.append(
            _extract_or_render_page(fitz_doc, page, image_list, quality=85, grayscale=False)
        )
    fitz_doc.close()
    return inference_type, pages
