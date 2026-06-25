from django.test import TestCase
from django.urls import reverse
from pathlib import Path


class UploadViewTests(TestCase):
    def test_get_renders_upload_screen(self):
        response = self.client.get(reverse("upload"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "upload/upload.html")

    def test_upload_screen_normalizes_extracted_escaped_newlines(self):
        upload_screen = Path(
            "apps/upload/static/upload/js/upload-screen.js"
        ).read_text()

        self.assertIn("function normalizeExtractedText(value)", upload_screen)
        self.assertIn('replace(/\\\\n/g, "\\n")', upload_screen)
        self.assertIn("q.enunciado = normalizeExtractedText(q.enunciado)", upload_screen)
        self.assertIn("q.resposta = normalizeExtractedText(q.resposta)", upload_screen)
        self.assertIn("sub.enunciado = normalizeExtractedText(sub.enunciado)", upload_screen)
        self.assertIn("sub.resposta = normalizeExtractedText(sub.resposta)", upload_screen)

    def test_katex_does_not_use_single_dollar_inline_delimiters(self):
        upload_screen = Path("apps/upload/static/upload/js/upload-screen.js").read_text()

        self.assertIn('{ left: "\\\\(", right: "\\\\)", display: false }', upload_screen)
        self.assertNotIn('{ left: "$", right: "$", display: false }', upload_screen)
