"""Configuration management for the First Story backend."""

from functools import lru_cache
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    model_config = ConfigDict(
        env_prefix="FIRST_STORY_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Application
    app_name: str = "First Story Backend"
    app_version: str = "0.1.0"
    debug: bool = False

    # Paths
    projects_root: Path = Path("projects")

    # API
    api_prefix: str = "/api/v1"

    # CORS - restricted to localhost only (any port), so the dev server can use
    # whatever port Vite falls back to without re-editing this list.
    cors_origin_regex: str = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]

    # LLM provider
    # API key is read from environment only (FIRST_STORY_LLM_API_KEY).
    # It MUST NOT be committed, echoed, or written to logs.
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-pro"
    llm_base_url: str = "https://api.deepseek.com"
    # Outbound LLM calls go through this proxy. Empty string = no proxy.
    llm_proxy: str = "http://127.0.0.1:7890"
    # Token budget placeholder (0 = unlimited; enforcement is future work).
    llm_token_budget: int = 0
    llm_timeout_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
