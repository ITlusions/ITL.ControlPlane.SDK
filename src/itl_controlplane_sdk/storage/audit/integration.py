"""
Audit Integration for Repository Layer.

Provides automatic audit logging for CRUD operations through:
1. AuditedRepository wrapper — wraps any repo to add audit logging
2. audit_operation decorator — manual decoration of methods
3. AuditMiddleware — FastAPI middleware for request context

Usage::

    from itl_controlplane_sdk.storage.audit import (
        AuditedRepository,
        SQLAuditEventAdapter,
        AuditEventPublisher,
    )
    
    # Wrap repository with audit logging
    engine = SQLAlchemyStorageEngine()
    adapter = SQLAuditEventAdapter(engine.session_factory)
    publisher = AuditEventPublisher(adapter)
    
    async with engine.session() as session:
        base_repo = engine.subscriptions(session)
        repo = AuditedRepository(base_repo, publisher, "ITL.Core/subscriptions")
        
        # All CRUD operations automatically logged
        sub = await repo.create_or_update(name="prod", display_name="Production")
"""

import functools
import logging
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, TYPE_CHECKING

from .publisher import AuditEventPublisher
from .models import AuditAction

if TYPE_CHECKING:
    from ..repositories import BaseRepository

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AuditedRepository(Generic[T]):
    """
    Wrapper that adds automatic audit logging to any repository.
    
    Intercepts create_or_update, delete_by_id, delete_by_name calls
    and logs appropriate audit events.
    
    Args:
        repository: The underlying repository to wrap
        publisher: AuditEventPublisher for logging events
        resource_type: ARM resource type (e.g., "ITL.Core/subscriptions")
        track_state: Whether to capture before/after state (default: True)
    
    Example::
    
        repo = SubscriptionRepository(session)
        audited = AuditedRepository(repo, publisher, "ITL.Core/subscriptions")
        
        # Automatically logs CREATE audit event
        sub = await audited.create_or_update(name="prod", display_name="Production")
    """
    
    def __init__(
        self,
        repository: "BaseRepository[T]",
        publisher: AuditEventPublisher,
        resource_type: str,
        track_state: bool = True,
    ):
        self._repo = repository
        self._publisher = publisher
        self._resource_type = resource_type
        self._track_state = track_state
    
    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to underlying repository."""
        return getattr(self._repo, name)
    
    async def create_or_update(self, **kwargs) -> T:
        """
        Create or update with automatic audit logging.
        
        Detects whether this is a CREATE or UPDATE by checking
        if the resource already exists.
        """
        # Determine resource name from kwargs
        resource_name = kwargs.get("name", "unknown")
        
        # Check if exists (to determine CREATE vs UPDATE)
        existing = await self._repo.get_by_name(resource_name)
        is_update = existing is not None
        
        # Capture previous state for updates
        previous_state = None
        if is_update and self._track_state and hasattr(existing, "to_dict"):
            try:
                previous_state = existing.to_dict()
            except Exception:
                pass
        
        # Execute the actual operation
        result = await self._repo.create_or_update(**kwargs)
        
        # Capture new state
        new_state = None
        if self._track_state and hasattr(result, "to_dict"):
            try:
                new_state = result.to_dict()
            except Exception:
                pass
        
        # Build resource ID
        resource_id = getattr(result, "id", None) or f"/{self._resource_type}/{resource_name}"
        
        # Log audit event
        try:
            if is_update:
                await self._publisher.log_update(
                    resource_id=resource_id,
                    resource_type=self._resource_type,
                    resource_name=resource_name,
                    previous_state=previous_state,
                    new_state=new_state,
                )
            else:
                await self._publisher.log_create(
                    resource_id=resource_id,
                    resource_type=self._resource_type,
                    resource_name=resource_name,
                    new_state=new_state,
                )
        except Exception as e:
            # Don't fail the operation if audit logging fails
            logger.warning("Audit logging failed for %s: %s", resource_id, e)
        
        return result
    
    async def delete_by_id(self, resource_id: str) -> bool:
        """Delete by ID with automatic audit logging."""
        # Get resource before deletion to capture state
        previous_state = None
        resource_name = resource_id.split("/")[-1] if "/" in resource_id else resource_id
        
        if self._track_state:
            existing = await self._repo.get_by_id(resource_id)
            if existing and hasattr(existing, "to_dict"):
                try:
                    previous_state = existing.to_dict()
                    resource_name = getattr(existing, "name", resource_name)
                except Exception:
                    pass
        
        # Execute deletion
        deleted = await self._repo.delete_by_id(resource_id)
        
        # Log audit event
        if deleted:
            try:
                await self._publisher.log_delete(
                    resource_id=resource_id,
                    resource_type=self._resource_type,
                    resource_name=resource_name,
                    previous_state=previous_state,
                )
            except Exception as e:
                logger.warning("Audit logging failed for delete %s: %s", resource_id, e)
        
        return deleted
    
    async def delete_by_name(self, name: str) -> bool:
        """Delete by name with automatic audit logging."""
        # Get resource before deletion
        previous_state = None
        resource_id = None
        
        if self._track_state:
            existing = await self._repo.get_by_name(name)
            if existing:
                resource_id = getattr(existing, "id", None)
                if hasattr(existing, "to_dict"):
                    try:
                        previous_state = existing.to_dict()
                    except Exception:
                        pass
        
        # Execute deletion
        deleted = await self._repo.delete_by_name(name)
        
        # Log audit event
        if deleted:
            resource_id = resource_id or f"/{self._resource_type}/{name}"
            try:
                await self._publisher.log_delete(
                    resource_id=resource_id,
                    resource_type=self._resource_type,
                    resource_name=name,
                    previous_state=previous_state,
                )
            except Exception as e:
                logger.warning("Audit logging failed for delete %s: %s", name, e)
        
        return deleted
    
    async def get_by_id(self, resource_id: str, log_read: bool = False) -> Optional[T]:
        """
        Get by ID, optionally logging READ audit events.
        
        Read logging is disabled by default to avoid noise,
        but can be enabled for sensitive resources.
        """
        result = await self._repo.get_by_id(resource_id)
        
        if log_read and result:
            resource_name = getattr(result, "name", resource_id.split("/")[-1])
            try:
                await self._publisher.log_read(
                    resource_id=resource_id,
                    resource_type=self._resource_type,
                    resource_name=resource_name,
                )
            except Exception as e:
                logger.warning("Audit logging failed for read %s: %s", resource_id, e)
        
        return result
    
    async def get_by_name(self, name: str, log_read: bool = False) -> Optional[T]:
        """Get by name, optionally logging READ audit events."""
        result = await self._repo.get_by_name(name)
        
        if log_read and result:
            resource_id = getattr(result, "id", f"/{self._resource_type}/{name}")
            try:
                await self._publisher.log_read(
                    resource_id=resource_id,
                    resource_type=self._resource_type,
                    resource_name=name,
                )
            except Exception as e:
                logger.warning("Audit logging failed for read %s: %s", name, e)
        
        return result


def audit_operation(
    action: AuditAction,
    resource_type: str,
    resource_id_param: str = "resource_id",
    resource_name_param: str = "name",
):
    """
    Decorator for auditing arbitrary operations.
    
    Use this for custom actions that don't fit the CRUD pattern.
    
    Args:
        action: The audit action type
        resource_type: ARM resource type
        resource_id_param: Parameter name containing resource ID
        resource_name_param: Parameter name containing resource name
    
    Example::
    
        @audit_operation(AuditAction.EXECUTE, "ITL.Compute/virtualMachines")
        async def start_vm(self, resource_id: str, name: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Extract resource identifiers
            resource_id = kwargs.get(resource_id_param, "")
            resource_name = kwargs.get(resource_name_param, "")
            
            # Get publisher from self if available
            publisher = getattr(self, "_publisher", None) or getattr(self, "publisher", None)
            
            # Execute the operation
            result = await func(self, *args, **kwargs)
            
            # Log audit event
            if publisher:
                try:
                    await publisher.log_action(
                        action=action,
                        resource_id=resource_id,
                        resource_type=resource_type,
                        resource_name=resource_name,
                        extra_data={"result": "success"},
                    )
                except Exception as e:
                    logger.warning("Audit logging failed: %s", e)
            
            return result
        return wrapper
    return decorator


class AuditedStorageEngine:
    """
    Factory for creating audited repositories from a storage engine.
    
    Example::
    
        from itl_controlplane_sdk.storage.engine import SQLAlchemyStorageEngine
        from itl_controlplane_sdk.storage.audit import (
            AuditedStorageEngine,
            SQLAuditEventAdapter,
            AuditEventPublisher,
        )
        
        engine = SQLAlchemyStorageEngine()
        await engine.initialize()
        
        adapter = SQLAuditEventAdapter(engine.session_factory)
        await adapter.initialize()
        publisher = AuditEventPublisher(adapter)
        
        audited_engine = AuditedStorageEngine(engine, publisher)
        
        async with engine.session() as session:
            repo = audited_engine.subscriptions(session)  # Returns AuditedRepository
            await repo.create_or_update(name="prod", display_name="Production")
    """
    
    # Mapping of repository methods to ARM resource types
    RESOURCE_TYPES = {
        "tenants": "ITL.Core/tenants",
        "management_groups": "ITL.Core/managementGroups",
        "subscriptions": "ITL.Core/subscriptions",
        "resource_groups": "ITL.Core/resourceGroups",
        "locations": "ITL.Core/locations",
        "extended_locations": "ITL.Core/extendedLocations",
        "policies": "ITL.Core/policies",
        "tags": "ITL.Core/tags",
        "deployments": "ITL.Core/deployments",
    }
    
    def __init__(self, engine, publisher: AuditEventPublisher, track_state: bool = True):
        self._engine = engine
        self._publisher = publisher
        self._track_state = track_state
    
    def _wrap(self, repo, resource_type: str) -> AuditedRepository:
        """Wrap a repository with audit logging."""
        return AuditedRepository(
            repository=repo,
            publisher=self._publisher,
            resource_type=resource_type,
            track_state=self._track_state,
        )
    
    def tenants(self, session):
        return self._wrap(self._engine.tenants(session), self.RESOURCE_TYPES["tenants"])
    
    def management_groups(self, session):
        return self._wrap(self._engine.management_groups(session), self.RESOURCE_TYPES["management_groups"])
    
    def subscriptions(self, session):
        return self._wrap(self._engine.subscriptions(session), self.RESOURCE_TYPES["subscriptions"])
    
    def resource_groups(self, session):
        return self._wrap(self._engine.resource_groups(session), self.RESOURCE_TYPES["resource_groups"])
    
    def locations(self, session):
        return self._wrap(self._engine.locations(session), self.RESOURCE_TYPES["locations"])
    
    def extended_locations(self, session):
        return self._wrap(self._engine.extended_locations(session), self.RESOURCE_TYPES["extended_locations"])
    
    def policies(self, session):
        return self._wrap(self._engine.policies(session), self.RESOURCE_TYPES["policies"])
    
    def tags(self, session):
        return self._wrap(self._engine.tags(session), self.RESOURCE_TYPES["tags"])
    
    def deployments(self, session):
        return self._wrap(self._engine.deployments(session), self.RESOURCE_TYPES["deployments"])
    
    # Pass through non-audited methods
    def audit_events(self, session):
        return self._engine.audit_events(session)
    
    def relationships(self, session):
        return self._engine.relationships(session)
    
    # Proxy engine methods
    def __getattr__(self, name: str):
        return getattr(self._engine, name)
