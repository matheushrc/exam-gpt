import string
from typing import Any, Literal

from google import genai
from pydantic import BaseModel, Field, model_validator
from pydantic_ai import Agent, BinaryContent, Tool
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider

type InferenceType = Literal["IMAGE", "TEXT"]


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


class BedrockAgent:
    def __init__(
        self,
        api_key: str,
    ):
        self.provider = genai.Client(api_key=api_key)

    def create_agent(
        self,
        output_type: type[BaseModel] | None = None,
        model_name: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        retries: int = 3,
        model_settings: dict[str, Any] | None = None,
        system_prompt: str | None = None,
        tools: list[Tool] | None = None,
        **kwargs: Any,
    ) -> Agent:
        agent_kwargs: dict[str, Any] = {
            "output_type": output_type,
            "retries": retries,
        }

        if system_prompt is not None:
            agent_kwargs["system_prompt"] = system_prompt
        if model_settings:
            agent_kwargs["model_settings"] = GoogleModelSettings(**model_settings)
        if tools:
            agent_kwargs["tools"] = tools

        return Agent(
            GoogleModel(
                model_name=model_name,
                provider=GoogleProvider(
                    client=self.provider,
                ),
            ),
            **agent_kwargs,
            **kwargs,
        )

    def get_inference(self, inference_data: InferenceCreate, agent: Agent) -> Any:
        if inference_data.invoke_params:
            inference_data.user_prompt = inference_data.user_prompt.format(
                **inference_data.invoke_params
            )

        # Prepare message content with prompt
        message_content = [inference_data.user_prompt]

        # Add image if provided
        if inference_data.image_list:
            if isinstance(inference_data.image_list, bytes):
                inference_data.image_list = [inference_data.image_list]
            for image in inference_data.image_list:
                if isinstance(image, bytes):
                    message_content.append(
                        BinaryContent(
                            data=image,
                            media_type=inference_data.image_media_type,
                        )
                    )

        # Run the agent with the content. If a message history is provided,
        # pass it as `messages` so the agent can use it as context for follow-up runs.
        run_kwargs = {}
        if inference_data.message_history:
            # pydantic-ai expects the parameter name `message_history` for prior messages
            run_kwargs["message_history"] = inference_data.message_history

        run_input = (
            message_content
            if inference_data.inference_type == "IMAGE"
            else inference_data.user_prompt
        )

        response = agent.run_sync(
            user_prompt=run_input,
            **run_kwargs,
        )
        return getattr(response, "output", response)

    async def get_inference_async(
        self,
        user_prompt: str,
        agent: Agent,
        image_content: bytes | list[bytes] | None = None,
        image_media_type: str = "image/jpeg",
        message_history: list[Any] | None = None,
    ) -> Any:
        """Async inference method that returns the full AgentRunResult.

        The caller can access:
          - result.output  — the parsed output model
          - result.usage() — RunUsage with token counts
          - result.all_messages() — message history
        """
        # Prepare message content with prompt
        message_content = [user_prompt]

        # Add images if provided
        if image_content:
            if isinstance(image_content, bytes):
                image_content = [image_content]
            for image in image_content:
                if isinstance(image, bytes):
                    message_content.append(
                        BinaryContent(
                            data=image,
                            media_type=image_media_type,
                        )
                    )

        # Run the agent with the content
        run_kwargs = {}
        if message_history:
            run_kwargs["message_history"] = message_history

        result = await agent.run(
            user_prompt=message_content if image_content else user_prompt,
            **run_kwargs,
        )

        return result
