#!/usr/bin/env python3
"""
ITL Audit Event Consumer — Standalone Service

This script runs an audit event consumer that reads from RabbitMQ
and forwards events to configured SIEM/analytics backends.

Environment Variables:
    RABBITMQ_URL            — AMQP connection URL (required)
    CONSUMER_QUEUE          — Queue name (default: audit-siem-consumer)
    
    # Elasticsearch
    ELASTICSEARCH_ENABLED   — Enable Elasticsearch (default: false)
    ELASTICSEARCH_HOSTS     — Comma-separated hosts
    ELASTICSEARCH_INDEX     — Index prefix (default: audit-events)
    ELASTICSEARCH_API_KEY   — API key (optional)
    ELASTICSEARCH_USERNAME  — Username (optional)
    ELASTICSEARCH_PASSWORD  — Password (optional)
    
    # Splunk
    SPLUNK_ENABLED          — Enable Splunk HEC (default: false)
    SPLUNK_HEC_URL          — HEC endpoint URL
    SPLUNK_TOKEN            — HEC token
    SPLUNK_INDEX            — Index name (default: main)
    
    # ClickHouse
    CLICKHOUSE_ENABLED      — Enable ClickHouse (default: false)
    CLICKHOUSE_HOST         — Host
    CLICKHOUSE_PORT         — Port (default: 8123)
    CLICKHOUSE_DATABASE     — Database (default: default)
    
    # Webhook
    WEBHOOK_ENABLED         — Enable webhook (default: false)
    WEBHOOK_URL             — Webhook URL
    
    # Slack Alerts
    SLACK_ENABLED           — Enable Slack alerts (default: false)
    SLACK_WEBHOOK_URL       — Slack webhook URL
    SLACK_CHANNEL           — Channel override (optional)

Usage:
    # Direct execution
    python -m itl_controlplane_sdk.storage.audit.consumer_service
    
    # Docker
    docker run -e RABBITMQ_URL=amqp://... -e ELASTICSEARCH_ENABLED=true \\
               -e ELASTICSEARCH_HOSTS=http://es:9200 \\
               itl-audit-consumer
"""

import asyncio
import logging
import os
import signal
import sys
from typing import List, Optional

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_bool_env(name: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    value = os.getenv(name, str(default)).lower()
    return value in ("true", "1", "yes", "on")


async def create_handlers():
    """Create handlers based on environment configuration."""
    from itl_controlplane_sdk.storage.audit import (
        AuditEventHandler,
        FanoutHandler,
        ElasticSearchForwarder,
        SplunkForwarder,
        ClickHouseForwarder,
        WebhookForwarder,
        SlackAlertHandler,
        FilteringHandler,
    )
    from itl_controlplane_sdk.storage.audit.models import AuditAction
    
    handlers: List[AuditEventHandler] = []
    
    # Elasticsearch
    if get_bool_env("ELASTICSEARCH_ENABLED"):
        hosts_str = os.getenv("ELASTICSEARCH_HOSTS", "http://localhost:9200")
        hosts = [h.strip() for h in hosts_str.split(",")]
        
        handler = ElasticSearchForwarder(
            hosts=hosts,
            index_prefix=os.getenv("ELASTICSEARCH_INDEX", "audit-events"),
            api_key=os.getenv("ELASTICSEARCH_API_KEY"),
            username=os.getenv("ELASTICSEARCH_USERNAME"),
            password=os.getenv("ELASTICSEARCH_PASSWORD"),
            verify_certs=get_bool_env("ELASTICSEARCH_VERIFY_CERTS", True),
        )
        handlers.append(handler)
        logger.info("Elasticsearch forwarder enabled: %s", hosts)
    
    # Splunk
    if get_bool_env("SPLUNK_ENABLED"):
        hec_url = os.getenv("SPLUNK_HEC_URL")
        token = os.getenv("SPLUNK_TOKEN")
        
        if hec_url and token:
            handler = SplunkForwarder(
                hec_url=hec_url,
                token=token,
                index=os.getenv("SPLUNK_INDEX", "main"),
                source=os.getenv("SPLUNK_SOURCE", "itl-controlplane"),
                sourcetype=os.getenv("SPLUNK_SOURCETYPE", "itl:audit:event"),
                verify_ssl=get_bool_env("SPLUNK_VERIFY_SSL", True),
            )
            handlers.append(handler)
            logger.info("Splunk forwarder enabled: %s", hec_url)
        else:
            logger.warning("SPLUNK_ENABLED but missing SPLUNK_HEC_URL or SPLUNK_TOKEN")
    
    # ClickHouse
    if get_bool_env("CLICKHOUSE_ENABLED"):
        handler = ClickHouseForwarder(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            database=os.getenv("CLICKHOUSE_DATABASE", "default"),
            table=os.getenv("CLICKHOUSE_TABLE", "audit_events"),
            username=os.getenv("CLICKHOUSE_USERNAME"),
            password=os.getenv("CLICKHOUSE_PASSWORD"),
        )
        handlers.append(handler)
        logger.info("ClickHouse forwarder enabled: %s", os.getenv("CLICKHOUSE_HOST"))
    
    # Webhook
    if get_bool_env("WEBHOOK_ENABLED"):
        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url:
            handler = WebhookForwarder(
                url=webhook_url,
                timeout=float(os.getenv("WEBHOOK_TIMEOUT", "10")),
                verify_ssl=get_bool_env("WEBHOOK_VERIFY_SSL", True),
            )
            handlers.append(handler)
            logger.info("Webhook forwarder enabled: %s", webhook_url)
        else:
            logger.warning("WEBHOOK_ENABLED but missing WEBHOOK_URL")
    
    # Slack Alerts
    if get_bool_env("SLACK_ENABLED"):
        slack_url = os.getenv("SLACK_WEBHOOK_URL")
        if slack_url:
            handler = SlackAlertHandler(
                webhook_url=slack_url,
                channel=os.getenv("SLACK_CHANNEL"),
                username=os.getenv("SLACK_USERNAME", "ITL Audit"),
                icon_emoji=os.getenv("SLACK_ICON_EMOJI", ":shield:"),
            )
            
            # Optional: Filter to only important actions
            filter_actions = os.getenv("SLACK_FILTER_ACTIONS")
            if filter_actions:
                actions = {a.strip().upper() for a in filter_actions.split(",")}
                handler = FilteringHandler(
                    inner_handler=handler,
                    filter_fn=lambda e: e.action.value in actions,
                )
            
            handlers.append(handler)
            logger.info("Slack alerting enabled")
        else:
            logger.warning("SLACK_ENABLED but missing SLACK_WEBHOOK_URL")
    
    if not handlers:
        logger.error("No handlers configured! Set at least one *_ENABLED=true")
        sys.exit(1)
    
    # Create fanout if multiple handlers
    if len(handlers) == 1:
        return handlers[0]
    
    return FanoutHandler(handlers)


async def main():
    """Main entry point."""
    from itl_controlplane_sdk.storage.audit import RabbitMQConsumer
    
    # Validate required environment
    rabbitmq_url = os.getenv("RABBITMQ_URL")
    if not rabbitmq_url:
        logger.error("RABBITMQ_URL environment variable is required")
        sys.exit(1)
    
    # Create handlers
    handler = await create_handlers()
    
    # Create consumer
    consumer = RabbitMQConsumer(
        url=rabbitmq_url,
        handler=handler,
        exchange=os.getenv("AUDIT_EXCHANGE", "audit.events"),
        queue=os.getenv("CONSUMER_QUEUE", "audit-siem-consumer"),
        routing_key=os.getenv("ROUTING_KEY", "#"),
        prefetch_count=int(os.getenv("PREFETCH_COUNT", "10")),
    )
    
    # Setup graceful shutdown
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()
    
    def handle_signal():
        logger.info("Shutdown signal received")
        shutdown_event.set()
        asyncio.create_task(consumer.stop())
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: handle_signal())
    
    logger.info("Starting audit event consumer...")
    logger.info("RabbitMQ: %s", rabbitmq_url.split("@")[-1])  # Log without credentials
    
    try:
        await consumer.run()
    except Exception as e:
        logger.error("Consumer failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
