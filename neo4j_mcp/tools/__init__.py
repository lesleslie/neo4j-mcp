"""MCP tool registration groups for neo4j-mcp.

Maps ``register_<group>`` callables to the W0 tool profile dispatch
hierarchy (see ``neo4j_mcp.tools.profiles``). Two groups exist:

- ``health_tools`` — registers the MCP ``health_check`` tool plus the
  HTTP ``/health`` readiness route (always available at MINIMAL).
- ``graph_tools`` — registers the 9 Neo4j graph MCP tools (cypher,
  nodes, relationships, paths, schema). Tier-A trivial mapping puts
  this group behind STANDARD/FULL.

The split mirrors excalidraw-mcp's W4.2 pattern and enables
``MINIMAL=health`` without re-loading Neo4j state at startup.

The ``register_graph_tools_for_profile`` wrapper threads the caller-
supplied ``Neo4jSettings`` through to the existing ``register_graph_tools``
implementation (which expects a constructed ``Neo4jClient`` instance).

Backward-compat: ``register_graph_tools`` (the original 2-arg signature
taking ``(app, client)``) is still re-exported so existing callers
that pre-construct the client continue to work. New code should use
``register_graph_tools_for_profile(app, settings)`` (the profile-aware
entry point consumed by ``register_all_tool_groups``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_common.fastmcp import FastMCP

    from neo4j_mcp.client import Neo4jClient
    from neo4j_mcp.config import Neo4jSettings

__all__ = [
    "register_health_tool",
    "register_graph_tools",
    "register_graph_tools_for_profile",
]


def register_health_tool(mcp: FastMCP, settings: Neo4jSettings) -> None:
    """Register the MCP ``health_check`` tool plus the HTTP ``/health`` route.

    Split out from the graph-registration group so the W0 tool profile
    dispatch can expose ``health_check`` independently at the MINIMAL
    profile (the canonical W4 mapping: ``MINIMAL=health``). The HTTP
    ``/health`` route is registered alongside the MCP health tool so
    launchd wrappers, orchestrators, and ad-hoc ``curl`` checks have a
    plain HTTP readiness probe.

    The MCP-level ``health_check`` tool is intentionally lightweight —
    it returns a static snapshot of service identity (version, mode,
    database) without opening a Neo4j connection. The HTTP ``/health``
    route is the load-bearing readiness probe (matches the mcp-common
    ``register_http_health_route`` contract).

    Args:
        mcp: FastMCP server instance.
        settings: Server configuration (used for service/version
            metadata and to surface the database name in the response).
    """
    from mcp_common.health import register_http_health_route

    from neo4j_mcp import __version__

    @mcp.tool()
    async def health_check() -> dict[str, Any]:
        """Check neo4j-mcp server health.

        Returns:
            Status, version, mode (mock/live), and configured database.
            Pure status check — does not mutate graph state or open a
            live Neo4j session.
        """
        return {
            "status": "healthy",
            "service": "neo4j-mcp",
            "version": __version__,
            "database": settings.database,
            "mock_mode": settings.mock_mode,
        }

    register_http_health_route(
        mcp,
        service_name="neo4j-mcp",
        version=__version__,
    )


def register_graph_tools_for_profile(mcp: FastMCP, settings: Neo4jSettings) -> None:
    """Register the 9 Neo4j graph MCP tools (the FULL/STANDARD surface).

    Threads the caller-supplied ``Neo4jSettings`` into the existing
    ``register_graph_tools(app, client)`` by constructing the
    ``Neo4jClient`` from the settings. This is the profile-aware entry
    point that the W0 helper dispatches to at STANDARD/FULL profiles.

    The client lifecycle is managed by the server lifespan in
    ``neo4j_mcp.server.create_app`` — the client is closed in the
    lifespan ``finally`` block, so we do NOT call ``close()`` here.

    Args:
        mcp: FastMCP server instance.
        settings: The caller-supplied ``Neo4jSettings`` (NOT re-loaded
            from env — the W4.1 round-1 reviewer fix).
    """
    from neo4j_mcp.client import Neo4jClient
    from neo4j_mcp.tools.graph_tools import register_graph_tools

    client: Neo4jClient = Neo4jClient(settings)
    register_graph_tools(mcp, client)


# Original 2-arg signature preserved for backward compat. New profile-aware
# code should use ``register_graph_tools_for_profile`` (which delegates
# here with a constructed client).
def register_graph_tools(app: Any, client: Neo4jClient) -> None:
    """Register graph database tools (legacy 2-arg signature).

    Re-exported from ``neo4j_mcp.tools.graph_tools`` for backward
    compatibility with callers that pre-construct the
    ``Neo4jClient``. New code should use
    ``register_graph_tools_for_profile(app, settings)`` so the
    caller-supplied ``Neo4jSettings`` flows through the registration
    chain intact (the W4.1 round-1 reviewer fix).
    """
    from neo4j_mcp.tools.graph_tools import (
        register_graph_tools as _register_graph_tools,
    )

    _register_graph_tools(app, client)
