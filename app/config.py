"""
Centralized application configuration.

All runtime configuration is loaded from environment variables (or a local
.env file during development). Nothing sensitive is hard-coded.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "BazaarSync WhatsApp Workflow"
    environment: str = "development"  # development | staging | production
    log_level: str = "INFO"

    # --- Database ---
    # Defaults to a local SQLite file for zero-setup local dev.
    # In production, point this at Postgres, e.g.:
    # postgresql+psycopg2://user:password@host:5432/bazaarsync
    database_url: str = "sqlite:///./bazaarsync.db"

    # --- LLM (Anthropic Claude) ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # --- WhatsApp ingestion (Twilio WhatsApp Sandbox by default) ---
    whatsapp_provider: str = "twilio"  # twilio | meta
    twilio_auth_token: str = ""
    twilio_validate_signature: bool = False  # set True in production

    # --- API security ---
    api_key: str = ""  # optional shared-secret for internal API endpoints

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so we parse the environment only once."""
    return Settings()
