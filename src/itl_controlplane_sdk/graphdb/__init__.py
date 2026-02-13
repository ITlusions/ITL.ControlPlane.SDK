"""
Graph Database Module for ITL ControlPlane SDK.

Provides graph-based metadata storage and relationship tracking for resources,
subscriptions, resource groups, and their dependencies.

Supports:
- In-memory graph database (development/testing)
- Neo4j backend (production)

Install::

    pip install itl-controlplane-sdk[graphdb]          # in-memory only
    pip install itl-controlplane-sdk[graphdb-neo4j]     # + Neo4j driver

Example:
    from itl_controlplane_sdk.graphdb import (
        create_graph_database,
        MetadataService,
    )

    # In-memory for development
    metadata = MetadataService("inmemory")
    await metadata.initialize()

    # Register a subscription
    sub = await metadata.register_subscription(
        subscription_id="sub-123",
        name="My Subscription",
        tenant_id="tenant-456",
    )

    # Register a resource group under that subscription
    rg = await metadata.register_resource_group(
        subscription_id="sub-123",
        resource_group_name="my-rg",
        location="westeurope",
    )

    # Query hierarchy
    hierarchy = await metadata.get_resource_hierarchy("sub-123")
"""

from .models import (
    # Enums
    NodeType,
    RelationshipType,
    # Base types
    GraphNode,
    GraphRelationship,
    # Specific node types
    SubscriptionNode,
    ResourceGroupNode,
    ResourceNode,
    ProviderNode,
    LocationNode,
    # Query types
    GraphQuery,
    GraphQueryResult,
    # Result types
    ResourceDependency,
    ResourceHierarchy,
    GraphMetrics,
)

from .interfaces import GraphDatabaseInterface
from .backends import (
    InMemoryGraphDatabase,
    SQLGraphDatabase,
    SQLiteGraphDatabase,
    PostgresGraphDatabase,
    SQLConnectionAdapter,
    SQLiteAdapter,
    PostgresAdapter,
)
from .factory import create_graph_database
from .services import MetadataService

__all__ = [
    # Enums
    "NodeType",
    "RelationshipType",
    # Base types
    "GraphNode",
    "GraphRelationship",
    # Specific node types
    "SubscriptionNode",
    "ResourceGroupNode",
    "ResourceNode",
    "ProviderNode",
    "LocationNode",
    # Query types
    "GraphQuery",
    "GraphQueryResult",
    # Result types
    "ResourceDependency",
    "ResourceHierarchy",
    "GraphMetrics",
    # Database
    "GraphDatabaseInterface",
    "InMemoryGraphDatabase",
    "SQLGraphDatabase",
    "SQLiteGraphDatabase",
    "PostgresGraphDatabase",
    "SQLConnectionAdapter",
    "SQLiteAdapter",
    "PostgresAdapter",
    "create_graph_database",
    # Service
    "MetadataService",
]
