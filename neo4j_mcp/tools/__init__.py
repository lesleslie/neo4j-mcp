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

``register_graph_tools_for_profile`` constructs a ``Neo4jClient`` from
the caller-supplied ``Neo4jSettings`` (lazy — does NOT open a driver
until first query) and returns it so ``create_app`` can hold the
reference and call ``await client.close()`` in the lifespan shutdown
block. This restores the pre-W4 lifecycle (the original
``create_app`` had ``await client.close()`` in the lifespan finally).

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
    "register_graph_tools_with_client",
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


def register_graph_tools_with_client(mcp: FastMCP, client: Neo4jClient) -> None:
    """Register the 9 Neo4j graph MCP tools with a pre-built client.

    Profile-aware entry point when the caller has already constructed
    the ``Neo4jClient`` (e.g. ``create_app`` builds it upfront so the
    lifespan can call ``await client.close()`` on shutdown — the W4.3
    round-1 reviewer fix). When the caller wants the client built
    automatically, use ``register_graph_tools_for_profile`` instead.

    Args:
        mcp: FastMCP server instance.
        client: The caller-supplied ``Neo4jClient``. Returned unchanged
            so the caller can retain a reference for cleanup.
    """
    from neo4j_mcp.tools.graph_tools import register_graph_tools

    register_graph_tools(mcp, client)


def register_graph_tools_for_profile(
    mcp: FastMCP, settings: Neo4jSettings
) -> Neo4jClient:
    """Register the 9 Neo4j graph MCP tools and return the client.

    Convenience wrapper for the W0 helper's profile dispatch path.
    Constructs a fresh ``Neo4jClient`` from ``settings`` (lazy — does
    not open a driver until first query), registers the graph tools,
    and returns the client so callers that need lifecycle management
    (e.g. ``create_app``'s lifespan) can close it.

    NOTE: when called via the W0 helper's ``register_all_fn``, the
    helper discards this return value. To retain the client reference
    across the lifespan, build the client in ``create_app`` and use
    ``register_graph_tools_with_client`` via ``register_all_tool_groups``.

    Args:
        mcp: FastMCP server instance.
        settings: The caller-supplied ``Neo4jSettings`` (NOT re-loaded
            from env — the W4.1 round-1 reviewer fix).

    Returns:
        The constructed ``Neo4jClient`` so callers can close it on
        shutdown.
    """
    from neo4j_mcp.client import Neo4jClient

    client = Neo4jClient(settings)
    register_graph_tools_with_client(mcp, client)
    return client


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
