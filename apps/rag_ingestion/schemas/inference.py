import string
from typing import Any

from pydantic import BaseModel, Field, model_validator

from apps.rag_ingestion.pdf_convert import InferenceType


class InferenceCreate(BaseModel):
    inference_type: InferenceType = Field(
        "IMAGE", description="Tipo de inferência a ser utilizado"
    )
    user_prompt: str = Field(
        default="Execute sua função.",
        description="O prompt a ser enviado para o agente",
    )
    invoke_params: dict[str, str] | None = Field(
        None,
        description="Parâmetros adicionais para a invocação do agente, serão formatados no prompt_template",
    )
    image_list: bytes | list[bytes] | None = Field(
        None, description="Lista de imagens a serem enviadas junto com o prompt"
    )
    image_media_type: str = Field(
        default="image/jpeg",
        description="Tipo de mídia da imagem",
    )

    message_history: list[Any] | None = Field(
        None,
        description="Histórico de mensagens opcional a ser incluído na chamada do agente",
    )

    @model_validator(mode="after")
    def check_inference_type(self):
        if self.inference_type == "IMAGE" and not self.image_list:
            raise ValueError(
                "A lista de imagens (image_list) é obrigatória quando o tipo de inferência (inference_type) for 'IMAGE'"
            )
        return self

    @model_validator(mode="after")
    def check_invoke_params(self):
        # Detecta placeholders no prompt_template
        placeholders = [
            name for _, name, _, _ in string.Formatter().parse(self.user_prompt) if name
        ]
        if self.inference_type == "TEXT" and placeholders:
            missing = []
            if self.invoke_params is None:
                missing = placeholders
            else:
                missing = [
                    p
                    for p in placeholders
                    if p not in self.invoke_params or self.invoke_params[p] is None
                ]
            if missing:
                raise ValueError(
                    f"Os parâmetros de invocação (invoke_params) são obrigatórios para os placeholders não preenchidos: {missing}"
                )
        return self
