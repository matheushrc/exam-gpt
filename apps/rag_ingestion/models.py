# Autores: Matheus Henrique Rodrigues da Costa e Valtemir Gomes da Silva Junior

from typing import ClassVar

from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateField,
    FloatField,
    ForeignKey,
    IntegerField,
    JSONField,
    Manager,
    ManyToManyField,
    Model,
    PositiveIntegerField,
    TextField,
    UniqueConstraint,
)


class Questao(Model):
    ordem = IntegerField(
        help_text="Posição ordinal da questão, usada para reconstruir a ordem original — não é exibida ao usuário.",
    )

    enunciado = TextField(
        help_text="Texto completo da questão, incluindo expressões matemáticas em LaTeX inline (\\(...\\)) e blocos em $$...$$.",
    )
    subquestoes = JSONField(default=list)

    resposta = TextField(
        help_text="Resposta completa da questão, incluindo explicações e expressões matemáticas em LaTeX inline (\\(...\\)) e blocos em $$...$$.",
        null=True,
    )

    pontuacao = FloatField(
        help_text="Pontuação da questão.",
        null=True,
    )

    nota_recebida = FloatField(
        help_text="Nota recebida pelo aluno nesta questão.",
        null=True,
        blank=True,
    )

    class Meta:
        constraints: ClassVar[list] = [
            UniqueConstraint(fields=["ordem", "enunciado"], name="unique_questao"),
        ]


class Chunks(Model):
    id_questao = ForeignKey(
        to=Questao,
        on_delete=CASCADE,
    )

    turbo_id = PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints: ClassVar[list] = [
            UniqueConstraint(fields=["id_questao"], name="unique_chunk_per_questao"),
        ]


class Prova(Model):
    professor = TextField()
    cursos = JSONField()
    materia = TextField()
    ano_semestre = CharField(
        max_length=7,
        help_text="Ano e semestre no formato YYYY.S (ex: 2026.1 ou 2026.2).",
    )
    data_aplicacao = DateField()
    numero_avaliacao = IntegerField()
    questoes = ManyToManyField(to=Questao, related_name="provas")

    nota_final = FloatField(
        help_text="Nota total recebida pelo aluno nesta prova.",
        null=True,
        blank=True,
    )
    recuperacao = BooleanField(
        default=False,
        help_text="True se esta avaliação é uma recuperação.",
    )

    objects = Manager()

    class Meta:
        constraints: ClassVar[list] = [
            UniqueConstraint(
                fields=["materia", "ano_semestre", "numero_avaliacao"],
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
