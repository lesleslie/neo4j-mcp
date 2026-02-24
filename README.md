# neo4j-mcp

MCP server for Neo4j graph database operations.

## Installation

```bash
uv pip install -e .
```

## Usage

```bash
# Stdio mode (default)
neo4j-mcp serve

# HTTP mode
neo4j-mcp serve --http --port 3045

# With mock mode for testing
neo4j-mcp serve --mock

# With custom connection
neo4j-mcp serve --uri bolt://localhost:7687 --database neo4j
```

## Tools

**Queries:**
- `run_cypher` - Execute Cypher queries

**Nodes:**
- `create_node` - Create a node
- `get_node` - Get node by ID
- `delete_node` - Delete a node
- `find_nodes` - Find nodes by criteria

**Relationships:**
- `create_relationship` - Create relationship
- `delete_relationship` - Delete relationship

**Paths:**
- `find_paths` - Find paths between nodes

**Schema:**
- `get_schema` - Get database schema info

## Configuration

Set via environment variables with `NEO4J_MCP_` prefix:
- `NEO4J_MCP_URI` - Neo4j URI (default: bolt://localhost:7687)
- `NEO4J_MCP_USER` - Username (default: neo4j)
- `NEO4J_MCP_PASSWORD` - Password
- `NEO4J_MCP_DATABASE` - Database name (default: neo4j)
- `NEO4J_MCP_MOCK_MODE` - Enable mock mode
