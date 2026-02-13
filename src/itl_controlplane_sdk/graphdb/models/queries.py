"""
Graph Query and Result Models for ITL ControlPlane SDK.

Query interfaces and result types for graph database operations.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any

from .nodes import GraphNode
from .relationships import GraphRelationship


@dataclass
class GraphQuery:
    """Graph database query."""
    query: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphQueryResult:
    """Result from a graph query."""
    nodes: List[GraphNode] = field(default_factory=list)
    relationships: List[GraphRelationship] = field(default_factory=list)
    raw_result: Any = None


@dataclass
class ResourceDependency:
    """Resource dependency information."""
    resource_id: str
    depends_on: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    dependency_type: str = "DEPENDS_ON"


@dataclass
class ResourceHierarchy:
    """Resource hierarchy for a subscription."""
    subscription_id: str
    resource_groups: List[str] = field(default_factory=list)
    resources: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class GraphMetrics:
    """Graph database metrics."""
    total_nodes: int = 0
    total_relationships: int = 0
    node_counts: Dict[str, int] = field(default_factory=dict)
    relationship_counts: Dict[str, int] = field(default_factory=dict)
