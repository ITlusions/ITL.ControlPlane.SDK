"""
Core Resource Provider base classes and interfaces for the ITL ControlPlane SDK

This module defines the ResourceProvider abstract base class (ABC) that all
resource providers must implement to be compatible with the ITL Control Plane.

The ResourceProvider interface provides:
  - Standard CRUD operations (create, get, delete, list)
  - Custom action execution (POST operations)
  - Health checking and status reporting
  - Request validation
  - Async lifecycle management (context managers)

Every operation receives a ProviderContext that scopes the operation to a
specific tenant and includes audit information (user_id, request_id, etc.).

Example::

    from itl_controlplane_sdk.providers.base import ResourceProvider
    from itl_controlplane_sdk.core import ResourceRequest, ProviderContext
    
    class MyProvider(ResourceProvider):
        async def create_or_update_resource(
            self, 
            request: ResourceRequest, 
            context: ProviderContext
        ) -> ResourceResponse:
            # Create resource in your cloud/service
            # Use context.tenant_id for multi-tenancy
            # Log with context.request_id for tracing
            ...
"""
import abc
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from prometheus_client import Counter, Histogram

from itl_controlplane_sdk.core import (
    ResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ProviderContext,
)

logger = logging.getLogger(__name__)

# ============================================================
# Prometheus Metrics
# ============================================================

# Counter metrics
resource_operations_total = Counter(
    "resource_operations_total",
    "Total number of resource operations",
    ["operation", "resource_type", "status"],
)

# Histogram metrics (in seconds)
resource_operation_duration_seconds = Histogram(
    "resource_operation_duration_seconds",
    "Resource operation duration in seconds",
    ["operation", "resource_type"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
)


class HealthStatus:
    """Health status of a provider."""
    
    def __init__(
        self,
        status: str = "healthy",
        message: str = "",
        checks: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Initialize health status.
        
        Args:
            status: Status enum ("healthy", "degraded", "unhealthy")
            message: Optional status message
            checks: Dict of component health checks
            timestamp: Timestamp of health check
        """
        self.status = status
        self.message = message
        self.checks = checks or {}
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "message": self.message,
            "checks": self.checks,
            "timestamp": self.timestamp.isoformat(),
        }


class ResourceStatus:
    """Operational status of a resource."""
    
    def __init__(
        self,
        state: str = "Active",
        health: str = "Healthy",
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize resource status.
        
        Args:
            state: Resource state ("Active", "Inactive", "Deleted", "Pending", "Error")
            health: Health status ("Healthy", "Degraded", "Unhealthy")
            message: Optional status message
            details: Additional status details
        """
        self.state = state
        self.health = health
        self.message = message
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "state": self.state,
            "health": self.health,
        }
        if self.message:
            result["message"] = self.message
        if self.details:
            result["details"] = self.details
        return result


class ResourceProvider(abc.ABC):
    """
    Abstract base class for all Resource Providers.
    
    This interface defines the standard contract that all resource providers
    must implement to operate within the ITL Control Plane ecosystem.
    
    Providers are responsible for:
      - Creating and managing resources in their domain (cloud, service, etc.)
      - Validating resource specifications
      - Tracking resource state and providing status updates
      - Executing custom actions on resources
      - Reporting provider health and readiness
    
    All operations receive a ProviderContext that includes:
      - tenant_id: Multi-tenancy isolation
      - user_id: Subject for audit trail
      - request_id: Request tracing ID
      - correlation_id: Distributed tracing (optional)
      - metadata: Additional context-specific data
    
    Attributes:
        provider_namespace: Namespace for this provider (e.g., "ITL.Compute")
        supported_resource_types: List of resource types this provider supports
    """
    
    def __init__(self, provider_namespace: str):
        """
        Initialize the resource provider.
        
        Args:
            provider_namespace: Namespace for provider (e.g., "ITL.Compute")
        """
        self.provider_namespace = provider_namespace
        self.supported_resource_types: List[str] = []
        self._operation_start_time: Dict[str, float] = {}  # Track operation timing
    
    # ============================================================
    # CRUD Operations (Template Method Pattern with Lifecycle Hooks)
    # ============================================================
    # Public methods call lifecycle hooks around protected implementation methods.
    # Subclasses override _do_* protected methods, hooks are automatic.
    
    async def create_or_update_resource(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> ResourceResponse:
        """
        Create or update a resource (PUT/POST operation).
        
        This method:
          1. Calls on_creating() pre-hook (can raise to abort)
          2. Delegates to _do_create_or_update_resource() implementation
          3. Calls on_created() or on_updated() post-hook (exceptions logged)
        
        Subclasses should override _do_create_or_update_resource() instead.
        Hooks are automatically called.
        
        Args:
            request: Resource creation/update request
            context: Execution context (tenant, user, tracing info)
            
        Returns:
            ResourceResponse with created/updated resource details
            
        Raises:
            Exceptions from on_creating() will abort the operation
            Other exceptions from implementation are propagated
        """
        # Determine if this is a create or update
        resource_exists = False
        try:
            await self._do_get_resource(request, context)
            resource_exists = True
        except:
            resource_exists = False
        
        # Call appropriate pre-hook
        if resource_exists:
            await self.on_updating(request, context)
        else:
            await self.on_creating(request, context)
        
        # Implement CRUD operation
        response = await self._do_create_or_update_resource(request, context)
        
        # Call appropriate post-hook (exceptions are logged, not fatal)
        try:
            if resource_exists:
                await self.on_updated(request, response, context)
            else:
                await self.on_created(request, response, context)
        except Exception as e:
            logger.error(f"Error in post-hook: {str(e)}", exc_info=True)
        
        return response
    
    @abc.abstractmethod
    async def _do_create_or_update_resource(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> ResourceResponse:
        """
        Protected implementation method for create/update.
        
        Subclasses override this instead of create_or_update_resource().
        Lifecycle hooks are automatically called by create_or_update_resource().
        
        Must:
          - Validate the resource specification
          - Create or update the resource in the provider's domain
          - Return the created/updated resource with metadata
          - Handle idempotency (create is idempotent if same spec)
        
        Args:
            request: Resource creation/update request
            context: Execution context (tenant, user, tracing info)
            
        Returns:
            ResourceResponse with created/updated resource details
            
        Raises:
            InvalidSpecError: Resource specification validation failed
            ResourceConflictError: Resource already exists with different spec
            ProviderError: Provider operation failed
        """
        pass
    
    async def get_resource(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> ResourceResponse:
        """
        Get a specific resource (GET operation).
        
        This method:
          1. Calls on_getting() pre-hook (can raise to abort/deny)
          2. Delegates to _do_get_resource() implementation
        
        Subclasses should override _do_get_resource() instead.
        Hooks are automatically called.
        
        Args:
            request: Resource retrieval request
            context: Execution context
            
        Returns:
            ResourceResponse with resource details
            
        Raises:
            Exceptions from on_getting() will abort the operation
            Other exceptions from implementation are propagated
        """
        # Call pre-hook (can raise to deny access)
        await self.on_getting(request, context)
        
        # Get resource from implementation
        response = await self._do_get_resource(request, context)
        
        return response
    
    @abc.abstractmethod
    async def _do_get_resource(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> ResourceResponse:
        """
        Protected implementation method for get.
        
        Subclasses override this instead of get_resource().
        Lifecycle hooks are automatically called by get_resource().
        
        Must:
          - Validate the resource exists
          - Return current resource state from provider
          - Include all resource metadata and properties
        
        Args:
            request: Resource retrieval request
            context: Execution context
            
        Returns:
            ResourceResponse with resource details
            
        Raises:
            ResourceNotFoundError: Resource not found
            ProviderError: Provider operation failed
        """
        pass
    
    async def delete_resource(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> ResourceResponse:
        """
        Delete a resource (DELETE operation).
        
        This method:
          1. Calls on_deleting() pre-hook (can raise to abort)
          2. Delegates to _do_delete_resource() implementation
          3. Calls on_deleted() post-hook (exceptions logged)
        
        Subclasses should override _do_delete_resource() instead.
        Hooks are automatically called.
        
        Args:
            request: Resource deletion request
            context: Execution context
            
        Returns:
            ResourceResponse confirming deletion
            
        Raises:
            Exceptions from on_deleting() will abort the operation
            Other exceptions from implementation are propagated
        """
        # Call pre-hook (can raise to abort deletion)
        await self.on_deleting(request, context)
        
        # Delete from implementation
        response = await self._do_delete_resource(request, context)
        
        # Call post-hook (exceptions are logged, not fatal)
        try:
            await self.on_deleted(request, context)
        except Exception as e:
            logger.error(f"Error in post-hook: {str(e)}", exc_info=True)
        
        return response
    
    @abc.abstractmethod
    async def _do_delete_resource(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> ResourceResponse:
        """
        Protected implementation method for delete.
        
        Subclasses override this instead of delete_resource().
        Lifecycle hooks are automatically called by delete_resource().
        
        Must:
          - Validate the resource exists
          - Delete the resource from provider domain
          - Handle cascading deletes if applicable
          - Return confirmation response
        
        Args:
            request: Resource deletion request
            context: Execution context
            
        Returns:
            ResourceResponse confirming deletion
            
        Raises:
            ResourceNotFoundError: Resource not found
            ProviderError: Provider operation failed
        """
        pass
    
    async def list_resources(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> ResourceListResponse:
        """
        List resources of this type (GET collection operation).
        
        Default implementation returns empty list. Override for full support.
        
        Implementation should:
          - Return all resources matching filter criteria
          - Support pagination via skip/take
          - Support filtering by tags
          - Respect tenant scoping from context
        
        Args:
            request: Resource list request
            context: Execution context
            
        Returns:
            ResourceListResponse with list of resources
        """
        # Default implementation returns empty list
        return ResourceListResponse(value=[])
    
    # ============================================================
    # Lifecycle Hooks (Optional)
    # ============================================================
    # These are called around CRUD operations. Override if needed.
    # Pre-hooks can raise exceptions to abort (e.g., validation).
    # Post-hooks should not raise (failures are logged, not fatal).
    
    async def on_creating(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Pre-creation hook called before create_or_update_resource.
        
        Override to add custom validation, policy checks, or prerequisites.
        Can raise exceptions to abort creation.
        
        Default implementation logs creation attempt with tracing and metrics.
        
        Args:
            request: Resource creation request
            context: Execution context
            
        Raises:
            Any exception to abort creation
        """
        # Track operation start time for duration metrics
        self._operation_start_time[context.request_id] = time.time()
        
        # Record operation counter
        resource_operations_total.labels(
            operation="create",
            resource_type=request.resource_type,
            status="started"
        ).inc()
        
        logger.info(
            f"[{context.request_id}] Creating {request.resource_type}: {request.resource_name}",
            extra={
                "request_id": context.request_id,
                "user_id": context.user_id,
                "tenant_id": context.tenant_id,
                "resource_type": request.resource_type,
                "resource_name": request.resource_name,
            }
        )
    
    async def on_created(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        """
        Post-creation hook called after successful create_or_update_resource.
        
        Override to add audit logging, notifications, or side effects.
        Exceptions are logged but do NOT abort (operation succeeded).
        
        Default implementation logs successful creation with tracing and metrics.
        
        Args:
            request: Original creation request
            response: Created resource response
            context: Execution context
        """
        # Record operation counter (success)
        resource_operations_total.labels(
            operation="create",
            resource_type=request.resource_type,
            status="success"
        ).inc()
        
        # Record operation duration
        start_time = self._operation_start_time.pop(context.request_id, time.time())
        duration = time.time() - start_time
        resource_operation_duration_seconds.labels(
            operation="create",
            resource_type=request.resource_type,
        ).observe(duration)
        
        logger.info(
            f"[{context.request_id}] Successfully created {request.resource_type}: {response.id} ({duration:.3f}s)",
            extra={
                "request_id": context.request_id,
                "user_id": context.user_id,
                "tenant_id": context.tenant_id,
                "resource_id": response.id,
                "resource_type": request.resource_type,
                "provisioning_state": response.provisioning_state,
                "duration_seconds": duration,
            }
        )
    
    async def on_getting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Pre-get hook called before get_resource.
        
        Override to add access control or logging.
        Can raise exceptions to deny access.
        
        Default implementation logs get request with tracing and metrics.
        
        Args:
            request: Resource retrieval request
            context: Execution context
            
        Raises:
            Any exception to abort get operation
        """
        # Track operation start time for duration metrics
        self._operation_start_time[context.request_id] = time.time()
        
        # Record operation counter
        resource_operations_total.labels(
            operation="get",
            resource_type=request.resource_type,
            status="started"
        ).inc()
        
        logger.debug(
            f"[{context.request_id}] Getting {request.resource_type}: {request.resource_name}",
            extra={
                "request_id": context.request_id,
                "user_id": context.user_id,
                "resource_type": request.resource_type,
                "resource_name": request.resource_name,
            }
        )
    
    async def on_updating(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Pre-update hook called before create_or_update_resource (on updates).
        
        Override to add validation, immutability checks, or version control.
        Can raise exceptions to abort update.
        
        Default implementation logs update attempt with tracing and metrics.
        
        Args:
            request: Resource update request
            context: Execution context
            
        Raises:
            Any exception to abort update
        """
        # Track operation start time for duration metrics
        self._operation_start_time[context.request_id] = time.time()
        
        # Record operation counter
        resource_operations_total.labels(
            operation="update",
            resource_type=request.resource_type,
            status="started"
        ).inc()
        
        logger.info(
            f"[{context.request_id}] Updating {request.resource_type}: {request.resource_name}",
            extra={
                "request_id": context.request_id,
                "user_id": context.user_id,
                "tenant_id": context.tenant_id,
                "resource_type": request.resource_type,
                "resource_name": request.resource_name,
            }
        )
    
    async def on_updated(
        self,
        request: ResourceRequest,
        response: ResourceResponse,
        context: ProviderContext,
    ) -> None:
        """
        Post-update hook called after successful resource update.
        
        Override to add audit logging, cache invalidation, or notifications.
        Exceptions are logged but do NOT abort (operation succeeded).
        
        Default implementation logs successful update with tracing and metrics.
        
        Args:
            request: Original update request
            response: Updated resource response
            context: Execution context
        """
        # Record operation counter (success)
        resource_operations_total.labels(
            operation="update",
            resource_type=request.resource_type,
            status="success"
        ).inc()
        
        # Record operation duration
        start_time = self._operation_start_time.pop(context.request_id, time.time())
        duration = time.time() - start_time
        resource_operation_duration_seconds.labels(
            operation="update",
            resource_type=request.resource_type,
        ).observe(duration)
        
        logger.info(
            f"[{context.request_id}] Successfully updated {request.resource_type}: {response.id} ({duration:.3f}s)",
            extra={
                "request_id": context.request_id,
                "user_id": context.user_id,
                "tenant_id": context.tenant_id,
                "resource_id": response.id,
                "resource_type": request.resource_type,
                "provisioning_state": response.provisioning_state,
                "duration_seconds": duration,
            }
        )
    
    async def on_deleting(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Pre-deletion hook called before delete_resource.
        
        Override to add dependency checks or policy enforcement.
        Can raise exceptions to abort deletion.
        
        Default implementation logs deletion attempt with tracing and metrics.
        
        Args:
            request: Resource deletion request
            context: Execution context
            
        Raises:
            Any exception to abort deletion (e.g., blocking dependencies)
        """
        # Track operation start time for duration metrics
        self._operation_start_time[context.request_id] = time.time()
        
        # Record operation counter
        resource_operations_total.labels(
            operation="delete",
            resource_type=request.resource_type,
            status="started"
        ).inc()
        
        logger.info(
            f"[{context.request_id}] Deleting {request.resource_type}: {request.resource_name}",
            extra={
                "request_id": context.request_id,
                "user_id": context.user_id,
                "tenant_id": context.tenant_id,
                "resource_type": request.resource_type,
                "resource_name": request.resource_name,
            }
        )
    
    async def on_deleted(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> None:
        """
        Post-deletion hook called after successful delete_resource.
        
        Override to add cleanup, deregistration, or audit logging.
        Exceptions are logged but do NOT abort (deletion succeeded).
        
        Default implementation logs successful deletion with tracing and metrics.
        
        Args:
            request: Original deletion request
            context: Execution context
        """
        # Record operation counter (success)
        resource_operations_total.labels(
            operation="delete",
            resource_type=request.resource_type,
            status="success"
        ).inc()
        
        # Record operation duration
        start_time = self._operation_start_time.pop(context.request_id, time.time())
        duration = time.time() - start_time
        resource_operation_duration_seconds.labels(
            operation="delete",
            resource_type=request.resource_type,
        ).observe(duration)
        
        logger.info(
            f"[{context.request_id}] Successfully deleted {request.resource_type}: {request.resource_name} ({duration:.3f}s)",
            extra={
                "request_id": context.request_id,
                "user_id": context.user_id,
                "tenant_id": context.tenant_id,
                "resource_type": request.resource_type,
                "resource_name": request.resource_name,
                "duration_seconds": duration,
            }
        )
    
    # ============================================================
    # Actions
    # ============================================================
    
    async def execute_action(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> ResourceResponse:
        """
        Execute a custom action on a resource (POST operation).
        
        Default implementation raises NotImplementedError.
        Override to support custom actions like "start", "stop", "restart", etc.
        
        Args:
            request: Action request with action name and parameters
            context: Execution context
            
        Returns:
            ResourceResponse with action result
            
        Raises:
            NotImplementedError: Action not supported by provider
        """
        raise NotImplementedError(
            f"Action '{request.action}' not supported by this provider"
        )
    
    # ============================================================
    # Status & Health
    # ============================================================
    
    async def get_resource_status(
        self,
        request: ResourceRequest,
        context: ProviderContext,
    ) -> ResourceStatus:
        """
        Get operational status of a resource.
        
        Default implementation queries provider for current state.
        Override for custom status logic.
        
        Note: Uses _do_get_resource to bypass hooks (internal status check,
        not a user-initiated get operation).
        
        Args:
            request: Request with resource to query
            context: Execution context
            
        Returns:
            ResourceStatus with state, health, and details
            
        Raises:
            ResourceNotFoundError: Resource not found
            ProviderError: Provider operation failed
        """
        # Default: get resource and infer status
        try:
            resource = await self._do_get_resource(request, context)
            return ResourceStatus(
                state="Active",
                health="Healthy",
                details={
                    "provisioning_state": resource.provisioning_state,
                },
            )
        except Exception as e:
            logger.error(f"Error getting resource status: {str(e)}", exc_info=True)
            return ResourceStatus(
                state="Error",
                health="Unhealthy",
                message=str(e),
            )
    
    async def health_check(self) -> HealthStatus:
        """
        Verify provider can reach its backend service.
        
        Default implementation returns healthy. Override to implement
        actual health checks (e.g., test cloud API connectivity).
        
        Returns:
            HealthStatus indicating provider readiness
        """
        return HealthStatus(status="healthy")
    
    # ============================================================
    # Utilities
    # ============================================================
    
    def supports_resource_type(self, resource_type: str) -> bool:
        """
        Check if this provider supports the given resource type.
        
        Args:
            resource_type: The resource type to check
            
        Returns:
            True if supported, False otherwise
        """
        return resource_type in self.supported_resource_types
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.
        
        Returns:
            Dict with provider metadata
        """
        return {
            "namespace": self.provider_namespace,
            "resourceTypes": self.supported_resource_types,
            "apiVersion": "2023-01-01",
        }
    
    def generate_resource_id(
        self,
        subscription_id: str,
        resource_group: str,
        resource_type: str,
        resource_name: str,
    ) -> str:
        """
        Generate standard ARM-style resource ID.
        
        Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/{namespace}/{type}/{name}
        
        Args:
            subscription_id: Azure subscription ID
            resource_group: Azure resource group name
            resource_type: Resource type name
            resource_name: Resource instance name
            
        Returns:
            Standard resource ID string
        """
        return (
            f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/"
            f"providers/{self.provider_namespace}/{resource_type}/{resource_name}"
        )
    
    def validate_request(self, request: ResourceRequest) -> List[str]:
        """
        Validate resource request has required fields.
        
        Default validation checks for required fields. Override for
        provider-specific validation logic.
        
        Args:
            request: Request to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not request.subscription_id:
            errors.append("subscription_id is required")
        if not request.resource_group:
            errors.append("resource_group is required")
        if not request.resource_name:
            errors.append("resource_name is required")
        if not request.location:
            errors.append("location is required")
        if not request.body:
            errors.append("body is required")
        
        return errors
    
    # ============================================================
    # Async Lifecycle (Context Manager Support)
    # ============================================================
    
    async def __aenter__(self):
        """
        Async context manager entry.
        
        Override if provider needs initialization before operations.
        """
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.
        
        Override if provider needs cleanup after operations.
        """
        await self.cleanup()
        if exc_type:
            logger.error(f"Error during provider operation: {exc_val}", exc_info=True)
    
    async def initialize(self) -> None:
        """
        Initialize provider (e.g., connect to cloud SDK).
        
        Default implementation does nothing. Override if needed.
        """
        pass
    
    async def cleanup(self) -> None:
        """
        Clean up provider resources (e.g., close connections).
        
        Default implementation does nothing. Override if needed.
        """
        pass
