"""
Graph Database Models for ITL ControlPlane SDK.

Provides graph node types, relationship types, and query models for
storing resource metadata, dependencies, and hierarchical structures.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from enum import Enum
import uuid


class NodeType(Enum):
    """Types of nodes in the resource graph."""
    SUBSCRIPTION = "subscription"
    RESOURCE_GROUP = "resourceGroup"
    RESOURCE = "resource"
    PROVIDER = "provider"
    NAMESPACE = "namespace"
    TENANT = "tenant"
    LOCATION = "location"
    EXTENDED_LOCATION = "extendedLocation"
    MANAGEMENT_GROUP = "managementGroup"
    DEPLOYMENT = "deployment"
    POLICY = "policy"
    TAG = "tag"


class RelationshipType(Enum):
    """Types of relationships between nodes."""
    CONTAINS = "CONTAINS"          # subscription CONTAINS resourceGroup
    BELONGS_TO = "BELONGS_TO"      # resource BELONGS_TO resourceGroup
    DEPENDS_ON = "DEPENDS_ON"      # resource DEPENDS_ON resource
    PROVIDES = "PROVIDES"          # provider PROVIDES resourceType
    DEPLOYED_IN = "DEPLOYED_IN"    # resource DEPLOYED_IN location
    MANAGED_BY = "MANAGED_BY"      # resource MANAGED_BY provider
    REFERENCES = "REFERENCES"      # resource REFERENCES resource
    INHERITS = "INHERITS"          # resource INHERITS configuration


@dataclass
class GraphNode:
    """Base node for the resource graph."""
    id: str
    node_type: NodeType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    labels: Set[str] = field(default_factory=set)
    created_time: datetime = field(default_factory=datetime.utcnow)
    modified_time: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        self.labels.add(self.node_type.value)


@dataclass
class GraphRelationship:
    """Relationship between two graph nodes."""
    id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    properties: Dict[str, Any] = field(default_factory=dict)
    created_time: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Specific node types
# ---------------------------------------------------------------------------

@dataclass
class SubscriptionNode(GraphNode):
    """Subscription node with tenant binding."""

    def __init__(self, subscription_id: str, name: str, tenant_id: str, **kwargs):
        super().__init__(
            id=subscription_id,
            node_type=NodeType.SUBSCRIPTION,
            name=name,
            properties={
                "subscriptionId": subscription_id,
                "tenantId": tenant_id,
                **kwargs,
            },
        )


@dataclass
class ResourceGroupNode(GraphNode):
    """Resource group node scoped to a subscription."""

    def __init__(self, resource_group_name: str, subscription_id: str, location: str, **kwargs):
        resource_group_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}"
        super().__init__(
            id=resource_group_id,
            node_type=NodeType.RESOURCE_GROUP,
            name=resource_group_name,
            properties={
                "resourceGroupName": resource_group_name,
                "subscriptionId": subscription_id,
                "location": location,
                **kwargs,
            },
        )


@dataclass
class ResourceNode(GraphNode):
    """Generic resource node."""

    def __init__(
        self,
        resource_id: str,
        resource_name: str,
        resource_type: str,
        subscription_id: str,
        resource_group: str,
        location: str,
        provider_namespace: str,
        **kwargs,
    ):
        super().__init__(
            id=resource_id,
            node_type=NodeType.RESOURCE,
            name=resource_name,
            properties={
                "resourceName": resource_name,
                "resourceType": resource_type,
                "subscriptionId": subscription_id,
                "resourceGroup": resource_group,
                "location": location,
                "providerNamespace": provider_namespace,
                **kwargs,
            },
        )


@dataclass
class ProviderNode(GraphNode):
    """Resource provider node."""

    def __init__(self, provider_namespace: str, **kwargs):
        super().__init__(
            id=provider_namespace,
            node_type=NodeType.PROVIDER,
            name=provider_namespace,
            properties={
                "namespace": provider_namespace,
                **kwargs,
            },
        )


@dataclass
class LocationNode(GraphNode):
    """Location / region node."""

    def __init__(self, location: str, display_name: Optional[str] = None, **kwargs):
        super().__init__(
            id=location,
            node_type=NodeType.LOCATION,
            name=display_name or location,
            properties={
                "location": location,
                "displayName": display_name or location,
                **kwargs,
            },
        )


# ---------------------------------------------------------------------------
# Query & result models
# ---------------------------------------------------------------------------

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
