"""Settings from env (04 §9)."""
import logging
import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SPECIAL26_", env_file=".env", extra="ignore")

    serpapi_api_key: SecretStr | None = Field(default=None, validation_alias="SERPAPI_API_KEY")
    mode: Literal["live", "replay"] = "live"
    db_path: str = "data/special26.db"
    demo_db: str = "data/demo.db"
    record_to: str | None = None
    credit_budget_per_check: int = 14
    daily_credit_cap: int = 200
    cache_ttl_hours: int = 72
    public_base_url: str | None = None
    share_salt: str = ""
    llm_provider: Literal["none", "anthropic", "openai"] = "none"
    llm_api_key: SecretStr | None = None
    rate_limit_per_hour: int = 10
    gl: str = "in"
    hl: str = "en"
    uploads_dir: str = "data/uploads"

    def model_post_init(self, _):
        if not self.share_salt:
            self.share_salt = secrets.token_urlsafe(32)
            log.warning("SPECIAL26_SHARE_SALT not set; using a random salt, share and image links reset on restart")


@lru_cache
def get_settings() -> Settings:
    return Settings()
