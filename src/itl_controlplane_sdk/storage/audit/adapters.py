"""
Audit event adapters for different storage backends.

Implements the Adapter pattern for pluggable audit event storage:
- SQLAuditEventAdapter: PostgreSQL via SQLAlchemy
- RabbitMQAuditEventAdapter: Message queue for async processing
- CompositeAuditEventAdapter: Fan-out to multiple adapters
- InMemoryAuditEventAdapter: For testing
- NoOpAuditEventAdapter: Disabled audit logging
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, List, Optional, TYPE_CHECKING, Callable, Awaitable

from .models import AuditEvent, AuditEventQuery, AuditEventPage, AuditAction, ActorType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from aio_pika import Connection, Channel, Exchange

logger = logging.getLogger(__name__)


# ============================================================================
# Base Adapter (ABC)
# ============================================================================

class AuditEventAdapter(ABC):
    """
    Abstract base class for audit event adapters.
    
    All adapters must implement:
    - publish(): Store/send a single event
    - publish_batch(): Store/send multiple events efficiently
    - query(): Search for events (for backends that support querying)
    - initialize(): Setup connections/resources
    - shutdown(): Cleanup connections/resources
    
    Optional capabilities:
    - supports_query(): Whether the adapter supports querying
    - supports_batch(): Whether the adapter supports batch operations
    """
    
    @abstractmethod
    async def publish(self, event: AuditEvent) -> bool:
        """
        Publish a single audit event.
        
        Args:
            event: The audit event to publish
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    async def publish_batch(self, events: List[AuditEvent]) -> int:
        """
        Publish multiple audit events.
        
        Default implementation calls publish() for each event.
        Subclasses can override for more efficient batch operations.
        
        Args:
            events: List of events to publish
            
        Returns:
            Number of successfully published events
        """
        count = 0
        for event in events:
            if await self.publish(event):
                count += 1
        return count
    
    async def query(self, query: AuditEventQuery) -> AuditEventPage:
        """
        Query audit events (if supported).
        
        Args:
            query: Query parameters
            
        Returns:
            Paginated list of matching events
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support querying"
        )
    
    async def initialize(self) -> None:
        """
        Initialize the adapter (establish connections, etc.).
        
        Called once on application startup.
        """
        pass
    
    async def shutdown(self) -> None:
        """
        Shutdown the adapter (close connections, flush buffers, etc.).
        
        Called once on application shutdown.
        """
        pass
    
    @property
    def supports_query(self) -> bool:
        """Whether this adapter supports querying events."""
        return False
    
    @property
    def supports_batch(self) -> bool:
        """Whether this adapter has optimized batch operations."""
        return False


# ============================================================================
# SQL Adapter (PostgreSQL via SQLAlchemy)
# ============================================================================

class SQLAuditEventAdapter(AuditEventAdapter):
    """
    SQL adapter for storing audit events in PostgreSQL.
    
    Uses the AuditEventModel from the storage module for persistence.
    This adapter supports full CRUD and querying capabilities.
    
    Example:
        from itl_controlplane_sdk.storage.engine import SQLAlchemyStorageEngine
        
        engine = SQLAlchemyStorageEngine("postgresql+asyncpg://...")
        await engine.initialize()
        
        adapter = SQLAuditEventAdapter(engine)
        await adapter.publish(event)
    """
    
    def __init__(
        self,
        engine: Any,  # SQLAlchemyStorageEngine
        batch_size: int = 100,
    ):
        """
        Initialize SQL adapter.
        
        Args:
            engine: SQLAlchemyStorageEngine instance
            batch_size: Max events per batch insert
        """
        self._engine = engine
        self._batch_size = batch_size
    
    async def publish(self, event: AuditEvent) -> bool:
        """Store event in PostgreSQL."""
        try:
            from ..models import AuditEventModel
            
            async with self._engine.session() as session:
                model = AuditEventModel(
                    id=event.id,
                    resource_id=event.resource_id,
                    resource_type=event.resource_type,
                    resource_name=event.resource_name,
                    action=event.action.value,
                    actor_id=event.actor_id,
                    actor_type=event.actor_type.value,
                    actor_display_name=event.actor_display_name,
                    timestamp=event.timestamp,
                    previous_state=event.previous_state,
                    new_state=event.new_state,
                    change_summary=event.change_summary,
                    correlation_id=event.correlation_id,
                    request_id=event.request_id,
                    source_ip=event.source_ip,
                    user_agent=event.user_agent,
                    extra_data=event.extra_data or {},
                )
                session.add(model)
                await session.commit()
                logger.debug(f"Stored audit event {event.id} in SQL")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")
            return False
    
    async def publish_batch(self, events: List[AuditEvent]) -> int:
        """Store multiple events in PostgreSQL with bulk insert."""
        if not events:
            return 0
            
        try:
            from ..models import AuditEventModel
            
            count = 0
            async with self._engine.session() as session:
                # Process in chunks
                for i in range(0, len(events), self._batch_size):
                    chunk = events[i:i + self._batch_size]
                    models = [
                        AuditEventModel(
                            id=e.id,
                            resource_id=e.resource_id,
                            resource_type=e.resource_type,
                            resource_name=e.resource_name,
                            action=e.action.value,
                            actor_id=e.actor_id,
                            actor_type=e.actor_type.value,
                            actor_display_name=e.actor_display_name,
                            timestamp=e.timestamp,
                            previous_state=e.previous_state,
                            new_state=e.new_state,
                            change_summary=e.change_summary,
                            correlation_id=e.correlation_id,
                            request_id=e.request_id,
                            source_ip=e.source_ip,
                            user_agent=e.user_agent,
                            extra_data=e.extra_data or {},
                        )
                        for e in chunk
                    ]
                    session.add_all(models)
                    await session.commit()
                    count += len(models)
                    
            logger.debug(f"Stored {count} audit events in SQL")
            return count
            
        except Exception as e:
            logger.error(f"Failed to store audit events batch: {e}")
            return 0
    
    async def query(self, query: AuditEventQuery) -> AuditEventPage:
        """Query audit events from PostgreSQL."""
        from sqlalchemy import select, func, desc, asc
        from ..models import AuditEventModel
        
        async with self._engine.session() as session:
            # Build base query
            stmt = select(AuditEventModel)
            count_stmt = select(func.count(AuditEventModel.id))
            
            # Apply filters
            if query.resource_id:
                stmt = stmt.where(AuditEventModel.resource_id == query.resource_id)
                count_stmt = count_stmt.where(AuditEventModel.resource_id == query.resource_id)
            if query.resource_type:
                stmt = stmt.where(AuditEventModel.resource_type == query.resource_type)
                count_stmt = count_stmt.where(AuditEventModel.resource_type == query.resource_type)
            if query.resource_name:
                stmt = stmt.where(AuditEventModel.resource_name == query.resource_name)
                count_stmt = count_stmt.where(AuditEventModel.resource_name == query.resource_name)
            if query.action:
                stmt = stmt.where(AuditEventModel.action == query.action.value)
                count_stmt = count_stmt.where(AuditEventModel.action == query.action.value)
            if query.actor_id:
                stmt = stmt.where(AuditEventModel.actor_id == query.actor_id)
                count_stmt = count_stmt.where(AuditEventModel.actor_id == query.actor_id)
            if query.correlation_id:
                stmt = stmt.where(AuditEventModel.correlation_id == query.correlation_id)
                count_stmt = count_stmt.where(AuditEventModel.correlation_id == query.correlation_id)
            if query.start_time:
                stmt = stmt.where(AuditEventModel.timestamp >= query.start_time)
                count_stmt = count_stmt.where(AuditEventModel.timestamp >= query.start_time)
            if query.end_time:
                stmt = stmt.where(AuditEventModel.timestamp <= query.end_time)
                count_stmt = count_stmt.where(AuditEventModel.timestamp <= query.end_time)
            
            # Get total count
            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0
            
            # Apply sorting
            order_col = getattr(AuditEventModel, query.order_by, AuditEventModel.timestamp)
            if query.descending:
                stmt = stmt.order_by(desc(order_col))
            else:
                stmt = stmt.order_by(asc(order_col))
            
            # Apply pagination
            stmt = stmt.offset(query.offset).limit(query.limit)
            
            # Execute
            result = await session.execute(stmt)
            models = result.scalars().all()
            
            # Convert to Pydantic models
            events = [
                AuditEvent(
                    id=m.id,
                    resource_id=m.resource_id,
                    resource_type=m.resource_type,
                    resource_name=m.resource_name,
                    action=AuditAction(m.action),
                    actor_id=m.actor_id,
                    actor_type=ActorType(m.actor_type),
                    actor_display_name=m.actor_display_name,
                    timestamp=m.timestamp,
                    previous_state=m.previous_state,
                    new_state=m.new_state,
                    change_summary=m.change_summary,
                    correlation_id=m.correlation_id,
                    request_id=m.request_id,
                    source_ip=m.source_ip,
                    user_agent=m.user_agent,
                    extra_data=m.extra_data,
                )
                for m in models
            ]
            
            return AuditEventPage(
                events=events,
                total=total,
                limit=query.limit,
                offset=query.offset,
                has_more=query.offset + len(events) < total,
            )
    
    @property
    def supports_query(self) -> bool:
        return True
    
    @property
    def supports_batch(self) -> bool:
        return True


# ============================================================================
# RabbitMQ Adapter (Message Bus)
# ============================================================================

class RabbitMQAuditEventAdapter(AuditEventAdapter):
    """
    RabbitMQ adapter for publishing audit events to a message bus.
    
    Features:
    - Topic exchange for flexible routing (audit.itl.core.subscriptions.create)
    - Durable queues for reliability
    - Message persistence
    - Batch publishing support
    
    Message format:
    - Routing key: audit.{namespace}.{type}.{action}
    - Body: JSON-serialized AuditEvent
    - Headers: correlation_id, timestamp, content-type
    
    Example:
        adapter = RabbitMQAuditEventAdapter(
            url="amqp://guest:guest@rabbitmq:5672/",
            exchange="audit.events",
        )
        await adapter.initialize()
        await adapter.publish(event)
        
        # Consumers can bind to specific patterns:
        # - "audit.#" for all events
        # - "audit.itl.core.*" for all Core events
        # - "audit.itl.iam.users.create" for specific event type
    """
    
    def __init__(
        self,
        url: str = "amqp://guest:guest@localhost:5672/",
        exchange: str = "audit.events",
        exchange_type: str = "topic",
        durable: bool = True,
        delivery_mode: int = 2,  # Persistent
        confirm_publish: bool = True,
    ):
        """
        Initialize RabbitMQ adapter.
        
        Args:
            url: AMQP connection URL
            exchange: Exchange name for audit events
            exchange_type: Exchange type (topic, direct, fanout)
            durable: Whether the exchange is durable
            delivery_mode: 1=transient, 2=persistent
            confirm_publish: Enable publisher confirms
        """
        self._url = url
        self._exchange_name = exchange
        self._exchange_type = exchange_type
        self._durable = durable
        self._delivery_mode = delivery_mode
        self._confirm_publish = confirm_publish
        
        self._connection: Optional[Connection] = None
        self._channel: Optional[Channel] = None
        self._exchange: Optional[Exchange] = None
    
    async def initialize(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            import aio_pika
            
            self._connection = await aio_pika.connect_robust(self._url)
            self._channel = await self._connection.channel()
            
            if self._confirm_publish:
                await self._channel.set_qos(prefetch_count=10)
            
            # Declare exchange
            self._exchange = await self._channel.declare_exchange(
                self._exchange_name,
                type=aio_pika.ExchangeType[self._exchange_type.upper()],
                durable=self._durable,
            )
            
            logger.info(f"RabbitMQ audit adapter initialized: {self._exchange_name}")
            
        except ImportError:
            logger.error("aio-pika not installed. Install with: pip install aio-pika")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ adapter: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Close RabbitMQ connection."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQ audit adapter shutdown")
    
    async def publish(self, event: AuditEvent) -> bool:
        """Publish event to RabbitMQ exchange."""
        if not self._exchange:
            logger.error("RabbitMQ adapter not initialized")
            return False
            
        try:
            import aio_pika
            
            routing_key = event.to_routing_key()
            body = json.dumps(event.to_message_body()).encode()
            
            message = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode(self._delivery_mode),
                content_type="application/json",
                correlation_id=event.correlation_id or event.id,
                timestamp=event.timestamp,
                headers={
                    "event_id": event.id,
                    "resource_type": event.resource_type,
                    "action": event.action.value,
                    "actor_id": event.actor_id or "",
                },
            )
            
            await self._exchange.publish(message, routing_key=routing_key)
            logger.debug(f"Published audit event {event.id} to {routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish audit event to RabbitMQ: {e}")
            return False
    
    async def publish_batch(self, events: List[AuditEvent]) -> int:
        """Publish multiple events to RabbitMQ."""
        count = 0
        for event in events:
            if await self.publish(event):
                count += 1
        return count
    
    @property
    def supports_query(self) -> bool:
        return False  # RabbitMQ is write-only (consumers handle reads)


# ============================================================================
# Composite Adapter (Fan-out)
# ============================================================================

class CompositeAuditEventAdapter(AuditEventAdapter):
    """
    Composite adapter that publishes to multiple backends.
    
    Use cases:
    - Store in SQL for compliance queries + publish to RabbitMQ for real-time
    - Store in SQL + send to external SIEM (Splunk, Elastic, etc.)
    - Write to primary + backup for redundancy
    
    Error handling:
    - By default, continues even if some adapters fail
    - Can be configured to require all adapters to succeed
    
    Example:
        composite = CompositeAuditEventAdapter([
            SQLAuditEventAdapter(engine),
            RabbitMQAuditEventAdapter(url="amqp://..."),
        ])
        await composite.initialize()
        await composite.publish(event)
    """
    
    def __init__(
        self,
        adapters: List[AuditEventAdapter],
        require_all: bool = False,
        parallel: bool = True,
    ):
        """
        Initialize composite adapter.
        
        Args:
            adapters: List of adapters to publish to
            require_all: If True, fail if any adapter fails
            parallel: If True, publish to all adapters concurrently
        """
        self._adapters = adapters
        self._require_all = require_all
        self._parallel = parallel
    
    async def initialize(self) -> None:
        """Initialize all adapters."""
        if self._parallel:
            await asyncio.gather(
                *[a.initialize() for a in self._adapters],
                return_exceptions=True,
            )
        else:
            for adapter in self._adapters:
                await adapter.initialize()
    
    async def shutdown(self) -> None:
        """Shutdown all adapters."""
        if self._parallel:
            await asyncio.gather(
                *[a.shutdown() for a in self._adapters],
                return_exceptions=True,
            )
        else:
            for adapter in self._adapters:
                await adapter.shutdown()
    
    async def publish(self, event: AuditEvent) -> bool:
        """Publish to all adapters."""
        if self._parallel:
            results = await asyncio.gather(
                *[a.publish(event) for a in self._adapters],
                return_exceptions=True,
            )
            successes = sum(1 for r in results if r is True)
        else:
            successes = 0
            for adapter in self._adapters:
                try:
                    if await adapter.publish(event):
                        successes += 1
                except Exception as e:
                    logger.error(f"Adapter {adapter.__class__.__name__} failed: {e}")
        
        if self._require_all:
            return successes == len(self._adapters)
        return successes > 0
    
    async def publish_batch(self, events: List[AuditEvent]) -> int:
        """Publish batch to all adapters."""
        if self._parallel:
            results = await asyncio.gather(
                *[a.publish_batch(events) for a in self._adapters],
                return_exceptions=True,
            )
            # Return max successes from any adapter
            return max((r for r in results if isinstance(r, int)), default=0)
        else:
            max_count = 0
            for adapter in self._adapters:
                try:
                    count = await adapter.publish_batch(events)
                    max_count = max(max_count, count)
                except Exception as e:
                    logger.error(f"Adapter {adapter.__class__.__name__} batch failed: {e}")
            return max_count
    
    async def query(self, query: AuditEventQuery) -> AuditEventPage:
        """Query from first adapter that supports querying."""
        for adapter in self._adapters:
            if adapter.supports_query:
                return await adapter.query(query)
        raise NotImplementedError("No adapter supports querying")
    
    @property
    def supports_query(self) -> bool:
        return any(a.supports_query for a in self._adapters)
    
    @property
    def supports_batch(self) -> bool:
        return any(a.supports_batch for a in self._adapters)
    
    def add_adapter(self, adapter: AuditEventAdapter) -> None:
        """Add an adapter to the composite."""
        self._adapters.append(adapter)
    
    def remove_adapter(self, adapter: AuditEventAdapter) -> bool:
        """Remove an adapter from the composite."""
        try:
            self._adapters.remove(adapter)
            return True
        except ValueError:
            return False


# ============================================================================
# In-Memory Adapter (Testing)
# ============================================================================

class InMemoryAuditEventAdapter(AuditEventAdapter):
    """
    In-memory adapter for testing purposes.
    
    Stores all events in memory with full query support.
    NOT for production use.
    
    Example:
        adapter = InMemoryAuditEventAdapter()
        await adapter.publish(event)
        
        # Query events
        page = await adapter.query(AuditEventQuery(resource_type="ITL.Core/subscriptions"))
        
        # Get all events
        all_events = adapter.events
        
        # Clear events
        adapter.clear()
    """
    
    def __init__(self, max_events: int = 10000):
        """
        Initialize in-memory adapter.
        
        Args:
            max_events: Maximum events to store (oldest are evicted)
        """
        self._events: List[AuditEvent] = []
        self._max_events = max_events
        self._by_resource: dict[str, List[AuditEvent]] = defaultdict(list)
        self._by_actor: dict[str, List[AuditEvent]] = defaultdict(list)
        self._by_correlation: dict[str, List[AuditEvent]] = defaultdict(list)
    
    @property
    def events(self) -> List[AuditEvent]:
        """Get all stored events."""
        return self._events.copy()
    
    def clear(self) -> None:
        """Clear all stored events."""
        self._events.clear()
        self._by_resource.clear()
        self._by_actor.clear()
        self._by_correlation.clear()
    
    async def publish(self, event: AuditEvent) -> bool:
        """Store event in memory."""
        # Evict oldest if at capacity
        while len(self._events) >= self._max_events:
            old = self._events.pop(0)
            self._by_resource[old.resource_id].remove(old)
            if old.actor_id:
                self._by_actor[old.actor_id].remove(old)
            if old.correlation_id:
                self._by_correlation[old.correlation_id].remove(old)
        
        self._events.append(event)
        self._by_resource[event.resource_id].append(event)
        if event.actor_id:
            self._by_actor[event.actor_id].append(event)
        if event.correlation_id:
            self._by_correlation[event.correlation_id].append(event)
        
        return True
    
    async def query(self, query: AuditEventQuery) -> AuditEventPage:
        """Query events from memory."""
        # Start with all events or use index
        if query.resource_id:
            events = self._by_resource.get(query.resource_id, [])
        elif query.actor_id:
            events = self._by_actor.get(query.actor_id, [])
        elif query.correlation_id:
            events = self._by_correlation.get(query.correlation_id, [])
        else:
            events = self._events
        
        # Apply filters
        filtered = []
        for e in events:
            if query.resource_type and e.resource_type != query.resource_type:
                continue
            if query.resource_name and e.resource_name != query.resource_name:
                continue
            if query.action and e.action != query.action:
                continue
            if query.actor_type and e.actor_type != query.actor_type:
                continue
            if query.start_time and e.timestamp < query.start_time:
                continue
            if query.end_time and e.timestamp > query.end_time:
                continue
            filtered.append(e)
        
        # Sort
        reverse = query.descending
        if query.order_by == "timestamp":
            filtered.sort(key=lambda e: e.timestamp, reverse=reverse)
        elif query.order_by == "resource_id":
            filtered.sort(key=lambda e: e.resource_id, reverse=reverse)
        elif query.order_by == "action":
            filtered.sort(key=lambda e: e.action.value, reverse=reverse)
        
        # Paginate
        total = len(filtered)
        start = query.offset
        end = start + query.limit
        page_events = filtered[start:end]
        
        return AuditEventPage(
            events=page_events,
            total=total,
            limit=query.limit,
            offset=query.offset,
            has_more=end < total,
        )
    
    @property
    def supports_query(self) -> bool:
        return True
    
    @property
    def supports_batch(self) -> bool:
        return True


# ============================================================================
# NoOp Adapter (Disabled)
# ============================================================================

class NoOpAuditEventAdapter(AuditEventAdapter):
    """
    No-operation adapter that silently discards all events.
    
    Use when audit logging is disabled or during testing when
    you don't want to capture events.
    
    Example:
        # Disable audit logging in development
        if os.getenv("DISABLE_AUDIT", "false") == "true":
            adapter = NoOpAuditEventAdapter()
        else:
            adapter = SQLAuditEventAdapter(engine)
    """
    
    async def publish(self, event: AuditEvent) -> bool:
        """Discard event."""
        return True
    
    async def publish_batch(self, events: List[AuditEvent]) -> int:
        """Discard all events."""
        return len(events)
    
    @property
    def supports_query(self) -> bool:
        return False


# ============================================================================
# Factory Functions
# ============================================================================

async def create_audit_adapter(
    adapter_type: str,
    **kwargs,
) -> AuditEventAdapter:
    """
    Factory function to create audit adapters by type.
    
    Args:
        adapter_type: One of "sql", "rabbitmq", "memory", "noop"
        **kwargs: Adapter-specific configuration
        
    Returns:
        Configured and initialized adapter
        
    Example:
        adapter = await create_audit_adapter(
            "sql",
            engine=storage_engine,
        )
    """
    adapters = {
        "sql": SQLAuditEventAdapter,
        "rabbitmq": RabbitMQAuditEventAdapter,
        "memory": InMemoryAuditEventAdapter,
        "noop": NoOpAuditEventAdapter,
    }
    
    if adapter_type not in adapters:
        raise ValueError(f"Unknown adapter type: {adapter_type}")
    
    adapter = adapters[adapter_type](**kwargs)
    await adapter.initialize()
    return adapter


def create_composite_adapter(
    configs: List[dict],
    require_all: bool = False,
    parallel: bool = True,
) -> CompositeAuditEventAdapter:
    """
    Create a composite adapter from configuration.
    
    Args:
        configs: List of adapter configs, each with "type" and adapter-specific keys
        require_all: Whether all adapters must succeed
        parallel: Whether to publish concurrently
        
    Returns:
        Configured composite adapter (not yet initialized)
        
    Example:
        composite = create_composite_adapter([
            {"type": "sql", "engine": engine},
            {"type": "rabbitmq", "url": "amqp://..."},
        ])
        await composite.initialize()
    """
    adapters_map = {
        "sql": SQLAuditEventAdapter,
        "rabbitmq": RabbitMQAuditEventAdapter,
        "memory": InMemoryAuditEventAdapter,
        "noop": NoOpAuditEventAdapter,
    }
    
    adapters = []
    for config in configs:
        adapter_type = config.pop("type")
        if adapter_type not in adapters_map:
            raise ValueError(f"Unknown adapter type: {adapter_type}")
        adapters.append(adapters_map[adapter_type](**config))
    
    return CompositeAuditEventAdapter(
        adapters=adapters,
        require_all=require_all,
        parallel=parallel,
    )
