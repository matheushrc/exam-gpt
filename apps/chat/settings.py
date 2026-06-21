from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DEFAULT_CHAT_MODEL: str = "gemini-3.1-flash-lite"
    DEFAULT_TOP_K: int = 5
    DEFAULT_SIMILARITY_THRESHOLD: float = 0.60
    DEFAULT_TEMPERATURE: float = 0.0
    DEFAULT_MAX_TOKENS: int = 8192


chat_settings = ChatSettings()
