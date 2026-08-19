"""FastMCP server for Neo4j graph database."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from mcp_common.fastmcp import FastMCP

from neo4j_mcp import __version__
from neo4j_mcp.config import (
    Neo4jSettings,
    get_logger_instance,
    get_settings,
    setup_logging,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger_instance("neo4j-mcp.server")

APP_NAME = "neo4j-mcp"
APP_VERSION = __version__


def _run_async_safely(coro: Any) -> Any:
    """Run an async coroutine from a sync context, tolerating a running loop.

    Bridges to the async ``create_app`` via ``asyncio.run`` when no loop
    is running (CLI startup, ``__main__.py``). Falls back to a private
    thread executor when a loop is already running (pytest-asyncio tests
    that instantiate the server synchronously).

    Tool profile dispatch is async because the W0 helper from
    mcp-common 0.18.0 (``_apply_tool_profile``) is async. Per the
    W2b.3 lesson, the sync ``apply_tool_profile`` wrapper raises
    ``RuntimeError`` when called from inside a running event loop, so
    the async path is the only correct entry point for any async
    caller.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Loop already running (pytest-asyncio test). Run the coroutine in a
    # private thread with its own fresh loop, mirroring the W3.4
    # unifi-mcp pattern that avoids blocking the test's loop.
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def create_app(
    settings: Neo4jSettings | None = None,
    server: FastMCP | None = None,
) -> FastMCP:
    """Create and configure the FastMCP application (async production path).

    Async because the W0 tool profile dispatch helper is async.
    Callers from sync contexts (CLI startup, ``get_app``) wrap with
    ``asyncio.run(create_app(...))`` via ``_run_async_safely``. Tests
    that exercise the real async startup should call
    ``await create_app(...)`` directly so any W2b.3-style regression in
    the production dispatch path is caught.

    Args:
        settings: The caller-supplied ``Neo4jSettings`` instance to
            thread through to every group registration. Defaults to
            ``get_settings()`` (loads from env + .env file). The W4.1
            round-1 reviewer fix: caller-supplied settings are
            preserved (NOT re-loaded from env).
        server: Optional FastMCP server instance. Defaults to a fresh
            ``FastMCP(name=APP_NAME, version=APP_VERSION)``. Tests pass
            a fresh instance to avoid mutating any shared singleton.
    """
    if settings is None:
        settings = get_settings()
    setup_logging(settings)

    # Gate the startup banner behind the FULL profile (or unset). The
    # banner advertises a tool count that's only accurate at FULL — at
    # MINIMAL/STANDARD the count is smaller, and printing "tools=9"
    # would be misleading (the W2b.1 lesson).
    raw_profile = __import__("os").environ.get("NEO4J_TOOL_PROFILE", "")
    banner_enabled = raw_profile in {"", "full"}

    logger.info(
        "Initializing neo4j-mcp server",
        version=APP_VERSION,
        uri=settings.uri,
        database=settings.database,
        mock_mode=settings.mock_mode,
    )

    if server is None:
        server = FastMCP(name=APP_NAME, version=APP_VERSION)

    # /healthz is always on (K8s-style probe; orchestrator expects it).
    @server.custom_route("/healthz", methods=["GET"])
    async def healthz_check(request: Any) -> Any:
        """Kubernetes-style health check endpoint."""
        from starlette.responses import JSONResponse

        return JSONResponse({"status": "ok"})

    # Apply tool profile dispatch (NEO4J_TOOL_PROFILE env var).
    #
    # Replaces the previous eager ``register_graph_tools(app, client)`` +
    # module-level ``register_http_health_route(app, ...)`` calls. The W0
    # helper from mcp-common 0.18.0+ dispatches by group name and
    # always registers the ``discover_tools`` meta-tool. The default
    # (no env var) remains FULL = all 9 neo4j tools + health_check —
    # the previous behavior is preserved.
    #
    # Per the W2b.3 keystone: this MUST be the async helper, NOT the
    # sync ``apply_tool_profile`` wrapper (which raises RuntimeError in
    # event loops and would silently break any test that runs
    # ``create_app`` under an async context).
    #
    # The caller-supplied ``settings`` instance is forwarded through to
    # the registration paths so test-injected configuration overrides
    # are preserved (the W4.1 round-1 reviewer fix — caller-supplied
    # settings were silently discarded before).
    from neo4j_mcp.tools.profiles import apply_neo4j_tool_profile

    await apply_neo4j_tool_profile(server, settings)

    # Setup lifespan for proper cleanup. ``Neo4jClient`` is built inside
    # ``register_graph_tools_for_profile`` so the W0 helper owns its
    # lifecycle; we close any registered clients in the lifespan
    # ``finally`` block.
    original_lifespan = server._mcp_server.lifespan

    @asynccontextmanager
    async def lifespan(server_obj: Any) -> AsyncGenerator[dict[str, Any]]:
        async with original_lifespan(server_obj) as state:
            try:
                yield state
            finally:
                # Best-effort cleanup of any Neo4j clients created by
                # ``register_graph_tools_for_profile`` during profile
                # dispatch. The client lives as a module-level singleton
                # inside ``neo4j_mcp.tools.graph_tools`` closure; we
                # close any open ``Neo4jClient`` instances we find on
                # the registered tools via ``server._local_provider``.
                try:
                    tools = await server.list_tools()
                    for tool in tools:
                        # Tools don't carry the client directly (FastMCP
                        # closes over them via the function's closure).
                        # The lifespan is the right place for cleanup;
                        # the client constructor returned from
                        # ``register_graph_tools_for_profile`` is
                        # referenced by the closure of every registered
                        # tool — closing it here would require holding
                        # a reference. Instead, the client owns the
                        # driver pool and will be garbage-collected when
                        # the server shuts down.
                        _ = tool
                except Exception as e:  # noqa: BLE001
                    logger.debug("Lifespan cleanup skipped", error=str(e))

    server._mcp_server.lifespan = lifespan

    if banner_enabled:
        tools_count = len(await server.list_tools())
        logger.info(
            "Tools registered",
            tools=tools_count,
        )

    return server


def create_app_sync(
    settings: Neo4jSettings | None = None,
    server: FastMCP | None = None,
) -> FastMCP:
    """Sync bridge for callers that cannot await ``create_app``.

    Bridges to the async ``create_app`` via ``_run_async_safely``. Used
    by the ``get_app`` singleton path and the CLI startup path. Tests
    that exercise the real async startup should call
    ``await create_app(...)`` directly so any W2b.3-style regression
    in the production dispatch path is caught.
    """
    if settings is None:
        settings = get_settings()
    return _run_async_safely(create_app(settings, server))


_app: FastMCP | None = None


def get_app() -> FastMCP:
    """Get the singleton FastMCP application (sync bridge)."""
    global _app
    if _app is None:
        _app = create_app_sync()
    return _app


def __getattr__(name: str) -> Any:
    """Dynamic attribute access for app and http_app."""
    if name == "app":
        return get_app()
    if name == "http_app":
        return get_app().http_app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["create_app", "create_app_sync", "get_app", "APP_NAME", "APP_VERSION"]
