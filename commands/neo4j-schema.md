---
description: "Retrieve the Neo4j schema: labels, relationship types, indexes, and constraints."
argument-hint: "[--labels] [--relationships] [--indexes] [--constraints]"
allowed-tools: mcp__neo4j__get_schema, mcp__neo4j__health_check
---

# /neo4j-schema

Inspect the live Neo4j schema using the neo4j MCP server.

## Usage

`/neo4j-schema [--labels] [--relationships] [--indexes] [--constraints]`

Arguments:

- `--labels`: include node labels and their property keys.
- `--relationships`: include relationship types and their property keys.
- `--indexes`: include index definitions.
- `--constraints`: include constraint definitions.

By default the server returns the full schema snapshot. Use the flags to narrow the output when you only need a slice.

## Workflow

1. Call `mcp__neo4j__health_check` to confirm the server and database are reachable.
2. Call `mcp__neo4j__get_schema` with the requested flag(s). If no flags are supplied, the full schema is returned.
3. Report the structure as a compact summary: list of labels, relationship types, indexes, and constraints.

## Example

`/neo4j-schema --labels --indexes`
