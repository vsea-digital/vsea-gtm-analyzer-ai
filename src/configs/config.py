import os
from dataclasses import dataclass, field
from pathlib import Path

import tomli


def _load_toml() -> dict:
    paths = [
        Path(__file__).parent / "config.toml",
        Path("/ext_configs/config.toml"),
    ]
    for p in paths:
        if p.exists():
            with open(p, "rb") as f:
                return tomli.load(f)
    return {}


_TOML = _load_toml()


@dataclass
class ProjectConfig:
    name: str = _TOML.get("project", {}).get("name", "vsea-gtm-analyzer-ai")
    version: str = _TOML.get("project", {}).get("version", "0.1.0")


@dataclass
class APIConfig:
    host: str = _TOML.get("api", {}).get("host", "0.0.0.0")
    port: int = _TOML.get("api", {}).get("port", 8003)


@dataclass
class GeminiConfig:
    model_name: str = _TOML.get("gemini", {}).get(
        "model_name", "gemini-3-flash-preview"
    )
    temperature: float = _TOML.get("gemini", {}).get("temperature", 0.1)
    max_output_tokens: int = _TOML.get("gemini", {}).get("max_output_tokens", 8000)
    thinking_budget: int = _TOML.get("gemini", {}).get("thinking_budget", 1024)


@dataclass
class GCSConfig:
    upload_prefix: str = _TOML.get("gcs", {}).get("upload_prefix", "gtm-uploads/")
    signed_url_expiry_minutes: int = _TOML.get("gcs", {}).get(
        "signed_url_expiry_minutes", 60
    )


@dataclass
class UploadConfig:
    max_bytes: int = _TOML.get("upload", {}).get("max_bytes", 52_428_800)


@dataclass
class Secrets:
    GOOGLE_API_KEY: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    SERVICE_API_KEY: str = field(
        default_factory=lambda: os.getenv("SERVICE_API_KEY", "")
    )
    GCS_BUCKET_NAME: str = field(
        default_factory=lambda: os.getenv("GCS_BUCKET_NAME", "")
    )
    GOOGLE_APPLICATION_CREDENTIALS: str = field(
        default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    )
    CORS_ORIGINS: str = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*"))


@dataclass
class Config:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    api: APIConfig = field(default_factory=APIConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    gcs: GCSConfig = field(default_factory=GCSConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)
    secrets: Secrets = field(default_factory=Secrets)


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
