"""
Graph Node types for ITL ControlPlane SDK.

Specific node implementations for subscriptions, resource groups, resources, etc.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set
from datetime import datetime
import uuid

from .enums import NodeType


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
