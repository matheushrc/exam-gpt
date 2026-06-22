from datetime import date

from pydantic import BaseModel, Field


class Nota(BaseModel):
    """Representa a pontuação de uma questão ou subquestão."""

    nota_questao: float = Field(description="Pontuação máxima atribuída (= pontuacao).")
    nota_recebida: float | None = Field(
        default=None,
        description="Pontuação efetivamente recebida pelo aluno.",
    )


class QuestaoBase(BaseModel):
    enunciado: str = Field(
        description="Texto completo da questão em Markdown.",
        examples=[
            "**Alice** afirma que o protocolo _X_ é ineficiente. **Alice está certa?** Justifique."
        ],
    )
    pontuacao: float = Field(
        description="Pontuação da questão.",
        examples=[1.5, 2.0, 0.5],
        ge=0.0,
    )
    resposta: str | None = Field(
        description="Resposta do aluno em Markdown. Null se em branco.",
        default=None,
    )
    nota_recebida: float | None = Field(
        default=None,
        description="Nota recebida pelo aluno nesta questão/subquestão.",
    )


class SubQuestao(QuestaoBase):
    pass


class Questao(QuestaoBase):
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
    ano_semestre: str = Field(
        pattern=r"^\d{4}\.[12]$",
        description="Ano e semestre no formato 2026.1 ou 2026.2.",
        examples=["2026.1", "2026.2"],
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
    recuperacao: bool = Field(default=False)
    nota_final: float | None = Field(
        default=None,
        description="Nota total recebida pelo aluno.",
    )

    questoes: list[Questao] = Field(
        description="Lista de questões da prova, na ordem em que aparecem.",
    )
