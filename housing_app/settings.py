"""Runtime configuration from environment variables or the project's .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE / ".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )
    openai_api_key: SecretStr = SecretStr("")
    main_model: str = "gpt-6-luna"
    model_timeout_seconds: float = Field(90, gt=0)
    model_max_retries: int = Field(2, ge=0, le=5)
    # Optional Responses API reasoning effort (e.g. "low"); empty keeps the model default.
    model_reasoning_effort: str = ""
    # Simultaneous OpenAI conversations per process; extra requests wait their turn.
    chat_max_concurrency: int = Field(4, ge=1, le=64)
    # Earlier conversation turns replayed to the model (each turn = question + answer).
    chat_history_turns: int = Field(6, ge=0, le=50)
    naver_maps_client_id: str = ""
    naver_maps_client_secret: SecretStr = SecretStr("")
    database_path: Path = BASE / "data" / "housing.sqlite"
    chat_checkpoint_path: Path = BASE / "data" / "chat_checkpoints.sqlite"
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings; tests call ``get_settings.cache_clear()`` after changing env."""
    return Settings()
