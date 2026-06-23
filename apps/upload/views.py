from django.shortcuts import render
from django.views import View


class UploadView(View):
    async def get(self, request):
        # DC "Enviar prova" screen. The empty -> processing -> review flow is
        # driven client-side against the JSON endpoints (/api/provas/extract/,
        # /api/provas/).
        return render(request, "upload/upload.html")
