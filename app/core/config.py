from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "KnowledgeAssistant"
    app_version: str = "0.1.0"
    environment: str = "local"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/knowledge_assistant",
        alias="DATABASE_URL",
    )
    lm_studio_url: str = Field(default="http://127.0.0.1:1234", alias="LM_STUDIO_URL")
    llm_base_url: str = Field(default="http://127.0.0.1:1234/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="google/gemma-4-e4b", alias="LLM_MODEL")
    embedding_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        alias="EMBEDDING_BASE_URL",
    )
    embedding_model: str = Field(
        default="text-embedding-embeddinggemma-300m-qat",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")
    embedding_timeout_seconds: float = Field(default=60.0, alias="EMBEDDING_TIMEOUT_SECONDS")

    chunk_size: int = Field(default=1200, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    top_k: int = Field(default=8, alias="TOP_K")
    retrieval_min_similarity: float = Field(default=0.3, alias="RETRIEVAL_MIN_SIMILARITY")


settings = Settings()
