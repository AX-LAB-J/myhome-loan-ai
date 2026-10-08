"""Independent local settings; never read the sibling project's secret .env."""

from pathlib import Path
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE / ".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )
    openai_api_key: SecretStr = SecretStr("")
    main_model: str = "gpt-6-luna"  # project/src/deep_agent_app/settings.py
    model_timeout_seconds: float = Field(90, gt=0)
    model_max_retries: int = Field(2, ge=0, le=5)
    naver_maps_client_id: str = ""
    naver_maps_client_secret: SecretStr = SecretStr("")
    database_path: Path = BASE / "data" / "housing.sqlite"
    chat_checkpoint_path: Path = BASE / "data" / "chat_checkpoints.sqlite"
