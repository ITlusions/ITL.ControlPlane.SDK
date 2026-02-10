"""
Messaging Module for ITL ControlPlane SDK.

Provides an event-driven messaging abstraction for resource providers.
Supports RabbitMQ for production and an in-memory broker for
development/testing.

Install::

    pip install itl-controlplane-sdk[messaging]          # in-memory only
    pip install itl-controlplane-sdk[messaging-rabbitmq]  # + RabbitMQ

Example::

    from itl_controlplane_sdk.messaging import MessageBrokerManager

    broker = MessageBrokerManager()
    await broker.initialize()

    await broker.publish_event(
        "resource.created",
        {"id": "sub-123", "type": "subscription"},
        source="core-provider",
    )
"""

from .broker import MessageBroker, InMemoryBroker
from .manager import MessageBrokerManager

__all__ = [
    "MessageBroker",
    "InMemoryBroker",
    "MessageBrokerManager",
]

# Conditional import — only available if aio_pika is installed
try:
    from .rabbitmq import RabbitMQBroker
    __all__.append("RabbitMQBroker")
except ImportError:
    pass
