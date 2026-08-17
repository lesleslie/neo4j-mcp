'''CI guard: ensure __version__ matches pyproject.toml distribution version.'''
from importlib.metadata import version

from neo4j_mcp import __version__


def test_version_sync() -> None:
    dist_version = version("neo4j-mcp")
    assert __version__ == dist_version, (
        f"__version__ ({__version__}) drifted from pyproject ({dist_version})"
    )
