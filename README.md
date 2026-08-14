# Neo4j MCP Server

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)
[![Runtime: oneiric](https://img.shields.io/badge/runtime-oneiric-6e5494)](https://github.com/lesleslie/oneiric)
[![Framework: FastMCP](https://img.shields.io/badge/framework-FastMCP-0ea5e9)](https://github.com/jlowin/fastmcp)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13%2B-green)](https://www.python.org/downloads/)

MCP server for Neo4j graph database operations.

**Version:** 0.2.0
**Status:** Internal Bodai integration component

## Quick Links

- [Overview](#overview)
- [Capabilities](#capabilities)
- [Quick Start](#quick-start)
- [MCP Server Configuration](#mcp-server-configuration)
- [Tool Reference](#tool-reference)
- [Configuration](#configuration)
- [Development](#development)

## Quality & CI

Crackerjack is the standard quality-control and CI/CD gate for Neo4j MCP changes. Local verification should mirror the Crackerjack workflow used across the Bodai ecosystem.

______________________________________________________________________

## Overview

Neo4j MCP exposes graph database workflows through a FastMCP server. It gives agents a typed interface for Cypher execution, node and relationship management, path discovery, and schema inspection while preserving a narrow database client boundary.

Use this server when an agent needs to query or mutate graph data directly. Keep domain-specific graph policies in the calling system or a higher-level service layer rather than embedding them in generic Neo4j tools.

## Capabilities

Implemented tool surface:

- **Cypher execution**: run parameterized Cypher queries
- **Node management**: create, retrieve, delete, and search nodes
- **Relationship management**: create and delete relationships between nodes
- **Path discovery**: find bounded paths between two nodes
- **Schema inspection**: retrieve labels, relationship types, indexes, and constraints
- **Mock mode**: exercise tool behavior without a live Neo4j connection
- **HTTP health routes**: `/health` and `/healthz` for MCP client and process supervision checks

## Quick Start

### Prerequisites

- Python 3.13+
- UV package manager
- Neo4j server for live access

### Local Setup

```bash
git clone https://github.com/lesleslie/neo4j-mcp.git
cd neo4j-mcp
uv sync --group dev
```

### Run In Mock Mode

```bash
export NEO4J_MCP_MOCK_MODE=true
uv run neo4j-mcp start
uv run neo4j-mcp health
```

### Run With Neo4j

```bash
export NEO4J_MCP_URI="bolt://localhost:7687"
export NEO4J_MCP_USER="neo4j"
export NEO4J_MCP_PASSWORD="your-password"
export NEO4J_MCP_DATABASE="neo4j"
uv run neo4j-mcp start
```

The default HTTP bind is `127.0.0.1:3045`.

## CLI Commands

The CLI is built with `mcp-common` and provides the standard lifecycle command surface used by Bodai MCP servers.

```bash
uv run neo4j-mcp start      # Start the HTTP MCP server
uv run neo4j-mcp stop       # Stop the managed server process
uv run neo4j-mcp restart    # Restart the managed server process
uv run neo4j-mcp status     # Show process status
uv run neo4j-mcp health     # Run the local health probe
```

## MCP Server Configuration

### Claude / Codex Style Configuration

Add the server to an MCP client configuration:

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "uv",
      "args": ["run", "neo4j-mcp", "start"],
      "cwd": "<absolute-path-to-cloned-neo4j-mcp>",
      "env": {
        "NEO4J_MCP_URI": "bolt://localhost:7687",
        "NEO4J_MCP_USER": "neo4j",
        "NEO4J_MCP_PASSWORD": "your-password",
        "NEO4J_MCP_DATABASE": "neo4j"
      }
    }
  }
}
```

For tests or local client wiring, replace live connection values with `NEO4J_MCP_MOCK_MODE=true`.

### Health Checks

```bash
curl http://127.0.0.1:3045/health
curl http://127.0.0.1:3045/healthz
```

## Tool Reference

| Tool | Purpose | Required Inputs |
|------|---------|-----------------|
| `run_cypher` | Execute a Cypher query | `query` |
| `create_node` | Create a node with labels and properties | `labels` |
| `get_node` | Retrieve a node by ID | `node_id` |
| `delete_node` | Delete a node by ID | `node_id` |
| `find_nodes` | Search nodes by labels and properties | none |
| `create_relationship` | Create a typed relationship between nodes | `type`, `start_node_id`, `end_node_id` |
| `delete_relationship` | Delete a relationship by ID | `relationship_id` |
| `find_paths` | Find paths between two nodes | `start_node_id`, `end_node_id` |
| `get_schema` | Retrieve database schema details | none |

Tool responses follow a consistent `ToolResponse` shape:

```json
{
  "success": true,
  "message": "Query returned 3 records",
  "data": {},
  "error": null,
  "next_steps": []
}
```

## Configuration

Committed defaults live in `settings/neo4j.yaml`. Runtime overrides should come from environment variables or a local `.env` file that is not committed.

| Setting | Environment Variable | Default |
|---------|----------------------|---------|
| Neo4j URI | `NEO4J_MCP_URI` | `bolt://localhost:7687` |
| User | `NEO4J_MCP_USER` | `neo4j` |
| Password | `NEO4J_MCP_PASSWORD` | empty |
| Database | `NEO4J_MCP_DATABASE` | `neo4j` |
| Max connection lifetime | `NEO4J_MCP_MAX_CONNECTION_LIFETIME` | `3600` |
| Max pool size | `NEO4J_MCP_MAX_CONNECTION_POOL_SIZE` | `50` |
| Connection timeout | `NEO4J_MCP_CONNECTION_TIMEOUT` | `30.0` |
| Mock mode | `NEO4J_MCP_MOCK_MODE` | `false` |
| Enable HTTP transport | `NEO4J_MCP_ENABLE_HTTP_TRANSPORT` | `false` |
| HTTP host | `NEO4J_MCP_HTTP_HOST` | `127.0.0.1` |
| HTTP port | `NEO4J_MCP_HTTP_PORT` | `3045` |
| Log level | `NEO4J_MCP_LOG_LEVEL` | `INFO` |
| JSON logs | `NEO4J_MCP_LOG_JSON` | `true` |

## Project Structure

```text
neo4j_mcp/
  __init__.py            # Package surface (__version__, model re-exports)
  __main__.py            # Module entry point (`python -m neo4j_mcp`)
  cli.py                 # mcp-common lifecycle CLI
  client.py              # Neo4j driver boundary
  config.py              # Pydantic settings and logging
  models.py              # Typed graph request and response models
  server.py              # FastMCP application factory
  tools/
    __init__.py          # Re-exports register_graph_tools
    graph_tools.py       # Registered MCP tools
settings/
  neo4j.yaml             # Committed defaults (documentation; see note below)
tests/
```

> **Note:** `settings/neo4j.yaml` documents the operator-facing defaults but
> is not loaded by pydantic-settings at runtime — `Neo4jSettings` reads from
> the `NEO4J_MCP_*` environment variables and the `.env` file only. Use
> `settings/neo4j.yaml` as a reference when authoring your local `.env`.

## Development

```bash
uv sync --group dev
uv run pytest
uv run ruff check neo4j_mcp tests
uv run ruff format neo4j_mcp tests
uv run mypy neo4j_mcp
```

Use targeted tests when isolating graph behavior:

```bash
uv run pytest tests -k graph -v
```

## Security Notes

- Do not commit Neo4j passwords or connection strings containing credentials.
- Prefer parameterized Cypher through `params` when passing user-controlled values.
- Treat `run_cypher` as a privileged tool because it can mutate data.
- Use database permissions and separate users to constrain agent-accessible operations.
