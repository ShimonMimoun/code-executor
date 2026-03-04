"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, TomlConfigSettingsSource
from typing import List, Type, Tuple


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    # --- App ---
    app_name: str = "Code Executor Platform"
    app_version: str = "1.0.0"
    debug: bool = False

    # --- API ---
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --- Auth ---
    api_keys: List[str] = ["dev-api-key-change-me"]

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"
    result_ttl_seconds: int = 3600  # 1 hour

    # --- Docker Sandbox ---
    docker_base_url: str = "unix:///var/run/docker.sock"
    sandbox_image: str = "code-executor-sandbox:latest"
    default_timeout: int = 30  # seconds
    max_timeout: int = 120
    default_memory_limit: str = "256m"
    max_memory_limit: str = "512m"
    default_cpu_limit: float = 1.0
    max_concurrent_executions: int = 10

    # --- Supported Languages Configuration ---
    supported_languages: List[str] = [
        "python",
        "javascript",
        "go",
        "bash",
        "java",
        "csharp",
        "html",
        "react",
    ]

    # Python
    python_versions: dict[str, str] = {
        "3.9": "python:3.9-slim", "3.10": "python:3.10-slim", 
        "3.11": "python:3.11-slim", "3.12": "python:3.12-slim", "3.13": "python:3.13-slim"
    }
    python_default_version: str = "3.12"

    # Node.js
    javascript_versions: dict[str, str] = {
        "18": "node:18-slim", "19": "node:19-slim", "20": "node:20-slim", 
        "21": "node:21-slim", "22": "node:22-slim", "23": "node:23-slim", "24": "node:24-slim"
    }
    javascript_default_version: str = "22"

    # Go
    go_versions: dict[str, str] = {
        "1.20": "golang:1.20-alpine", "1.21": "golang:1.21-alpine", 
        "1.22": "golang:1.22-alpine", "1.23": "golang:1.23-alpine"
    }
    go_default_version: str = "1.22"

    # Java
    java_versions: dict[str, str] = {
        "17": "eclipse-temurin:17-jdk-alpine", "21": "eclipse-temurin:21-jdk-alpine", 
        "22": "eclipse-temurin:22-jdk-alpine", "23": "eclipse-temurin:23-jdk-alpine"
    }
    java_default_version: str = "21"

    # C#
    csharp_versions: dict[str, str] = {
        "8": "mcr.microsoft.com/dotnet/sdk:8.0-alpine", "9": "mcr.microsoft.com/dotnet/sdk:9.0-alpine"
    }
    csharp_default_version: str = "8"

    # Bash
    bash_versions: dict[str, str] = {"5": "bash:5"}
    bash_default_version: str = "5"

    # HTML
    html_versions: dict[str, str | None] = {"5": None}
    html_default_version: str = "5"

    # React
    react_versions: dict[str, str | None] = {"18": None, "19": None}
    react_default_version: str = "19"

    model_config = {"env_prefix": "CODE_EXEC_", "toml_file": "config.toml"}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls),
        )

settings = Settings()
