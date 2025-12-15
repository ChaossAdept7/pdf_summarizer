"""
Application configuration and settings management.

Secrets are loaded from .env file (OPENAI_API_KEY).
All other configuration uses hardcoded defaults.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.

    Secrets (sensitive credentials) are loaded from .env file.
    Configuration parameters are hardcoded as defaults.
    """

    # ========================================
    # SECRETS (from .env file)
    # ========================================
    openai_api_key: str = Field(..., description="OpenAI API key (required)")
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model for vision tasks"
    )

    # ========================================
    # APPLICATION CONFIGURATION (hardcoded defaults)
    # ========================================

    # Application Info
    app_name: str = "PDF Summarizer API"
    app_version: str = "1.0.0"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # OpenAI Configuration
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.3
    vision_detail_level: str = "auto"  # low, high, auto

    # File Upload Settings
    max_file_size: int = 52428800  # 50MB in bytes
    max_pages: int = 100
    allowed_extensions: List[str] = [".pdf"]

    # Storage Settings
    upload_dir: Path = Path("./uploads")
    temp_dir: Path = Path("./temp")

    # History Settings
    max_history_size: int = 5

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS Settings
    cors_origins: List[str] = [
        "http://localhost:5173",  # Frontend dev server (Vite)
        "http://localhost:3000",  # Frontend in Docker
        "http://localhost:8000"   # Backend (for testing)
    ]

    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "text"

    # PDF Processing Settings
    image_format: str = "png"  # png or jpg
    image_dpi: int = 200

    # Performance Settings
    request_timeout: int = 300  # seconds
    max_concurrent_tasks: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def model_post_init(self, __context):
        """Create directories after model initialization."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_allowed_extensions_set(self) -> set:
        """Get allowed extensions as a set for fast lookup."""
        return set(self.allowed_extensions)

    def is_file_allowed(self, filename: str) -> bool:
        """Check if a filename has an allowed extension."""
        return any(filename.lower().endswith(ext) for ext in self.allowed_extensions)


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()