"""
BaseResourceService - Reusable service pattern for resource providers

Provides common functionality for all provider services:
- Idempotency (prevent duplicate operations)
- Event publishing (event-driven architecture)
- Tenant isolation (multi-tenant safety)
- Error handling and retry queueing
- Transaction safety and state management

Each provider's service (TenantService, OrganizationService, ResourceGroupService, etc.)
inherits from this base class and implements provider-specific logic.

Example Usage (in provider):
    class MyResourceService(BaseResourceService):
        async def create_resource(self, spec, idempotency_key, request_context):
            # Call parent for idempotency check
            existing = await self._check_idempotency(idempotency_key, spec)
            if existing:
                return existing
            
            # Provider-specific logic
            resource = await self.provider.create_my_resource(spec)
            
            # Call parent for storing idempotency result
            await self._store_idempotency_result(idempotency_key, resource)
            
            # Call parent for event publishing
            await self._publish_event("resource.created", resource)
            
            return resource
"""
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)


class BaseResourceService:
    """
    Base service class for resource management.
    
    Provides common patterns that all provider services need:
    - Idempotency (at-least-once semantics)
    - Event publishing (pub/sub)
    - Tenant isolation (multi-tenant verification)
    - Error recovery (retry queues)
    - Transaction safety
    
    Subclasses implement provider-specific resource operations.
    """

    def __init__(
        self,
        provider: Any,
        graph_db_service: Optional[Any] = None,
        event_bus: Optional[Any] = None,
        idempotency_store: Optional[Any] = None,
    ):
        """
        Initialize BaseResourceService.

        Args:
            provider: Resource provider instance (required)
                Handles actual resource operations (create, delete, etc.)
            graph_db_service: GraphDB service for metadata (optional)
                Stores relationships and metadata for fast searching
            event_bus: Event bus for publishing events (optional)
                Enables event-driven subscribers (audit, email, metrics)
            idempotency_store: Store for idempotency keys (optional)
                Default: in-memory dict
                Production: Redis or database with TTL support
        """
        self.provider = provider
        self.graph_db_service = graph_db_service
        self.event_bus = event_bus
        self.idempotency_store = idempotency_store or {}  # In-memory fallback
        self.logger = logger
        self._retry_queue: List[Dict[str, Any]] = []

    # ======================== IDEMPOTENCY ========================

    async def _check_idempotency(
        self,
        idempotency_key: str,
        spec: Any,
    ) -> Optional[Any]:
        """
        Check if operation already completed (idempotency).

        IDEMPOTENCY SEMANTICS:
        - If key not found: operation is new, return None
        - If key found with same spec: operation already succeeded, return cached result
        - If key found with different spec: conflict (client error), raise ConflictError

        This ensures:
        - Network retries are safe (same request returns same result)
        - Client bugs detected (different spec = something wrong)
        - At-most-once semantics (only one real operation per key)

        Args:
            idempotency_key: Unique request identifier
            spec: Resource spec (check against stored spec)

        Returns:
            Resource if already created with same spec
            None if key not found (proceed with creation)

        Raises:
            ConflictError: If key exists with different spec (tampering?)

        Example:
            result = await service._check_idempotency("req-123", spec)
            if result:
                return result  # Already done, return cached
            # Otherwise continue with creation
        """
        if idempotency_key not in self.idempotency_store:
            return None

        stored_entry = self.idempotency_store[idempotency_key]
        stored_spec = stored_entry.get("spec")
        current_spec_dict = spec.dict() if hasattr(spec, "dict") else str(spec)

        if stored_spec != current_spec_dict:
            raise Exception(
                f"Idempotency key '{idempotency_key}' already used with different spec. "
                f"Stored: {stored_spec}, Current: {current_spec_dict}"
            )

        # Return cached result
        result = stored_entry.get("result")
        self.logger.info(
            "Idempotency check: returning cached result",
            extra={"idempotency_key": idempotency_key},
        )
        return result

    async def _store_idempotency_result(
        self,
        idempotency_key: str,
        result: Any,
        ttl_hours: int = 24,
    ) -> None:
        """
        Store operation result for idempotency.

        Prevents duplicate creation if same request retried within TTL.
        Results automatically expire after TTL in production stores (Redis, DB).

        IMPORTANT:
        - Development: In-memory dict (results never expire)
        - Production: Redis or database with TTL support

        Args:
            idempotency_key: Unique request key
            result: Operation result (Resource object or error)
            ttl_hours: How long to keep result (default 24 hours)

        Example:
            resource = Resource(id="res-1", name="MyResource")
            await service._store_idempotency_result(
                "req-123",
                resource,
                ttl_hours=24,
            )
            # Result is cached for 24 hours
        """
        self.idempotency_store[idempotency_key] = {
            "result": result,
            "spec": result.dict() if hasattr(result, "dict") else str(result),
            "stored_at": datetime.now(timezone.utc),
            "ttl_hours": ttl_hours,
        }

        self.logger.debug(
            "Idempotency result stored",
            extra={
                "idempotency_key": idempotency_key,
                "ttl_hours": ttl_hours,
            },
        )

    # ======================== EVENT PUBLISHING ========================

    async def _publish_event(
        self,
        event_type: str,
        resource: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Publish event for event-driven subscribers.

        Events enable:
        - Real-time notifications (email, webhook)
        - Audit logging (who created what when)
        - System synchronization (GraphDB, caches)
        - Metrics and analytics

        EVENT FORMAT:
        {
            "event_type": "resource.created",
            "resource_id": "...",
            "timestamp": "2024-01-31T...",
            "context": {
                "trace_id": "...",
                "user_id": "...",
                "correlation_id": "...",
            }
        }

        Args:
            event_type: Event type ("resource.created", "resource.deleted", etc.)
            resource: Affected resource object
            context: Additional context (user_id, trace_id, tenant_id, etc.)

        Example:
            await service._publish_event(
                event_type="resource.created",
                resource=created_resource,
                context={
                    "trace_id": "trace-123",
                    "user_id": "user-456",
                    "tenant_id": "tenant-789",
                },
            )
        """
        if not self.event_bus:
            self.logger.debug("Event bus not configured, skipping event publishing")
            return

        try:
            context = context or {}
            event_payload = {
                "event_type": event_type,
                "resource_id": getattr(resource, "id", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": context,
                "resource": resource.dict() if hasattr(resource, "dict") else str(resource),
            }

            await self.event_bus.publish(event_type, event_payload)

            self.logger.info(
                "Event published",
                extra={
                    "event_type": event_type,
                    "resource_id": event_payload["resource_id"],
                    "trace_id": context.get("trace_id", ""),
                },
            )
        except Exception as e:
            self.logger.error(
                "Failed to publish event",
                extra={
                    "event_type": event_type,
                    "error": str(e),
                },
            )

    # ======================== TENANT ISOLATION ========================

    async def _verify_tenant_isolation(
        self,
        spec_tenant_id: str,
        user_tenant_id: str,
    ) -> None:
        """
        Verify tenant isolation (user can only operate in their own tenant).

        CRITICAL for multi-tenant safety:
        - User from tenant A cannot create resources in tenant B
        - User from tenant A cannot see resources in tenant B
        - User from tenant A cannot delete resources in tenant B

        Args:
            spec_tenant_id: Tenant ID in resource spec
            user_tenant_id: User's tenant ID from JWT/context

        Raises:
            AuthorizationError: If spec_tenant_id != user_tenant_id

        Example:
            await service._verify_tenant_isolation(
                spec_tenant_id=spec.tenant_id,
                user_tenant_id=request_context['tenant_id'],
            )
            # Raises AuthorizationError if different
        """
        if spec_tenant_id != user_tenant_id:
            raise Exception(
                f"Tenant mismatch: spec tenant '{spec_tenant_id}' != "
                f"user tenant '{user_tenant_id}'. Cannot operate across tenant boundaries."
            )

    # ======================== ERROR RECOVERY ========================

    async def _queue_for_retry(
        self,
        operation: str,
        spec: Any,
        error: Exception,
        attempt: int = 0,
    ) -> None:
        """
        Queue failed operation for retry.

        Uses exponential backoff for transient errors.
        Allows operations team to investigate and recover from failures.

        BACKOFF STRATEGY:
        - Attempt 0: 100ms (first retry)
        - Attempt 1: 200ms
        - Attempt 2: 400ms
        - Attempt 3: 800ms (max, then give up)

        Args:
            operation: What operation failed ("create_resource", etc.)
            spec: Original spec that failed
            error: Error that occurred
            attempt: Retry attempt number (0 = first retry)

        Example:
            try:
                await provider.create_resource(spec)
            except RetryableError as e:
                await service._queue_for_retry("create", spec, e, attempt=0)
        """
        max_attempts = 3
        if attempt >= max_attempts:
            self.logger.error(
                "Operation exceeded max retry attempts, giving up",
                extra={
                    "operation": operation,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "error": str(error),
                },
            )
            return

        # Exponential backoff: 100ms, 200ms, 400ms, 800ms
        backoff_ms = min(100 * (2 ** attempt), 800)

        self._retry_queue.append({
            "operation": operation,
            "spec": spec,
            "error": str(error),
            "attempt": attempt,
            "backoff_ms": backoff_ms,
            "queued_at": datetime.now(timezone.utc),
        })

        self.logger.info(
            "Operation queued for retry",
            extra={
                "operation": operation,
                "attempt": attempt,
                "backoff_ms": backoff_ms,
                "queue_size": len(self._retry_queue),
            },
        )

    # ======================== GRAPH DATABASE SYNC ========================

    async def _sync_to_graph_database(
        self,
        resource: Any,
        operation: str = "create",
    ) -> None:
        """
        Sync resource to graph database for metadata and relationships.

        Enables:
        - Fast searching by properties (<10ms with indexes)
        - Relationship discovery (dependencies, ownership)
        - Disaster recovery (complete metadata snapshot)

        Args:
            resource: Resource to sync
            operation: "create", "update", or "delete"

        Example:
            resource = Resource(id="res-1", name="MyResource", tenant_id="tenant-1")
            await service._sync_to_graph_database(resource, operation="create")
        """
        if not self.graph_db_service:
            self.logger.debug("Graph database service not configured, skipping sync")
            return

        try:
            resource_id = getattr(resource, "id", "unknown")
            resource_type = resource.__class__.__name__

            if operation == "create":
                await self.graph_db_service.register_resource(resource)
            elif operation == "update":
                await self.graph_db_service.update_resource(resource)
            elif operation == "delete":
                await self.graph_db_service.delete_resource(resource_id)

            self.logger.debug(
                "Resource synced to graph database",
                extra={
                    "resource_id": resource_id,
                    "resource_type": resource_type,
                    "operation": operation,
                },
            )
        except Exception as e:
            self.logger.warning(
                "Failed to sync resource to graph database",
                extra={
                    "error": str(e),
                    "resource_id": getattr(resource, "id", "unknown"),
                },
            )


__all__ = ["BaseResourceService"]
