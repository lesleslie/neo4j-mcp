# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

For a shorter, tool-neutral bootstrap document, start with `AGENTS.md`.

## Project Overview

**neo4j-mcp** is an MCP server for Neo4j graph database operations, providing graph query and node/relationship management, and path finding capabilities via the Model Context Protocol.

**Key Dependencies**: Python 3.13+, mcp-common, neo4j-driver

## Core Features

- **Cypher Queries**: Execute Cypher queries with parameterized inputs
- **Node Operations**: Create, get, delete, find nodes
- **Relationship Operations**: Create and delete relationships
- **Path Finding**: Find paths between nodes
- **Schema Inspection**: Get database schema info
- **Mock Mode**: Testing without real Neo4j instance

## Most Common Commands

The CLI is built via `mcp-common`'s `MCPServerCLIFactory` and exposes the
standard Bodai MCP lifecycle surface (no per-flag subcommands). Connection
overrides are environment variables, not CLI flags.

```bash
# Start the managed HTTP MCP server
uv run neo4j-mcp start

# Stop / restart / status / health probes
uv run neo4j-mcp stop
uv run neo4j-mcp restart
uv run neo4j-mcp status
uv run neo4j-mcp health

# Custom connection details via environment variables
NEO4J_MCP_URI=bolt://localhost:7687 \
NEO4J_MCP_DATABASE=neo4j \
    uv run neo4j-mcp start

# Mock mode (no live Neo4j required)
NEO4J_MCP_MOCK_MODE=true uv run neo4j-mcp start
```

## Critical Rules

### 1. SECURITY IS NON-NEGOTIABLE

- **NEVER** expose database passwords in code
- **ALWAYS** use environment variables for credentials
- **NEVER** log credential values
- **ALWAYS** sanitize Cypher query inputs to prevent injection

### 2. NEO4J CONNECTION MANAGEMENT

- Use connection pooling for performance
- Handle connection errors gracefully
- Close connections properly in cleanup

### 3. NO PLACEHOLDERS - EVER

- **NEVER** use dummy node IDs or placeholder data
- **ALWAYS** use proper variable references

### 4. MCP-COMMON PATTERNS

- Follow mcp-common patterns for server lifecycle
- Use MCPServerCLIFactory for CLI commands
- Inherit from base settings classes

## Configuration

Set via environment variables with `NEO4J_MCP_` prefix. See [README.md §
Configuration](./README.md#configuration) for the full table (12 settings
including connection-pool sizing, HTTP transport, and logging knobs).

## Tool Profile System

neo4j-mcp exposes its MCP tool surface via a 3-tier profile dispatch
(mcp-common 0.18.0+ W0 helper). Profiles are selected via the
`NEO4J_TOOL_PROFILE` env var:

| Profile | Tools registered |
|----------|-------------------------------------------------------------------|
| MINIMAL | `health_check` + `discover_tools` |
| STANDARD | All 9 graph tools + `health_check` + `discover_tools` |
| FULL | Same as STANDARD (Tier-A trivial — `STANDARD == FULL`) |
| unset | FULL (default per spec) |

`essential_tool_names={"health_check"}` enforces the W4 invariant
that `health_check` MUST be present at every profile. The dispatch
runs inside `neo4j_mcp.server.create_app` via the async
`_apply_tool_profile` helper (NOT the sync `apply_tool_profile`
wrapper — the W2b.3 spline keystone).

The startup banner (`Tools registered`) is gated behind
`NEO4J_TOOL_PROFILE in {"", "full"}` — at MINIMAL/STANDARD it would
otherwise advertise a misleading tool count (the W2b.1 lesson).

See [docs/architecture/tool-profile-rationale.md](docs/architecture/tool-profile-rationale.md)
for the full rationale.

## Tools Provided

**Queries:**
| Tool | Description |
|------|-------------|
| `run_cypher` | Execute Cypher queries |

**Nodes:**
| Tool | Description |
|------|-------------|
| `create_node` | Create a node |
| `get_node` | Get node by ID |
| `delete_node` | Delete a node |
| `find_nodes` | Find nodes by criteria |

**Relationships:**
| Tool | Description |
|------|-------------|
| `create_relationship` | Create relationship |
| `delete_relationship` | Delete relationship |

**Paths:**
| Tool | Description |
|------|-------------|
| `find_paths` | Find paths between nodes |

**Schema:**
| Tool | Description |
|------|-------------|
| `get_schema` | Get database schema info |

## Additional Resources

- **[README.md](./README.md)**: Complete project documentation
- **[mcp-common](../mcp-common)**: Shared MCP utilities
