from pydantic import BaseModel, Field, field_validator

from apps.rag_ingestion.schemas.prova import Prova


class ExamFileName(BaseModel):
    disciplina: str = Field(
        description="Pasta da disciplina, sem acento, em kebab-case."
    )
    nome_arquivo: str = Field(
        description="Nome do arquivo JSON no padrão de nomes da prova.",
        pattern=r"^\d{4}-\d{2}-\d{2}_np\d+(?:_rec)?(?:_p\d+)?_[a-z0-9]+(?:[._-][a-z0-9]+)*\.json$",
    )

    @field_validator("disciplina", "nome_arquivo")
    @classmethod
    def reject_path_separators(cls, value: str) -> str:
        if "/" in value or "\\" in value:
            raise ValueError("Use apenas um segmento de caminho, sem separadores.")
        return value


class ProvaComNome(Prova):
    arquivo: ExamFileName = Field(
        description="Destino sugerido para salvar a prova extraída em JSON."
    )
