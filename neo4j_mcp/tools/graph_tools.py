"""Graph database tools for Neo4j MCP server."""

from __future__ import annotations

from typing import Any

from neo4j_mcp.client import Neo4jClient
from neo4j_mcp.config import get_logger_instance
from neo4j_mcp.models import (
    NodeCreate,
    RelationshipCreate,
    ToolResponse,
)

logger = get_logger_instance("neo4j-mcp.tools.graph")


def register_graph_tools(app: Any, client: Neo4jClient) -> None:
    """Register graph database tools."""

    @app.tool()
    async def run_cypher(
        query: str,
        params: dict[str, Any] | None = None,
    ) -> ToolResponse:
        """Execute a Cypher query against the Neo4j database.

        Args:
            query: Cypher query string
            params: Optional query parameters

        Returns:
            ToolResponse with query results
        """
        logger.info("Running Cypher query", query=query[:50])

        try:
            results = await client.run_cypher(query, params)

            return ToolResponse(
                success=True,
                message=f"Query returned {len(results)} records",
                data={
                    "records": results,
                    "count": len(results),
                },
            )

        except Exception as e:
            logger.error("Cypher query failed", error=str(e))
            return ToolResponse(
                success=False,
                message="Cypher query execution failed",
                error=str(e),
            )

    @app.tool()
    async def create_node(
        labels: list[str],
        properties: dict[str, Any] | None = None,
    ) -> ToolResponse:
        """Create a new node in the graph.

        Args:
            labels: List of labels for the node (e.g., ["Person", "User"])
            properties: Optional node properties

        Returns:
            ToolResponse with created node details
        """
        logger.info("Creating node", labels=labels)

        try:
            node_data = NodeCreate(
                labels=labels,
                properties=properties or {},
            )
            node = await client.create_node(node_data)

            return ToolResponse(
                success=True,
                message=f"Created node with labels: {', '.join(labels)}",
                data={"node": node.model_dump()},
                next_steps=[
                    "Create relationships with create_relationship",
                    "Query nodes with run_cypher",
                ],
            )

        except Exception as e:
            logger.error("Failed to create node", error=str(e))
            return ToolResponse(
                success=False,
                message="Failed to create node",
                error=str(e),
            )

    @app.tool()
    async def get_node(node_id: str) -> ToolResponse:
        """Get a node by its ID.

        Args:
            node_id: The node ID

        Returns:
            ToolResponse with node details
        """
        logger.info("Getting node", node_id=node_id)

        try:
            node = await client.get_node(node_id)

            if node:
                return ToolResponse(
                    success=True,
                    message=f"Found node: {node_id}",
                    data={"node": node.model_dump()},
                )
            else:
                return ToolResponse(
                    success=False,
                    message=f"Node not found: {node_id}",
                    error="Node does not exist",
                )

        except Exception as e:
            logger.error("Failed to get node", error=str(e))
            return ToolResponse(
                success=False,
                message=f"Failed to get node {node_id}",
                error=str(e),
            )

    @app.tool()
    async def delete_node(node_id: str) -> ToolResponse:
        """Delete a node by its ID.

        Args:
            node_id: The node ID to delete

        Returns:
            ToolResponse confirming deletion
        """
        logger.info("Deleting node", node_id=node_id)

        try:
            await client.delete_node(node_id)

            return ToolResponse(
                success=True,
                message=f"Deleted node: {node_id}",
                data={"node_id": node_id},
            )

        except Exception as e:
            logger.error("Failed to delete node", error=str(e))
            return ToolResponse(
                success=False,
                message=f"Failed to delete node {node_id}",
                error=str(e),
            )

    @app.tool()
    async def find_nodes(
        labels: list[str] | None = None,
        properties: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> ToolResponse:
        """Find nodes matching criteria.

        Args:
            labels: Filter by labels (optional)
            properties: Filter by properties (optional)
            limit: Maximum results to return (default: 100)

        Returns:
            ToolResponse with matching nodes
        """
        logger.info("Finding nodes", labels=labels, limit=limit)

        try:
            nodes = await client.find_nodes(labels, properties, limit)

            return ToolResponse(
                success=True,
                message=f"Found {len(nodes)} matching nodes",
                data={
                    "nodes": [n.model_dump() for n in nodes],
                    "count": len(nodes),
                },
            )

        except Exception as e:
            logger.error("Failed to find nodes", error=str(e))
            return ToolResponse(
                success=False,
                message="Failed to find nodes",
                error=str(e),
            )

    @app.tool()
    async def create_relationship(
        type: str,
        start_node_id: str,
        end_node_id: str,
        properties: dict[str, Any] | None = None,
    ) -> ToolResponse:
        """Create a relationship between two nodes.

        Args:
            type: Relationship type (e.g., "KNOWS", "WORKS_FOR")
            start_node_id: ID of the start node
            end_node_id: ID of the end node
            properties: Optional relationship properties

        Returns:
            ToolResponse with created relationship
        """
        logger.info(
            "Creating relationship",
            type=type,
            start=start_node_id,
            end=end_node_id,
        )

        try:
            rel_data = RelationshipCreate(
                type=type,
                start_node_id=start_node_id,
                end_node_id=end_node_id,
                properties=properties or {},
            )
            rel = await client.create_relationship(rel_data)

            return ToolResponse(
                success=True,
                message=f"Created {type} relationship",
                data={"relationship": rel.model_dump()},
            )

        except Exception as e:
            logger.error("Failed to create relationship", error=str(e))
            return ToolResponse(
                success=False,
                message="Failed to create relationship",
                error=str(e),
            )

    @app.tool()
    async def delete_relationship(relationship_id: str) -> ToolResponse:
        """Delete a relationship by its ID.

        Args:
            relationship_id: The relationship ID to delete

        Returns:
            ToolResponse confirming deletion
        """
        logger.info("Deleting relationship", rel_id=relationship_id)

        try:
            await client.delete_relationship(relationship_id)

            return ToolResponse(
                success=True,
                message=f"Deleted relationship: {relationship_id}",
                data={"relationship_id": relationship_id},
            )

        except Exception as e:
            logger.error("Failed to delete relationship", error=str(e))
            return ToolResponse(
                success=False,
                message=f"Failed to delete relationship {relationship_id}",
                error=str(e),
            )

    @app.tool()
    async def find_paths(
        start_node_id: str,
        end_node_id: str,
        max_depth: int = 5,
        relationship_types: list[str] | None = None,
        limit: int = 10,
    ) -> ToolResponse:
        """Find paths between two nodes.

        Args:
            start_node_id: Starting node ID
            end_node_id: Target node ID
            max_depth: Maximum path depth (default: 5)
            relationship_types: Filter by relationship types (optional)
            limit: Maximum paths to return (default: 10)

        Returns:
            ToolResponse with paths found
        """
        logger.info(
            "Finding paths",
            start=start_node_id,
            end=end_node_id,
            max_depth=max_depth,
        )

        try:
            paths = await client.find_paths(
                start_node_id,
                end_node_id,
                max_depth,
                relationship_types,
                limit,
            )

            return ToolResponse(
                success=True,
                message=f"Found {len(paths)} paths",
                data={
                    "paths": [p.model_dump() for p in paths],
                    "count": len(paths),
                },
            )

        except Exception as e:
            logger.error("Failed to find paths", error=str(e))
            return ToolResponse(
                success=False,
                message="Failed to find paths",
                error=str(e),
            )

    @app.tool()
    async def get_schema() -> ToolResponse:
        """Get database schema information.

        Returns:
            ToolResponse with indexes, constraints, labels, and relationship types
        """
        logger.info("Getting database schema")

        try:
            schema = await client.get_schema()

            return ToolResponse(
                success=True,
                message="Schema retrieved",
                data={"schema": schema.model_dump()},
            )

        except Exception as e:
            logger.error("Failed to get schema", error=str(e))
            return ToolResponse(
                success=False,
                message="Failed to get schema",
                error=str(e),
            )
