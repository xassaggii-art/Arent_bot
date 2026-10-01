from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    admin_chat_id: int | None = None

    flaresolverr_url: str = "http://localhost:8191"
    flaresolverr_max_timeout_ms: int = 90_000

    poll_interval_sec: int = 180
    database_path: str = "./data/bot.sqlite3"

    facebook_enabled: bool = False
    facebook_cookie: str | None = None


settings = Settings()  # type: ignore[call-arg]
