"""
Metadata Service for ITL ControlPlane SDK Graph Module.

High-level service that manages resource metadata using a graph database
to store relationships, dependencies, and hierarchical structures.

Uses ``core.models.ResourceRequest`` and ``core.models.ResourceResponse``
instead of duplicating model definitions.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..interfaces import GraphDatabaseInterface
from ..factory import create_graph_database
from ..models import (
    GraphNode,
    GraphRelationship,
    NodeType,
    RelationshipType,
    SubscriptionNode,
    ResourceGroupNode,
    ResourceNode,
    ProviderNode,
    LocationNode,
    ResourceDependency,
    ResourceHierarchy,
    GraphMetrics,
)

# Import core SDK models — no more duplicate definitions
from itl_controlplane_sdk.core.models import (
    ResourceRequest,
    ResourceResponse,
    ProvisioningState,
)

logger = logging.getLogger(__name__)


class MetadataService:
    """
    Service for managing resource metadata using a graph database.

    Example::

        service = MetadataService("inmemory")
        await service.initialize()

        sub = await service.register_subscription("sub-1", "My Sub", "tenant-1")
        rg  = await service.register_resource_group("sub-1", "my-rg", "westeurope")

        hierarchy = await service.get_resource_hierarchy("sub-1")
    """

    def __init__(self, database_type: str = "inmemory", **db_kwargs):
        self.graph_db: GraphDatabaseInterface = create_graph_database(database_type, **db_kwargs)
        self.connected = False

    async def initialize(self) -> bool:
        """Initialize the metadata service and populate default nodes."""
        try:
            self.connected = await self.graph_db.connect()
            if self.connected:
                await self._create_initial_nodes()
                logger.info("MetadataService initialized (backend=%s)", type(self.graph_db).__name__)
            return self.connected
        except Exception as e:
            logger.error("Failed to initialize MetadataService: %s", e)
            return False

    async def shutdown(self) -> None:
        """Gracefully shut down the metadata service."""
        if self.connected:
            await self.graph_db.disconnect()
            self.connected = False
            logger.info("MetadataService shut down")

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    async def _create_initial_nodes(self) -> None:
        """Seed common locations and provider namespaces."""
        locations = [
            ("eastus", "East US"),
            ("westus", "West US"),
            ("northeurope", "North Europe"),
            ("westeurope", "West Europe"),
            ("southeastasia", "Southeast Asia"),
        ]
        for loc, display in locations:
            try:
                if not await self.graph_db.get_node(loc):
                    await self.graph_db.create_node(LocationNode(loc, display))
            except Exception as e:
                logger.debug("Could not create location node %s: %s", loc, e)

        providers = [
            "ITL.Identity",
            "ITL.Compute",
            "ITL.Storage",
            "ITL.Network",
            "ITL.Core",
        ]
        for ns in providers:
            try:
                if not await self.graph_db.get_node(ns):
                    await self.graph_db.create_node(ProviderNode(ns))
            except Exception as e:
                logger.debug("Could not create provider node %s: %s", ns, e)

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    async def register_subscription(
        self, subscription_id: str, name: str, tenant_id: str, **kwargs
    ) -> SubscriptionNode:
        """Register a subscription in the metadata graph."""
        existing = await self.graph_db.get_node(subscription_id)
        if existing:
            logger.debug("Subscription %s already exists", subscription_id)
            return SubscriptionNode(
                subscription_id=existing.id,
                name=existing.name,
                tenant_id=existing.properties.get("tenantId", ""),
            )
        node = SubscriptionNode(subscription_id, name, tenant_id, **kwargs)
        created = await self.graph_db.create_node(node)
        return SubscriptionNode(
            subscription_id=created.id,
            name=created.name,
            tenant_id=created.properties.get("tenantId", ""),
        )

    async def get_subscription(self, subscription_id: str) -> Optional[SubscriptionNode]:
        """Retrieve subscription metadata."""
        node = await self.graph_db.get_node(subscription_id)
        if node and node.node_type == NodeType.SUBSCRIPTION:
            return SubscriptionNode(
                subscription_id=node.id,
                name=node.name,
                tenant_id=node.properties.get("tenantId", ""),
            )
        return None

    async def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription and all its relationships."""
        return await self.graph_db.delete_node(subscription_id)

    async def list_subscriptions(self) -> List[SubscriptionNode]:
        """List all subscriptions."""
        nodes = await self.graph_db.find_nodes(node_type=NodeType.SUBSCRIPTION)
        return [
            SubscriptionNode(
                subscription_id=n.id,
                name=n.name,
                tenant_id=n.properties.get("tenantId", ""),
            )
            for n in nodes
        ]

    # ------------------------------------------------------------------
    # Resource Group management
    # ------------------------------------------------------------------

    async def register_resource_group(
        self, subscription_id: str, resource_group_name: str, location: str, **kwargs
    ) -> ResourceGroupNode:
        """Register a resource group in the metadata graph."""
        rg_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}"
        existing = await self.graph_db.get_node(rg_id)
        if existing:
            logger.debug("Resource group %s already exists", resource_group_name)
            return ResourceGroupNode(
                resource_group_name=existing.properties.get("resourceGroupName", existing.name),
                subscription_id=existing.properties.get("subscriptionId", subscription_id),
                location=existing.properties.get("location", location),
            )

        rg_node = ResourceGroupNode(resource_group_name, subscription_id, location, **kwargs)
        created = await self.graph_db.create_node(rg_node)

        # Create relationships: subscription -> rg, rg -> location
        await self._create_containment_relationship(subscription_id, rg_id)
        await self._create_location_relationship(rg_id, location)

        return ResourceGroupNode(
            resource_group_name=created.properties.get("resourceGroupName", created.name),
            subscription_id=created.properties.get("subscriptionId", subscription_id),
            location=created.properties.get("location", location),
        )

    async def get_resource_group(
        self, subscription_id: str, resource_group_name: str
    ) -> Optional[ResourceGroupNode]:
        """Retrieve resource group metadata."""
        rg_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}"
        node = await self.graph_db.get_node(rg_id)
        if node and node.node_type == NodeType.RESOURCE_GROUP:
            return ResourceGroupNode(
                resource_group_name=node.properties.get("resourceGroupName", node.name),
                subscription_id=node.properties.get("subscriptionId", subscription_id),
                location=node.properties.get("location", ""),
            )
        return None

    async def delete_resource_group(self, subscription_id: str, resource_group_name: str) -> bool:
        """Delete a resource group."""
        rg_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}"
        return await self.graph_db.delete_node(rg_id)

    async def list_resource_groups(self, subscription_id: str) -> List[ResourceGroupNode]:
        """List all resource groups in a subscription."""
        nodes = await self.graph_db.find_nodes(
            node_type=NodeType.RESOURCE_GROUP,
            properties={"subscriptionId": subscription_id},
        )
        return [
            ResourceGroupNode(
                resource_group_name=n.properties.get("resourceGroupName", n.name),
                subscription_id=n.properties.get("subscriptionId", subscription_id),
                location=n.properties.get("location", ""),
            )
            for n in nodes
        ]

    # ------------------------------------------------------------------
    # Resource management
    # ------------------------------------------------------------------

    async def register_resource(
        self, request: ResourceRequest, response: ResourceResponse
    ) -> ResourceNode:
        """Register a resource in the metadata graph."""
        resource_id = response.id
        existing = await self.graph_db.get_node(resource_id)
        if existing:
            existing.properties.update({
                "properties": response.properties,
                "tags": response.tags,
                "provisioning_state": response.provisioning_state.value,
                "modified_time": datetime.utcnow().isoformat(),
            })
            updated = await self.graph_db.update_node(existing)
            return ResourceNode(**{
                k: v for k, v in updated.__dict__.items()
                if k in ("resource_id", "resource_name", "resource_type",
                         "subscription_id", "resource_group", "location", "provider_namespace")
            }) if False else self._to_resource_node(updated, request)

        resource_node = ResourceNode(
            resource_id=resource_id,
            resource_name=request.resource_name,
            resource_type=request.resource_type,
            subscription_id=request.subscription_id,
            resource_group=request.resource_group,
            location=request.location,
            provider_namespace=request.provider_namespace,
            properties=response.properties,
            tags=response.tags,
            provisioning_state=response.provisioning_state.value,
        )
        created = await self.graph_db.create_node(resource_node)

        # Relationships: resource -> rg, resource -> location, resource -> provider
        rg_id = f"/subscriptions/{request.subscription_id}/resourceGroups/{request.resource_group}"
        await self._safe_relationship(
            f"{resource_id}-belongs-{rg_id}",
            resource_id, rg_id,
            RelationshipType.BELONGS_TO,
        )
        await self._create_location_relationship(resource_id, request.location)
        await self._safe_relationship(
            f"{resource_id}-managed-{request.provider_namespace}",
            resource_id, request.provider_namespace,
            RelationshipType.MANAGED_BY,
        )

        return self._to_resource_node(created, request)

    async def get_resource(self, resource_id: str) -> Optional[ResourceNode]:
        """Get resource metadata by ID."""
        node = await self.graph_db.get_node(resource_id)
        if node and node.node_type == NodeType.RESOURCE:
            return self._node_to_resource_node(node)
        return None

    async def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource from metadata."""
        return await self.graph_db.delete_node(resource_id)

    async def list_resources(
        self, subscription_id: str, resource_group: Optional[str] = None
    ) -> List[ResourceNode]:
        """List resources in a subscription, optionally filtered by resource group."""
        props: Dict[str, Any] = {"subscriptionId": subscription_id}
        if resource_group:
            props["resourceGroup"] = resource_group
        nodes = await self.graph_db.find_nodes(node_type=NodeType.RESOURCE, properties=props)
        return [self._node_to_resource_node(n) for n in nodes]

    # ------------------------------------------------------------------
    # Dependency management
    # ------------------------------------------------------------------

    async def add_dependency(
        self, source_id: str, target_id: str, dependency_type: str = "DEPENDS_ON"
    ) -> bool:
        """Add a dependency between two resources."""
        return await self._safe_relationship(
            f"{source_id}-{dependency_type.lower()}-{target_id}",
            source_id, target_id,
            RelationshipType.DEPENDS_ON,
            properties={"dependency_type": dependency_type},
        )

    async def get_resource_dependencies(self, resource_id: str) -> ResourceDependency:
        """Get all dependencies for a resource."""
        outgoing = await self.graph_db.get_relationships(
            resource_id, RelationshipType.DEPENDS_ON, "outgoing"
        )
        incoming = await self.graph_db.get_relationships(
            resource_id, RelationshipType.DEPENDS_ON, "incoming"
        )
        return ResourceDependency(
            resource_id=resource_id,
            depends_on=[r.target_id for r in outgoing],
            dependents=[r.source_id for r in incoming],
        )

    # ------------------------------------------------------------------
    # Hierarchy & query
    # ------------------------------------------------------------------

    async def get_resource_hierarchy(self, subscription_id: str) -> ResourceHierarchy:
        """Get the complete resource hierarchy for a subscription."""
        rgs = await self.list_resource_groups(subscription_id)
        hierarchy = ResourceHierarchy(subscription_id=subscription_id)
        for rg in rgs:
            rg_name = rg.properties.get("resourceGroupName") or rg.name
            hierarchy.resource_groups.append(rg_name)
            resources = await self.list_resources(subscription_id, rg_name)
            hierarchy.resources[rg_name] = [r.name for r in resources]
        return hierarchy

    async def search_resources(
        self, search_term: str, subscription_id: Optional[str] = None
    ) -> List[ResourceNode]:
        """Search resources by name or property values."""
        all_nodes = await self.graph_db.find_nodes(node_type=NodeType.RESOURCE)
        term = search_term.lower()
        results = []
        for node in all_nodes:
            if subscription_id and node.properties.get("subscriptionId") != subscription_id:
                continue
            if term in node.name.lower() or any(
                term in str(v).lower() for v in node.properties.values()
            ):
                results.append(self._node_to_resource_node(node))
        return results

    async def get_metrics(self) -> GraphMetrics:
        """Get metadata service metrics."""
        return await self.graph_db.get_metrics()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _create_containment_relationship(self, parent_id: str, child_id: str) -> bool:
        """Create a CONTAINS relationship (parent -> child)."""
        return await self._safe_relationship(
            f"{parent_id}-contains-{child_id}",
            parent_id, child_id,
            RelationshipType.CONTAINS,
        )

    async def _create_location_relationship(self, source_id: str, location: str) -> bool:
        """Create a DEPLOYED_IN relationship (source -> location)."""
        return await self._safe_relationship(
            f"{source_id}-deployed-{location}",
            source_id, location,
            RelationshipType.DEPLOYED_IN,
        )

    async def _safe_relationship(
        self,
        rel_id: str,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a relationship, swallowing errors for missing nodes."""
        try:
            await self.graph_db.create_relationship(
                GraphRelationship(
                    id=rel_id,
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=rel_type,
                    properties=properties or {},
                )
            )
            return True
        except Exception as e:
            logger.debug("Could not create relationship %s: %s", rel_id, e)
            return False

    @staticmethod
    def _to_resource_node(node: GraphNode, request: ResourceRequest) -> ResourceNode:
        """Convert a GraphNode back to a ResourceNode using the original request."""
        return ResourceNode(
            resource_id=node.id,
            resource_name=request.resource_name,
            resource_type=request.resource_type,
            subscription_id=request.subscription_id,
            resource_group=request.resource_group,
            location=request.location,
            provider_namespace=request.provider_namespace,
        )

    @staticmethod
    def _node_to_resource_node(node: GraphNode) -> ResourceNode:
        """Convert a GraphNode to a ResourceNode using stored properties."""
        props = node.properties
        return ResourceNode(
            resource_id=node.id,
            resource_name=props.get("resourceName", node.name),
            resource_type=props.get("resourceType", ""),
            subscription_id=props.get("subscriptionId", ""),
            resource_group=props.get("resourceGroup", ""),
            location=props.get("location", ""),
            provider_namespace=props.get("providerNamespace", ""),
        )
