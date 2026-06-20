from pydantic_settings import BaseSettings, SettingsConfigDict

from settings.settings import BASE_DIR


class SearchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    INDEX_PATH: str = f"{BASE_DIR}/indexes/index.tvim"
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIMS: int = 768
    TOP_K: int = 5
    MIN_SIMILARITY_SCORE: float = 0.60


search_settings = SearchSettings()
