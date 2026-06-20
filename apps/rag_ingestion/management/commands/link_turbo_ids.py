import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.rag_ingestion.models import Chunks, Questao
from settings.settings import BASE_DIR


class Command(BaseCommand):
    help = "Backfill Chunks.turbo_id from an existing Turbovec index_mapping.json file."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--mapping-path",
            default=str(BASE_DIR / "indexes" / "index_mapping.json"),
            help="Path to the legacy index_mapping.json file.",
        )

    def handle(self, *args, **options) -> None:
        mapping_path = Path(options["mapping_path"])
        if not mapping_path.exists():
            raise CommandError(f"Mapping file not found: {mapping_path}")

        with mapping_path.open(encoding="utf-8") as mapping_file:
            question_ids = json.load(mapping_file)

        linked = 0
        missing = 0
        for turbo_id, question_id in enumerate(question_ids):
            questao = Questao.objects.filter(id=question_id).first()
            if questao is None:
                missing += 1
                continue

            Chunks.objects.update_or_create(
                id_questao=questao,
                defaults={"turbo_id": turbo_id},
            )
            linked += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Linked {linked} chunks to Turbovec IDs; {missing} questions missing."
            )
        )
