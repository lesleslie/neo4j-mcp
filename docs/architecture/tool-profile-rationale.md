# neo4j-mcp Tool Profile Adoption Rationale

**Status:** DONE (W4.3, Tier-A trivial)

## Context

neo4j-mcp is a Tier-A MCP server: 9 graph tools (cypher, nodes,
relationships, paths, schema) plus a single HTTP `/health` route.
Before W4.3, every tool was registered eagerly at startup, exposing
all 9 to every Claude session regardless of role. Control-plane /
health-probe deployments paid the full surface area even though they
only needed the health probe.

W4 of the MCP tool profile adoption plan (see the upstream `mahavishnu`
design spec and implementation plan for the full program) introduces
a 3-tier dispatch (MINIMAL / STANDARD / FULL) driven by the
`{SERVER_NAME}_TOOL_PROFILE` env var. The W0 helper in mcp-common
0.18.0+ (`_apply_tool_profile` async + `apply_tool_profile` sync
wrapper) handles the dispatch mechanics; this repo wires it in and
enforces the W4 spec invariant.

## Decision

**Adopt ToolProfile dispatch with the canonical Tier-A trivial
mapping: `MINIMAL=health`, `STANDARD/FULL=all`.**

| Profile | Tools registered |
|----------|-------------------------------------------------|
| MINIMAL | `health_check` + `discover_tools` |
| STANDARD | All 9 graph tools + `health_check` + `discover_tools` |
| FULL | All 9 graph tools + `health_check` + `discover_tools` (via `register_all_fn` bulk path) |

The mapping is driven by the `NEO4J_TOOL_PROFILE` env var (default
FULL when unset, per spec). `essential_tool_names={"health_check"}`
enforces the W4 invariant: `health_check` is present at every
profile. The `MANDATORY_GROUPS` set is empty — no group is
guaranteed on top of the per-profile dispatch.

## Architecture

### Registration groups

Two groups exist in `neo4j_mcp/tools/__init__.py`:

1. **`health_tools`** (`register_health_tool`) — registers the MCP
   `health_check` tool + the HTTP `/health` readiness route. Always
   available at MINIMAL.
2. **`graph_tools`** (`register_graph_tools_for_profile`) — registers
   the 9 Neo4j graph MCP tools. Available at STANDARD/FULL only.

The split mirrors the W4.2 excalidraw-mcp pattern and enables
`MINIMAL=health` without re-loading Neo4j state at startup.

The `_GROUP_REGISTRY` constant in `neo4j_mcp/tools/profiles.py` is
the SSOT (single source of truth) for group keys — both
`_build_registration_map` and `register_all_tool_groups` derive
from it via `getattr(neo4j_mcp.tools, attr_name)`. Adding a new
group requires editing only this constant.

### Production dispatch path

`neo4j_mcp/server.py::create_app(settings, server)` is **async** and
calls `await apply_neo4j_tool_profile(server, settings)`. The
async helper (`_apply_tool_profile`, NOT the sync
`apply_tool_profile` wrapper) is used because the W2b.3 spline
lesson: the sync wrapper raises `RuntimeError` inside a running
event loop.

The `create_app_sync(settings)` bridge handles sync callers
(CLI startup, `get_app` singleton) via `asyncio.run()` when no loop
is running, or a private `ThreadPoolExecutor` when a loop is
already running (pytest-asyncio tests).

### Caller-supplied settings threading

The `Neo4jSettings` instance flows through the entire registration
chain unmodified:

```
create_app(settings)
  -> apply_neo4j_tool_profile(server, settings)
       -> _build_registration_map(settings)
            -> register_fn(server, settings)  # default-arg capture
       -> register_all_fn(server) -> register_all_tool_groups(server, settings)
```

Two regression tests (`test_build_registration_map_binds_caller_settings`
and `test_register_all_tool_groups_does_not_reload_settings`)
monkey-patch `Neo4jSettings.__init__` to detect silent re-loads.
They fail loud if any link in the chain reloads from env.

## Critical Lessons Applied

| Wave | Lesson | Applied |
|------|--------|---------|
| W2b.1 | Audit startup banners; gate behind FULL | `Tools registered` banner gated behind `NEO4J_TOOL_PROFILE in {"", "full"}` (test: `test_tools_registered_banner_gated_by_full_profile`) |
| W2b.2 | Sync `__init__.py` `__version__` | `__init__.py` uses `importlib.metadata.version()` — auto-syncs |
| W2b.3 | Production path uses async helper, NOT sync wrapper | `create_app` calls `await apply_neo4j_tool_profile`; AST keystone test verifies the structural `ast.Await` shape |
| W3.2 | `_GROUP_REGISTRY` SSOT constant | Extracted as `list[tuple[str, str]]`; both map builders derive from it |
| W3.2 | AST guard structurally checks for `ast.Await` | `test_server_awaits_apply_neo4j_tool_profile` uses structural Await check, not count; `test_guard_fails_when_await_is_removed` is the regression guard |
| W4.1 | `MINIMAL=health` not rationalized to empty | `MINIMAL_REGISTRATIONS = ["health_tools"]`; `test_minimal_profile_real_path` asserts `names == {"health_check", "discover_tools"}` |
| W4.1 | Caller-supplied settings preserved | Two negative-tests (`test_build_...` and `test_register_all_tool_groups_does_not_reload_settings`) fail loud on silent re-load |
| W4.2 | Verify tool count with grep | Pre-flight grep confirmed 9 graph tools (brief said 9 — correct) |

## Behavioral Parity

| Profile | Before (no profile) | After |
|---------|---------------------|-------|
| FULL (default) | All 9 graph tools registered | All 9 graph tools + `health_check` + `discover_tools` (11 total) |
| STANDARD | n/a (didn't exist) | Same as FULL (Tier-A trivial) |
| MINIMAL | n/a (didn't exist) | `health_check` + `discover_tools` (2 total) |

At FULL (the default), the only behavioral change is the addition of
two new MCP tools (`health_check` and `discover_tools`). The 9
existing graph tools are unchanged.

## Files Touched

- `neo4j_mcp/tools/__init__.py` — added `register_health_tool` +
  `register_graph_tools_with_client` (2-arg entry point that holds
  the client reference for lifespan cleanup) +
  `register_graph_tools_for_profile` (backward-compat shim);
  preserved legacy `register_graph_tools` re-export
- `neo4j_mcp/tools/profiles.py` — NEW: dispatch machinery
- `neo4j_mcp/server.py` — `create_app` is now async + accepts
  caller-supplied settings; lifespan captures `Neo4jClient` and
  closes it on shutdown
- `pyproject.toml` — bumped `mcp-common>=0.18.0`
- `tests/unit/test_tool_profile.py` — NEW: 26 tests covering
  structural guards, AST keystone, profile semantics, settings
  preservation, lifespan cleanup, real production-path tests,
  banner gating
- `CLAUDE.md` — added "Tool Profile System" subsection
- `docs/architecture/tool-profile-rationale.md` — THIS document
