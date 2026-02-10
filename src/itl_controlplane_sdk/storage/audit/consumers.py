"""
Audit Event Consumer Framework.

Provides base consumers for processing audit events from message queues
and forwarding to SIEM/analytics systems.

Architecture:
```
    RabbitMQ (audit.events exchange)
          ↓
    AuditEventConsumer (ABC)
          ↓
┌─────────────────────────────────────────┐
│ SIEMForwarder        → Elastic/Splunk   │
│ AnalyticsConsumer    → ClickHouse/TimescaleDB │
│ AlertingConsumer     → PagerDuty/Slack  │
│ ComplianceLogger     → S3/Azure Blob    │
└─────────────────────────────────────────┘
```

Usage::

    from itl_controlplane_sdk.storage.audit.consumers import (
        RabbitMQConsumer,
        ElasticSearchForwarder,
        SplunkForwarder,
        WebhookForwarder,
    )
    
    # Create Elasticsearch forwarder
    forwarder = ElasticSearchForwarder(
        hosts=["http://elasticsearch:9200"],
        index_prefix="audit-events",
    )
    
    # Create RabbitMQ consumer
    consumer = RabbitMQConsumer(
        url="amqp://guest:guest@rabbitmq:5672/",
        exchange="audit.events",
        queue="siem-forwarder",
        handler=forwarder,
    )
    
    # Run consumer (blocks)
    await consumer.run()
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .models import AuditEvent

logger = logging.getLogger(__name__)


# ===================================================================
# Abstract Event Handlers
# ===================================================================

class AuditEventHandler(ABC):
    """Abstract base class for handling audit events."""
    
    @abstractmethod
    async def handle(self, event: AuditEvent) -> bool:
        """
        Process a single audit event.
        
        Args:
            event: The audit event to process
            
        Returns:
            True if successfully processed, False otherwise
        """
        pass
    
    async def handle_batch(self, events: List[AuditEvent]) -> int:
        """
        Process a batch of events.
        
        Default implementation processes one at a time.
        Override for bulk operations.
        
        Returns:
            Number of successfully processed events
        """
        success_count = 0
        for event in events:
            try:
                if await self.handle(event):
                    success_count += 1
            except Exception as e:
                logger.error("Failed to handle event %s: %s", event.id, e)
        return success_count
    
    async def initialize(self):
        """Initialize handler resources (connections, etc.)."""
        pass
    
    async def shutdown(self):
        """Clean up handler resources."""
        pass


class FilteringHandler(AuditEventHandler):
    """
    Handler wrapper that filters events before forwarding.
    
    Example::
    
        # Only forward DELETE events
        handler = FilteringHandler(
            inner_handler=elasticsearch_forwarder,
            filter_fn=lambda e: e.action == AuditAction.DELETE
        )
    """
    
    def __init__(
        self,
        inner_handler: AuditEventHandler,
        filter_fn: Callable[[AuditEvent], bool],
    ):
        self._inner = inner_handler
        self._filter = filter_fn
    
    async def handle(self, event: AuditEvent) -> bool:
        if self._filter(event):
            return await self._inner.handle(event)
        return True  # Filtered out, not an error
    
    async def initialize(self):
        await self._inner.initialize()
    
    async def shutdown(self):
        await self._inner.shutdown()


class FanoutHandler(AuditEventHandler):
    """
    Handler that forwards to multiple downstream handlers.
    
    Example::
    
        handler = FanoutHandler([
            elasticsearch_forwarder,
            splunk_forwarder,
            compliance_logger,
        ])
    """
    
    def __init__(self, handlers: List[AuditEventHandler]):
        self._handlers = handlers
    
    async def handle(self, event: AuditEvent) -> bool:
        results = await asyncio.gather(
            *[h.handle(event) for h in self._handlers],
            return_exceptions=True,
        )
        # Success if at least one succeeded
        return any(r is True for r in results)
    
    async def initialize(self):
        await asyncio.gather(*[h.initialize() for h in self._handlers])
    
    async def shutdown(self):
        await asyncio.gather(*[h.shutdown() for h in self._handlers])


# ===================================================================
# Concrete Handlers — SIEM & Analytics
# ===================================================================

class ElasticSearchForwarder(AuditEventHandler):
    """
    Forward audit events to Elasticsearch.
    
    Creates daily indices: {prefix}-YYYY.MM.DD
    
    Args:
        hosts: List of Elasticsearch hosts
        index_prefix: Prefix for index names (default: "audit-events")
        api_key: Optional API key for authentication
        username: Optional username for basic auth
        password: Optional password for basic auth
        verify_certs: Whether to verify TLS certificates
    """
    
    def __init__(
        self,
        hosts: List[str],
        index_prefix: str = "audit-events",
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_certs: bool = True,
    ):
        self.hosts = hosts
        self.index_prefix = index_prefix
        self.api_key = api_key
        self.username = username
        self.password = password
        self.verify_certs = verify_certs
        self._client = None
    
    async def initialize(self):
        """Initialize Elasticsearch async client."""
        try:
            from elasticsearch import AsyncElasticsearch
        except ImportError:
            raise ImportError(
                "elasticsearch package required. Install with: pip install elasticsearch[async]"
            )
        
        auth_kwargs = {}
        if self.api_key:
            auth_kwargs["api_key"] = self.api_key
        elif self.username and self.password:
            auth_kwargs["basic_auth"] = (self.username, self.password)
        
        self._client = AsyncElasticsearch(
            hosts=self.hosts,
            verify_certs=self.verify_certs,
            **auth_kwargs,
        )
        
        # Create index template for proper mappings
        await self._create_index_template()
    
    async def _create_index_template(self):
        """Create index template for audit events."""
        template = {
            "index_patterns": [f"{self.index_prefix}-*"],
            "priority": 100,
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "resource_id": {"type": "keyword"},
                        "resource_type": {"type": "keyword"},
                        "resource_name": {"type": "keyword"},
                        "action": {"type": "keyword"},
                        "actor_id": {"type": "keyword"},
                        "actor_type": {"type": "keyword"},
                        "actor_display_name": {"type": "text"},
                        "timestamp": {"type": "date"},
                        "previous_state": {"type": "object", "enabled": False},
                        "new_state": {"type": "object", "enabled": False},
                        "change_summary": {"type": "text"},
                        "correlation_id": {"type": "keyword"},
                        "request_id": {"type": "keyword"},
                        "source_ip": {"type": "ip"},
                        "user_agent": {"type": "text"},
                        "extra_data": {"type": "object", "enabled": False},
                    }
                }
            }
        }
        
        try:
            await self._client.indices.put_index_template(
                name=f"{self.index_prefix}-template",
                body=template,
            )
        except Exception as e:
            logger.warning("Failed to create index template: %s", e)
    
    async def handle(self, event: AuditEvent) -> bool:
        """Index a single audit event."""
        if not self._client:
            return False
        
        # Daily index
        date_str = event.timestamp.strftime("%Y.%m.%d")
        index = f"{self.index_prefix}-{date_str}"
        
        doc = event.model_dump(mode="json")
        
        try:
            await self._client.index(index=index, id=event.id, document=doc)
            return True
        except Exception as e:
            logger.error("Failed to index event %s: %s", event.id, e)
            return False
    
    async def handle_batch(self, events: List[AuditEvent]) -> int:
        """Bulk index events."""
        if not self._client or not events:
            return 0
        
        operations = []
        for event in events:
            date_str = event.timestamp.strftime("%Y.%m.%d")
            index = f"{self.index_prefix}-{date_str}"
            
            operations.append({"index": {"_index": index, "_id": event.id}})
            operations.append(event.model_dump(mode="json"))
        
        try:
            response = await self._client.bulk(operations=operations)
            if response.get("errors"):
                error_count = sum(1 for item in response["items"] if "error" in item.get("index", {}))
                return len(events) - error_count
            return len(events)
        except Exception as e:
            logger.error("Bulk index failed: %s", e)
            return 0
    
    async def shutdown(self):
        """Close Elasticsearch client."""
        if self._client:
            await self._client.close()
            self._client = None


class SplunkForwarder(AuditEventHandler):
    """
    Forward audit events to Splunk via HTTP Event Collector (HEC).
    
    Args:
        hec_url: Splunk HEC endpoint (e.g., https://splunk:8088/services/collector)
        token: HEC authentication token
        index: Splunk index name
        source: Source identifier
        sourcetype: Sourcetype for events (default: itl:audit:event)
        verify_ssl: Whether to verify TLS certificates
    """
    
    def __init__(
        self,
        hec_url: str,
        token: str,
        index: str = "main",
        source: str = "itl-controlplane",
        sourcetype: str = "itl:audit:event",
        verify_ssl: bool = True,
    ):
        self.hec_url = hec_url.rstrip("/")
        self.token = token
        self.index = index
        self.source = source
        self.sourcetype = sourcetype
        self.verify_ssl = verify_ssl
        self._session = None
    
    async def initialize(self):
        """Initialize HTTP session."""
        import httpx
        self._session = httpx.AsyncClient(
            verify=self.verify_ssl,
            headers={
                "Authorization": f"Splunk {self.token}",
                "Content-Type": "application/json",
            },
        )
    
    async def handle(self, event: AuditEvent) -> bool:
        """Send a single event to Splunk HEC."""
        if not self._session:
            return False
        
        payload = {
            "time": event.timestamp.timestamp(),
            "host": "itl-controlplane",
            "source": self.source,
            "sourcetype": self.sourcetype,
            "index": self.index,
            "event": event.model_dump(mode="json"),
        }
        
        try:
            response = await self._session.post(
                f"{self.hec_url}/services/collector/event",
                json=payload,
            )
            if response.status_code == 200:
                return True
            logger.error("Splunk HEC returned %d: %s", response.status_code, response.text)
            return False
        except Exception as e:
            logger.error("Failed to send event to Splunk: %s", e)
            return False
    
    async def handle_batch(self, events: List[AuditEvent]) -> int:
        """Batch send events to Splunk HEC."""
        if not self._session or not events:
            return 0
        
        # Splunk HEC accepts newline-delimited JSON
        payload = "\n".join(
            json.dumps({
                "time": event.timestamp.timestamp(),
                "host": "itl-controlplane",
                "source": self.source,
                "sourcetype": self.sourcetype,
                "index": self.index,
                "event": event.model_dump(mode="json"),
            })
            for event in events
        )
        
        try:
            response = await self._session.post(
                f"{self.hec_url}/services/collector/event",
                content=payload,
            )
            if response.status_code == 200:
                return len(events)
            logger.error("Splunk HEC batch returned %d", response.status_code)
            return 0
        except Exception as e:
            logger.error("Failed to batch send to Splunk: %s", e)
            return 0
    
    async def shutdown(self):
        """Close HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None


class WebhookForwarder(AuditEventHandler):
    """
    Forward audit events to a webhook endpoint.
    
    Useful for:
    - Custom SIEM integrations
    - Alerting systems (PagerDuty, OpsGenie, Slack)
    - Compliance logging services
    
    Args:
        url: Webhook URL
        headers: Optional additional headers
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify TLS certificates
        transform_fn: Optional function to transform events before sending
    """
    
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        verify_ssl: bool = True,
        transform_fn: Optional[Callable[[AuditEvent], Dict[str, Any]]] = None,
    ):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.transform_fn = transform_fn
        self._session = None
    
    async def initialize(self):
        """Initialize HTTP session."""
        import httpx
        self._session = httpx.AsyncClient(
            verify=self.verify_ssl,
            timeout=self.timeout,
            headers={
                "Content-Type": "application/json",
                **self.headers,
            },
        )
    
    async def handle(self, event: AuditEvent) -> bool:
        """Send event to webhook."""
        if not self._session:
            return False
        
        payload = (
            self.transform_fn(event)
            if self.transform_fn
            else event.model_dump(mode="json")
        )
        
        try:
            response = await self._session.post(self.url, json=payload)
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error("Webhook failed: %s", e)
            return False
    
    async def shutdown(self):
        """Close HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None


class ClickHouseForwarder(AuditEventHandler):
    """
    Forward audit events to ClickHouse for analytics.
    
    Creates an optimized table for time-series analytics:
    - Partitioned by month
    - Ordered by (resource_type, action, timestamp)
    - LowCardinality columns for string optimization
    
    Args:
        host: ClickHouse host
        port: ClickHouse HTTP port (default: 8123)
        database: Database name
        table: Table name (default: audit_events)
        username: Optional username
        password: Optional password
    """
    
    def __init__(
        self,
        host: str,
        port: int = 8123,
        database: str = "default",
        table: str = "audit_events",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.table = table
        self.username = username
        self.password = password
        self._client = None
    
    async def initialize(self):
        """Initialize ClickHouse connection and create table."""
        try:
            import aiochclient
        except ImportError:
            raise ImportError(
                "aiochclient package required. Install with: pip install aiochclient"
            )
        
        import httpx
        self._http_session = httpx.AsyncClient()
        self._client = aiochclient.ChClient(
            self._http_session,
            url=f"http://{self.host}:{self.port}",
            database=self.database,
            user=self.username,
            password=self.password,
        )
        
        # Create table if not exists
        await self._create_table()
    
    async def _create_table(self):
        """Create ClickHouse table with optimized schema."""
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.{self.table} (
            id String,
            resource_id String,
            resource_type LowCardinality(String),
            resource_name String,
            action LowCardinality(String),
            actor_id Nullable(String),
            actor_type LowCardinality(String),
            actor_display_name Nullable(String),
            timestamp DateTime64(3, 'UTC'),
            previous_state Nullable(String),
            new_state Nullable(String),
            change_summary Nullable(String),
            correlation_id Nullable(String),
            request_id Nullable(String),
            source_ip Nullable(IPv4),
            user_agent Nullable(String),
            extra_data Nullable(String)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (resource_type, action, timestamp)
        TTL timestamp + INTERVAL 1 YEAR
        """
        
        try:
            await self._client.execute(create_sql)
        except Exception as e:
            logger.warning("Failed to create ClickHouse table: %s", e)
    
    async def handle(self, event: AuditEvent) -> bool:
        """Insert a single event."""
        if not self._client:
            return False
        
        try:
            await self._client.execute(
                f"INSERT INTO {self.database}.{self.table} VALUES",
                self._event_to_row(event),
            )
            return True
        except Exception as e:
            logger.error("ClickHouse insert failed: %s", e)
            return False
    
    async def handle_batch(self, events: List[AuditEvent]) -> int:
        """Bulk insert events."""
        if not self._client or not events:
            return 0
        
        rows = [self._event_to_row(event) for event in events]
        
        try:
            await self._client.execute(
                f"INSERT INTO {self.database}.{self.table} VALUES",
                *rows,
            )
            return len(events)
        except Exception as e:
            logger.error("ClickHouse bulk insert failed: %s", e)
            return 0
    
    def _event_to_row(self, event: AuditEvent) -> tuple:
        """Convert event to ClickHouse row."""
        return (
            event.id,
            event.resource_id,
            event.resource_type,
            event.resource_name,
            event.action.value,
            event.actor_id,
            event.actor_type.value,
            event.actor_display_name,
            event.timestamp,
            json.dumps(event.previous_state) if event.previous_state else None,
            json.dumps(event.new_state) if event.new_state else None,
            event.change_summary,
            event.correlation_id,
            event.request_id,
            event.source_ip,
            event.user_agent,
            json.dumps(event.extra_data) if event.extra_data else None,
        )
    
    async def shutdown(self):
        """Close ClickHouse connection."""
        if self._http_session:
            await self._http_session.aclose()
            self._http_session = None
            self._client = None


class SlackAlertHandler(AuditEventHandler):
    """
    Send audit event alerts to Slack.
    
    Useful for alerting on specific events (e.g., DELETE operations,
    privilege escalations, policy violations).
    
    Args:
        webhook_url: Slack incoming webhook URL
        channel: Optional channel override
        username: Bot username (default: ITL Audit)
        icon_emoji: Bot icon (default: :shield:)
    """
    
    def __init__(
        self,
        webhook_url: str,
        channel: Optional[str] = None,
        username: str = "ITL Audit",
        icon_emoji: str = ":shield:",
    ):
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji
        self._session = None
    
    async def initialize(self):
        """Initialize HTTP session."""
        import httpx
        self._session = httpx.AsyncClient()
    
    async def handle(self, event: AuditEvent) -> bool:
        """Send Slack notification."""
        if not self._session:
            return False
        
        # Build Slack message
        color = self._action_color(event.action.value)
        
        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "title": f"{event.action.value}: {event.resource_type}",
                    "title_link": None,
                    "text": f"Resource: `{event.resource_name}`",
                    "fields": [
                        {
                            "title": "Resource ID",
                            "value": f"`{event.resource_id}`",
                            "short": False,
                        },
                        {
                            "title": "Actor",
                            "value": event.actor_display_name or event.actor_id or "Unknown",
                            "short": True,
                        },
                        {
                            "title": "Actor Type",
                            "value": event.actor_type.value,
                            "short": True,
                        },
                        {
                            "title": "Timestamp",
                            "value": event.timestamp.isoformat(),
                            "short": True,
                        },
                        {
                            "title": "Source IP",
                            "value": event.source_ip or "N/A",
                            "short": True,
                        },
                    ],
                    "footer": f"Correlation ID: {event.correlation_id or 'N/A'}",
                    "ts": int(event.timestamp.timestamp()),
                }
            ],
        }
        
        if self.channel:
            payload["channel"] = self.channel
        
        if event.change_summary:
            payload["attachments"][0]["fields"].append({
                "title": "Changes",
                "value": event.change_summary,
                "short": False,
            })
        
        try:
            response = await self._session.post(self.webhook_url, json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error("Slack notification failed: %s", e)
            return False
    
    def _action_color(self, action: str) -> str:
        """Get color for action type."""
        colors = {
            "CREATE": "#36a64f",    # Green
            "UPDATE": "#2196f3",    # Blue
            "DELETE": "#ff5252",    # Red
            "ENABLE": "#4caf50",    # Green
            "DISABLE": "#ff9800",   # Orange
            "ASSIGN": "#9c27b0",    # Purple
            "UNASSIGN": "#e91e63",  # Pink
        }
        return colors.get(action, "#607d8b")  # Grey default
    
    async def shutdown(self):
        """Close HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None


# ===================================================================
# RabbitMQ Consumer
# ===================================================================

class RabbitMQConsumer:
    """
    RabbitMQ consumer for audit events.
    
    Subscribes to the audit event exchange and processes events
    using the provided handler.
    
    Args:
        url: AMQP connection URL
        exchange: Exchange name (default: audit.events)
        queue: Queue name (default: audit-consumer)
        routing_key: Routing key pattern (default: # for all)
        handler: AuditEventHandler for processing events
        prefetch_count: Number of messages to prefetch (default: 10)
    
    Usage::
    
        consumer = RabbitMQConsumer(
            url="amqp://guest:guest@localhost:5672/",
            handler=ElasticSearchForwarder(hosts=["http://localhost:9200"]),
        )
        
        # Run forever (blocks)
        await consumer.run()
        
        # Or run with graceful shutdown
        async def main():
            consumer = RabbitMQConsumer(...)
            task = asyncio.create_task(consumer.run())
            
            # On shutdown signal
            await consumer.stop()
            await task
    """
    
    def __init__(
        self,
        url: str,
        handler: AuditEventHandler,
        exchange: str = "audit.events",
        queue: str = "audit-consumer",
        routing_key: str = "#",
        prefetch_count: int = 10,
    ):
        self.url = url
        self.handler = handler
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.prefetch_count = prefetch_count
        
        self._connection = None
        self._channel = None
        self._running = False
    
    async def run(self):
        """
        Start consuming messages.
        
        This method blocks until stop() is called or connection fails.
        """
        try:
            import aio_pika
        except ImportError:
            raise ImportError(
                "aio-pika package required. Install with: pip install aio-pika"
            )
        
        # Initialize handler
        await self.handler.initialize()
        
        # Connect to RabbitMQ
        self._connection = await aio_pika.connect_robust(self.url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self.prefetch_count)
        
        # Declare exchange and queue
        exchange = await self._channel.declare_exchange(
            self.exchange,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        
        queue = await self._channel.declare_queue(
            self.queue,
            durable=True,
        )
        await queue.bind(exchange, routing_key=self.routing_key)
        
        logger.info(
            "Started consuming from %s (exchange=%s, routing_key=%s)",
            self.queue,
            self.exchange,
            self.routing_key,
        )
        
        self._running = True
        
        # Consume messages
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                if not self._running:
                    break
                
                async with message.process():
                    try:
                        # Parse event
                        data = json.loads(message.body.decode())
                        event = AuditEvent.model_validate(data)
                        
                        # Handle event
                        success = await self.handler.handle(event)
                        
                        if not success:
                            logger.warning(
                                "Handler returned False for event %s",
                                event.id,
                            )
                    except Exception as e:
                        logger.error("Failed to process message: %s", e)
        
        logger.info("Consumer stopped")
    
    async def stop(self):
        """Stop consuming and clean up."""
        self._running = False
        
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()
        
        await self.handler.shutdown()


# ===================================================================
# Standalone Consumer Script
# ===================================================================

async def run_consumer(
    rabbitmq_url: str,
    handler: AuditEventHandler,
    queue_name: str = "audit-consumer",
):
    """
    Utility function to run a consumer with graceful shutdown.
    
    Example::
    
        import asyncio
        from itl_controlplane_sdk.storage.audit.consumers import (
            run_consumer,
            ElasticSearchForwarder,
        )
        
        handler = ElasticSearchForwarder(hosts=["http://localhost:9200"])
        asyncio.run(run_consumer(
            rabbitmq_url="amqp://guest:guest@localhost:5672/",
            handler=handler,
        ))
    """
    import signal
    
    consumer = RabbitMQConsumer(
        url=rabbitmq_url,
        handler=handler,
        queue=queue_name,
    )
    
    # Setup signal handlers
    loop = asyncio.get_running_loop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(consumer.stop()))
    
    await consumer.run()
