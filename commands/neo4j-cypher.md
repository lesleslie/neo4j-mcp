---
description: Run a parameterized Cypher query against the Neo4j database and return the result rows.
argument-hint: "<cypher-query> [--params JSON]"
allowed-tools: mcp__neo4j__run_cypher, mcp__neo4j__health_check, mcp__neo4j__get_schema
---

# /neo4j-cypher

Run a parameterized Cypher query against the Neo4j database using the neo4j MCP server.

## Usage

`/neo4j-cypher <cypher-query> [--params JSON]`

Arguments:

- `<cypher-query>`: a Cypher statement. Use `$param` placeholders for values supplied via `--params`.
- `--params JSON`: optional, JSON object of parameter bindings. Example: `'{"personId": "123"}'`.

## Workflow

1. Call `mcp__neo4j__health_check` to confirm the server and database are reachable.
2. If the query references unfamiliar labels or property names, call `mcp__neo4j__get_schema` first to verify the schema.
3. Call `mcp__neo4j__run_cypher` with `query` and (when supplied) the parsed `params` object.
4. Report the number of rows returned and a compact preview of the result set.

## Example

`/neo4j-cypher 'MATCH (p:Person {id: $personId})-[:KNOWS]->(f) RETURN f.name LIMIT 10' --params '{"personId": "123"}'`
