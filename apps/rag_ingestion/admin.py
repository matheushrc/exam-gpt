from django.contrib import admin

from .models import Chunks, Prova, Questao

ProvaQuestao = Prova.questoes.through


class ProvaQuestaoInline(admin.TabularInline):
    model = ProvaQuestao
    extra = 0
    raw_id_fields = ("questao",)


@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    list_display = ("id", "ordem", "pontuacao", "nota_recebida")
    search_fields = ("enunciado", "resposta")
    list_filter = ("pontuacao",)


@admin.register(Chunks)
class ChunksAdmin(admin.ModelAdmin):
    list_display = ("id", "id_questao", "turbo_id")
    search_fields = ("turbo_id",)
    raw_id_fields = ("id_questao",)


@admin.register(ProvaQuestao)
class ProvaQuestaoAdmin(admin.ModelAdmin):
    list_display = ("id", "prova", "questao")
    raw_id_fields = ("prova", "questao")


@admin.register(Prova)
class ProvaAdmin(admin.ModelAdmin):
    list_display = ("id", "materia", "professor", "ano_semestre", "numero_avaliacao", "recuperacao", "nota_final")
    search_fields = ("materia", "professor", "ano_semestre")
    list_filter = ("recuperacao", "ano_semestre")
    inlines = [ProvaQuestaoInline]
