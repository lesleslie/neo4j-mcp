# Repository Guidelines

## Project Structure & Module Organization

- `neo4j_mcp/` contains the MCP server package, including driver integration, query helpers, schemas, and tool definitions.
- `settings/` stores configuration defaults, and `tests/` should mirror the package structure for query, node, relationship, and path coverage.
- Keep operator guidance in root docs rather than ad hoc scripts.

## Build, Test, and Development Commands

- `uv sync --group dev` installs development dependencies.
- Use the documented local stdio or HTTP server commands for smoke tests.
- `uv run pytest` runs the test suite.
- `uv run ruff check neo4j_mcp tests` and `uv run ruff format neo4j_mcp tests` cover linting and formatting.

## Coding Style & Naming Conventions

- Use explicit type hints, parameterized queries, and small composable helpers around the Neo4j driver.
- Keep modules snake_case, classes PascalCase, and tool responses structured and validated.

## Testing Guidelines

- Add tests for Cypher execution, schema inspection, and path-finding behavior.
- Prefer mocked or containerized graph setups over depending on a shared live database.

## Commit & Pull Request Guidelines

- Use focused commits such as `feat(paths): add shortest path tool options`.
- PRs should call out query behavior changes, commands run, and any compatibility implications.

## Security & Configuration Tips

- Never commit database credentials or internal connection URIs.
- Validate user-supplied labels, property filters, and query parameters strictly.
