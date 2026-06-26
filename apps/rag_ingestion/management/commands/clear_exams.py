from django.core.management.base import BaseCommand

from apps.rag_ingestion.models import Prova


class Command(BaseCommand):
    help = "Remove all exams from the database and clear their vectors from the index."

    def handle(self, *args, **options):
        count = Prova.objects.count()
        Prova.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} prova(s)."))
