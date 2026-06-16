"""Configuration management for the First Story backend."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "First Story Backend"
    app_version: str = "0.1.0"
    debug: bool = False

    # Paths
    projects_root: Path = Path("projects")

    # API
    api_prefix: str = "/api/v1"

    # CORS - restricted to localhost for security
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]

    class Config:
        env_prefix = "FIRST_STORY_"
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
