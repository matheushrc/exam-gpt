from django.test import TestCase
from django.urls import reverse


class UploadViewTests(TestCase):
    def test_get_renders_upload_screen(self):
        response = self.client.get(reverse("upload"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "upload/upload.html")
