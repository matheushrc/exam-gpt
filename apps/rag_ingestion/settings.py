from pydantic_settings import BaseSettings, SettingsConfigDict

from settings.settings import BASE_DIR


class EmbeddingsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    INDEX_PATH: str = f"{BASE_DIR}/indexes/index.tvim"
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIMS: int = 768
    EXTRACTION_MODEL: str = "gemini-3.5-flash"
    EXTRACTION_FALLBACK_MODEL: str = "gemini-3.1-flash-lite"
    INPUT_ROOT: str = f"{BASE_DIR}/input/provas"
    OUTPUT_ROOT: str = f"{BASE_DIR}/input/converted_provas"


embeddings_settings = EmbeddingsSettings()
