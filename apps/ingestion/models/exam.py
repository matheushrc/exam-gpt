from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def validate_semestre(v: int) -> int:
    if v not in (1, 2):
        raise ValueError(f"Semestre deve ser 1 ou 2, recebido: {v}.")
    return v


Semestre = Annotated[int, AfterValidator(validate_semestre)]


class QuestaoBase(BaseModel):
    enunciado: str = Field(
        description="Texto completo da questão, incluindo expressões matemáticas em LaTeX inline ($...$).",
    )
    pontuacao: float = Field(
        description="Pontuação da questão.",
        examples=[1.5, 2.0, 0.5],
        ge=0.0,
    )
    resposta: str | None = Field(
        description="Resposta completa da questão, incluindo explicações e expressões matemáticas em LaTeX inline ($...$).",
        default=None,
    )


class SubQuestao(QuestaoBase):
    label: str = Field(
        description="Rótulo da subquestão conforme aparece na prova.",
        examples=["(a)", "(b)", "(c)"],
    )


class Questao(QuestaoBase):
    numero: int = Field(description="Número ordinal da questão na prova.", ge=1)
    subquestoes: list[SubQuestao] | None = Field(
        default=None,
        description="Subquestões da questão. Null se a questão não tiver subdivisões.",
    )


class Prova(BaseModel):
    professor: str = Field(
        description="Nome completo do professor responsável pela avaliação."
    )
    cursos: list[str] | None = Field(
        description="Lista de cursos para os quais a prova foi aplicada.",
        examples=[
            ["Engenharia Civil"],
            ["Engenharia Civil", "Arquitetura"],
        ],
        default=None,
    )
    materia: str = Field(description="Nome da disciplina avaliada.")
    ano: int = Field(description="Ano de aplicação da prova.", ge=2000, le=2100)
    semestre: Semestre = Field(
        description="Semestre de aplicação: 1 para primeiro semestre, 2 para segundo semestre.",
        examples=[1, 2],
    )
    data_aplicacao: date = Field(
        description="Data de aplicação da prova.",
        examples=["2024-03-15", "2023-11-02"],
    )
    numero_avaliacao: int = Field(
        description="Número ordinal da avaliação.",
        examples=[1, 2, 3],
        ge=1,
    )
    questoes: list[Questao] = Field(
        description="Lista de questões da prova, na ordem em que aparecem.",
    )
