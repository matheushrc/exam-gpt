from django.shortcuts import render
from django.views import View

from apps.chat.settings import chat_settings


class UploadView(View):
    async def get(self, request):
        # DC "Enviar prova" screen. The empty -> processing -> review flow is
        # driven client-side against the JSON endpoints (/api/provas/extract/,
        # /api/provas/).
        return render(
            request,
            "upload/upload.html",
            {"chat_model_presets": chat_settings.CHAT_MODEL_PRESETS},
        )
