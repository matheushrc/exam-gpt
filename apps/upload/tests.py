from django.test import TestCase
from django.urls import reverse
from pathlib import Path

from apps.chat.settings import chat_settings


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

    def test_marked_preserves_parenthesized_math_delimiters_for_katex(self):
        upload_screen = Path("apps/upload/static/upload/js/upload-screen.js").read_text()

        self.assertIn(
            "function preserveMathDelimitersForMarkdown(source)", upload_screen
        )
        self.assertIn(
            'marked.parse(\n        preserveMathDelimitersForMarkdown(source || "")\n      )',
            upload_screen,
        )

    def test_upload_view_passes_model_presets_to_template(self):
        response = self.client.get(reverse("upload"))

        self.assertEqual(
            list(response.context["chat_model_presets"]),
            [
                "gemini-3.1-flash-lite",
                "gemini-3.5-flash",
                "gemini-3-flash-preview",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
            ],
        )

    def test_upload_page_renders_one_preset_chip_per_configured_model(self):
        response = self.client.get(reverse("upload"))
        html = response.content.decode("utf-8")

        for model in chat_settings.CHAT_MODEL_PRESETS:
            self.assertIn(f'data-model="{model}"', html)
        self.assertNotIn('data-model="gemini-3.1-flash"', html)
        self.assertNotIn('data-model="gemini-3.1-pro"', html)
