"""
IMPLEMENTATION: Add Default Hook Behavior to ResourceProvider Base Class

This is how to modify ResourceProvider so ALL providers inherit default behaviors.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from itl_controlplane_sdk.core import (
    ResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ProviderContext,
)

logger = logging.getLogger(__name__)


# ============================================================================
# STEP 1: Add Default Implementations to ResourceProvider
# ============================================================================

class ResourceProviderWithDefaults:
    """
    Enhanced ResourceProvider with default hook implementations.
    
    Replace the current no-op hooks in provider.py with these.
    All providers automatically inherit this behavior.
    """
    
    # =========== BEFORE (no-op) ===========
    
    # async def on_creating(self, request, context):
    #     pass  # Does nothing
    
    # =========== AFTER (with defaults) ===========
    
    async def on_creating(self, request: ResourceRequest, context: ProviderContext) -> None:
        """
        Default pre-creation hook: Log the request.
        
        This is called before create_or_update_resource() for every provider.
        All providers inherit this automatically. Providers can override and
        call super() to keep the default behavior.
        
        Args:
            request: Resource creation request
            context: Execution context with tenant_id, user_id, request_id
            
        Raises:
            Can raise exceptions to abort creation
        """
        # Default: Log the operation
        logger.info(
            f"Creating {request.resource_type}: "
            f"name={request.spec.get('name')} "
            f"user={context.user_id} "
            f"request_id={context.request_id}"
        )
    
    async def on_created(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        """
        Default post-creation hook: Audit log + metrics.
        
        This is called after successful create_or_update_resource().
        Handles standard setup that applies to ALL resource types.
        
        Args:
            request: Original creation request
            response: Created resource response
            context: Execution context
        """
        try:
            # Default 1: Unified audit logging
            await self._audit_log(
                operation="ResourceCreated",
                resource_type=request.resource_type,
                resource_id=response.id,
                resource_name=response.name,
                user_id=context.user_id,
                request_id=context.request_id,
                timestamp=datetime.utcnow().isoformat(),
            )
            
            # Default 2: Metrics recording
            await self._record_metric(
                metric_name="resources_created_total",
                value=1,
                tags={
                    "resource_type": request.resource_type,
                    "tenant_id": context.tenant_id,
                    "user_id": context.user_id,
                },
            )
            
            # Default 3: Event publishing (for integrations)
            await self._publish_event(
                event_type="resource.created",
                resource_id=response.id,
                resource_type=request.resource_type,
                timestamp=datetime.utcnow().isoformat(),
            )
        
        except Exception as e:
            # Don't fail creation - just log
            logger.warning(f"Post-creation defaults failed: {e}")
    
    async def on_getting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Default pre-get hook: Log the retrieval.
        
        Called before get_resource() for every provider.
        """
        logger.debug(
            f"Getting {request.resource_type}: "
            f"id={request.resource_id} "
            f"user={context.user_id}"
        )
    
    async def on_updating(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Default pre-update hook: Log the update request.
        
        Called before create_or_update_resource() during updates.
        """
        logger.info(
            f"Updating {request.resource_type}: "
            f"name={request.spec.get('name')} "
            f"user={context.user_id}"
        )
    
    async def on_updated(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        """
        Default post-update hook: Audit log + metrics.
        
        Called after successful resource update.
        """
        try:
            await self._audit_log(
                operation="ResourceUpdated",
                resource_type=request.resource_type,
                resource_id=response.id,
                user_id=context.user_id,
                request_id=context.request_id,
            )
            
            await self._record_metric(
                metric_name="resources_updated_total",
                value=1,
                tags={"resource_type": request.resource_type},
            )
        
        except Exception as e:
            logger.warning(f"Post-update defaults failed: {e}")
    
    async def on_deleting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Default pre-delete hook: Log the deletion request.
        
        Called before delete_resource() for every provider.
        """
        logger.info(
            f"Deleting {request.resource_type}: "
            f"id={request.resource_id} "
            f"user={context.user_id}"
        )
    
    async def on_deleted(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Default post-delete hook: Audit log + cleanup.
        
        Called after successful resource deletion.
        """
        try:
            await self._audit_log(
                operation="ResourceDeleted",
                resource_id=request.resource_id,
                user_id=context.user_id,
                request_id=context.request_id,
            )
            
            await self._record_metric(
                metric_name="resources_deleted_total",
                value=1,
            )
        
        except Exception as e:
            logger.warning(f"Post-delete defaults failed: {e}")
    
    # =========== OPTIONAL HOOK HELPERS (Providers can override) ===========
    
    async def _audit_log(self, **details) -> None:
        """
        DEFAULT AUDIT LOGGING IMPLEMENTATION.
        
        This is called by default post-hooks to log operations.
        Providers can override to use different audit systems.
        
        Example override in your provider:
            async def _audit_log(self, **details):
                # Send to Elasticsearch instead
                await self.elasticsearch.index(index="audit", body=details)
        """
        logger.info(f"AUDIT_LOG: {details}")
        # Default: just log to Python logger
        # In real implementation: post to Elasticsearch, ClickHouse, etc.
    
    async def _record_metric(self, **metric) -> None:
        """
        DEFAULT METRICS RECORDING IMPLEMENTATION.
        
        This is called by default post-hooks to record metrics.
        Providers can override to use different metrics systems.
        
        Example override in your provider:
            async def _record_metric(self, **metric):
                # Send to Prometheus instead
                await self.prometheus.record(metric)
        """
        logger.debug(f"METRIC: {metric}")
        # Default: just log to Python logger
        # In real implementation: post to Prometheus, Datadog, etc.
    
    async def _publish_event(self, **event) -> None:
        """
        DEFAULT EVENT PUBLISHING IMPLEMENTATION.
        
        This is called by default post-hooks to publish events.
        Providers can override to use different event systems.
        
        Example override in your provider:
            async def _publish_event(self, **event):
                # Publish to Event Hub instead
                await self.event_hub.send(event)
        """
        logger.debug(f"EVENT: {event}")
        # Default: just log to Python logger
        # In real implementation: post to Event Hub, Kafka, SNS, etc.


# ============================================================================
# STEP 2: How Each Provider Uses the Defaults
# ============================================================================

class ExampleProvider1(ResourceProviderWithDefaults):
    """
    Provider 1: Use all defaults, no override needed.
    
    Gets automatic behavior:
    - Audit logging ✓
    - Metrics recording ✓
    - Event publishing ✓
    - Request logging ✓
    """
    
    async def create_or_update_resource(self, request, context):
        """Create resource."""
        # on_creating called automatically before this
        # on_created called automatically after this
        
        response = ResourceResponse(
            id=f"/resources/{request.spec.get('name')}",
            name=request.spec.get('name'),
            type="Custom/Resource",
        )
        return response
    
    # No hook overrides needed - gets all defaults


class ExampleProvider2(ResourceProviderWithDefaults):
    """
    Provider 2: Override to add custom behavior AND keep defaults.
    
    Gets automatic behavior:
    - Audit logging ✓ (from parent)
    - Metrics recording ✓ (from parent)
    - Event publishing ✓ (from parent)
    
    Plus custom VM-specific logic.
    """
    
    async def create_or_update_resource(self, request, context):
        response = ResourceResponse(id="vm-123", name="vm", type="VM")
        return response
    
    async def on_created(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        """
        Override: Add VM-specific setup PLUS keep default behavior.
        
        Step 1: Call parent to get defaults (audit, metrics, events)
        Step 2: Add VM-specific logic
        """
        # Step 1: Run all defaults from parent class
        await super().on_created(request, response, context)
        
        # Step 2: Add custom VM-specific behavior
        logger.info(f"[VM] Setting up VM: {response.id}")
        try:
            await self._setup_vm_networking(response.id)
            await self._setup_vm_monitoring(response.id)
        except Exception as e:
            logger.warning(f"[VM] Custom setup failed: {e}")
    
    async def _setup_vm_networking(self, vm_id: str) -> None:
        logger.debug(f"Setting up networking for {vm_id}")
    
    async def _setup_vm_monitoring(self, vm_id: str) -> None:
        logger.debug(f"Setting up monitoring for {vm_id}")


class ExampleProvider3(ResourceProviderWithDefaults):
    """
    Provider 3: Customize the audit/metrics/events systems.
    
    Gets default hooks, but uses custom implementations for:
    - Audit logging → Elasticsearch
    - Metrics recording → Prometheus
    - Event publishing → Event Hub
    """
    
    def __init__(self):
        self.elasticsearch = None  # Custom audit system
        self.prometheus = None  # Custom metrics system
        self.event_hub = None  # Custom event system
    
    async def create_or_update_resource(self, request, context):
        response = ResourceResponse(id="rg-123", name="rg", type="ResourceGroup")
        return response
    
    # Override the default helper methods to use custom systems
    
    async def _audit_log(self, **details) -> None:
        """
        Override: Use Elasticsearch for audit instead of logger.
        
        Parent class calls this from on_created, on_updated, on_deleted.
        By overriding it, we change WHERE the audit goes.
        """
        logger.debug(f"Posting audit to Elasticsearch: {details}")
        # In real implementation:
        # await self.elasticsearch.index(index="audit", body=details)
    
    async def _record_metric(self, **metric) -> None:
        """
        Override: Use Prometheus for metrics instead of logger.
        """
        logger.debug(f"Posting metric to Prometheus: {metric}")
        # In real implementation:
        # await self.prometheus.record(metric)
    
    async def _publish_event(self, **event) -> None:
        """
        Override: Use Event Hub for events instead of logger.
        """
        logger.debug(f"Publishing event to Event Hub: {event}")
        # In real implementation:
        # await self.event_hub.send(event)


# ============================================================================
# STEP 3: Changes Needed in Provider Base Class
# ============================================================================

CHANGES_TO_PROVIDER_PY = """
In src/itl_controlplane_sdk/providers/base/provider.py:

BEFORE (current):
    async def on_creating(self, request, context):
        '''Override to add custom validation.'''
        pass  # No-op

AFTER (with defaults):
    async def on_creating(self, request, context):
        '''Default pre-creation hook: Log the request.
        
        Providers inherit this automatically. Can override and call super()
        to keep the default.
        '''
        logger.info(f"Creating {request.resource_type}:...")

    async def on_created(self, request, response, context):
        '''Default post-creation hook: Audit + metrics.
        
        Automatically logs, records metrics, publishes events.
        Providers can override and call super() to keep defaults.
        '''
        try:
            await self._audit_log(...)
            await self._record_metric(...)
            await self._publish_event(...)
        except Exception as e:
            logger.warning(f"Defaults failed: {e}")

And add:
    async def _audit_log(self, **details) -> None:
        '''Default audit logging. Override in subclass.'''
        logger.info(f"AUDIT_LOG: {details}")
    
    async def _record_metric(self, **metric) -> None:
        '''Default metrics recording. Override in subclass.'''
        logger.debug(f"METRIC: {metric}")
    
    async def _publish_event(self, **event) -> None:
        '''Default event publishing. Override in subclass.'''
        logger.debug(f"EVENT: {event}")

Do the same for all 7 hooks:
    - on_creating: Log (done)
    - on_created: Audit + metrics + events (done)
    - on_getting: Log
    - on_updating: Log
    - on_updated: Audit + metrics
    - on_deleting: Log
    - on_deleted: Audit + metrics
"""

SUMMARY = """
Three Ways to Use Default Hooks:

1. USE ALL DEFAULTS (Easiest)
   class MyProvider(ResourceProvider):
       # That's it! Get audit, metrics, events automatically
       
   What you get:
   - All operations logged
   - All operations audited
   - All operations recorded as metrics
   - All operations published as events

2. OVERRIDE SPECIFIC HOOKS (Keep defaults, add custom)
   class MyProvider(ResourceProvider):
       async def on_created(self, request, response, context):
           await super().on_created(...)  # Keep defaults
           # Add custom logic here
   
   What you get:
   - All defaults (audit, metrics, events)
   - PLUS your custom behavior

3. CUSTOMIZE SYSTEMS (Change where data goes)
   class MyProvider(ResourceProvider):
       async def _audit_log(self, **details):
           await elasticsearch.log(details)  # Use ES instead of logger
   
   What you get:
   - All defaults with your systems (ES, Prometheus, etc.)
   - No need to override hooks
"""
