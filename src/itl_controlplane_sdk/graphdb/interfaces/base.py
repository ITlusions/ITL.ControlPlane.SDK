"""
Graph Database Interface for ITL ControlPlane SDK.

Abstract interface for graph database operations, enabling multiple
backend implementations (in-memory, SQL, Neo4j, etc.).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from ..models import (
    GraphNode,
    GraphRelationship,
    GraphQuery,
    GraphQueryResult,
    NodeType,
    RelationshipType,
    GraphMetrics,
)


class GraphDatabaseInterface(ABC):
    """Abstract interface for graph database operations."""

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the graph database."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the graph database."""

    @abstractmethod
    async def create_node(self, node: GraphNode) -> GraphNode:
        """Create a new node in the graph."""

    @abstractmethod
    async def update_node(self, node: GraphNode) -> GraphNode:
        """Update an existing node."""

    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its relationships."""

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by its ID."""

    @abstractmethod
    async def create_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
        """Create a relationship between two nodes."""

    @abstractmethod
    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship."""

    @abstractmethod
    async def query(self, query: GraphQuery) -> GraphQueryResult:
        """Execute a graph query."""

    @abstractmethod
    async def find_nodes(
        self,
        node_type: Optional[NodeType] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> List[GraphNode]:
        """Find nodes by type and/or properties."""

    @abstractmethod
    async def get_relationships(
        self,
        node_id: str,
        relationship_type: Optional[RelationshipType] = None,
        direction: str = "both",
    ) -> List[GraphRelationship]:
        """Get relationships for a node."""

    @abstractmethod
    async def get_metrics(self) -> GraphMetrics:
        """Get database metrics."""
