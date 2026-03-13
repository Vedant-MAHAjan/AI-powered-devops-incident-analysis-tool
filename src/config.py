"""Application configuration using pydantic-settings."""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # App
    app_name: str = "AI DevOps Incident Copilot"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Ollama / LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    llm_mock_mode: bool = True

    # GitHub
    github_token: str = ""
    github_repo_owner: str = ""
    github_repo_name: str = "ai-devops-copilot"
    github_dry_run: bool = True

    # Anomaly Detection
    scan_interval: int = 30

    # Database
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'incidents.db'}"

    # Log Simulator
    simulator_enabled: bool = True
    simulator_interval: float = 2.0
    simulator_batch_size: int = 10

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
