from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    AI_PROVIDER: Literal["chatgpt_desktop", "local_http", "codex_cli"] = "chatgpt_desktop"
    IMAGE_PROVIDER: Literal["chatgpt_desktop", "openai", "codex_cli"] | None = None
    IMAGE_API_BASE_URL: str = "https://api.openai.com/v1"
    IMAGE_API_KEY: str | None = None
    IMAGE_API_MODEL: str = "gpt-image-1"
    ENABLE_LOCAL_SETTINGS: bool = True
    LOCAL_GPT_BASE_URL: str = "http://127.0.0.1:1234/v1"
    LOCAL_GPT_API_KEY: str | None = None
    COMIC_FONT_PATH: str | None = None
    MAX_MODEL_REQUESTS_PER_TASK: int = Field(default=96, ge=1, le=1000)
    GPT_TIMEOUT: float = 180.0
    CODEX_CLI_PATH: str | None = None
    CODEX_MODEL: str = ""
    CODEX_TIMEOUT: int = Field(default=600, ge=30, le=1800)
    IMAGE_EDIT_PROVIDER: Literal["chatgpt_desktop", "openai", "codex_cli"] = "chatgpt_desktop"
    IMAGE_EDIT_BASE_URL: str | None = None
    IMAGE_EDIT_API_KEY: str | None = None
    IMAGE_EDIT_MODEL: str = "gpt-image-1"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    POSTGRES_URL: str | None = None
    REDIS_URL: str | None = None
    MINIO_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str | None = None
    MINIO_SECRET_KEY: str | None = None
    MINIO_BUCKET_NAME: str = "comic-images"

    QWEN_API_KEY: str | None = None
    QWEN_API_BASE_URL: str = "https://api.doubao.com/v1"
    QWEN_IMAGE_API_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None

    DEFAULT_TEXT_MODEL: str = "doubao-pro"
    DEFAULT_INFERENCE_MODEL: str = "doubao-pro"
    DEFAULT_VISION_MODEL: str = "doubao-pro"
    DEFAULT_IMAGE_MODEL: str = "doubao-pro"

    SD_WEBUI_URL: str = "http://localhost:7860"
    SD_WEBUI_API_KEY: str | None = None
    CHROMA_DB_URL: str = "http://localhost:8001"
    CHROMA_DB_AUTH_CREDENTIALS: str = "admin:admin"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None


    @property
    def image_provider(self):
        return self.IMAGE_PROVIDER or ("chatgpt_desktop" if self.AI_PROVIDER in {"chatgpt_desktop", "codex_cli"} else "openai")


settings = Settings()
