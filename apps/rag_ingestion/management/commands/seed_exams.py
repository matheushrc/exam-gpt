from pathlib import Path

from django.core.management.base import BaseCommand

from apps.rag_ingestion.embed import DEFAULT_JSON_ROOT, seed_exam_jsons


class Command(BaseCommand):
    help = "Seed exam JSON files and rebuild the vector index."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json-root",
            type=Path,
            default=DEFAULT_JSON_ROOT,
            help="JSON file or directory to ingest.",
        )

    def handle(self, *args, **options):
        result = seed_exam_jsons(options["json_root"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {result.provas} exams, {result.questoes} questions, "
                f"{result.chunks} chunks. Index: {result.index_path}"
            )
        )
