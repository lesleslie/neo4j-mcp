"""FastMCP server for Neo4j graph database."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from neo4j_mcp import __version__
from neo4j_mcp.client import Neo4jClient
from neo4j_mcp.config import get_logger_instance, get_settings, setup_logging
from neo4j_mcp.tools import register_graph_tools

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger_instance("neo4j-mcp.server")

APP_NAME = "neo4j-mcp"
APP_VERSION = __version__


def create_app() -> FastMCP:
    """Create and configure the FastMCP application."""
    settings = get_settings()
    setup_logging(settings)

    logger.info(
        "Initializing neo4j-mcp server",
        version=APP_VERSION,
        uri=settings.uri,
        database=settings.database,
        mock_mode=settings.mock_mode,
    )

    app = FastMCP(name=APP_NAME, version=APP_VERSION)
    client = Neo4jClient(settings)

    # Register tools
    register_graph_tools(app, client)

    # Setup lifespan for proper cleanup
    original_lifespan = app._mcp_server.lifespan

    @asynccontextmanager
    async def lifespan(server: Any) -> AsyncGenerator[dict[str, Any]]:
        async with original_lifespan(server) as state:
            try:
                yield state
            finally:
                await client.close()

    app._mcp_server.lifespan = lifespan

    logger.info(
        "Tools registered",
        tools=9,
    )

    return app


_app: FastMCP | None = None


def get_app() -> FastMCP:
    """Get the singleton FastMCP application."""
    global _app
    if _app is None:
        _app = create_app()
    return _app


def __getattr__(name: str) -> Any:
    """Dynamic attribute access for app and http_app."""
    if name == "app":
        return get_app()
    if name == "http_app":
        return get_app().http_app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["create_app", "get_app", "APP_NAME", "APP_VERSION"]
