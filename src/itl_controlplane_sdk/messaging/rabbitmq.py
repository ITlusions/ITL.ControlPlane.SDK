"""
RabbitMQ message broker implementation.

Requires the ``aio_pika`` package — install with::

    pip install itl-controlplane-sdk[messaging-rabbitmq]
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from .broker import MessageBroker

logger = logging.getLogger(__name__)


class RabbitMQBroker(MessageBroker):
    """
    RabbitMQ message broker implementation using ``aio_pika``.

    Configuration via environment variables:

    - ``RABBITMQ_URL`` — AMQP connection URL
      (default: ``amqp://guest:guest@localhost:5672/``)
    """

    def __init__(self):
        self.url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.connection = None
        self.channel = None
        self.connected = False
        self.subscriptions: Dict[str, Any] = {}

    async def connect(self) -> bool:
        """Connect to RabbitMQ."""
        try:
            import aio_pika

            self.connection = await aio_pika.connect_robust(self.url)
            self.channel = await self.connection.channel()
            self.connected = True
            logger.info("Connected to RabbitMQ at %s", self.url)
            return True
        except Exception as e:
            logger.error("Failed to connect to RabbitMQ: %s", e)
            self.connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        if self.connection:
            await self.connection.close()
            self.connected = False
            logger.info("Disconnected from RabbitMQ")

    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        routing_key: Optional[str] = None,
    ) -> bool:
        """Publish message to a RabbitMQ exchange (topic)."""
        if not self.connected or not self.channel:
            logger.warning("RabbitMQ not connected, message not published")
            return False

        try:
            import aio_pika

            exchange = await self.channel.declare_exchange(
                name=topic,
                type=aio_pika.ExchangeType.TOPIC,
                durable=True,
            )

            message_body = {
                "event": message.get("event", topic),
                "data": message.get("data", message),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": message.get("source", "unknown"),
                "trace_id": message.get("trace_id", ""),
                "correlation_id": message.get("correlation_id", ""),
            }

            amqp_message = aio_pika.Message(
                body=json.dumps(message_body).encode(),
                content_type="application/json",
                content_encoding="utf-8",
                timestamp=datetime.now(timezone.utc),
            )

            routing_key = routing_key or topic
            await exchange.publish(amqp_message, routing_key=routing_key)
            logger.info("Published message to %s (routing_key: %s)", topic, routing_key)
            return True

        except Exception as e:
            logger.error("Failed to publish message to %s: %s", topic, e)
            return False

    async def subscribe(
        self,
        queue_name: str,
        topic: str,
        callback: Callable,
        routing_key: Optional[str] = None,
    ) -> bool:
        """Subscribe to a RabbitMQ queue with a callback."""
        if not self.connected or not self.channel:
            logger.error("RabbitMQ not connected")
            return False

        try:
            import aio_pika

            exchange = await self.channel.declare_exchange(
                name=topic,
                type=aio_pika.ExchangeType.TOPIC,
                durable=True,
            )

            queue = await self.channel.declare_queue(
                name=queue_name,
                durable=True,
            )

            routing_key = routing_key or topic
            await queue.bind(exchange, routing_key=routing_key)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            body = json.loads(message.body.decode())
                            await callback(body)
                        except Exception as e:
                            logger.error("Error processing message: %s", e)

            self.subscriptions[queue_name] = {
                "topic": topic,
                "routing_key": routing_key,
                "callback": callback,
            }
            logger.info("Subscribed to %s via queue %s", topic, queue_name)
            return True

        except Exception as e:
            logger.error("Failed to subscribe to %s: %s", topic, e)
            return False

    async def unsubscribe(self, queue_name: str) -> bool:
        """Unsubscribe from a queue."""
        try:
            if queue_name in self.subscriptions:
                del self.subscriptions[queue_name]
            logger.info("Unsubscribed from %s", queue_name)
            return True
        except Exception as e:
            logger.error("Failed to unsubscribe: %s", e)
            return False
