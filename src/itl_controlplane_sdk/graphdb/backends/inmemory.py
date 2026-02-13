"""
In-Memory Graph Database Implementation for ITL ControlPlane SDK.

Fast, zero-dependency backend suitable for development, testing,
and single-instance deployments.
"""
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from ..interfaces import GraphDatabaseInterface
from ..models import (
    GraphNode,
    GraphRelationship,
    GraphQuery,
    GraphQueryResult,
    NodeType,
    RelationshipType,
    GraphMetrics,
)

logger = logging.getLogger(__name__)


class InMemoryGraphDatabase(GraphDatabaseInterface):
    """In-memory graph database for development and testing."""

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.relationships: Dict[str, GraphRelationship] = {}
        self.node_relationships: Dict[str, Set[str]] = {}  # node_id -> relationship_ids
        self.connected = False

    async def connect(self) -> bool:
        self.connected = True
        logger.info("Connected to in-memory graph database")
        return True

    async def disconnect(self) -> None:
        self.connected = False
        logger.info("Disconnected from in-memory graph database")

    # -- Node CRUD ----------------------------------------------------------

    async def create_node(self, node: GraphNode) -> GraphNode:
        if node.id in self.nodes:
            raise ValueError(f"Node with ID {node.id} already exists")
        node.created_time = datetime.utcnow()
        node.modified_time = datetime.utcnow()
        self.nodes[node.id] = node
        self.node_relationships[node.id] = set()
        logger.debug("Created node: %s (%s)", node.id, node.node_type.value)
        return node

    async def update_node(self, node: GraphNode) -> GraphNode:
        if node.id not in self.nodes:
            raise ValueError(f"Node with ID {node.id} not found")
        node.modified_time = datetime.utcnow()
        self.nodes[node.id] = node
        logger.debug("Updated node: %s", node.id)
        return node

    async def delete_node(self, node_id: str) -> bool:
        if node_id not in self.nodes:
            return False
        # Remove all relationships first
        for rel_id in list(self.node_relationships.get(node_id, set())):
            await self.delete_relationship(rel_id)
        del self.nodes[node_id]
        del self.node_relationships[node_id]
        logger.debug("Deleted node: %s", node_id)
        return True

    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes.get(node_id)

    # -- Relationship CRUD --------------------------------------------------

    async def create_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
        if relationship.source_id not in self.nodes:
            raise ValueError(f"Source node {relationship.source_id} not found")
        if relationship.target_id not in self.nodes:
            raise ValueError(f"Target node {relationship.target_id} not found")
        relationship.created_time = datetime.utcnow()
        self.relationships[relationship.id] = relationship
        self.node_relationships[relationship.source_id].add(relationship.id)
        self.node_relationships[relationship.target_id].add(relationship.id)
        logger.debug(
            "Created relationship: %s -> %s (%s)",
            relationship.source_id,
            relationship.target_id,
            relationship.relationship_type.value,
        )
        return relationship

    async def delete_relationship(self, relationship_id: str) -> bool:
        if relationship_id not in self.relationships:
            return False
        rel = self.relationships[relationship_id]
        self.node_relationships.get(rel.source_id, set()).discard(relationship_id)
        self.node_relationships.get(rel.target_id, set()).discard(relationship_id)
        del self.relationships[relationship_id]
        logger.debug("Deleted relationship: %s", relationship_id)
        return True

    # -- Querying -----------------------------------------------------------

    async def query(self, query: GraphQuery) -> GraphQueryResult:
        """Simplified query — for production, use Neo4j with Cypher."""
        result_nodes: List[GraphNode] = []
        if "nodes" in query.query.lower() and "type" in query.parameters:
            node_type = NodeType(query.parameters["type"])
            result_nodes = [n for n in self.nodes.values() if n.node_type == node_type]
        return GraphQueryResult(
            nodes=result_nodes,
            raw_result={"query": query.query, "parameters": query.parameters},
        )

    async def find_nodes(
        self,
        node_type: Optional[NodeType] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> List[GraphNode]:
        results = list(self.nodes.values())
        if node_type:
            results = [n for n in results if n.node_type == node_type]
        if properties:
            results = [
                n for n in results
                if all(n.properties.get(k) == v for k, v in properties.items())
            ]
        return results

    async def get_relationships(
        self,
        node_id: str,
        relationship_type: Optional[RelationshipType] = None,
        direction: str = "both",
    ) -> List[GraphRelationship]:
        if node_id not in self.nodes:
            return []
        rel_ids = self.node_relationships.get(node_id, set())
        rels = [self.relationships[rid] for rid in rel_ids if rid in self.relationships]
        if relationship_type:
            rels = [r for r in rels if r.relationship_type == relationship_type]
        if direction == "outgoing":
            rels = [r for r in rels if r.source_id == node_id]
        elif direction == "incoming":
            rels = [r for r in rels if r.target_id == node_id]
        return rels

    async def get_metrics(self) -> GraphMetrics:
        node_counts: Dict[str, int] = {}
        for node in self.nodes.values():
            key = node.node_type.value
            node_counts[key] = node_counts.get(key, 0) + 1
        rel_counts: Dict[str, int] = {}
        for rel in self.relationships.values():
            key = rel.relationship_type.value
            rel_counts[key] = rel_counts.get(key, 0) + 1
        return GraphMetrics(
            total_nodes=len(self.nodes),
            total_relationships=len(self.relationships),
            node_counts=node_counts,
            relationship_counts=rel_counts,
        )
