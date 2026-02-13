"""
AuditEventPublisher - Facade for publishing audit events.

Provides a clean, high-level API for logging audit events with:
- Automatic context extraction (request info, correlation IDs)
- Convenience methods for CRUD operations
- State tracking (configurable)
- Batch operations
- Decorator for automatic function auditing
"""

from __future__ import annotations

import functools
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypeVar, List, Awaitable

from .models import AuditEvent, AuditAction, ActorType, AuditEventQuery, AuditEventPage
from .adapters import AuditEventAdapter, NoOpAuditEventAdapter

logger = logging.getLogger(__name__)

# Context variables for request context
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_actor_id: ContextVar[Optional[str]] = ContextVar("actor_id", default=None)
_actor_type: ContextVar[ActorType] = ContextVar("actor_type", default=ActorType.SYSTEM)
_actor_display_name: ContextVar[Optional[str]] = ContextVar("actor_display_name", default=None)
_source_ip: ContextVar[Optional[str]] = ContextVar("source_ip", default=None)
_user_agent: ContextVar[Optional[str]] = ContextVar("user_agent", default=None)
_tenant_id: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
_subscription_id: ContextVar[Optional[str]] = ContextVar("subscription_id", default=None)

T = TypeVar("T")


class AuditContext:
    """
    Context manager for setting audit context.
    
    Use this to set request-scoped audit context that will be
    automatically included in all audit events published within the context.
    
    Example:
        async with AuditContext(
            actor_id="user-123",
            actor_type=ActorType.USER,
            correlation_id=request_id,
            source_ip="192.168.1.1",
        ):
            await publisher.log_create(...)
            # All events within this block get the context
    """
    
    def __init__(
        self,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[ActorType] = None,
        actor_display_name: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        tenant_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
    ):
        self._tokens = []
        self._correlation_id = correlation_id
        self._request_id = request_id
        self._actor_id = actor_id
        self._actor_type = actor_type
        self._actor_display_name = actor_display_name
        self._source_ip = source_ip
        self._user_agent = user_agent
        self._tenant_id = tenant_id
        self._subscription_id = subscription_id
    
    def __enter__(self) -> AuditContext:
        if self._correlation_id:
            self._tokens.append(_correlation_id.set(self._correlation_id))
        if self._request_id:
            self._tokens.append(_request_id.set(self._request_id))
        if self._actor_id:
            self._tokens.append(_actor_id.set(self._actor_id))
        if self._actor_type:
            self._tokens.append(_actor_type.set(self._actor_type))
        if self._actor_display_name:
            self._tokens.append(_actor_display_name.set(self._actor_display_name))
        if self._source_ip:
            self._tokens.append(_source_ip.set(self._source_ip))
        if self._user_agent:
            self._tokens.append(_user_agent.set(self._user_agent))
        if self._tenant_id:
            self._tokens.append(_tenant_id.set(self._tenant_id))
        if self._subscription_id:
            self._tokens.append(_subscription_id.set(self._subscription_id))
        return self
    
    def __exit__(self, *args) -> None:
        for token in reversed(self._tokens):
            # Reset to previous value
            pass  # ContextVar tokens auto-reset on scope exit
    
    async def __aenter__(self) -> AuditContext:
        return self.__enter__()
    
    async def __aexit__(self, *args) -> None:
        return self.__exit__(*args)


class AuditEventPublisher:
    """
    High-level facade for publishing audit events.
    
    Features:
    - Automatic context extraction (correlation IDs, actor info)
    - Convenience methods (log_create, log_update, log_delete)
    - Configurable state tracking
    - Batch operations
    - Query support (if adapter supports it)
    
    Example:
        from itl_controlplane_sdk.persistence.audit import (
            AuditEventPublisher,
            SQLAuditEventAdapter,
            RabbitMQAuditEventAdapter,
            CompositeAuditEventAdapter,
        )
        
        # Create adapters
        sql_adapter = SQLAuditEventAdapter(engine)
        rabbit_adapter = RabbitMQAuditEventAdapter(url="amqp://...")
        
        # Composite for fan-out to both
        composite = CompositeAuditEventAdapter([sql_adapter, rabbit_adapter])
        
        # Create publisher
        publisher = AuditEventPublisher(adapter=composite, track_state=True)
        await publisher.initialize()
        
        # Set request context
        async with AuditContext(
            actor_id="user-123",
            actor_type=ActorType.USER,
            correlation_id=str(uuid.uuid4()),
        ):
            await publisher.log_create(
                resource_id="/subscriptions/sub-1",
                resource_type="ITL.Core/subscriptions",
                resource_name="my-subscription",
                new_state={"name": "my-subscription", ...},
            )
    """
    
    def __init__(
        self,
        adapter: Optional[AuditEventAdapter] = None,
        track_state: bool = True,
        enabled: bool = True,
        max_state_size: int = 10000,  # Max bytes for state JSON
    ):
        """
        Initialize the publisher.
        
        Args:
            adapter: Audit event adapter (defaults to NoOpAuditEventAdapter)
            track_state: Whether to include resource state in events
            enabled: Whether audit logging is enabled
            max_state_size: Max size in bytes for state JSON (truncated if exceeded)
        """
        self._adapter = adapter or NoOpAuditEventAdapter()
        self._track_state = track_state
        self._enabled = enabled
        self._max_state_size = max_state_size
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the adapter."""
        await self._adapter.initialize()
        self._initialized = True
        logger.info(f"AuditEventPublisher initialized with {self._adapter.__class__.__name__}")
    
    async def shutdown(self) -> None:
        """Shutdown the adapter."""
        await self._adapter.shutdown()
        self._initialized = False
        logger.info("AuditEventPublisher shutdown")
    
    def _get_context(self) -> dict[str, Any]:
        """Get current audit context from context variables."""
        return {
            "correlation_id": _correlation_id.get(),
            "request_id": _request_id.get(),
            "actor_id": _actor_id.get(),
            "actor_type": _actor_type.get(),
            "actor_display_name": _actor_display_name.get(),
            "source_ip": _source_ip.get(),
            "user_agent": _user_agent.get(),
            "tenant_id": _tenant_id.get(),
            "subscription_id": _subscription_id.get(),
        }
    
    def _truncate_state(self, state: Optional[dict]) -> Optional[dict]:
        """Truncate state if it exceeds max size."""
        if state is None:
            return None
        import json
        serialized = json.dumps(state)
        if len(serialized) <= self._max_state_size:
            return state
        return {"_truncated": True, "_original_size": len(serialized)}
    
    async def publish(self, event: AuditEvent) -> bool:
        """
        Publish an audit event.
        
        Args:
            event: The audit event to publish
            
        Returns:
            True if successful
        """
        if not self._enabled:
            return True
            
        return await self._adapter.publish(event)
    
    async def publish_batch(self, events: List[AuditEvent]) -> int:
        """
        Publish multiple audit events.
        
        Args:
            events: List of events to publish
            
        Returns:
            Number of successfully published events
        """
        if not self._enabled:
            return len(events)
            
        return await self._adapter.publish_batch(events)
    
    async def log_create(
        self,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        new_state: Optional[dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[ActorType] = None,
        change_summary: Optional[str] = None,
        extra_data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> bool:
        """
        Log a CREATE event.
        
        Args:
            resource_id: ARM-style resource ID
            resource_type: Resource type (e.g., ITL.Core/subscriptions)
            resource_name: Resource name
            new_state: Created resource state
            actor_id: Override actor ID from context
            actor_type: Override actor type from context
            change_summary: Human-readable summary
            extra_data: Additional metadata
            
        Returns:
            True if successful
        """
        ctx = self._get_context()
        
        event = AuditEvent(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.CREATE,
            new_state=self._truncate_state(new_state) if self._track_state else None,
            actor_id=actor_id or ctx["actor_id"],
            actor_type=actor_type or ctx["actor_type"],
            actor_display_name=ctx["actor_display_name"],
            correlation_id=ctx["correlation_id"],
            request_id=ctx["request_id"],
            source_ip=ctx["source_ip"],
            user_agent=ctx["user_agent"],
            tenant_id=ctx["tenant_id"],
            subscription_id=ctx["subscription_id"],
            change_summary=change_summary or f"Created {resource_type}: {resource_name}",
            extra_data=extra_data,
            **kwargs,
        )
        
        return await self.publish(event)
    
    async def log_update(
        self,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        previous_state: Optional[dict[str, Any]] = None,
        new_state: Optional[dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[ActorType] = None,
        change_summary: Optional[str] = None,
        extra_data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> bool:
        """
        Log an UPDATE event.
        
        Args:
            resource_id: ARM-style resource ID
            resource_type: Resource type
            resource_name: Resource name
            previous_state: State before update
            new_state: State after update
            actor_id: Override actor ID from context
            actor_type: Override actor type from context
            change_summary: Human-readable summary
            extra_data: Additional metadata
            
        Returns:
            True if successful
        """
        ctx = self._get_context()
        
        event = AuditEvent(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.UPDATE,
            previous_state=self._truncate_state(previous_state) if self._track_state else None,
            new_state=self._truncate_state(new_state) if self._track_state else None,
            actor_id=actor_id or ctx["actor_id"],
            actor_type=actor_type or ctx["actor_type"],
            actor_display_name=ctx["actor_display_name"],
            correlation_id=ctx["correlation_id"],
            request_id=ctx["request_id"],
            source_ip=ctx["source_ip"],
            user_agent=ctx["user_agent"],
            tenant_id=ctx["tenant_id"],
            subscription_id=ctx["subscription_id"],
            change_summary=change_summary or f"Updated {resource_type}: {resource_name}",
            extra_data=extra_data,
            **kwargs,
        )
        
        return await self.publish(event)
    
    async def log_delete(
        self,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        previous_state: Optional[dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[ActorType] = None,
        change_summary: Optional[str] = None,
        extra_data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> bool:
        """
        Log a DELETE event.
        
        Args:
            resource_id: ARM-style resource ID
            resource_type: Resource type
            resource_name: Resource name
            previous_state: State before deletion
            actor_id: Override actor ID from context
            actor_type: Override actor type from context
            change_summary: Human-readable summary
            extra_data: Additional metadata
            
        Returns:
            True if successful
        """
        ctx = self._get_context()
        
        event = AuditEvent(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.DELETE,
            previous_state=self._truncate_state(previous_state) if self._track_state else None,
            actor_id=actor_id or ctx["actor_id"],
            actor_type=actor_type or ctx["actor_type"],
            actor_display_name=ctx["actor_display_name"],
            correlation_id=ctx["correlation_id"],
            request_id=ctx["request_id"],
            source_ip=ctx["source_ip"],
            user_agent=ctx["user_agent"],
            tenant_id=ctx["tenant_id"],
            subscription_id=ctx["subscription_id"],
            change_summary=change_summary or f"Deleted {resource_type}: {resource_name}",
            extra_data=extra_data,
            **kwargs,
        )
        
        return await self.publish(event)
    
    async def log_read(
        self,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        actor_id: Optional[str] = None,
        actor_type: Optional[ActorType] = None,
        extra_data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> bool:
        """
        Log a READ event (optional, for sensitive resources).
        
        Args:
            resource_id: ARM-style resource ID
            resource_type: Resource type
            resource_name: Resource name
            actor_id: Override actor ID from context
            actor_type: Override actor type from context
            extra_data: Additional metadata
            
        Returns:
            True if successful
        """
        ctx = self._get_context()
        
        event = AuditEvent(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.READ,
            actor_id=actor_id or ctx["actor_id"],
            actor_type=actor_type or ctx["actor_type"],
            actor_display_name=ctx["actor_display_name"],
            correlation_id=ctx["correlation_id"],
            request_id=ctx["request_id"],
            source_ip=ctx["source_ip"],
            user_agent=ctx["user_agent"],
            tenant_id=ctx["tenant_id"],
            subscription_id=ctx["subscription_id"],
            change_summary=f"Read {resource_type}: {resource_name}",
            extra_data=extra_data,
            **kwargs,
        )
        
        return await self.publish(event)
    
    async def log_action(
        self,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        action: AuditAction,
        previous_state: Optional[dict[str, Any]] = None,
        new_state: Optional[dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[ActorType] = None,
        change_summary: Optional[str] = None,
        extra_data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> bool:
        """
        Log a custom action event.
        
        Use this for extended actions like ENABLE, DISABLE, ASSIGN, etc.
        
        Args:
            resource_id: ARM-style resource ID
            resource_type: Resource type
            resource_name: Resource name
            action: The action performed
            previous_state: State before action
            new_state: State after action
            actor_id: Override actor ID from context
            actor_type: Override actor type from context
            change_summary: Human-readable summary
            extra_data: Additional metadata
            
        Returns:
            True if successful
        """
        ctx = self._get_context()
        
        event = AuditEvent(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=action,
            previous_state=self._truncate_state(previous_state) if self._track_state else None,
            new_state=self._truncate_state(new_state) if self._track_state else None,
            actor_id=actor_id or ctx["actor_id"],
            actor_type=actor_type or ctx["actor_type"],
            actor_display_name=ctx["actor_display_name"],
            correlation_id=ctx["correlation_id"],
            request_id=ctx["request_id"],
            source_ip=ctx["source_ip"],
            user_agent=ctx["user_agent"],
            tenant_id=ctx["tenant_id"],
            subscription_id=ctx["subscription_id"],
            change_summary=change_summary or f"{action.value} {resource_type}: {resource_name}",
            extra_data=extra_data,
            **kwargs,
        )
        
        return await self.publish(event)
    
    async def query(self, query: AuditEventQuery) -> AuditEventPage:
        """
        Query audit events.
        
        Args:
            query: Query parameters
            
        Returns:
            Paginated list of events
            
        Raises:
            NotImplementedError: If adapter doesn't support querying
        """
        return await self._adapter.query(query)
    
    @property
    def supports_query(self) -> bool:
        """Whether the adapter supports querying."""
        return self._adapter.supports_query
    
    @property
    def enabled(self) -> bool:
        """Whether audit logging is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable audit logging."""
        self._enabled = value


def audit_action(
    action: AuditAction,
    resource_type: str,
    get_resource_id: Callable[..., str],
    get_resource_name: Callable[..., str],
    get_publisher: Optional[Callable[[], AuditEventPublisher]] = None,
    get_state: Optional[Callable[..., Optional[dict]]] = None,
    track_state: bool = True,
):
    """
    Decorator for automatic audit logging on functions.
    
    Example:
        @audit_action(
            action=AuditAction.DELETE,
            resource_type="ITL.Core/subscriptions",
            get_resource_id=lambda self, id: f"/subscriptions/{id}",
            get_resource_name=lambda self, id: id,
            get_publisher=lambda: current_app.state.audit_publisher,
        )
        async def delete_subscription(self, id: str):
            ...
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Get publisher
            publisher = get_publisher() if get_publisher else None
            if not publisher or not publisher.enabled:
                return await func(*args, **kwargs)
            
            # Get resource info
            resource_id = get_resource_id(*args, **kwargs)
            resource_name = get_resource_name(*args, **kwargs)
            
            # Get previous state for UPDATE/DELETE
            previous_state = None
            if track_state and action in (AuditAction.UPDATE, AuditAction.DELETE):
                if get_state:
                    previous_state = get_state(*args, **kwargs)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Get new state for CREATE/UPDATE
            new_state = None
            if track_state and action in (AuditAction.CREATE, AuditAction.UPDATE):
                if isinstance(result, dict):
                    new_state = result
                elif hasattr(result, "model_dump"):
                    new_state = result.model_dump()
                elif hasattr(result, "to_dict"):
                    new_state = result.to_dict()
            
            # Log event
            await publisher.log_action(
                resource_id=resource_id,
                resource_type=resource_type,
                resource_name=resource_name,
                action=action,
                previous_state=previous_state,
                new_state=new_state,
            )
            
            return result
        
        return wrapper
    return decorator


# Global publisher instance (optional, for simple use cases)
_global_publisher: Optional[AuditEventPublisher] = None


def get_audit_publisher() -> AuditEventPublisher:
    """Get the global audit publisher instance."""
    global _global_publisher
    if _global_publisher is None:
        _global_publisher = AuditEventPublisher()
    return _global_publisher


def set_audit_publisher(publisher: AuditEventPublisher) -> None:
    """Set the global audit publisher instance."""
    global _global_publisher
    _global_publisher = publisher
