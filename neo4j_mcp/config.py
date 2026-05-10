"""Configuration for neo4j-mcp using Oneiric patterns."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Oneiric logging imports
try:
    from oneiric.core.logging import LoggingConfig, configure_logging, get_logger

    ONEIRIC_LOGGING_AVAILABLE = True
except ImportError:
    ONEIRIC_LOGGING_AVAILABLE = False
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

    def configure_logging(*args: Any, **kwargs: Any) -> None:
        logging.basicConfig(level=logging.INFO)


class Neo4jSettings(BaseSettings):
    """Neo4j MCP server configuration."""

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_MCP_",
        env_file=(".env",),
        extra="ignore",
        case_sensitive=False,
    )

    # Server identification
    server_name: str = Field(
        default="neo4j-mcp",
        description="Server name for identification",
    )
    server_description: str = Field(
        default="MCP server for Neo4j graph database",
        description="Server description",
    )

    # Neo4j Connection Configuration
    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI",
    )
    user: str = Field(
        default="neo4j",
        description="Neo4j username",
    )
    password: str = Field(
        default="",
        description="Neo4j password",
    )
    database: str = Field(
        default="neo4j",
        description="Database name",
    )
    max_connection_lifetime: int = Field(
        default=3600,
        description="Max connection lifetime in seconds",
    )
    max_connection_pool_size: int = Field(
        default=50,
        description="Max connection pool size",
    )
    connection_timeout: float = Field(
        default=30.0,
        description="Connection timeout in seconds",
    )

    # Mock mode for testing
    mock_mode: bool = Field(
        default=False,
        description="Run in mock mode without real Neo4j connection",
    )

    # HTTP transport
    enable_http_transport: bool = Field(
        default=False,
        description="Enable HTTP transport",
    )
    http_host: str = Field(
        default="127.0.0.1",
        description="HTTP server host",
    )
    http_port: int = Field(
        default=3045,
        ge=1024,
        le=65535,
        description="HTTP server port",
    )

    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_json: bool = Field(
        default=True,
        description="Use JSON logging format",
    )

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, v: str) -> str:
        """Validate Neo4j URI format."""
        if not v.startswith(("bolt://", "bolt+s://", "neo4j://", "neo4j+s://")):
            raise ValueError(
                "uri must start with bolt://, bolt+s://, neo4j://, or neo4j+s://"
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid}")
        return v.upper()


@lru_cache
def get_settings() -> Neo4jSettings:
    """Get cached settings instance."""
    return Neo4jSettings()


def setup_logging(settings: Neo4jSettings | None = None) -> None:
    """Configure logging using Oneiric patterns."""
    if settings is None:
        settings = get_settings()

    if ONEIRIC_LOGGING_AVAILABLE:
        config = LoggingConfig(
            level=settings.log_level,
            emit_json=settings.log_json,
            service_name="neo4j-mcp",
        )
        configure_logging(config)
    else:
        # Fallback to standard logging
        import logging

        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )


def get_logger_instance(name: str = "neo4j-mcp") -> Any:
    """Get a structured logger instance."""
    if ONEIRIC_LOGGING_AVAILABLE:
        return get_logger(name)
    import logging

    return logging.getLogger(name)


__all__ = [
    "Neo4jSettings",
    "get_settings",
    "setup_logging",
    "get_logger_instance",
    "ONEIRIC_LOGGING_AVAILABLE",
]
