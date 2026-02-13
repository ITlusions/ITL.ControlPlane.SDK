"""
Graph Database Enums for ITL ControlPlane SDK.

Provides enumeration types for graph node and relationship types.
"""
from enum import Enum


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
