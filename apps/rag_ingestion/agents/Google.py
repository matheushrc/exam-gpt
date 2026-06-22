from typing import Any

from google import genai
from pydantic import BaseModel
from pydantic_ai import Agent, BinaryContent, Tool
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider

from apps.rag_ingestion.schemas.inference import InferenceCreate


class GoogleAgent:
    def __init__(
        self,
        api_key: str,
    ):
        self.provider = genai.Client(api_key=api_key)

    def create_agent(
        self,
        output_type: type[BaseModel] | None = None,
        model_name: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        fallback_model_names: list[str] | None = None,
        retries: int = 3,
        model_settings: dict[str, Any] | None = None,
        system_prompt: str | None = None,
        tools: list[Tool] | None = None,
        **kwargs: Any,
    ) -> Agent:
        agent_kwargs: dict[str, Any] = {
            "retries": retries,
        }

        if output_type is not None:
            agent_kwargs["output_type"] = output_type
        if system_prompt is not None:
            agent_kwargs["system_prompt"] = system_prompt
        if model_settings:
            agent_kwargs["model_settings"] = GoogleModelSettings(**model_settings)
        if tools:
            agent_kwargs["tools"] = tools

        def _google_model(name: str) -> GoogleModel:
            return GoogleModel(
                model_name=name,
                provider=GoogleProvider(client=self.provider),
            )

        model: GoogleModel | FallbackModel = _google_model(model_name)
        if fallback_model_names:
            model = FallbackModel(
                model, *(_google_model(name) for name in fallback_model_names)
            )

        return Agent(
            model,
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
        agent: Agent,
        user_prompt: str = "",
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

    def run_stream(
        self,
        agent: Agent,
        user_prompt: str = "",
        message_history: list[Any] | None = None,
    ):
        """Returns the `agent.run_stream()` async context manager for live
        token streaming. Use as:

            async with google_client.run_stream(agent=agent, user_prompt=q) as result:
                async for delta in result.stream_text(delta=True):
                    ...
        """
        run_kwargs = {}
        if message_history:
            run_kwargs["message_history"] = message_history

        return agent.run_stream(user_prompt=user_prompt, **run_kwargs)
