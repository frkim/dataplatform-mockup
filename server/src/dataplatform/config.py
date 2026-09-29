"""Process configuration, read from ``DATAPLATFORM_*`` environment variables (twelve-factor)."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

CsvList = Annotated[list[str], NoDecode]


class AppConfig(BaseSettings):
    """Startup configuration. Runtime-editable settings live in ``PlatformSettings`` instead."""

    model_config = SettingsConfigDict(env_prefix="DATAPLATFORM_", env_file=".env", extra="ignore")

    host: str = Field(default="127.0.0.1", description="Interface the HTTP server binds to.")
    port: int = Field(default=8000, ge=1, le=65_535)
    public_base_url: str = Field(
        default="http://localhost:8000",
        description="Externally reachable base URL, used in agent cards and endpoint discovery.",
    )
    cors_allowed_origins: CsvList = Field(default_factory=lambda: ["http://localhost:3000"])
    mcp_allowed_hosts: CsvList = Field(
        default_factory=lambda: ["localhost:*", "127.0.0.1:*", "[::1]:*"],
        description="Host header allowlist for the MCP endpoint (DNS rebinding protection).",
    )
    mcp_allowed_origins: CsvList = Field(
        default_factory=lambda: ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"],
        description="Origin header allowlist for the MCP endpoint.",
    )
    query_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    query_history_size: int = Field(default=500, ge=10, le=10_000)
    engine_memory_limit: str = Field(default="1GB", pattern=r"^\d+(KB|MB|GB)$")
    engine_threads: int = Field(default=4, ge=1, le=64)
    data_seed: int = 42
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("cors_allowed_origins", "mcp_allowed_hosts", "mcp_allowed_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def _no_wildcard_origin(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("wildcard CORS origins are not allowed; list the allowed origins explicitly")
        return value

    @field_validator("public_base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_config() -> AppConfig:
    """Return the process-wide configuration."""
    return AppConfig()
