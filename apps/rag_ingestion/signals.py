from django.db.models.signals import pre_delete
from django.dispatch import receiver

from apps.rag_ingestion.models import Chunks, Prova, Questao
from apps.rag_ingestion.vector_index import remove_turbo_ids


@receiver(pre_delete, sender=Prova)
def clear_chunks_for_deleted_prova(sender, instance: Prova, **kwargs) -> None:
    question_ids = [
        questao.pk
        for questao in instance.questoes.all()
        if not questao.provas.exclude(pk=instance.pk).exists()
    ]
    if not question_ids:
        return

    chunks = Chunks.objects.filter(id_questao_id__in=question_ids).exclude(
        turbo_id=None
    )
    turbo_ids = list(chunks.values_list("turbo_id", flat=True))
    remove_turbo_ids([int(turbo_id) for turbo_id in turbo_ids])
    Chunks.objects.filter(id_questao_id__in=question_ids).delete()
    Questao.objects.filter(pk__in=question_ids).delete()
