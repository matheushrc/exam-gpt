from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DEFAULT_CHAT_MODEL: str = "gemini-3.1-flash-lite"
    DEFAULT_TOP_K: int = 5
    DEFAULT_SIMILARITY_THRESHOLD: float = 0.60
    SIMILARITY_THRESHOLD_HIGH: float = 0.85
    SIMILARITY_THRESHOLD_MEDIUM: float = 0.65
    DEFAULT_TEMPERATURE: float = 0.0
    DEFAULT_MAX_TOKENS: int = 8192

    HORARIO_ENDPOINT: str = "https://cc.uffs.edu.br/horario/"
    GROUPS_ENDPOINT: str = "https://cc.uffs.edu.br/horario/data/{semester}/groups.json"
    SCHEDULE_ENDPOINT: str = (
        "https://cc.uffs.edu.br/horario/data/{semester}/schedule.json"
    )
    CACHE_ROOT: str = "cache/schedule"


chat_settings = ChatSettings()
