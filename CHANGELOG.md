# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-08-20

### Added

- neo4j-mcp: Adopt ToolProfile dispatch (W4.3)
- neo4j: Bodai plugin conversion (manifest, mcp.json, slash commands)

### Fixed

- neo4j-mcp: Apply W4.3 round 1 re-review Minor items
- neo4j-mcp: Remove unused os import
- neo4j-mcp: Restore client.close() in lifespan, fix os import (W4.3 round 1)

### Internal

- gitignore: Untrack .pyscn/ (bodai 2026-08-20)
- neo4j-mcp: Add [tool.creosote] to skip self-tool scan
- neo4j-mcp: Bootstrap [tool.crackerjack] section + uv sync upgrade
- neo4j-mcp: Gitignore .lycheecache (file, not just dir)
- neo4j-mcp: Gitignore .lycheecache + .hypothesis
- neo4j-mcp: Refresh oneiric + mcp-common deps
- neo4j-mcp: Untrack .lycheecache + .hypothesis runtime artifacts

## [0.2.1] - 2026-08-16

### Documentation

- Align CLI examples, version, env-var table, and structure tree

### Internal

- Untrack backup files (.backup, .backup.json, .bak)

## [0.2.0] - 2026-08-12

### Fixed

- Add ty suppressions for Neo4j session.run + Record.copy
- Drop --cov-fail-under for empty test dir
- Drop unused # type: ignore directives
- Migrate RuntimeHealthSnapshot to new API + pass None to factory
- Move ty: ignore to query line (the actual arg being flagged)
- neo4j-mcp: Resolve _mock_\* unresolved-attribute ty errors
- Use ty: ignore directly on session.run query arg
- Wrap session.run queries in Query() to satisfy typed Cypher

### Internal

- Adopt register_http_health_route from mcp-common
- Bump oneiric dep to >=0.16.0
- Migrate MCPBaseSettings → OneiricMCPConfig, bump fastmcp to >=3.4.0,\<4
- neo4j-mcp: Remove 5 vestigial ty: ignore[invalid-argument-type] suppressions
- neo4j-mcp: Remove bare # type: ignore straggler in client.py

## [0.1.4] - 2026-06-20

### Fixed

- Track .cache dir via .gitkeep for gitleaks support

### Internal

- Add mypy.ini and track .cache dir for quality tooling
- Untrack and delete 1 historical *.backup/*.bak files
