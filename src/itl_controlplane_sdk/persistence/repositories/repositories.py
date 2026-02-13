"""
Repository Pattern for ITL ControlPlane resource persistence.

Provides async CRUD repositories for each resource type, built on
SQLAlchemy 2.0 async sessions. Each repository handles:
- Create / Update (upsert)
- Get by ID or name
- List with optional filtering
- Delete
- Relationship management

Repositories also trigger Neo4j sync when a sync service is configured.

Usage::

    from itl_controlplane_sdk.persistence.repositories import (
        SubscriptionRepository,
        ResourceGroupRepository,
    )
    
    repo = SubscriptionRepository(session)
    sub = await repo.create(name="prod-sub", display_name="Production", ...)
    subs = await repo.list_all()
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic

from sqlalchemy import select, delete as sa_delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..data.models import (
    Base,
    TenantModel,
    ManagementGroupModel,
    SubscriptionModel,
    ResourceGroupModel,
    LocationModel,
    ExtendedLocationModel,
    PolicyModel,
    TagModel,
    DeploymentModel,
    ResourceRelationshipModel,
    AuditEventModel,
    AuditAction,
    ActorType,
    DEFAULT_TENANT_NAME,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Base)


# ===================================================================
# Base Repository
# ===================================================================

class BaseRepository(Generic[T]):
    """
    Generic async repository with common CRUD operations.
    
    Subclasses only need to set ``model_class`` and optionally override
    methods for resource-specific logic.
    """

    model_class: Type[T]

    def __init__(self, session: AsyncSession, neo4j_sync=None):
        self.session = session
        self.neo4j_sync = neo4j_sync

    async def get_by_id(self, resource_id: str) -> Optional[T]:
        """Get a resource by its primary key ID."""
        result = await self.session.get(self.model_class, resource_id)
        return result

    async def get_by_name(self, name: str) -> Optional[T]:
        """Get a resource by its unique name."""
        stmt = select(self.model_class).where(self.model_class.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, **filters) -> List[T]:
        """List all resources, optionally filtered by column values."""
        stmt = select(self.model_class)
        for key, value in filters.items():
            if hasattr(self.model_class, key) and value is not None:
                stmt = stmt.where(getattr(self.model_class, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **filters) -> int:
        """Count resources, optionally filtered."""
        stmt = select(func.count()).select_from(self.model_class)
        for key, value in filters.items():
            if hasattr(self.model_class, key) and value is not None:
                stmt = stmt.where(getattr(self.model_class, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def delete_by_id(self, resource_id: str) -> bool:
        """Delete a resource by ID. Returns True if found and deleted."""
        obj = await self.get_by_id(resource_id)
        if obj:
            await self.session.delete(obj)
            await self.session.flush()
            # Neo4j sync
            if self.neo4j_sync:
                await self.neo4j_sync.delete_node(
                    resource_id, self.model_class.__tablename__
                )
            return True
        return False

    async def delete_by_name(self, name: str) -> bool:
        """Delete a resource by name."""
        obj = await self.get_by_name(name)
        if obj:
            await self.session.delete(obj)
            await self.session.flush()
            if self.neo4j_sync:
                await self.neo4j_sync.delete_node(
                    obj.id, self.model_class.__tablename__
                )
            return True
        return False

    async def _sync_to_neo4j(self, obj: T, relationships: Optional[List[dict]] = None):
        """Sync a resource to Neo4j if sync service is configured.

        Important: obj.to_dict() is called here while the SQLAlchemy greenlet
        context is still active, so all lazy-loaded attributes are resolved
        before control passes to the Neo4j async driver.
        """
        if self.neo4j_sync and hasattr(obj, "to_dict"):
            # Eagerly resolve all ORM attributes while still in the
            # SQLAlchemy greenlet context to avoid MissingGreenlet errors.
            props = obj.to_dict()
            await self.neo4j_sync.sync_node(
                node_type=self.model_class.__tablename__,
                node_id=obj.id,
                properties=props,
                relationships=relationships,
            )


# ===================================================================
# Tenant Repository
# ===================================================================

class TenantRepository(BaseRepository[TenantModel]):
    model_class = TenantModel

    async def create_or_update(
        self,
        name: str,
        display_name: str,
        tenant_id: Optional[str] = None,
        description: Optional[str] = None,
        state: str = "Active",
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> TenantModel:
        """Create or update a tenant."""
        arm_id = f"/providers/ITL.Management/tenants/{name}"
        t_id = tenant_id or str(uuid.uuid4())

        existing = await self.get_by_id(arm_id)
        if existing:
            existing.display_name = display_name
            existing.description = description
            existing.state = state
            existing.tags = tags or existing.tags
            existing.properties = properties or existing.properties
            await self.session.flush()
            # Refresh to eagerly load all columns, preventing
            # MissingGreenlet errors during Neo4j sync.
            await self.session.refresh(existing)
            obj = existing
        else:
            obj = TenantModel(
                id=arm_id,
                name=name,
                display_name=display_name,
                tenant_id=t_id,
                description=description,
                state=state,
                tags=tags or {},
                properties=properties or {},
            )
            self.session.add(obj)
            await self.session.flush()

        await self._sync_to_neo4j(obj)
        return obj

    async def ensure_default_tenant(self) -> TenantModel:
        """Ensure the default ITL tenant exists. Creates it if missing."""
        existing = await self.get_by_name(DEFAULT_TENANT_NAME)
        if existing:
            return existing
        return await self.create_or_update(
            name=DEFAULT_TENANT_NAME,
            display_name="ITL Default Tenant",
            description="Default tenant for all resources. Auto-created on startup.",
            state="Active",
            tags={"system": "true", "default": "true"},
        )

    async def get_default_tenant_id(self) -> str:
        """Get the ARM ID of the default tenant."""
        tenant = await self.ensure_default_tenant()
        return tenant.id


# ===================================================================
# Management Group Repository
# ===================================================================

class ManagementGroupRepository(BaseRepository[ManagementGroupModel]):
    model_class = ManagementGroupModel

    async def create_or_update(
        self,
        name: str,
        display_name: str,
        parent_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ManagementGroupModel:
        """Create or update a management group."""
        mg_id = f"/providers/ITL.Management/managementGroups/{name}"

        # Resolve parent_id: could be a name or ARM path
        resolved_parent_id = None
        if parent_id:
            if parent_id.startswith("/"):
                resolved_parent_id = parent_id
            else:
                resolved_parent_id = f"/providers/ITL.Management/managementGroups/{parent_id}"

        # Resolve tenant_id: default to ITL tenant if not provided
        resolved_tenant_id = None
        if tenant_id:
            if tenant_id.startswith("/"):
                resolved_tenant_id = tenant_id
            else:
                resolved_tenant_id = f"/providers/ITL.Management/tenants/{tenant_id}"
        else:
            # Auto-assign default tenant
            resolved_tenant_id = f"/providers/ITL.Management/tenants/{DEFAULT_TENANT_NAME}"

        existing = await self.get_by_id(mg_id)
        if existing:
            existing.display_name = display_name
            existing.parent_id = resolved_parent_id
            existing.tenant_id = resolved_tenant_id
            existing.description = description
            existing.tags = tags or existing.tags
            existing.properties = properties or existing.properties
            await self.session.flush()
            await self.session.refresh(existing)
            obj = existing
        else:
            obj = ManagementGroupModel(
                id=mg_id,
                name=name,
                display_name=display_name,
                parent_id=resolved_parent_id,
                tenant_id=resolved_tenant_id,
                description=description,
                tags=tags or {},
                properties=properties or {},
            )
            self.session.add(obj)
            await self.session.flush()

        # Neo4j sync with parent and tenant relationships
        rels = []
        if resolved_parent_id:
            rels.append({
                "type": "BELONGS_TO",
                "target_type": "management_groups",
                "target_id": resolved_parent_id,
            })
        if resolved_tenant_id:
            rels.append({
                "type": "BELONGS_TO",
                "target_type": "tenants",
                "target_id": resolved_tenant_id,
            })
        await self._sync_to_neo4j(obj, rels)
        return obj

    async def get_hierarchy(self, root_name: Optional[str] = None) -> List[ManagementGroupModel]:
        """Get the full management group hierarchy starting from root."""
        if root_name:
            root = await self.get_by_name(root_name)
            if not root:
                return []
            stmt = select(ManagementGroupModel).where(
                ManagementGroupModel.parent_id == root.id
            )
        else:
            stmt = select(ManagementGroupModel).where(
                ManagementGroupModel.parent_id.is_(None)
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# ===================================================================
# Subscription Repository
# ===================================================================

class SubscriptionRepository(BaseRepository[SubscriptionModel]):
    model_class = SubscriptionModel

    async def create_or_update(
        self,
        name: str,
        display_name: str,
        subscription_id: Optional[str] = None,
        state: str = "Enabled",
        management_group_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> SubscriptionModel:
        """Create or update a subscription."""
        sub_uuid = subscription_id or str(uuid.uuid4())
        sub_db_id = f"/subscriptions/{name}"

        # Resolve management_group_id: could be name or ARM path
        resolved_mg_id = None
        if management_group_id:
            if management_group_id.startswith("/"):
                resolved_mg_id = management_group_id
            else:
                resolved_mg_id = f"/providers/ITL.Management/managementGroups/{management_group_id}"

        # Resolve tenant_id: could be name or ARM path
        resolved_tenant_id = None
        if tenant_id:
            if tenant_id.startswith("/"):
                resolved_tenant_id = tenant_id
            else:
                resolved_tenant_id = f"/providers/ITL.Management/tenants/{tenant_id}"

        existing = await self.get_by_id(sub_db_id)
        if existing:
            existing.display_name = display_name
            existing.state = state
            existing.management_group_id = resolved_mg_id
            existing.tenant_id = resolved_tenant_id
            existing.tags = tags or existing.tags
            existing.properties = properties or existing.properties
            await self.session.flush()
            await self.session.refresh(existing)
            obj = existing
        else:
            obj = SubscriptionModel(
                id=sub_db_id,
                name=name,
                display_name=display_name,
                subscription_id=sub_uuid,
                state=state,
                management_group_id=resolved_mg_id,
                tenant_id=resolved_tenant_id,
                tags=tags or {},
                properties=properties or {},
            )
            self.session.add(obj)
            await self.session.flush()

        # Neo4j sync with management group relationship
        rels = []
        if resolved_mg_id:
            rels.append({
                "type": "BELONGS_TO",
                "target_type": "management_groups",
                "target_id": resolved_mg_id,
            })
        if resolved_tenant_id:
            rels.append({
                "type": "BELONGS_TO",
                "target_type": "tenants",
                "target_id": resolved_tenant_id,
            })
        await self._sync_to_neo4j(obj, rels)
        return obj

    async def get_by_subscription_id(self, subscription_id: str) -> Optional[SubscriptionModel]:
        """Find a subscription by its UUID subscription_id."""
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.subscription_id == subscription_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


# ===================================================================
# Resource Group Repository
# ===================================================================

class ResourceGroupRepository(BaseRepository[ResourceGroupModel]):
    model_class = ResourceGroupModel

    async def create_or_update(
        self,
        name: str,
        subscription_id: str,
        location: str,
        tenant_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ResourceGroupModel:
        """Create or update a resource group within a subscription scope."""
        # Resolve subscription: could be a name, UUID, or ARM path
        sub_db_id = await self._resolve_subscription_id(subscription_id)
        # Extract the subscription part for the RG ARM id
        rg_id = f"{sub_db_id}/resourceGroups/{name}"

        # Resolve tenant_id: could be name or ARM path
        resolved_tenant_id = None
        if tenant_id:
            if tenant_id.startswith("/"):
                resolved_tenant_id = tenant_id
            else:
                resolved_tenant_id = f"/providers/ITL.Management/tenants/{tenant_id}"

        existing = await self.get_by_id(rg_id)
        if existing:
            existing.location = location
            existing.tenant_id = resolved_tenant_id
            existing.tags = tags or existing.tags
            existing.properties = properties or existing.properties
            await self.session.flush()
            await self.session.refresh(existing)
            obj = existing
        else:
            obj = ResourceGroupModel(
                id=rg_id,
                name=name,
                subscription_id=sub_db_id,
                tenant_id=resolved_tenant_id,
                location=location,
                tags=tags or {},
                properties=properties or {},
            )
            self.session.add(obj)
            await self.session.flush()

        # Neo4j sync with subscription relationship
        rels = [{
            "type": "BELONGS_TO",
            "target_type": "subscriptions",
            "target_id": sub_db_id,
        }]
        if resolved_tenant_id:
            rels.append({
                "type": "BELONGS_TO",
                "target_type": "tenants",
                "target_id": resolved_tenant_id,
            })
        await self._sync_to_neo4j(obj, rels)
        return obj

    async def _resolve_subscription_id(self, subscription_ref: str) -> str:
        """
        Resolve a subscription reference (name, UUID, or ARM path) to the
        subscription's primary key (ARM-style ID).
        """
        # Already an ARM path
        if subscription_ref.startswith("/subscriptions/"):
            return subscription_ref

        # Try by UUID (subscription_id column)
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.subscription_id == subscription_ref
        )
        result = await self.session.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub:
            return sub.id

        # Try by name
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.name == subscription_ref
        )
        result = await self.session.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub:
            return sub.id

        # Fallback: construct ARM path from ref (may fail FK constraint)
        return f"/subscriptions/{subscription_ref}"

    async def list_by_subscription(self, subscription_name: str) -> List[ResourceGroupModel]:
        """List all resource groups in a subscription."""
        sub_db_id = f"/subscriptions/{subscription_name}"
        stmt = select(ResourceGroupModel).where(
            ResourceGroupModel.subscription_id == sub_db_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# ===================================================================
# Location Repository
# ===================================================================

class LocationRepository(BaseRepository[LocationModel]):
    model_class = LocationModel

    async def create_or_update(
        self,
        name: str,
        display_name: str,
        shortname: Optional[str] = None,
        region: Optional[str] = None,
        geography: Optional[str] = None,
        geography_group: Optional[str] = None,
        location_type: str = "Region",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        physical_location: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> LocationModel:
        """Create or update a location."""
        loc_id = f"location:{name}"

        existing = await self.get_by_id(loc_id)
        if existing:
            existing.display_name = display_name
            existing.shortname = shortname or existing.shortname
            existing.region = region or existing.region
            existing.geography = geography or existing.geography
            existing.geography_group = geography_group or existing.geography_group
            existing.location_type = location_type
            existing.latitude = latitude
            existing.longitude = longitude
            existing.physical_location = physical_location
            existing.properties = properties or existing.properties
            await self.session.flush()
            return existing
        else:
            obj = LocationModel(
                id=loc_id,
                name=name,
                display_name=display_name,
                shortname=shortname,
                region=region,
                geography=geography,
                geography_group=geography_group,
                location_type=location_type,
                latitude=latitude,
                longitude=longitude,
                physical_location=physical_location,
                properties=properties or {},
            )
            self.session.add(obj)
            await self.session.flush()
            await self._sync_to_neo4j(obj)
            return obj

    async def seed_defaults(self, default_locations: list, extended_locations: list):
        """Seed default locations if they don't exist."""
        count = 0
        for loc in default_locations:
            existing = await self.get_by_name(loc["name"])
            if not existing:
                await self.create_or_update(
                    name=loc["name"],
                    display_name=loc.get("display_name", loc["name"]),
                    shortname=loc.get("shortname"),
                    region=loc.get("region"),
                    location_type=loc.get("location_type", "Region"),
                )
                count += 1
        logger.info("Seeded %d new locations (total available: %d)",
                     count, len(default_locations))


# ===================================================================
# Extended Location Repository
# ===================================================================

class ExtendedLocationRepository(BaseRepository[ExtendedLocationModel]):
    model_class = ExtendedLocationModel

    async def create_or_update(
        self,
        name: str,
        display_name: str,
        shortname: Optional[str] = None,
        region: Optional[str] = None,
        location_type: str = "EdgeZone",
        home_location: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ExtendedLocationModel:
        """Create or update an extended location."""
        ext_id = f"extendedLocation:{name}"

        existing = await self.get_by_id(ext_id)
        if existing:
            existing.display_name = display_name
            existing.location_type = location_type
            existing.home_location = home_location
            existing.properties = properties or existing.properties
            await self.session.flush()
            return existing
        else:
            obj = ExtendedLocationModel(
                id=ext_id,
                name=name,
                display_name=display_name,
                shortname=shortname,
                region=region,
                location_type=location_type,
                home_location=home_location,
                properties=properties or {},
            )
            self.session.add(obj)
            await self.session.flush()
            await self._sync_to_neo4j(obj)
            return obj


# ===================================================================
# Policy Repository
# ===================================================================

class PolicyRepository(BaseRepository[PolicyModel]):
    model_class = PolicyModel

    async def create_or_update(
        self,
        name: str,
        display_name: Optional[str] = None,
        policy_type: str = "Custom",
        mode: str = "Indexed",
        description: Optional[str] = None,
        rules: Optional[dict] = None,
        parameters: Optional[dict] = None,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> PolicyModel:
        """Create or update a policy."""
        policy_id = f"policy:{name}"

        existing = await self.get_by_id(policy_id)
        if existing:
            existing.display_name = display_name or existing.display_name
            existing.policy_type = policy_type
            existing.mode = mode
            existing.description = description
            existing.rules = rules
            existing.parameters = parameters
            existing.tags = tags or existing.tags
            existing.properties = properties or existing.properties
            await self.session.flush()
            return existing
        else:
            obj = PolicyModel(
                id=policy_id,
                name=name,
                display_name=display_name or name,
                policy_type=policy_type,
                mode=mode,
                description=description,
                rules=rules,
                parameters=parameters,
                tags=tags or {},
                properties=properties or {},
            )
            self.session.add(obj)
            await self.session.flush()
            await self._sync_to_neo4j(obj)
            return obj


# ===================================================================
# Tag Repository
# ===================================================================

class TagRepository(BaseRepository[TagModel]):
    model_class = TagModel

    async def create_or_update(
        self,
        name: str,
        count: int = 0,
        values: Optional[list] = None,
    ) -> TagModel:
        """Create or update a tag."""
        tag_id = f"tag:{name}"

        existing = await self.get_by_id(tag_id)
        if existing:
            existing.count = count
            existing.values = values
            await self.session.flush()
            return existing
        else:
            obj = TagModel(
                id=tag_id,
                name=name,
                count=count,
                values=values or [],
            )
            self.session.add(obj)
            await self.session.flush()
            return obj


# ===================================================================
# Deployment Repository
# ===================================================================

class DeploymentRepository(BaseRepository[DeploymentModel]):
    model_class = DeploymentModel

    async def create_or_update(
        self,
        name: str,
        resource_group: Optional[str] = None,
        location: Optional[str] = None,
        template: Optional[dict] = None,
        parameters: Optional[dict] = None,
        mode: str = "Incremental",
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> DeploymentModel:
        """Create or update a deployment."""
        dep_id = f"deployment:{name}"

        existing = await self.get_by_id(dep_id)
        if existing:
            existing.resource_group = resource_group or existing.resource_group
            existing.location = location or existing.location
            existing.template = template
            existing.parameters = parameters
            existing.mode = mode
            existing.tags = tags or existing.tags
            existing.properties = properties or existing.properties
            await self.session.flush()
            return existing
        else:
            obj = DeploymentModel(
                id=dep_id,
                name=name,
                resource_group=resource_group,
                location=location,
                template=template,
                parameters=parameters,
                mode=mode,
                tags=tags or {},
                properties=properties or {},
            )
            self.session.add(obj)
            await self.session.flush()
            await self._sync_to_neo4j(obj)
            return obj


# ===================================================================
# Relationship Repository
# ===================================================================

class RelationshipRepository:
    """
    Manages resource relationships (graph edges).
    
    Used for explicit relationship tracking beyond what FK constraints provide.
    """

    def __init__(self, session: AsyncSession, neo4j_sync=None):
        self.session = session
        self.neo4j_sync = neo4j_sync

    async def create_relationship(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ResourceRelationshipModel:
        """Create a relationship between two resources (upsert)."""
        rel_id = f"{source_id}->{relationship_type}->{target_id}"
        
        existing = await self.session.get(ResourceRelationshipModel, rel_id)
        if existing:
            existing.properties = properties or existing.properties
            await self.session.flush()
            return existing

        rel = ResourceRelationshipModel(
            id=rel_id,
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relationship_type=relationship_type,
            properties=properties or {},
        )
        self.session.add(rel)
        await self.session.flush()

        # Sync to Neo4j
        if self.neo4j_sync:
            await self.neo4j_sync.sync_relationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                properties=properties or {},
            )
        return rel

    async def get_relationships(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
    ) -> List[ResourceRelationshipModel]:
        """Query relationships with optional filters."""
        stmt = select(ResourceRelationshipModel)
        if source_id:
            stmt = stmt.where(ResourceRelationshipModel.source_id == source_id)
        if target_id:
            stmt = stmt.where(ResourceRelationshipModel.target_id == target_id)
        if relationship_type:
            stmt = stmt.where(
                ResourceRelationshipModel.relationship_type == relationship_type
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_relationship(self, rel_id: str) -> bool:
        """Delete a relationship by ID."""
        rel = await self.session.get(ResourceRelationshipModel, rel_id)
        if rel:
            await self.session.delete(rel)
            await self.session.flush()
            if self.neo4j_sync:
                await self.neo4j_sync.delete_relationship(rel_id)
            return True
        return False

    async def delete_relationships_for(self, resource_id: str) -> int:
        """Delete all relationships involving a resource."""
        stmt = sa_delete(ResourceRelationshipModel).where(
            (ResourceRelationshipModel.source_id == resource_id) |
            (ResourceRelationshipModel.target_id == resource_id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0


# ===================================================================
# Audit Event Repository
# ===================================================================

class AuditEventRepository(BaseRepository[AuditEventModel]):
    """
    Repository for audit event logging.
    
    Provides methods to:
    - Log CRUD events with full context
    - Query audit history for resources
    - Retrieve events by actor, time range, or correlation ID
    
    Usage::
    
        repo = AuditEventRepository(session)
        
        # Log a create event
        await repo.log_create(
            resource_id="/subscriptions/sub-123",
            resource_type="ITL.Core/subscriptions",
            resource_name="my-sub",
            new_state={"name": "my-sub", ...},
            actor_id="user-456",
        )
        
        # Query audit history
        events = await repo.get_events_for_resource("/subscriptions/sub-123")
    """

    model_class = AuditEventModel

    async def log_event(
        self,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        action: AuditAction,
        actor_id: str = None,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_display_name: str = None,
        previous_state: dict = None,
        new_state: dict = None,
        change_summary: str = None,
        correlation_id: str = None,
        request_id: str = None,
        source_ip: str = None,
        user_agent: str = None,
        extra_data: dict = None,
        track_state: bool = True,
    ) -> AuditEventModel:
        """
        Log an audit event.
        
        Args:
            resource_id: ARM-style resource ID
            resource_type: Resource type (e.g., ITL.Core/subscriptions)
            resource_name: Resource name
            action: CRUD action (AuditAction enum)
            actor_id: User or service principal ID
            actor_type: Type of actor (ActorType enum)
            actor_display_name: Display name of actor
            previous_state: State before change (for UPDATE/DELETE)
            new_state: State after change (for CREATE/UPDATE)
            change_summary: Human-readable summary
            correlation_id: Distributed tracing correlation ID
            request_id: Original request ID
            source_ip: Source IP address
            user_agent: User agent string
            extra_data: Additional metadata
            track_state: Whether to store state (configurable)
            
        Returns:
            Created AuditEventModel
        """
        event = AuditEventModel(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=action.value if isinstance(action, AuditAction) else action,
            actor_id=actor_id,
            actor_type=actor_type.value if isinstance(actor_type, ActorType) else actor_type,
            actor_display_name=actor_display_name,
            previous_state=previous_state if track_state else None,
            new_state=new_state if track_state else None,
            change_summary=change_summary,
            correlation_id=correlation_id,
            request_id=request_id,
            source_ip=source_ip,
            user_agent=user_agent,
            extra_data=extra_data or {},
        )
        self.session.add(event)
        await self.session.flush()
        logger.debug(
            "Audit event logged: %s %s on %s by %s",
            action, resource_type, resource_name, actor_id or "SYSTEM"
        )
        return event

    async def log_create(
        self,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        new_state: dict = None,
        **kwargs,
    ) -> AuditEventModel:
        """Log a CREATE event."""
        return await self.log_event(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.CREATE,
            new_state=new_state,
            change_summary=f"Created {resource_type} '{resource_name}'",
            **kwargs,
        )

    async def log_update(
        self,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        previous_state: dict = None,
        new_state: dict = None,
        **kwargs,
    ) -> AuditEventModel:
        """Log an UPDATE event."""
        return await self.log_event(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.UPDATE,
            previous_state=previous_state,
            new_state=new_state,
            change_summary=f"Updated {resource_type} '{resource_name}'",
            **kwargs,
        )

    async def log_delete(
        self,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        previous_state: dict = None,
        **kwargs,
    ) -> AuditEventModel:
        """Log a DELETE event."""
        return await self.log_event(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.DELETE,
            previous_state=previous_state,
            change_summary=f"Deleted {resource_type} '{resource_name}'",
            **kwargs,
        )

    async def get_events_for_resource(
        self,
        resource_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEventModel]:
        """Get audit events for a specific resource."""
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.resource_id == resource_id)
            .order_by(AuditEventModel.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_events_by_actor(
        self,
        actor_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEventModel]:
        """Get audit events by actor."""
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.actor_id == actor_id)
            .order_by(AuditEventModel.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_events_by_correlation_id(
        self,
        correlation_id: str,
    ) -> List[AuditEventModel]:
        """Get all events with a specific correlation ID."""
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.correlation_id == correlation_id)
            .order_by(AuditEventModel.timestamp.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_events_by_type_and_action(
        self,
        resource_type: str,
        action: AuditAction = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEventModel]:
        """Get events filtered by resource type and optionally action."""
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.resource_type == resource_type)
        )
        if action:
            action_value = action.value if isinstance(action, AuditAction) else action
            stmt = stmt.where(AuditEventModel.action == action_value)
        stmt = (
            stmt.order_by(AuditEventModel.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_events(
        self,
        resource_id: str = None,
        resource_type: str = None,
        action: AuditAction = None,
        actor_id: str = None,
    ) -> int:
        """Count events with optional filters."""
        stmt = select(func.count()).select_from(AuditEventModel)
        if resource_id:
            stmt = stmt.where(AuditEventModel.resource_id == resource_id)
        if resource_type:
            stmt = stmt.where(AuditEventModel.resource_type == resource_type)
        if action:
            action_value = action.value if isinstance(action, AuditAction) else action
            stmt = stmt.where(AuditEventModel.action == action_value)
        if actor_id:
            stmt = stmt.where(AuditEventModel.actor_id == actor_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
