"""
Message Broker — abstract interface and in-memory implementation.

The ``MessageBroker`` ABC defines the contract that all broker backends
must implement. The ``InMemoryBroker`` is provided for development and
testing — it routes messages to subscribers within the same process.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MessageBroker(ABC):
    """
    Abstract message broker interface.

    All broker implementations (RabbitMQ, in-memory, etc.) must implement
    these five methods.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the message broker."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the message broker."""
        ...

    @abstractmethod
    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        routing_key: Optional[str] = None,
    ) -> bool:
        """Publish a message to a topic/exchange."""
        ...

    @abstractmethod
    async def subscribe(
        self,
        queue_name: str,
        topic: str,
        callback: Callable,
        routing_key: Optional[str] = None,
    ) -> bool:
        """Subscribe to a topic/queue with a callback handler."""
        ...

    @abstractmethod
    async def unsubscribe(self, queue_name: str) -> bool:
        """Unsubscribe from a queue."""
        ...


class InMemoryBroker(MessageBroker):
    """
    In-memory message broker for development and testing.

    Routes messages to subscribers within the same process. All state
    is lost when the process stops.
    """

    def __init__(self):
        self.topics: Dict[str, List[Dict[str, Any]]] = {}
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.connected = False

    async def connect(self) -> bool:
        self.connected = True
        logger.info("Connected to in-memory message broker")
        return True

    async def disconnect(self) -> None:
        self.connected = False
        logger.info("Disconnected from in-memory broker")

    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        routing_key: Optional[str] = None,
    ) -> bool:
        if not self.connected:
            return False

        message_with_meta = {
            "event": message.get("event", topic),
            "data": message.get("data", message),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": message.get("source", "unknown"),
            "trace_id": message.get("trace_id", ""),
            "routing_key": routing_key or topic,
        }

        if topic not in self.topics:
            self.topics[topic] = []
        self.topics[topic].append(message_with_meta)

        # Deliver to subscribers
        if topic in self.subscriptions:
            for callback in self.subscriptions[topic]:
                try:
                    await callback(message_with_meta)
                except Exception as e:
                    logger.error("Callback error: %s", e)

        logger.debug("Published to %s: %s", topic, message.get("event", "unknown"))
        return True

    async def subscribe(
        self,
        queue_name: str,
        topic: str,
        callback: Callable,
        routing_key: Optional[str] = None,
    ) -> bool:
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        self.subscriptions[topic].append(callback)
        logger.info("Subscribed %s to %s", queue_name, topic)
        return True

    async def unsubscribe(self, queue_name: str) -> bool:
        logger.info("Unsubscribed %s", queue_name)
        return True
