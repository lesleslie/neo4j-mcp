"""Neo4j client with mock mode support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from neo4j_mcp.config import get_logger_instance, get_settings
from neo4j_mcp.models import (
    ConstraintInfo,
    IndexInfo,
    Node,
    NodeCreate,
    Path,
    Relationship,
    RelationshipCreate,
    SchemaInfo,
)

if TYPE_CHECKING:
    from neo4j_mcp.config import Neo4jSettings

logger = get_logger_instance("neo4j-mcp.client")


class Neo4jClient:
    """Async client for Neo4j database operations."""

    def __init__(self, settings: Neo4jSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self._driver: AsyncDriver | None = None

    async def __aenter__(self) -> Neo4jClient:
        await self._ensure_driver()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def _ensure_driver(self) -> AsyncDriver:
        """Ensure Neo4j driver is connected."""
        if self._driver is None:
            if self.settings.mock_mode:
                # In mock mode, don't actually connect
                logger.info("Running in mock mode - no real Neo4j connection")
                return None  # type: ignore

            self._driver = AsyncGraphDatabase.driver(
                self.settings.uri,
                auth=(self.settings.user, self.settings.password),
                max_connection_lifetime=self.settings.max_connection_lifetime,
                max_connection_pool_size=self.settings.max_connection_pool_size,
                connection_timeout=self.settings.connection_timeout,
            )
        return self._driver

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    def _get_session(self) -> AsyncSession | None:
        """Get a Neo4j session."""
        if self.settings.mock_mode:
            return None
        if self._driver is None:
            raise RuntimeError("Driver not initialized")
        return self._driver.session(database=self.settings.database)

    # Query Operations

    async def run_cypher(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results."""
        if self.settings.mock_mode:
            return self._mock_run_cypher(query, params)

        logger.debug("Running Cypher query", query=query[:100])
        session = self._get_session()
        if session is None:
            return []

        async with session:
            result = await session.run(query, params or {})
            records = [dict(record) async for record in result]
            return records

    # Node Operations

    async def create_node(self, node: NodeCreate) -> Node:
        """Create a new node."""
        if self.settings.mock_mode:
            return self._mock_create_node(node)

        labels_str = ":".join(node.labels)
        props_str = ", ".join(f"{k}: ${k}" for k in node.properties)

        query = f"CREATE (n:{labels_str} {{{props_str}}}) RETURN id(n) as id, labels(n) as labels, properties(n) as properties"

        session = self._get_session()
        if session is None:
            return Node(labels=node.labels, properties=node.properties)

        async with session:
            result = await session.run(query, node.properties)
            record = await result.single()
            if record:
                return Node(
                    id=str(record["id"]),
                    labels=record["labels"],
                    properties=record["properties"],
                )
            return Node(labels=node.labels, properties=node.properties)

    async def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        if self.settings.mock_mode:
            return self._mock_get_node(node_id)

        query = "MATCH (n) WHERE id(n) = $id RETURN id(n) as id, labels(n) as labels, properties(n) as properties"

        session = self._get_session()
        if session is None:
            return None

        async with session:
            result = await session.run(query, {"id": int(node_id)})
            record = await result.single()
            if record:
                return Node(
                    id=str(record["id"]),
                    labels=record["labels"],
                    properties=record["properties"],
                )
            return None

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node by ID."""
        if self.settings.mock_mode:
            return True

        query = "MATCH (n) WHERE id(n) = $id DETACH DELETE n"

        session = self._get_session()
        if session is None:
            return True

        async with session:
            await session.run(query, {"id": int(node_id)})
            return True

    async def find_nodes(
        self,
        labels: list[str] | None = None,
        properties: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[Node]:
        """Find nodes matching criteria."""
        if self.settings.mock_mode:
            return self._mock_find_nodes(labels, properties, limit)

        conditions = []
        params: dict[str, Any] = {}

        if labels:
            label_match = " AND ".join(f"'{label}' IN labels(n)" for label in labels)
            conditions.append(f"({label_match})")

        if properties:
            for key, value in properties.items():
                conditions.append(f"n.{key} = ${key}")
                params[key] = value

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"MATCH (n){where_clause} RETURN id(n) as id, labels(n) as labels, properties(n) as properties LIMIT {limit}"

        session = self._get_session()
        if session is None:
            return []

        async with session:
            result = await session.run(query, params)
            nodes = []
            async for record in result:
                nodes.append(
                    Node(
                        id=str(record["id"]),
                        labels=record["labels"],
                        properties=record["properties"],
                    )
                )
            return nodes

    # Relationship Operations

    async def create_relationship(self, rel: RelationshipCreate) -> Relationship:
        """Create a relationship between nodes."""
        if self.settings.mock_mode:
            return self._mock_create_relationship(rel)

        props_str = ", ".join(f"{k}: ${k}" for k in rel.properties) if rel.properties else ""
        props_clause = f" {{{props_str}}}" if props_str else ""

        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $start_id AND id(b) = $end_id
        CREATE (a)-[r:{rel.type}{props_clause}]->(b)
        RETURN id(r) as id, type(r) as type, id(a) as start_id, id(b) as end_id, properties(r) as properties
        """

        params = {
            "start_id": int(rel.start_node_id),
            "end_id": int(rel.end_node_id),
            **rel.properties,
        }

        session = self._get_session()
        if session is None:
            return Relationship(
                type=rel.type,
                start_node_id=rel.start_node_id,
                end_node_id=rel.end_node_id,
                properties=rel.properties,
            )

        async with session:
            result = await session.run(query, params)
            record = await result.single()
            if record:
                return Relationship(
                    id=str(record["id"]),
                    type=record["type"],
                    start_node_id=str(record["start_id"]),
                    end_node_id=str(record["end_id"]),
                    properties=record["properties"],
                )
            return Relationship(
                type=rel.type,
                start_node_id=rel.start_node_id,
                end_node_id=rel.end_node_id,
                properties=rel.properties,
            )

    async def delete_relationship(self, rel_id: str) -> bool:
        """Delete a relationship by ID."""
        if self.settings.mock_mode:
            return True

        query = "MATCH ()-[r]-() WHERE id(r) = $id DELETE r"

        session = self._get_session()
        if session is None:
            return True

        async with session:
            await session.run(query, {"id": int(rel_id)})
            return True

    # Path Operations

    async def find_paths(
        self,
        start_node_id: str,
        end_node_id: str,
        max_depth: int = 5,
        relationship_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[Path]:
        """Find paths between two nodes."""
        if self.settings.mock_mode:
            return self._mock_find_paths(start_node_id, end_node_id, max_depth)

        # Build relationship pattern
        if relationship_types:
            rel_pattern = "|".join(relationship_types)
            rel_match = f"[r:{rel_pattern}*1..{max_depth}]"
        else:
            rel_match = f"[r*1..{max_depth}]"

        query = f"""
        MATCH path = (a){rel_match}(b)
        WHERE id(a) = $start_id AND id(b) = $end_id
        RETURN path, length(path) as len
        ORDER BY len
        LIMIT {limit}
        """

        session = self._get_session()
        if session is None:
            return []

        async with session:
            result = await session.run(
                query,
                {"start_id": int(start_node_id), "end_id": int(end_node_id)},
            )
            paths = []
            async for record in result:
                path_data = record["path"]
                nodes = [
                    Node(
                        id=str(node.element_id),
                        labels=list(node.labels),
                        properties=dict(node),
                    )
                    for node in path_data.nodes
                ]
                relationships = [
                    Relationship(
                        id=str(rel.element_id),
                        type=rel.type,
                        start_node_id=str(rel.start_node.element_id),
                        end_node_id=str(rel.end_node.element_id),
                        properties=dict(rel),
                    )
                    for rel in path_data.relationships
                ]
                paths.append(
                    Path(
                        nodes=nodes,
                        relationships=relationships,
                        length=record["len"],
                    )
                )
            return paths

    # Schema Operations

    async def get_schema(self) -> SchemaInfo:
        """Get database schema information."""
        if self.settings.mock_mode:
            return self._mock_get_schema()

        session = self._get_session()
        if session is None:
            return SchemaInfo()

        async with session:
            # Get indexes
            indexes_result = await session.run("SHOW INDEXES")
            indexes = []
            async for record in indexes_result:
                indexes.append(
                    IndexInfo(
                        name=record.get("name", ""),
                        labels_or_types=record.get("labelsOrTypes", []),
                        properties=record.get("properties", []),
                        uniqueness=record.get("uniqueness", "NONUNIQUE") == "UNIQUE",
                    )
                )

            # Get constraints
            constraints_result = await session.run("SHOW CONSTRAINTS")
            constraints = []
            async for record in constraints_result:
                constraints.append(
                    ConstraintInfo(
                        name=record.get("name", ""),
                        type=record.get("type", ""),
                        label=record.get("labelsOrTypes", [""])[0],
                        properties=record.get("properties", []),
                    )
                )

            # Get labels
            labels_result = await session.run("CALL db.labels()")
            labels = [record["label"] async for record in labels_result]

            # Get relationship types
            rels_result = await session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] async for record in rels_result]

            # Get property keys
            props_result = await session.run("CALL db.propertyKeys()")
            prop_keys = [record["propertyKey"] async for record in props_result]

            return SchemaInfo(
                indexes=indexes,
                constraints=constraints,
                labels=labels,
                relationship_types=rel_types,
                property_keys=prop_keys,
            )

    # Mock Implementations

    def _mock_run_cypher(
        self,
        query: str,
        params: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        return [{"result": "mock_data"}]

    def _mock_create_node(self, node: NodeCreate) -> Node:
        return Node(
            id="mock-node-id",
            labels=node.labels,
            properties=node.properties,
        )

    def _mock_get_node(self, node_id: str) -> Node:
        return Node(
            id=node_id,
            labels=["MockLabel"],
            properties={"name": "Mock Node"},
        )

    def _mock_find_nodes(
        self,
        labels: list[str] | None,
        properties: dict[str, Any] | None,
        limit: int,
    ) -> list[Node]:
        return [
            Node(
                id="mock-1",
                labels=labels or ["MockLabel"],
                properties=properties or {"name": "Mock Node 1"},
            ),
        ]

    def _mock_create_relationship(self, rel: RelationshipCreate) -> Relationship:
        return Relationship(
            id="mock-rel-id",
            type=rel.type,
            start_node_id=rel.start_node_id,
            end_node_id=rel.end_node_id,
            properties=rel.properties,
        )

    def _mock_find_paths(
        self,
        start_id: str,
        end_id: str,
        max_depth: int,
    ) -> list[Path]:
        return [
            Path(
                nodes=[
                    Node(id=start_id, labels=["Mock"], properties={}),
                    Node(id=end_id, labels=["Mock"], properties={}),
                ],
                relationships=[
                    Relationship(
                        id="mock-rel",
                        type="RELATED_TO",
                        start_node_id=start_id,
                        end_node_id=end_id,
                        properties={},
                    ),
                ],
                length=1,
            ),
        ]

    def _mock_get_schema(self) -> SchemaInfo:
        return SchemaInfo(
            indexes=[
                IndexInfo(
                    name="mock_index",
                    labels_or_types=["MockLabel"],
                    properties=["name"],
                    uniqueness=False,
                ),
            ],
            constraints=[],
            labels=["MockLabel"],
            relationship_types=["RELATED_TO"],
            property_keys=["name", "id"],
        )
