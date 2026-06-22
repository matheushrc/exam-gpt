from django.urls import path

from apps.rag_ingestion.views import ProvaExtractAPIView, ProvaSaveAPIView

urlpatterns = [
    path(
        route="provas/extract/",
        view=ProvaExtractAPIView.as_view(),
        name="api-provas-extract",
    ),
    path(route="provas/", view=ProvaSaveAPIView.as_view(), name="api-provas-save"),
]
