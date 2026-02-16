"""
How to Define Default Hook Behavior in SDK for All Providers

Two approaches:

1. BUILT-IN DEFAULTS IN ResourceProvider BASE CLASS
   - All providers inherit without any work
   - Use super() to call parent hooks
   - Simple and clean

2. OPTIONAL HOOK MIXINS
   - Composable behaviors you can mix and match
   - Providers choose which behaviors to include
   - Maximum flexibility
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from itl_controlplane_sdk import (
    ResourceProvider,
    ResourceRequest,
    ResourceResponse,
    ProviderContext,
)

logger = logging.getLogger(__name__)


# ============================================================================
# APPROACH 1: BUILT-IN DEFAULTS IN ResourceProvider BASE CLASS
# ============================================================================
# Define default behavior right in ResourceProvider so all providers inherit it

class ResourceProviderWithDefaults(ResourceProvider):
    """
    Base ResourceProvider with built-in default hook implementations.
    
    All providers that inherit from this get:
    - Automatic audit logging on all operations
    - Standard error handling
    - Request tracing via request_id
    - Operation timing/metrics
    
    Providers can override hooks to add custom logic and call super() 
    to keep the defaults.
    """
    
    # =========== DEFAULT HOOKS WITH ACTUAL BEHAVIOR ===========
    
    async def on_creating(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Default pre-create behavior: Log the request.
        
        All providers inherit this. Can override and call super() to keep logging.
        """
        logger.info(
            f"[DEFAULT] Creating {request.resource_type}: "
            f"name={request.spec.get('name')} "
            f"request_id={context.request_id} "
            f"user={context.user_id}"
        )
    
    async def on_created(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        """
        Default post-create behavior: Audit log + metrics.
        
        Called after successful creation. Logs to audit system and records metrics.
        Cannot abort - exceptions are logged.
        """
        try:
            # Default behavior 1: Audit logging
            await self._default_audit_log(
                operation="ResourceCreated",
                resource_type=request.resource_type,
                resource_id=response.id,
                resource_name=response.name,
                user_id=context.user_id,
                request_id=context.request_id,
            )
            
            # Default behavior 2: Record metrics
            await self._default_record_metric(
                metric_name="resources_created",
                value=1,
                tags={
                    "resource_type": request.resource_type,
                    "tenant_id": context.tenant_id,
                },
            )
            
            logger.debug(f"[DEFAULT] Post-create complete: {response.id}")
        
        except Exception as e:
            # Log but don't raise - resource already created
            logger.warning(f"[DEFAULT] Post-create hook failed: {e}")
    
    async def on_getting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Default pre-get behavior: Log retrieval request.
        """
        logger.info(
            f"[DEFAULT] Getting {request.resource_type}: "
            f"id={request.resource_id} "
            f"request_id={context.request_id}"
        )
    
    async def on_updating(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Default pre-update behavior: Log update request.
        """
        logger.info(
            f"[DEFAULT] Updating {request.resource_type}: "
            f"id={request.resource_id} "
            f"request_id={context.request_id}"
        )
    
    async def on_updated(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        """
        Default post-update behavior: Audit log + metrics.
        """
        try:
            await self._default_audit_log(
                operation="ResourceUpdated",
                resource_type=request.resource_type,
                resource_id=response.id,
                user_id=context.user_id,
                request_id=context.request_id,
            )
            
            await self._default_record_metric(
                metric_name="resources_updated",
                value=1,
                tags={"resource_type": request.resource_type},
            )
        
        except Exception as e:
            logger.warning(f"[DEFAULT] Post-update hook failed: {e}")
    
    async def on_deleting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Default pre-delete behavior: Log deletion request.
        """
        logger.info(
            f"[DEFAULT] Deleting {request.resource_type}: "
            f"id={request.resource_id} "
            f"request_id={context.request_id}"
        )
    
    async def on_deleted(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Default post-delete behavior: Audit log + cleanup.
        """
        try:
            await self._default_audit_log(
                operation="ResourceDeleted",
                resource_id=request.resource_id,
                user_id=context.user_id,
                request_id=context.request_id,
            )
            
            await self._default_record_metric(
                metric_name="resources_deleted",
                value=1,
            )
        
        except Exception as e:
            logger.warning(f"[DEFAULT] Post-delete hook failed: {e}")
    
    # =========== DEFAULT HELPER METHODS ===========
    # Subclasses can override these or use them as-is
    
    async def _default_audit_log(self, **details) -> None:
        """
        Default audit logging implementation.
        
        Override in subclass to change audit system:
            async def _default_audit_log(self, **details):
                await self.elasticsearch.log(details)
        """
        logger.info(f"AUDIT: {details}")
        # In reality: post to Elasticsearch, ClickHouse, etc.
    
    async def _default_record_metric(self, **metric) -> None:
        """
        Default metrics recording implementation.
        
        Override in subclass to change metrics system:
            async def _default_record_metric(self, **metric):
                await self.prometheus.record(metric)
        """
        logger.debug(f"METRIC: {metric}")
        # In reality: post to Prometheus, Datadog, etc.


# ============================================================================
# USING APPROACH 1: Override and Call super()
# ============================================================================

class CustomVMProvider(ResourceProviderWithDefaults):
    """
    VM Provider that keeps defaults AND adds custom behavior.
    
    All default behaviors (audit, metrics) run automatically.
    We add VM-specific setup.
    """
    
    async def on_created(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        """
        VM-specific post-create setup.
        
        Calls super() to keep default behaviors (audit, metrics),
        then adds VM-specific logic.
        """
        # 1. Call defaults first (audit, metrics)
        await super().on_created(request, response, context)
        
        # 2. Add VM-specific setup
        logger.info(f"[VM] Setting up newly created VM: {response.id}")
        
        try:
            # VM-specific side effects
            await self._setup_vm_networking(response.id)
            await self._configure_vm_backups(response.id)
            await self._register_vm_monitoring(response.id)
        
        except Exception as e:
            logger.warning(f"[VM] Setup failed: {e}")
    
    async def on_deleting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        VM-specific pre-delete validation.
        
        Call defaults first, then add VM-specific checks.
        """
        # 1. Call defaults first (logging)
        await super().on_deleting(request, context)
        
        # 2. Add VM-specific validation
        logger.info(f"[VM] Checking VM dependencies: {request.resource_id}")
        
        is_running = await self._is_vm_running(request.resource_id)
        if is_running:
            raise ValueError(
                f"Cannot delete running VM: {request.resource_id}. "
                f"Stop it first."
            )
    
    # VM-specific helper methods
    async def _setup_vm_networking(self, vm_id: str) -> None:
        logger.debug(f"Networking setup for {vm_id}")
    
    async def _configure_vm_backups(self, vm_id: str) -> None:
        logger.debug(f"Backup config for {vm_id}")
    
    async def _register_vm_monitoring(self, vm_id: str) -> None:
        logger.debug(f"Monitoring register for {vm_id}")
    
    async def _is_vm_running(self, vm_id: str) -> bool:
        return False  # Stub


# ============================================================================
# APPROACH 2: OPTIONAL HOOK MIXINS
# ============================================================================
# For maximum flexibility, create reusable mixin classes

class AuditLoggingHook:
    """
    Mixin: Automatic audit logging for all operations.
    
    Mix with ResourceProvider to add audit behaviors.
    """
    
    async def on_created(self, request, response, context):
        """Log resource creation."""
        logger.info(
            f"[AUDIT] Created: {response.type} "
            f"{response.name} ({response.id})"
        )
        # Chain to parent if it exists
        if hasattr(super(), 'on_created'):
            await super().on_created(request, response, context)
    
    async def on_updated(self, request, response, context):
        """Log resource update."""
        logger.info(
            f"[AUDIT] Updated: {response.type} "
            f"{response.name} ({response.id})"
        )
        if hasattr(super(), 'on_updated'):
            await super().on_updated(request, response, context)
    
    async def on_deleted(self, request, context):
        """Log resource deletion."""
        logger.info(f"[AUDIT] Deleted: {request.resource_id}")
        if hasattr(super(), 'on_deleted'):
            await super().on_deleted(request, context)


class MetricsRecordingHook:
    """
    Mixin: Automatic metrics recording for all operations.
    
    Mix with ResourceProvider to add metrics tracking.
    """
    
    async def on_created(self, request, response, context):
        """Record creation metric."""
        logger.debug(f"METRIC: resources_created +1")
        if hasattr(super(), 'on_created'):
            await super().on_created(request, response, context)
    
    async def on_deleted(self, request, context):
        """Record deletion metric."""
        logger.debug(f"METRIC: resources_deleted +1")
        if hasattr(super(), 'on_deleted'):
            await super().on_deleted(request, context)


class RateLimitingHook:
    """
    Mixin: Automatic rate limiting on operations.
    """
    
    async def on_creating(self, request, context):
        """Check rate limits before creation."""
        daily_limit = 50
        daily_count = await self._get_daily_creates(context.user_id)
        
        if daily_count >= daily_limit:
            raise ValueError(
                f"Rate limit exceeded: {daily_count}/{daily_limit} "
                f"creates today"
            )
        
        if hasattr(super(), 'on_creating'):
            await super().on_creating(request, context)
    
    async def _get_daily_creates(self, user_id: str) -> int:
        return 0  # Stub


class QuotaEnforcementHook:
    """
    Mixin: Automatic quota enforcement on operations.
    """
    
    async def on_creating(self, request, context):
        """Check quota before creation."""
        quota = 100
        count = await self._get_resource_count(
            context.subscription_id,
            request.resource_type
        )
        
        if count >= quota:
            raise ValueError(
                f"Quota exceeded: {count}/{quota} {request.resource_type}"
            )
        
        if hasattr(super(), 'on_creating'):
            await super().on_creating(request, context)
    
    async def _get_resource_count(self, sub_id: str, res_type: str) -> int:
        return 0  # Stub


class DependencyCheckHook:
    """
    Mixin: Automatic dependency checking on deletion.
    """
    
    async def on_deleting(self, request, context):
        """Check for dependencies before deletion."""
        children = await self._get_child_resources(request.resource_id)
        
        if children:
            raise ValueError(
                f"Cannot delete: has {len(children)} child resources"
            )
        
        if hasattr(super(), 'on_deleting'):
            await super().on_deleting(request, context)
    
    async def _get_child_resources(self, resource_id: str) -> list:
        return []  # Stub


# ============================================================================
# USING APPROACH 2: Mix and Match Behaviors
# ============================================================================

class StorageProviderWithMixins(
    AuditLoggingHook,
    MetricsRecordingHook,
    QuotaEnforcementHook,
    DependencyCheckHook,
    ResourceProvider,  # Base class LAST
):
    """
    Storage Provider that mixes in multiple default behaviors.
    
    Gets:
    - Audit logging (from AuditLoggingHook)
    - Metrics recording (from MetricsRecordingHook)
    - Quota enforcement (from QuotaEnforcementHook)
    - Dependency checking (from DependencyCheckHook)
    
    Can still override specific hooks for custom logic.
    """
    
    async def on_created(self, request, response, context):
        """Storage-specific setup (mixin chain handles audit + metrics)."""
        # Mixin chain handles: audit, metrics, etc.
        await super().on_created(request, response, context)
        
        # Add storage-specific logic
        logger.info(f"[STORAGE] Configuring storage account: {response.id}")
        # await configure_storage_replication(response.id)


# ============================================================================
# COMPARISON
# ============================================================================

COMPARISON = """
APPROACH 1: Built-in Defaults (Recommended)
=============================================
Pattern:
    class BaseProvider(ResourceProvider):
        async def on_created(self, ...):
            # Default audit + metrics
            # All providers inherit automatically

Usage:
    class MyProvider(BaseProvider):
        async def on_created(self, ...):
            await super().on_created(...)  # Keep defaults
            # Add custom logic

Pros:
    + Simple - automatic for all providers
    + Clean inheritance
    + Easy to understand
    + Standard behavior guaranteed

Cons:
    - Less flexible
    - All providers get all defaults


APPROACH 2: Optional Mixins (Maximum Flexibility)
=================================================
Pattern:
    class AuditHook:
        async def on_created(self, ...):
            # Audit logging
    
    class MyProvider(AuditHook, ResourceProvider):
        # Gets audit from mixin

Usage:
    class MyProvider(AuditHook, MetricsHook, ResourceProvider):
        pass  # Gets audit + metrics from mixins

Pros:
    + Choose which behaviors to include
    + Composable and flexible
    + Mix and match as needed

Cons:
    - More complex
    - MRO (Method Resolution Order) must be correct
    - Can be confusing with many mixins


BEST PRACTICE: Combine Both
===========================
Use Approach 1 (built-in defaults) as the foundation.
Use Approach 2 (optional mixins) for specialized behaviors.

    class BaseProvider(ResourceProvider):
        # Required: audit logging, metrics, request logging
        async def on_created(self, ...):
            await _default_audit_log(...)
            await _default_record_metric(...)

    class SpecializedProvider(RateLimitingHook, BaseProvider):
        # Gets defaults from BaseProvider
        # Gets rate limiting from mixin
"""
