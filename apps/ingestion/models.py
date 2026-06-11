# Autores: Matheus Henrique Rodrigues da Costa e Valtemir Gomes da Silva Junior

from typing import ClassVar

from django.db.models import (
    CASCADE,
    DO_NOTHING,
    CharField,
    DateField,
    FloatField,
    ForeignKey,
    IntegerField,
    JSONField,
    Manager,
    Model,
    TextField,
    UniqueConstraint,
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

    class Meta:
        constraints: ClassVar[list] = [
            UniqueConstraint(fields=["numero", "enunciado"], name="unique_questao"),
        ]


class Chunks(Model):
    id_questao = ForeignKey(
        to=Questao,
        on_delete=CASCADE,
    )

    question_embedding = ArrayField(FloatField(), size=768, null=True, blank=True)

    class Meta:
        constraints: ClassVar[list] = [
            UniqueConstraint(fields=["id_questao"], name="unique_chunk_per_questao"),
        ]


class Prova(Model):
    professor = TextField()
    cursos = JSONField()
    materia = TextField()
    ano = IntegerField()
    semestre = CharField(max_length=6)
    data_aplicacao = DateField()
    numero_avaliacao = IntegerField()
    questoes = ForeignKey(
        to=Questao,
        on_delete=DO_NOTHING,
    )

    objects = Manager()

    class Meta:
        constraints: ClassVar[list] = [
            UniqueConstraint(
                fields=["materia", "ano", "semestre", "numero_avaliacao"],
                name="unique_prova",
            ),
        ]


# class Aluno(Model):
#     nome = TextField()
#     matricula = CharField(max_length=20, unique=True)
#
#
# class RespostaAluno(Model):
#     """One row per student per question — never overwrites, always appends."""
#
#     questao = ForeignKey(to=Questao, on_delete=CASCADE)
#     aluno = ForeignKey(to=Aluno, on_delete=CASCADE)
#     resposta = TextField(
#         help_text="Resposta do aluno em Markdown.",
#         null=True,
#     )
#     data_envio = DateTimeField(auto_now_add=True)
#
#     class Meta:
#         constraints: ClassVar[list] = [
#             UniqueConstraint(
#                 fields=["questao", "aluno"],
#                 name="unique_resposta_por_aluno",
#             ),
#         ]
