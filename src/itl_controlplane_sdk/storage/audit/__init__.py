"""
Audit Event Adapter System for ITL ControlPlane SDK.

This module provides a pluggable adapter pattern for storing and publishing
audit events to various backends:

- **SQL** (PostgreSQL via SQLAlchemy) - direct database storage
- **RabbitMQ** - async message bus for SIEM/analytics pipelines
- **Kafka** - high-throughput event streaming (optional)
- **Composite** - fan-out to multiple backends simultaneously

Architecture:
```
    AuditEvent (Pydantic model)
        ↓
    AuditEventPublisher (facade)
        ↓
┌─────────────────────────────────────────┐
│         AuditEventAdapter (ABC)          │
├─────────────────────────────────────────┤
│ SQLAuditEventAdapter                    │ → PostgreSQL
│ RabbitMQAuditEventAdapter               │ → RabbitMQ
│ KafkaAuditEventAdapter                  │ → Kafka (optional)
│ CompositeAuditEventAdapter              │ → Fan-out to multiple
│ InMemoryAuditEventAdapter               │ → Testing
└─────────────────────────────────────────┘
```

Usage:
    from itl_controlplane_sdk.storage.audit import (
        AuditEvent,
        AuditEventPublisher,
        SQLAuditEventAdapter,
        RabbitMQAuditEventAdapter,
        CompositeAuditEventAdapter,
        AuditAction,
        ActorType,
    )
    
    # Create adapters
    sql_adapter = SQLAuditEventAdapter(engine)
    rabbit_adapter = RabbitMQAuditEventAdapter(
        url="amqp://guest:guest@rabbitmq:5672/",
        exchange="audit.events",
    )
    
    # Composite for fan-out
    composite = CompositeAuditEventAdapter([sql_adapter, rabbit_adapter])
    
    # Publisher facade
    publisher = AuditEventPublisher(adapter=composite)
    
    # Log events
    await publisher.log_create(
        resource_id="/subscriptions/sub-123",
        resource_type="ITL.Core/subscriptions",
        resource_name="my-subscription",
        actor_id="user-456",
        new_state={"name": "my-subscription"},
    )
"""

from .models import (
    AuditEvent,
    AuditAction,
    ActorType,
    AuditEventQuery,
    AuditEventPage,
)

from .adapters import (
    AuditEventAdapter,
    SQLAuditEventAdapter,
    RabbitMQAuditEventAdapter,
    CompositeAuditEventAdapter,
    InMemoryAuditEventAdapter,
    NoOpAuditEventAdapter,
)

from .publisher import AuditEventPublisher, AuditContext

from .integration import (
    AuditedRepository,
    AuditedStorageEngine,
    audit_operation,
)

from .middleware import (
    AuditContextMiddleware,
    get_audit_context_from_request,
)

from .consumers import (
    AuditEventHandler,
    FilteringHandler,
    FanoutHandler,
    ElasticSearchForwarder,
    SplunkForwarder,
    WebhookForwarder,
    ClickHouseForwarder,
    SlackAlertHandler,
    RabbitMQConsumer,
    run_consumer,
)

__all__ = [
    # Models
    "AuditEvent",
    "AuditAction",
    "ActorType",
    "AuditEventQuery",
    "AuditEventPage",
    # Adapters
    "AuditEventAdapter",
    "SQLAuditEventAdapter",
    "RabbitMQAuditEventAdapter",
    "CompositeAuditEventAdapter",
    "InMemoryAuditEventAdapter",
    "NoOpAuditEventAdapter",
    # Publisher & Context
    "AuditEventPublisher",
    "AuditContext",
    # Repository Integration
    "AuditedRepository",
    "AuditedStorageEngine",
    "audit_operation",
    # Middleware
    "AuditContextMiddleware",
    "get_audit_context_from_request",
    # Consumers & Handlers
    "AuditEventHandler",
    "FilteringHandler",
    "FanoutHandler",
    "ElasticSearchForwarder",
    "SplunkForwarder",
    "WebhookForwarder",
    "ClickHouseForwarder",
    "SlackAlertHandler",
    "RabbitMQConsumer",
    "run_consumer",
]
