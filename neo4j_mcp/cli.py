"""Unified CLI for Neo4j MCP server using mcp-common.

Provides standard lifecycle commands (start, stop, restart, status, health).
"""

from __future__ import annotations

import os
import warnings

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", message=".*PyTorch.*TensorFlow.*Flax.*")

import uvicorn

from mcp_common import MCPServerCLIFactory, MCPServerSettings
from mcp_common.cli.health import RuntimeHealthSnapshot

from neo4j_mcp import __version__


class Neo4jSettings(MCPServerSettings):
    """Neo4j MCP server settings extending MCPServerSettings."""

    server_name: str = "neo4j-mcp"
    http_port: int = 3045
    startup_timeout: int = 10
    shutdown_timeout: int = 10
    force_kill_timeout: int = 5


def start_server_handler() -> None:
    """Start handler that launches the Neo4j MCP server in HTTP mode."""
    settings = Neo4jSettings()
    print(f"Starting Neo4j MCP server on port {settings.http_port}...")
    uvicorn.run(
        "neo4j_mcp.server:http_app",
        host="127.0.0.1",
        port=settings.http_port,
        log_level="info",
    )


def health_probe_handler() -> RuntimeHealthSnapshot:
    """Health probe handler for Neo4j MCP server."""
    from neo4j_mcp.config import get_settings

    settings = get_settings()
    return RuntimeHealthSnapshot(
        server_name="neo4j-mcp",
        status="healthy",
        version=__version__,
        extra={
            "uri": settings.uri,
            "database": settings.database,
            "mock_mode": settings.mock_mode,
        },
    )


factory = MCPServerCLIFactory(
    server_name="neo4j-mcp",
    settings=Neo4jSettings(),
    start_handler=start_server_handler,
    health_probe_handler=health_probe_handler,
)

app = factory.create_app()


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
