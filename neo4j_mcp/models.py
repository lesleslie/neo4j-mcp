"""Pydantic models for Neo4j operations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeLabel(str, Enum):
    """Common node labels."""

    PERSON = "Person"
    COMPANY = "Company"
    PROJECT = "Project"
    DOCUMENT = "Document"
    CONCEPT = "Concept"
    ENTITY = "Entity"


class RelationshipType(str, Enum):
    """Common relationship types."""

    KNOWS = "KNOWS"
    WORKS_FOR = "WORKS_FOR"
    CREATED = "CREATED"
    CONTAINS = "CONTAINS"
    REFERENCES = "REFERENCES"
    RELATED_TO = "RELATED_TO"


class Node(BaseModel):
    """Neo4j node model."""

    id: str | None = Field(default=None, description="Node ID")
    labels: list[str] = Field(default_factory=list, description="Node labels")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Node properties",
    )


class Relationship(BaseModel):
    """Neo4j relationship model."""

    id: str | None = Field(default=None, description="Relationship ID")
    type: str = Field(description="Relationship type")
    start_node_id: str = Field(description="Start node ID")
    end_node_id: str = Field(description="End node ID")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Relationship properties",
    )


class Path(BaseModel):
    """Neo4j path model."""

    nodes: list[Node] = Field(default_factory=list, description="Path nodes")
    relationships: list[Relationship] = Field(
        default_factory=list,
        description="Path relationships",
    )
    length: int = Field(description="Path length (number of relationships)")


class QueryResult(BaseModel):
    """Result of a Cypher query."""

    records: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Query result records",
    )
    summary: dict[str, Any] | None = Field(
        default=None,
        description="Query summary statistics",
    )


class NodeCreate(BaseModel):
    """Model for creating a node."""

    labels: list[str] = Field(description="Node labels")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Node properties",
    )


class RelationshipCreate(BaseModel):
    """Model for creating a relationship."""

    type: str = Field(description="Relationship type")
    start_node_id: str = Field(description="Start node ID or match pattern")
    end_node_id: str = Field(description="End node ID or match pattern")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Relationship properties",
    )


class PathQuery(BaseModel):
    """Model for path finding queries."""

    start_node: str = Field(description="Start node ID or pattern")
    end_node: str = Field(description="End node ID or pattern")
    max_depth: int = Field(default=5, ge=1, le=100, description="Maximum path depth")
    relationship_types: list[str] | None = Field(
        default=None,
        description="Filter by relationship types",
    )
    direction: str = Field(
        default="both",
        description="Direction: out, in, or both",
    )


class IndexInfo(BaseModel):
    """Index information."""

    name: str = Field(description="Index name")
    labels_or_types: list[str] = Field(description="Labels or relationship types")
    properties: list[str] = Field(description="Indexed properties")
    uniqueness: bool = Field(default=False, description="Whether index is unique")


class ConstraintInfo(BaseModel):
    """Constraint information."""

    name: str = Field(description="Constraint name")
    type: str = Field(description="Constraint type")
    label: str = Field(description="Node label")
    properties: list[str] = Field(description="Constrained properties")


class SchemaInfo(BaseModel):
    """Database schema information."""

    indexes: list[IndexInfo] = Field(default_factory=list, description="Indexes")
    constraints: list[ConstraintInfo] = Field(
        default_factory=list,
        description="Constraints",
    )
    labels: list[str] = Field(default_factory=list, description="Node labels in use")
    relationship_types: list[str] = Field(
        default_factory=list,
        description="Relationship types in use",
    )
    property_keys: list[str] = Field(
        default_factory=list,
        description="Property keys in use",
    )


class ToolResponse(BaseModel):
    """Standard response format for MCP tools."""

    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Human-readable result message")
    data: dict[str, Any] | None = Field(default=None, description="Response data")
    error: str | None = Field(default=None, description="Error message if failed")
    next_steps: list[str] | None = Field(default=None, description="Suggested next actions")


class Neo4jError(BaseModel):
    """Error response from Neo4j."""

    code: str = Field(description="Neo4j error code")
    message: str = Field(description="Error message")
    description: str | None = Field(default=None, description="Detailed description")
