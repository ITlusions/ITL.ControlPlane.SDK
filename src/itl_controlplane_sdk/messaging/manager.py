"""
MessageBrokerManager — lifecycle management for message brokers.

Provides a simple interface for initializing, publishing events, and
subscribing to events. Reads configuration from environment variables:

- ``MESSAGE_BROKER_ENABLED`` — "true" (default) or "false"
- ``MESSAGE_BROKER_TYPE`` — "memory" (default) or "rabbitmq"
"""

import logging
import os
from typing import Any, Callable, Dict, Optional

from .broker import MessageBroker, InMemoryBroker

logger = logging.getLogger(__name__)


class MessageBrokerManager:
    """
    Manages message broker connection and operations.

    Example::

        manager = MessageBrokerManager()
        await manager.initialize()

        await manager.publish_event(
            "subscription.created",
            {"subscription_id": "sub-123"},
            source="core-provider",
        )

        await manager.shutdown()
    """

    def __init__(self):
        self.broker: Optional[MessageBroker] = None
        self.enabled = os.getenv("MESSAGE_BROKER_ENABLED", "true").lower() == "true"
        self.broker_type = os.getenv("MESSAGE_BROKER_TYPE", "memory")

    async def initialize(self) -> None:
        """Initialize the message broker based on environment configuration."""
        if not self.enabled:
            logger.info("Message broker is disabled")
            return

        try:
            if self.broker_type == "rabbitmq":
                from .rabbitmq import RabbitMQBroker
                self.broker = RabbitMQBroker()
                logger.info("Using RabbitMQ message broker")
            else:
                self.broker = InMemoryBroker()
                logger.info("Using in-memory message broker")

            connected = await self.broker.connect()
            if connected:
                logger.info("Message broker initialized (%s)", self.broker_type)
            else:
                logger.error("Failed to initialize message broker")
                self.enabled = False

        except Exception as e:
            logger.error("Error initializing message broker: %s", e)
            self.enabled = False

    async def shutdown(self) -> None:
        """Shut down the message broker connection."""
        if self.broker:
            await self.broker.disconnect()

    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str = "system",
        trace_id: str = "",
        correlation_id: str = "",
    ) -> bool:
        """
        Publish an event to the broker.

        Returns True if published successfully, True if broker is disabled
        (silently skips), or False on error.
        """
        if not self.enabled or not self.broker:
            return True  # Silently skip if disabled

        try:
            message = {
                "event": event_type,
                "data": data,
                "source": source,
                "trace_id": trace_id,
                "correlation_id": correlation_id,
            }

            topic = f"events.{event_type}"
            success = await self.broker.publish(topic, message)

            if success:
                logger.info("Published event: %s", event_type)
            return success

        except Exception as e:
            logger.error("Error publishing event: %s", e)
            return False

    async def subscribe_to_events(
        self,
        event_pattern: str,
        queue_name: str,
        callback: Callable,
    ) -> bool:
        """Subscribe to events matching a pattern."""
        if not self.enabled or not self.broker:
            return False

        try:
            topic = f"events.{event_pattern}"
            return await self.broker.subscribe(queue_name, topic, callback)
        except Exception as e:
            logger.error("Error subscribing to events: %s", e)
            return False
