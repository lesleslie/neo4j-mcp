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

```bash
# Run server (stdio mode)
neo4j-mcp serve

# Run server (HTTP mode)
neo4j-mcp serve --http --port 3045

# With mock mode for testing
neo4j-mcp serve --mock

# With custom connection
neo4j-mcp serve --uri bolt://localhost:7687 --database neo4j
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

Set via environment variables with `NEO4J_MCP_` prefix:

| Variable | Description | Default |
|----------|-------------|---------|
| `NEO4J_MCP_URI` | Neo4j URI | bolt://localhost:7687 |
| `NEO4J_MCP_USER` | Username | neo4j |
| `NEO4J_MCP_PASSWORD` | Password | - |
| `NEO4J_MCP_DATABASE` | Database name | neo4j |
| `NEO4J_MCP_MOCK_MODE` | Enable mock mode | false |

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
