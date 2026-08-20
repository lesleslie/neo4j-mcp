---
description: Search Neo4j for nodes by label and property filters, returning matching nodes up to a limit.
argument-hint: "<label> [--property key=value]... [--limit N]"
allowed-tools: mcp__neo4j__find_nodes, mcp__neo4j__get_schema, mcp__neo4j__health_check
---

# /neo4j-find-nodes

Find nodes in the Neo4j graph by label and an optional set of property equality filters using the neo4j MCP server.

## Usage

`/neo4j-find-nodes <label> [--property key=value]... [--limit N]`

Arguments:

- `<label>`: node label to match (e.g. `Person`, `Company`).
- `--property key=value`: optional, repeatable. Equality filter on a node property. Use this flag multiple times to combine filters.
- `--limit N`: optional, integer 1-1000. Defaults to the server's default limit when omitted.

## Workflow

1. Call `mcp__neo4j__health_check` to confirm the server and database are reachable.
2. If `<label>` or any property key is unfamiliar, call `mcp__neo4j__get_schema` first to verify the schema.
3. Call `mcp__neo4j__find_nodes` with `label`, the compiled `properties` dict, and the `limit`.
4. Report the count of returned nodes and a compact preview of the result set.

## Example

`/neo4j-find-nodes Person --property name="Alice" --property active=true --limit 20`
