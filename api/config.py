from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    access_token: str = ""
    refresh_token: str = ""
    device_id: str = ""
    api_key: Optional[str] = None
    token_file: str = "data/tokens.json"

    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_reload: bool = False
    log_level: str = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
