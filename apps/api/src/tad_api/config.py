"""Application configuration, sourced entirely from environment variables.

No secrets have defaults — a missing required value fails fast at startup
rather than silently falling back to something that works locally but is
wrong (or dangerous) elsewhere.
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root_schema_dir() -> Path:
    """Walk upward from this file looking for a schemas/ directory.

    Used only as the local-dev fallback when TAD_SCHEMA_DIR isn't set. The
    container always sets TAD_SCHEMA_DIR explicitly (see Dockerfile),
    because inside the container there is no schemas/ directory reachable
    by walking *up* from this file — it lives at a sibling path (/schemas),
    not an ancestor. A hardcoded parents[N] index broke three times across
    local/test/Docker before this; searching by presence and only as a
    fallback (never eagerly, so it can't crash before the env var is even
    checked) is the fix that actually survives every environment.
    """
    for candidate in Path(__file__).resolve().parents:
        schema_dir = candidate / "schemas"
        if schema_dir.is_dir():
            return schema_dir
    raise RuntimeError(
        "TAD_SCHEMA_DIR is not set, and no schemas/ directory was found "
        f"walking up from {__file__}. Set TAD_SCHEMA_DIR explicitly."
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TAD_", env_file=".env")

    environment: str = "local"
    log_level: str = "INFO"
    schema_dir: Path | None = None

    # Phase 2 adds a real database_url. Phase 3 adds blob storage config.
    # Not declared yet — YAGNI until the phase that actually needs them.

    @field_validator("schema_dir", mode="before")
    @classmethod
    def _default_schema_dir(cls, value: Path | str | None) -> Path | str:
        return value if value is not None else _find_repo_root_schema_dir()


settings = Settings()
