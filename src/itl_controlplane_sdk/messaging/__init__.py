"""
Messaging Module for ITL ControlPlane SDK.

Provides:
- **Event Messaging** (MessageBroker): Pub/sub event streaming via RabbitMQ
- **Service Bus** (GenericServiceBusProvider): Request/response message patterns for providers

Install::

    pip install itl-controlplane-sdk[messaging]          # in-memory only
    pip install itl-controlplane-sdk[messaging-rabbitmq]  # + RabbitMQ

Examples::

    # Event-based messaging
    from itl_controlplane_sdk.messaging import MessageBrokerManager

    broker = MessageBrokerManager()
    await broker.initialize()
    await broker.publish_event(
        "resource.created",
        {"id": "sub-123", "type": "subscription"},
        source="core-provider",
    )

    # Service bus provider modes
    from itl_controlplane_sdk.messaging.servicebus import ProviderModeManager
    
    manager = ProviderModeManager(
        provider=my_provider,
        provider_namespace="ITL.Compute",
        app=fastapi_app,
        mode="hybrid"  # "api", "servicebus", or "hybrid"
    )
    await manager.run()
"""

from .broker import MessageBroker, InMemoryBroker
from .manager import MessageBrokerManager
from .servicebus import (
    GenericServiceBusProvider,
    ProviderModeManager,
    ProviderMode,
)

__all__ = [
    # Event messaging
    "MessageBroker",
    "InMemoryBroker",
    "MessageBrokerManager",
    # Service bus
    "GenericServiceBusProvider",
    "ProviderModeManager",
    "ProviderMode",
]

# Conditional import — only available if aio_pika is installed
