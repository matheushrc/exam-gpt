from pydantic_settings import BaseSettings, SettingsConfigDict

from settings.settings import BASE_DIR


class EmbeddingsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    INDEX_PATH: str = f"{BASE_DIR}/indexes/index.tvim"
    MAPPING_PATH: str = f"{BASE_DIR}/indexes/index_mapping.json"
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIMS: int = 768


embeddings_settings = EmbeddingsSettings()
