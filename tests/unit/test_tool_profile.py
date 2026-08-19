"""Unit tests for neo4j-mcp ToolProfile dispatch (W4.3).

Mirrors the W4.2 excalidraw-mcp test suite. Coverage:

- Structural guards (files exist, dicts defined, types match).
- AST keystone (production path uses async ``_apply_tool_profile``
  helper, not the sync ``apply_tool_profile`` wrapper). The guard
  verifies the structural ``ast.Await(value=ast.Call(...))`` shape
  (the W3.2 lesson: a count-only guard had false positives).
- Profile semantics: ``MINIMAL=health``, ``STANDARD/FULL=all``.
- Caller-supplied settings preservation (the W4.1 round-1 reviewer
  regression: caller-supplied settings were silently discarded).
- Real production-path tests via a fresh ``FastMCP`` instance with
  no mocks of the dispatch helper (the W2b.3 lesson: tests that
  mocked the SUT masked the sync-vs-async bug).

Run with::

    uv run pytest tests/unit/test_tool_profile.py -v
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest
from fastmcp import FastMCP
from mcp_common.tools import ToolProfile
from mcp_common.tools.dispatch import ALL_TOOLS

from neo4j_mcp import __version__
from neo4j_mcp.client import Neo4jClient
from neo4j_mcp.config import Neo4jSettings
from neo4j_mcp.server import create_app
from neo4j_mcp.tools import profiles as _profiles_module
from neo4j_mcp.tools.profiles import (
    _GROUP_REGISTRY,
    FULL_REGISTRATIONS,
    MINIMAL_REGISTRATIONS,
    PROFILE_REGISTRATIONS,
    apply_neo4j_tool_profile,
)

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "neo4j_mcp"
SERVER_PATH = PACKAGE_DIR / "server.py"
TOOLS_PROFILES_PATH = PACKAGE_DIR / "tools" / "profiles.py"
TOOLS_INIT_PATH = PACKAGE_DIR / "tools" / "__init__.py"


# ---------------------------------------------------------------------------
# Structural guards (file shape)
# ---------------------------------------------------------------------------


def test_profiles_module_exists() -> None:
    """``neo4j_mcp/tools/profiles.py`` must exist (W4 plan deliverable)."""
    assert TOOLS_PROFILES_PATH.exists(), (
        f"profiles.py not found at {TOOLS_PROFILES_PATH}"
    )


def test_tools_init_exposes_register_health_tool() -> None:
    """tools/__init__.py must export ``register_health_tool``.

    The W4.1 critical lesson: health_tools must be a separate callable
    that can be registered independently at MINIMAL. If it's a no-op or
    missing, the dispatch path will silently drop the health probe.
    """
    source = TOOLS_INIT_PATH.read_text()
    tree = ast.parse(source)
    exported = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert "register_health_tool" in exported, (
        "register_health_tool function must be defined in tools/__init__.py"
    )


def test_tools_init_exposes_register_graph_tools_for_profile() -> None:
    """tools/__init__.py must export ``register_graph_tools_for_profile``.

    This is the 2-arg ``(mcp, settings)`` wrapper around the legacy
    3-arg ``register_graph_tools(app, client)``. The W4.1 round-1
    reviewer fix: the wrapper threads caller-supplied settings into
    the registration chain instead of re-loading from env.
    """
    source = TOOLS_INIT_PATH.read_text()
    tree = ast.parse(source)
    exported = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert "register_graph_tools_for_profile" in exported, (
        "register_graph_tools_for_profile must be defined in tools/__init__.py"
    )


def test_group_registry_has_two_entries() -> None:
    """``_GROUP_REGISTRY`` must contain exactly ``health_tools`` and
    ``graph_tools`` — the canonical W4 split for Tier-A trivial."""
    keys = [key for key, _ in _GROUP_REGISTRY]
    assert keys == ["health_tools", "graph_tools"]


def test_profile_registrations_is_three_tier() -> None:
    """PROFILE_REGISTRATIONS must have keys for all three profiles."""
    assert set(PROFILE_REGISTRATIONS.keys()) == {
        ToolProfile.MINIMAL,
        ToolProfile.STANDARD,
        ToolProfile.FULL,
    }


def test_minimal_registrations_is_list_with_health_only() -> None:
    """MINIMAL_REGISTRATIONS must be a non-empty list containing
    exactly ``health_tools`` — the W4 spec invariant."""
    assert isinstance(MINIMAL_REGISTRATIONS, list)
    assert "health_tools" in MINIMAL_REGISTRATIONS
    assert len(MINIMAL_REGISTRATIONS) == 1


def test_full_registrations_includes_all_group_keys() -> None:
    """FULL_REGISTRATIONS must include every key from ``_GROUP_REGISTRY``."""
    expected = [key for key, _ in _GROUP_REGISTRY]
    assert list(FULL_REGISTRATIONS) == expected


def test_full_profile_uses_all_tools_sentinel() -> None:
    """FULL profile must use the ALL_TOOLS sentinel so the dispatch
    loop invokes ``register_all_fn``."""
    assert PROFILE_REGISTRATIONS[ToolProfile.FULL] is ALL_TOOLS


def test_standard_profile_uses_full_registrations_list() -> None:
    """STANDARD profile must reuse FULL_REGISTRATIONS (Tier-A trivial
    mapping: ``STANDARD == FULL``)."""
    assert PROFILE_REGISTRATIONS[ToolProfile.STANDARD] is FULL_REGISTRATIONS


# ---------------------------------------------------------------------------
# AST keystone: production path uses async helper, NOT sync wrapper
# ---------------------------------------------------------------------------


def _find_call_names(tree: ast.AST, func_name: str) -> list[ast.Call]:
    """Find every ``ast.Call`` whose function name is ``func_name``."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == func_name
    ]


def test_server_awaits_apply_neo4j_tool_profile() -> None:
    """``create_app`` must await ``apply_neo4j_tool_profile`` — NOT call it
    sync (the W2b.3 spline lesson). The AST guard is structural:

        ast.Await(value=ast.Call(func=ast.Name(id='apply_neo4j_tool_profile')))

    NOT a count of calls. This catches the regression where someone
    changes ``await apply_neo4j_tool_profile(...)`` to a plain call
    (which would raise ``RuntimeError`` inside the event loop).
    """
    tree = ast.parse(SERVER_PATH.read_text())
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "apply_neo4j_tool_profile"
    ]
    assert matches, (
        "create_app must `await apply_neo4j_tool_profile(server, settings)`. "
        "Production path must use the async W0 helper, NOT the sync "
        "apply_tool_profile wrapper (W2b.3 keystone)."
    )


def test_guard_fails_when_await_is_removed() -> None:
    """Regression guard: confirm the AST check above actually requires
    ``await``. Build a synthetic module that calls (but does NOT await)
    ``apply_neo4j_tool_profile`` and assert the guard returns False.

    This is the W3.2 round-1 fix lesson: a count-based guard had
    false positives; the structural Await check is the keystone.
    """
    synthetic = """
async def create_app():
    apply_neo4j_tool_profile(server, settings)
"""
    tree = ast.parse(synthetic)
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "apply_neo4j_tool_profile"
    ]
    assert matches == [], (
        "Guard must NOT match a plain (un-awaited) call. "
        "If this fires, the guard has regressed to count-only."
    )


def test_server_does_not_call_sync_apply_tool_profile() -> None:
    """The sync ``apply_tool_profile`` wrapper MUST NOT be called from
    ``server.py``. It raises ``RuntimeError`` inside an event loop, so
    any test or production caller that runs ``create_app`` under
    asyncio would silently break. The W2b.3 lesson in code.
    """
    tree = ast.parse(SERVER_PATH.read_text())
    sync_calls = _find_call_names(tree, "apply_tool_profile")
    assert sync_calls == [], (
        "server.py must not call sync `apply_tool_profile()`. "
        "Use `await _apply_tool_profile(...)` (the async helper)."
    )


# ---------------------------------------------------------------------------
# Profile semantics
# ---------------------------------------------------------------------------


def test_apply_neo4j_tool_profile_signature_is_async() -> None:
    """``apply_neo4j_tool_profile`` must be ``async def`` (callers
    must ``await`` it from ``create_app``)."""
    tree = ast.parse(TOOLS_PROFILES_PATH.read_text())
    matching = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "apply_neo4j_tool_profile"
    ]
    assert matching, (
        "apply_neo4j_tool_profile must be defined as `async def` in "
        f"{TOOLS_PROFILES_PATH}. Got zero AsyncFunctionDef matches."
    )
    assert len(matching) == 1, (
        f"Expected exactly 1 AsyncFunctionDef for apply_neo4j_tool_profile, "
        f"got {len(matching)}"
    )


def test_apply_neo4j_tool_profile_calls_helper_not_wrapper() -> None:
    """``apply_neo4j_tool_profile`` must call ``_apply_tool_profile``
    (the async helper), NOT the sync ``apply_tool_profile`` wrapper."""
    tree = ast.parse(TOOLS_PROFILES_PATH.read_text())
    helper_calls = _find_call_names(tree, "_apply_tool_profile")
    sync_calls = _find_call_names(tree, "apply_tool_profile")
    assert helper_calls, "apply_neo4j_tool_profile must call _apply_tool_profile"
    assert sync_calls == [], (
        "apply_neo4j_tool_profile must not call sync apply_tool_profile"
    )


def test_essential_tool_names_enforces_health_check() -> None:
    """``apply_neo4j_tool_profile`` must set ``essential_tool_names``
    so the W0 helper's subset check enforces ``health_check`` at every
    profile (the W4 spec invariant: MINIMAL must expose the health probe).
    """
    tree = ast.parse(TOOLS_PROFILES_PATH.read_text())
    func = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "apply_neo4j_tool_profile"
    )
    # Find every keyword=constant 'essential_tool_names'
    found = False
    for call in ast.walk(func):
        if isinstance(call, ast.Call):
            for kw in call.keywords:
                if kw.arg == "essential_tool_names" and isinstance(
                    kw.value, ast.Set
                ):
                    # The value should be a Set containing "health_check"
                    names = {
                        elt.value
                        for elt in kw.value.elts
                        if isinstance(elt, ast.Constant)
                    }
                    assert "health_check" in names, (
                        "essential_tool_names must include 'health_check'"
                    )
                    found = True
    assert found, "essential_tool_names must be passed to _apply_tool_profile"


def test_profile_env_var_is_neo4j_tool_profile() -> None:
    """``profile_env_var`` must be ``NEO4J_TOOL_PROFILE`` (the W4
    canonical env var for this repo)."""
    tree = ast.parse(TOOLS_PROFILES_PATH.read_text())
    func = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "apply_neo4j_tool_profile"
    )
    for call in ast.walk(func):
        if isinstance(call, ast.Call):
            for kw in call.keywords:
                if kw.arg == "profile_env_var":
                    assert isinstance(kw.value, ast.Constant)
                    assert kw.value.value == "NEO4J_TOOL_PROFILE"


# ---------------------------------------------------------------------------
# Caller-supplied settings preservation (W4.1 round-1 regression)
# ---------------------------------------------------------------------------


def test_build_registration_map_binds_caller_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_build_registration_map`` must bind the CALLER'S settings into
    every registration callback — NOT re-load from env.

    The W4.1 round-1 reviewer fix: the previous implementation
    re-instantiated ``Neo4jSettings()`` inside the registration path,
    silently discarding any caller-supplied overrides. We detect
    that regression by patching ``Neo4jSettings.__init__`` to flag
    silent re-loads.
    """

    caller_settings = Neo4jSettings(mock_mode=True, database="caller_db")
    original_init = Neo4jSettings.__init__
    init_calls: list[bool] = []

    def tracking_init(self: Neo4jSettings, *args: object, **kwargs: object) -> None:
        init_calls.append(True)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(Neo4jSettings, "__init__", tracking_init)

    mapping = _profiles_module._build_registration_map(caller_settings)

    # No Neo4jSettings.__init__ calls should have happened inside the
    # mapping builder (the caller already supplied settings).
    assert init_calls == [], (
        "_build_registration_map must NOT instantiate Neo4jSettings. "
        f"Silent re-load detected ({len(init_calls)} init calls). "
        "Thread caller-supplied settings through instead."
    )

    # The mapping must contain both group keys.
    assert set(mapping.keys()) == {"health_tools", "graph_tools"}

    # Each entry must be callable with a single FastMCP arg.
    for key, fn in mapping.items():
        assert callable(fn), f"{key} mapping entry must be callable"


def test_register_all_tool_groups_does_not_reload_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``register_all_tool_groups`` must thread the CALLER'S settings
    through, NOT re-instantiate ``Neo4jSettings()``. Same regression
    guard as ``_build_registration_map``."""
    caller_settings = Neo4jSettings(mock_mode=True, database="all_groups_db")
    original_init = Neo4jSettings.__init__
    init_calls: list[bool] = []

    def tracking_init(self: Neo4jSettings, *args: object, **kwargs: object) -> None:
        init_calls.append(True)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(Neo4jSettings, "__init__", tracking_init)

    # Use a fresh FastMCP server (no need to wire tools for this test).
    server = FastMCP(name="test-neo4j-mcp", version=__version__)
    _profiles_module.register_all_tool_groups(server, caller_settings)

    assert init_calls == [], (
        "register_all_tool_groups must NOT instantiate Neo4jSettings. "
        f"Silent re-load detected ({len(init_calls)} init calls)."
    )


def test_create_app_threads_caller_settings_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: caller-supplied settings survive the entire
    ``create_app`` -> ``apply_neo4j_tool_profile`` -> registration
    chain. If any link in the chain silently reloads from env, this
    fails loud.
    """
    caller_db = "caller_db_xyz"
    caller_settings = Neo4jSettings(mock_mode=True, database=caller_db)

    server = FastMCP(name="test-neo4j-mcp", version=__version__)

    import asyncio

    asyncio.run(create_app(caller_settings, server))

    tools = {t.name for t in asyncio.run(server.list_tools())}
    assert "health_check" in tools, (
        "create_app must register health_check (canonical MINIMAL mapping)"
    )
    # The health_check tool returns the caller's database.
    health_tool = next(
        t for t in asyncio.run(server.list_tools()) if t.name == "health_check"
    )
    # Verify the closure captured the caller's database by inspecting
    # the underlying function's default behavior. FastMCP wraps the
    # function via Tool.from_function — the body lives in the function
    # attribute. We invoke it directly.
    result = asyncio.run(health_tool.fn())  # type: ignore[attr-defined]
    assert result["database"] == caller_db, (
        "health_check must reflect caller-supplied settings.database, "
        "not env-loaded defaults."
    )


# ---------------------------------------------------------------------------
# Real production-path tests (no mocking of the dispatch helper)
# ---------------------------------------------------------------------------


async def _list_tool_names(server: FastMCP) -> set[str]:
    tools = await server.list_tools()
    return {t.name for t in tools}


async def test_create_app_full_profile_real_path() -> None:
    """FULL profile via fresh FastMCP: must register all 9 graph tools
    + ``health_check`` + ``discover_tools`` (11 total)."""
    server = FastMCP(name="test-neo4j-mcp-full", version=__version__)
    settings = Neo4jSettings(mock_mode=True)

    await create_app(settings, server)
    names = await _list_tool_names(server)

    expected_graph = {
        "run_cypher",
        "create_node",
        "get_node",
        "delete_node",
        "find_nodes",
        "create_relationship",
        "delete_relationship",
        "find_paths",
        "get_schema",
    }
    assert expected_graph.issubset(names), (
        f"FULL profile missing graph tools: {expected_graph - names}"
    )
    assert "health_check" in names
    assert "discover_tools" in names


async def test_create_app_standard_profile_real_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """STANDARD profile: must register the same set as FULL (Tier-A
    trivial)."""
    monkeypatch.setenv("NEO4J_TOOL_PROFILE", "standard")
    server = FastMCP(name="test-neo4j-mcp-standard", version=__version__)
    settings = Neo4jSettings(mock_mode=True)

    await create_app(settings, server)
    names = await _list_tool_names(server)

    assert "health_check" in names
    assert "run_cypher" in names, (
        "STANDARD profile must register all 9 graph tools (Tier-A trivial)"
    )


async def test_create_app_minimal_profile_real_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MINIMAL profile: must register ONLY ``health_check`` +
    ``discover_tools`` (2 tools total). NO graph tools. This is the
    W4.1 critical lesson: MINIMAL must include the health probe, NOT
    rationalize to empty."""
    monkeypatch.setenv("NEO4J_TOOL_PROFILE", "minimal")
    server = FastMCP(name="test-neo4j-mcp-minimal", version=__version__)
    settings = Neo4jSettings(mock_mode=True)

    await create_app(settings, server)
    names = await _list_tool_names(server)

    # Exactly 2 tools — health_check + discover_tools. No graph tools.
    assert names == {"health_check", "discover_tools"}, (
        f"MINIMAL profile must register ONLY health_check + discover_tools, "
        f"got {names}"
    )

    # The health tool MUST be present (the W4.1 critical lesson).
    assert "health_check" in names


async def test_minimal_subset_check_is_non_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``essential_tool_names={"health_check"}`` invariant means
    ``health_check`` MUST be present after dispatch at every profile.
    A refactor that accidentally drops ``health_tools`` from MINIMAL
    will trip the W0 helper's subset check.
    """
    monkeypatch.setenv("NEO4J_TOOL_PROFILE", "minimal")
    server = FastMCP(name="test-neo4j-mcp-subset", version=__version__)
    settings = Neo4jSettings(mock_mode=True)

    await apply_neo4j_tool_profile(server, settings)
    names = await _list_tool_names(server)

    assert "health_check" in names, (
        "essential_tool_names subset check must guarantee health_check"
    )


# ---------------------------------------------------------------------------
# Banner gating (W2b.1 lesson: gate startup banners behind FULL)
# ---------------------------------------------------------------------------


def test_tools_registered_banner_gated_by_full_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``Tools registered`` startup banner must NOT fire at MINIMAL
    or STANDARD — only at FULL (or unset, which defaults to FULL).

    The W2b.1 mailgun lesson: hardcoded banners that advertise a tool
    count are misleading at non-FULL profiles where the count is smaller.
    """
    import asyncio

    from neo4j_mcp import server as server_module

    # Capture log emissions via a mock handler.
    captured: list[str] = []

    class _Capture:
        def info(self, msg: str, **kwargs: object) -> None:
            if "Tools registered" in msg:
                captured.append(msg)

    monkeypatch.setattr(server_module.logger, "info", _Capture().info)

    # MINIMAL: banner must NOT fire.
    monkeypatch.setenv("NEO4J_TOOL_PROFILE", "minimal")
    server = FastMCP(name="test-banner-min", version=__version__)
    settings = Neo4jSettings(mock_mode=True)
    asyncio.run(create_app(settings, server))
    assert captured == [], (
        f"Tools registered banner must NOT fire at MINIMAL, got: {captured}"
    )

    # FULL (unset): banner MUST fire.
    monkeypatch.delenv("NEO4J_TOOL_PROFILE", raising=False)
    captured.clear()
    server = FastMCP(name="test-banner-full", version=__version__)
    settings = Neo4jSettings(mock_mode=True)
    asyncio.run(create_app(settings, server))
    assert captured, (
        "Tools registered banner MUST fire at FULL (or unset, defaults to FULL)"
    )


# ---------------------------------------------------------------------------
# Lifespan cleanup (W4.3 round-1 reviewer fix)
# ---------------------------------------------------------------------------


def test_lifespan_finally_calls_client_close() -> None:
    """AST guard: the lifespan ``finally`` block must call
    ``await client.close()``. The W4.3 round-1 reviewer fix —
    restoring the pre-W4 behavior that was lost when the dispatch
    refactor moved client construction into ``register_graph_tools_for_profile``.

    The original ``create_app`` had::

        @asynccontextmanager
        async def lifespan(server):
            async with original_lifespan(server) as state:
                try:
                    yield state
                finally:
                    await client.close()

    The round-1 regression replaced this with a no-op that iterated
    ``server.list_tools()`` and discarded each tool. This AST guard
    fails loud if any future refactor drops the ``await client.close()``
    call.
    """
    tree = ast.parse(SERVER_PATH.read_text())

    # Find every Await node whose value is a Call to ``client.close``.
    found = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Await)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "close"
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == "client"
        ):
            found = True
            break

    assert found, (
        "server.py must `await client.close()` somewhere (typically in the "
        "lifespan finally block). The W4.3 round-1 regression removed this "
        "call and broke the pre-W4 shutdown behavior."
    )


async def test_lifespan_actually_calls_client_close_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: ``await client.close()`` is actually invoked when
    the server lifespan exits. The W4.3 round-1 reviewer fix — the
    lifespan finally block must close the Neo4j client (not just be
    present in source).

    We monkey-patch ``Neo4jClient.close`` to track invocations, drive
    the lifespan, and assert the close was called.
    """
    monkeypatch.setenv("NEO4J_TOOL_PROFILE", "full")

    close_calls: list[int] = []
    original_close = Neo4jClient.close

    async def tracking_close(self: Neo4jClient) -> None:
        close_calls.append(1)
        await original_close(self)

    monkeypatch.setattr(Neo4jClient, "close", tracking_close)

    server = FastMCP(name="test-lifespan-cleanup", version=__version__)
    settings = Neo4jSettings(mock_mode=True)

    await create_app(settings, server)

    # Drive the lifespan (enter + exit). The lifespan is installed on
    # ``server._mcp_server.lifespan`` — call it via async context manager.
    lifespan_cm = server._mcp_server.lifespan(server)
    async with lifespan_cm as state:
        assert isinstance(state, dict), (
            "lifespan should yield a state dict (FastMCP convention)"
        )

    # After lifespan exit, the finally block must have invoked close.
    assert close_calls, (
        "lifespan finally block did not call `await client.close()`. "
        "The W4.3 round-1 regression — restoring this is the W4.3 "
        "round-1 Critical fix."
    )
