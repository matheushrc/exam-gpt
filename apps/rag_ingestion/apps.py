from django.apps import AppConfig


class RagIngestionConfig(AppConfig):
    name = "apps.rag_ingestion"

    def ready(self):
        import apps.rag_ingestion.signals  # noqa: F401
