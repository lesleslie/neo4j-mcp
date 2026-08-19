"""Tool profile registration groups for neo4j-mcp MCP server.

Maps ``ToolProfile`` levels to specific ``register_<group>_tools()`` call
lists, controlling which tools are exposed at startup based on the
``NEO4J_TOOL_PROFILE`` environment variable.

Profile tiers (Tier-A trivial — 3-tier mapping per the W4 plan):

    MINIMAL:  Only the ``health_check`` MCP tool + the ``discover_tools``
              meta-tool from the W0 helper. The ``/health`` HTTP route
              (registered inside ``register_health_tool``) is also
              always available. Useful for control-plane / health-probe
              deployments.
    STANDARD: All 9 graph tools + ``health_check`` + ``discover_tools``
              (Tier-A trivial: same set as FULL).
    FULL:     All 9 graph tools + ``health_check`` + ``discover_tools``
              (registered via the ``register_all_fn`` bulk path).

The dispatch surface (``PROFILE_REGISTRATIONS`` + ``REGISTRATION_MAP`` +
``register_all_tool_groups`` + ``apply_neo4j_tool_profile``) is consumed
by ``neo4j_mcp.server.create_app`` which delegates to
``mcp_common.tools.dispatch._apply_tool_profile`` (the async helper,
NOT the sync ``apply_tool_profile`` wrapper — the W2b.3 keystone).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_common.tools import ToolProfile
from mcp_common.tools.dispatch import ALL_TOOLS

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastmcp import FastMCP

    from neo4j_mcp.config import Neo4jSettings

# Canonical list of every register_<group>_tools group key + the matching
# attribute name on the ``neo4j_mcp.tools`` package. THIS is the single
# source of truth: ``FULL_REGISTRATIONS``, ``_build_registration_map``, and
# ``register_all_tool_groups`` all derive from this constant via
# ``getattr(neo4j_mcp.tools, attr_name)`` — no name-specific conditionals.
# Adding a new group requires editing only this constant (the W3.2 lesson).
_GROUP_REGISTRY: list[tuple[str, str]] = [
    ("health_tools", "register_health_tool"),
    ("graph_tools", "register_graph_tools_for_profile"),
]

# MINIMAL exposes the health probe (matches the canonical W4 mapping:
# ``MINIMAL=health, STANDARD/FULL=all``). The MCP ``health_check`` tool
# is the health probe; the ``/health`` HTTP route is registered
# alongside it inside ``register_health_tool``.
MINIMAL_REGISTRATIONS: list[str | Callable[[FastMCP], Awaitable[None] | None]] = [
    "health_tools",
]

# STANDARD uses ``FULL_REGISTRATIONS`` (a list) so the dispatch loop can
# iterate; ``ALL_TOOLS`` sentinel is only honored at the FULL key.
FULL_REGISTRATIONS: list[str | Callable[[FastMCP], Awaitable[None] | None]] = [
    key for key, _ in _GROUP_REGISTRY
]

PROFILE_REGISTRATIONS: dict[
    ToolProfile,
    list[str | Callable[[FastMCP], Awaitable[None] | None]] | type[ALL_TOOLS],
] = {
    ToolProfile.MINIMAL: MINIMAL_REGISTRATIONS,
    ToolProfile.STANDARD: FULL_REGISTRATIONS,
    ToolProfile.FULL: ALL_TOOLS,
}


def _build_registration_map(
    settings: Neo4jSettings,
) -> dict[str, Callable[[FastMCP], Awaitable[None] | None]]:
    """Build the {group_key: register_fn(server)} map from ``_GROUP_REGISTRY``.

    Each registry entry's ``attr_name`` is looked up dynamically on the
    ``neo4j_mcp.tools`` package (no hard-coded name-specific
    conditionals). The looked-up function takes 2 arguments
    ``(mcp, settings)``; the W0 helper expects single-arg callables, so
    each entry is wrapped in a lambda with default-argument capture of
    ``settings`` (the W3.1 graphics-mcp lesson + the W3.3
    ``_register_crs_with_app`` pattern).

    Args:
        settings: The caller-supplied ``Neo4jSettings`` instance to bind
            into every registration callback. Passed through from
            ``create_app(settings)`` — NOT re-loaded from the environment
            (the W4.1 round-1 reviewer finding: caller-supplied settings
            were silently discarded by registration paths).

    Returns:
        Mapping from group key (e.g. ``"health_tools"``) to a single-arg
        async-or-sync callable that takes the ``FastMCP`` server.
    """
    from neo4j_mcp import tools as _tools_module

    mapping: dict[str, Callable[[FastMCP], Awaitable[None] | None]] = {}
    for key, attr_name in _GROUP_REGISTRY:
        register_fn = getattr(_tools_module, attr_name)
        # Default-arg capture avoids late-binding bugs (W3.1 lesson) and
        # binds the CALLER'S settings, not an env-loaded one.
        mapping[key] = lambda server, _fn=register_fn, _cfg=settings: _fn(server, _cfg)
    return mapping


def register_all_tool_groups(server: FastMCP, settings: Neo4jSettings) -> None:
    """Bulk register every neo4j-mcp tool group (called at FULL profile).

    Iterates ``_GROUP_REGISTRY`` directly — no name-specific conditionals.
    Each entry's ``attr_name`` is looked up dynamically on the
    ``neo4j_mcp.tools`` package. Used as ``register_all_fn`` for the W0
    helper.

    Args:
        server: FastMCP server instance.
        settings: The caller-supplied ``Neo4jSettings`` to pass through
            to every group registration (NOT re-loaded from env — the
            W4.1 round-1 reviewer fix).
    """
    from neo4j_mcp import tools as _tools_module

    for _key, attr_name in _GROUP_REGISTRY:
        getattr(_tools_module, attr_name)(server, settings)


async def apply_neo4j_tool_profile(server: FastMCP, settings: Neo4jSettings) -> None:
    """Apply the NEO4J_TOOL_PROFILE dispatch to ``server`` at startup.

    Async because the W0 helper is async; called from
    ``neo4j_mcp.server.create_app`` via
    ``await apply_neo4j_tool_profile(server, settings)``. The sync
    ``apply_tool_profile`` wrapper raises ``RuntimeError`` in any async
    context, so this async path is the only correct entry point — the
    W2b.3 spline lesson is the keystone of this rule.

    The caller-supplied ``settings`` instance is forwarded through to
    ``_build_registration_map`` and ``register_all_tool_groups`` so any
    registration-time configuration overrides (e.g. test-injected
    settings) are preserved — this is the W4.1 round-1 reviewer fix.

    ``MANDATORY_GROUPS`` is empty because no group is *guaranteed* on
    top of the per-profile dispatch; ``essential_tool_names={"health_check"}``
    instead enforces the W4 spec invariant that ``health_check`` MUST be
    present at every profile (the canonical MINIMAL=health mapping).
    The subset check fails loud if a future refactor accidentally drops
    the health tool from a profile.
    """
    from mcp_common.tools.dispatch import _apply_tool_profile

    await _apply_tool_profile(
        server,
        profile_env_var="NEO4J_TOOL_PROFILE",
        registrations=PROFILE_REGISTRATIONS,
        registration_map=_build_registration_map(settings),
        register_all_fn=lambda server: register_all_tool_groups(server, settings),
        mandatory_groups=set(),
        essential_tool_names={"health_check"},
    )


__all__ = [
    "FULL_REGISTRATIONS",
    "MINIMAL_REGISTRATIONS",
    "PROFILE_REGISTRATIONS",
    "_GROUP_REGISTRY",
    "_build_registration_map",
    "apply_neo4j_tool_profile",
    "register_all_tool_groups",
]
