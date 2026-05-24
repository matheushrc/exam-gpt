from django.db.models import (
    CASCADE,
    DO_NOTHING,
    DateField,
    FloatField,
    ForeignKey,
    IntegerField,
    JSONField,
    Manager,
    Model,
    TextField,
)
from django_mongodb_backend.fields import ArrayField


class Questao(Model):
    numero = IntegerField(
        help_text="Número ordinal da questão na prova.",
    )

    enunciado = TextField(
        help_text="Texto completo da questão, incluindo expressões matemáticas em LaTeX inline ($...$).",
    )
    subquestoes = JSONField(default=list)

    resposta = TextField(
        help_text="Resposta completa da questão, incluindo explicações e expressões matemáticas em LaTeX inline ($...$).",
        null=True,
    )

    pontuacao = FloatField(
        help_text="Pontuação da questão.",
        null=True,
    )


class Chunks(Model):
    id_questao = ForeignKey(
        to=Questao,
        on_delete=CASCADE,
    )

    question_embedding = ArrayField(FloatField(), size=768, null=True, blank=True)


class Prova(Model):
    professor = TextField()
    cursos = JSONField()
    materia = TextField()
    ano = IntegerField()
    semestre = IntegerField()
    data_aplicacao = DateField()
    numero_avaliacao = IntegerField()
    questoes = ForeignKey(
        to=Questao,
        on_delete=DO_NOTHING,
    )

    objects = Manager()
