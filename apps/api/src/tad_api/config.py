"""Application configuration, sourced entirely from environment variables.

No secrets have defaults — a missing required value fails fast at startup
rather than silently falling back to something that works locally but is
wrong (or dangerous) elsewhere.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TAD_", env_file=".env")

    environment: str = "local"
    log_level: str = "INFO"

    # Phase 1: in-memory storage only. Phase 2 adds a real database_url.
    # Phase 3 adds blob storage config. Not declared yet — YAGNI until the
    # phase that actually needs them.


settings = Settings()
