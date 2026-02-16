"""
PATCH: Exact Code Changes to Add Default Hook Behavior to ResourceProvider

This shows exactly what to change in provider.py to add defaults.
"""

# ============================================================================
# CHANGE 1: Add Imports at Top (if not already present)
# ============================================================================

IMPORTS_TO_ADD = """
Add to imports section:

import logging
from datetime import datetime

logger = logging.getLogger(__name__)
"""

# ============================================================================
# CHANGE 2: Replace on_creating Hook (around line 274)
# ============================================================================

REPLACE_ON_CREATING = """
BEFORE:
    async def on_creating(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Pre-creation hook called before create_or_update_resource.
        
        Override to add custom validation, policy checks, or prerequisites.
        Can raise exceptions to abort creation.
        
        Default implementation does nothing (no-op).
        \"\"\"
        pass

AFTER:
    async def on_creating(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Pre-creation hook called before create_or_update_resource.
        
        Default: Logs the creation request with tenant, user, and request ID.
        
        Override to add custom validation or call super() to keep logging.
        Can raise exceptions to abort creation.
        
        Args:
            request: Resource creation request
            context: Execution context with tenant_id, user_id, request_id
        \"\"\"
        logger.info(
            f"Creating {request.resource_type}: "
            f"name={request.spec.get('name')} "
            f"user={context.user_id} "
            f"request_id={context.request_id}"
        )
"""

# ============================================================================
# CHANGE 3: Replace on_created Hook (around line 294)
# ============================================================================

REPLACE_ON_CREATED = """
BEFORE:
    async def on_created(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Post-creation hook called after successful create_or_update_resource.
        
        Override to add audit logging, notifications, or side effects.
        Exceptions are logged but do NOT abort (operation succeeded).
        
        Default implementation does nothing (no-op).
        \"\"\"
        pass

AFTER:
    async def on_created(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Post-creation hook called after successful create_or_update_resource.
        
        Default: Calls _audit_log, _record_metric, and _publish_event.
        Exceptions are logged but do NOT abort (operation succeeded).
        
        Override to add custom behavior and call super() to keep defaults.
        
        Args:
            request: Original creation request
            response: Created resource response
            context: Execution context
        \"\"\"
        try:
            # Default 1: Audit log
            await self._audit_log(
                operation="ResourceCreated",
                resource_type=request.resource_type,
                resource_id=response.id,
                resource_name=response.name,
                user_id=context.user_id,
                request_id=context.request_id,
                timestamp=datetime.utcnow().isoformat(),
            )
            
            # Default 2: Record metric
            await self._record_metric(
                metric_name="resources_created_total",
                value=1,
                tags={
                    "resource_type": request.resource_type,
                    "tenant_id": context.tenant_id,
                },
            )
            
            # Default 3: Publish event
            await self._publish_event(
                event_type="resource.created",
                resource_id=response.id,
                resource_type=request.resource_type,
                timestamp=datetime.utcnow().isoformat(),
            )
        
        except Exception as e:
            # Log but don't raise - resource already created
            logger.warning(f"Post-creation defaults failed: {e}")
"""

# ============================================================================
# CHANGE 4: Replace on_getting Hook (around line 314)
# ============================================================================

REPLACE_ON_GETTING = """
BEFORE:
    async def on_getting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Pre-get hook called before get_resource.
        
        Override to add access control or logging.
        Can raise exceptions to deny access.
        
        Default implementation does nothing (no-op).
        \"\"\"
        pass

AFTER:
    async def on_getting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Pre-get hook called before get_resource.
        
        Default: Logs the retrieval request.
        
        Override to add access control and call super() to keep logging.
        Can raise exceptions to deny access.
        \"\"\"
        logger.debug(
            f"Getting {request.resource_type}: "
            f"id={request.resource_id} "
            f"user={context.user_id}"
        )
"""

# ============================================================================
# CHANGE 5: Replace on_updating Hook (around line 334)
# ============================================================================

REPLACE_ON_UPDATING = """
BEFORE:
    async def on_updating(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Pre-update hook called before create_or_update_resource (on updates).
        
        Override to add validation, immutability checks, or version control.
        Can raise exceptions to abort update.
        
        Default implementation does nothing (no-op).
        \"\"\"
        pass

AFTER:
    async def on_updating(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Pre-update hook called before create_or_update_resource (on updates).
        
        Default: Logs the update request.
        
        Override to add validation and call super() to keep logging.
        Can raise exceptions to abort update.
        \"\"\"
        logger.info(
            f"Updating {request.resource_type}: "
            f"name={request.spec.get('name')} "
            f"user={context.user_id}"
        )
"""

# ============================================================================
# CHANGE 6: Replace on_updated Hook (around line 354)
# ============================================================================

REPLACE_ON_UPDATED = """
BEFORE:
    async def on_updated(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Post-update hook called after successful resource update.
        
        Override to add audit logging, cache invalidation, or notifications.
        Exceptions are logged but do NOT abort (operation succeeded).
        
        Default implementation does nothing (no-op).
        \"\"\"
        pass

AFTER:
    async def on_updated(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Post-update hook called after successful resource update.
        
        Default: Calls _audit_log and _record_metric.
        Exceptions are logged but do NOT abort (operation succeeded).
        
        Override to add custom behavior and call super() to keep defaults.
        \"\"\"
        try:
            await self._audit_log(
                operation="ResourceUpdated",
                resource_type=request.resource_type,
                resource_id=response.id,
                user_id=context.user_id,
                request_id=context.request_id,
                timestamp=datetime.utcnow().isoformat(),
            )
            
            await self._record_metric(
                metric_name="resources_updated_total",
                value=1,
                tags={"resource_type": request.resource_type},
            )
        
        except Exception as e:
            logger.warning(f"Post-update defaults failed: {e}")
"""

# ============================================================================
# CHANGE 7: Replace on_deleting Hook (around line 374)
# ============================================================================

REPLACE_ON_DELETING = """
BEFORE:
    async def on_deleting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Pre-deletion hook called before delete_resource.
        
        Override to add dependency checks or policy enforcement.
        Can raise exceptions to abort deletion.
        
        Default implementation does nothing (no-op).
        \"\"\"
        pass

AFTER:
    async def on_deleting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Pre-deletion hook called before delete_resource.
        
        Default: Logs the deletion request.
        
        Override to add checks and call super() to keep logging.
        Can raise exceptions to abort deletion.
        \"\"\"
        logger.info(
            f"Deleting {request.resource_type}: "
            f"id={request.resource_id} "
            f"user={context.user_id}"
        )
"""

# ============================================================================
# CHANGE 8: Replace on_deleted Hook (around line 394)
# ============================================================================

REPLACE_ON_DELETED = """
BEFORE:
    async def on_deleted(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Post-deletion hook called after successful delete_resource.
        
        Override to add cleanup, deregistration, or audit logging.
        Exceptions are logged but do NOT abort (deletion succeeded).
        
        Default implementation does nothing (no-op).
        \"\"\"
        pass

AFTER:
    async def on_deleted(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        \"\"\"
        Post-deletion hook called after successful delete_resource.
        
        Default: Calls _audit_log and _record_metric.
        Exceptions are logged but do NOT abort (deletion succeeded).
        
        Override to add custom behavior and call super() to keep defaults.
        \"\"\"
        try:
            await self._audit_log(
                operation="ResourceDeleted",
                resource_id=request.resource_id,
                user_id=context.user_id,
                request_id=context.request_id,
                timestamp=datetime.utcnow().isoformat(),
            )
            
            await self._record_metric(
                metric_name="resources_deleted_total",
                value=1,
            )
        
        except Exception as e:
            logger.warning(f"Post-delete defaults failed: {e}")
"""

# ============================================================================
# CHANGE 9: Add Helper Methods (at end of class, before execute_action)
# ============================================================================

ADD_HELPER_METHODS = """
Add these methods before the execute_action method (around line 426):

    async def _audit_log(self, **details) -> None:
        \"\"\"
        Default audit logging implementation.
        
        Called by post-hooks (on_created, on_updated, on_deleted).
        
        Override in subclass to send to different system:
            
            async def _audit_log(self, **details):
                await self.elasticsearch.index(index="audit", body=details)
        \"\"\"
        logger.info(f"AUDIT_LOG: {details}")
        # Default: log to Python logger
        # In production: post to Elasticsearch, ClickHouse, Splunk, etc.
    
    async def _record_metric(self, **metric) -> None:
        \"\"\"
        Default metrics recording implementation.
        
        Called by post-hooks (on_created, on_updated, on_deleted).
        
        Override in subclass to send to different system:
            
            async def _record_metric(self, **metric):
                await self.prometheus.record(metric)
        \"\"\"
        logger.debug(f"METRIC: {metric}")
        # Default: log to Python logger
        # In production: post to Prometheus, Datadog, New Relic, etc.
    
    async def _publish_event(self, **event) -> None:
        \"\"\"
        Default event publishing implementation.
        
        Called by on_created hook.
        
        Override in subclass to send to different system:
            
            async def _publish_event(self, **event):
                await self.event_hub.send(event)
        \"\"\"
        logger.debug(f"EVENT: {event}")
        # Default: log to Python logger
        # In production: post to Event Hub, Kafka, SNS, etc.
"""

# ============================================================================
# SUMMARY OF ALL CHANGES
# ============================================================================

ALL_CHANGES = """
Summary: 9 Code Changes to provider.py

1. Add logging import ✓
2. Replace on_creating (log request)
3. Replace on_created (audit + metrics + events)
4. Replace on_getting (log request)
5. Replace on_updating (log request)
6. Replace on_updated (audit + metrics)
7. Replace on_deleting (log request)
8. Replace on_deleted (audit + metrics)
9. Add _audit_log, _record_metric, _publish_event helper methods

Total changes: ~200 lines added/modified

Result: ALL providers automatically get:
  ✓ Request logging
  ✓ Audit logging
  ✓ Metrics recording
  ✓ Event publishing

Providers can:
  - Use all defaults (no changes needed)
  - Override hooks + call super() to keep defaults + add custom logic
  - Override _audit_log/_record_metric/_publish_event to change systems
"""

# ============================================================================
# PROOF OF CONCEPT: Exact Diff Format
# ============================================================================

EXACT_DIFF = """
--- a/src/itl_controlplane_sdk/providers/base/provider.py
+++ b/src/itl_controlplane_sdk/providers/base/provider.py
@@ -275,19 +275,42 @@ class ResourceProvider(abc.ABC):
     async def on_creating(
         self,
         request: ResourceRequest,
         context: ProviderContext,
     ) -> None:
         \"\"\"
-        Pre-creation hook called before create_or_update_resource.
-        
-        Override to add custom validation, policy checks, or prerequisites.
+        Pre-creation hook called before create_or_update_resource.
+        
+        Default: Logs the creation request.
         Can raise exceptions to abort creation.
+        
+        Override to add custom validation and call super() to keep logging.
         \"\"\"
-        pass
+        logger.info(
+            f"Creating {request.resource_type}: "
+            f"name={request.spec.get('name')} "
+            f"user={context.user_id} "
+            f"request_id={context.request_id}"
+        )
         
     async def on_created(
         self,
@@ -299,15 +322,38 @@ class ResourceProvider(abc.ABC):
         \"\"\"
         Post-creation hook called after successful create_or_update_resource.
         
+        Default: Logs audit, records metrics, publishes events.
         Exceptions are logged but do NOT abort (operation succeeded).
+        
+        Override to add custom behavior and call super() to keep defaults.
         \"\"\"
-        pass
+        try:
+            await self._audit_log(
+                operation="ResourceCreated",
+                resource_type=request.resource_type,
+                resource_id=response.id,
+                resource_name=response.name,
+                user_id=context.user_id,
+                request_id=context.request_id,
+                timestamp=datetime.utcnow().isoformat(),
+            )
+            
+            await self._record_metric(
+                metric_name="resources_created_total",
+                value=1,
+                tags={"resource_type": request.resource_type},
+            )
+            
+            await self._publish_event(
+                event_type="resource.created",
+                resource_id=response.id,
+                resource_type=request.resource_type,
+            )
+        except Exception as e:
+            logger.warning(f"Post-creation defaults failed: {e}")
"""

print(ALL_CHANGES)
