"""
Generic Service Bus Provider for ITL ControlPlane SDK.

Message-based provider consumer that works with any ResourceProvider.
Can be used by Core, Compute, IAM, and custom providers.

Enables any provider to run in:
- API Mode: Traditional HTTP server
- ServiceBus Mode: RabbitMQ message consumer
- Hybrid Mode: Both simultaneously
"""

import json
import logging
import asyncio
from typing import Optional, Dict, Any

try:
    import aio_pika
    HAS_AIOPIKA = True
except ImportError:
    HAS_AIOPIKA = False

from itl_controlplane_sdk.core import ResourceRequest
from itl_controlplane_sdk.providers import ResourceProvider

logger = logging.getLogger(__name__)


class GenericServiceBusProvider:
    """
    Generic message-based provider consumer
    
    Works with any ResourceProvider implementation.
    Listens to RabbitMQ request queues and processes ResourceRequests.
    
    Features:
    - Provider-agnostic (works with Core, Compute, IAM, etc.)
    - Customizable queue names
    - Request/response correlation via job_id
    - Automatic dead-letter queue handling
    - Structured error classification
    - Full message persistence
    
    Example:
        ```python
        from itl_controlplane_sdk.providers import ComputeProvider
        from itl_controlplane_sdk.messaging.servicebus import GenericServiceBusProvider
        
        provider = ComputeProvider(engine=storage_engine)
        bus = GenericServiceBusProvider(
            provider=provider,
            provider_namespace="ITL.Compute",
            rabbitmq_url="amqp://localhost/"
        )
        await bus.run()
        ```
    """
    
    def __init__(
        self,
        provider: ResourceProvider,
        provider_namespace: str,
        rabbitmq_url: str = "amqp://guest:guest@localhost/",
        queue_prefix: Optional[str] = None,
        request_queue: Optional[str] = None,
        response_queue: Optional[str] = None,
        dlq_queue: Optional[str] = None,
    ):
        """
        Initialize generic service bus provider
        
        Args:
            provider: Any ResourceProvider instance (Core, Compute, IAM, custom)
            provider_namespace: Provider namespace (e.g., "ITL.Core", "ITL.Compute")
            rabbitmq_url: RabbitMQ connection URL
            queue_prefix: Base queue name (auto-generated from namespace if not provided)
            request_queue: Override request queue name
            response_queue: Override response queue name
            dlq_queue: Override DLQ queue name
        """
        if not HAS_AIOPIKA:
            raise ImportError("aio-pika is required for GenericServiceBusProvider. Install with: pip install aio-pika")
        
        self.provider = provider
        self.provider_namespace = provider_namespace
        self.rabbitmq_url = rabbitmq_url
        
        # Generate queue prefix from namespace (e.g., "ITL.Core" → "provider.core")
        if not queue_prefix:
            ns_lower = provider_namespace.lower().replace(".", "-")
            queue_prefix = f"provider.{ns_lower}"
        
        # Queue names
        self.queue_prefix = queue_prefix
        self.request_queue_name = request_queue or f"{queue_prefix}.requests"
        self.response_queue_name = response_queue or f"{queue_prefix}.responses"
        self.dlq_queue_name = dlq_queue or f"{queue_prefix}.dlq"
        
        # RabbitMQ connection
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
    
    async def connect(self):
        """Connect to RabbitMQ and initialize queues"""
        logger.info(f"Connecting to RabbitMQ: {self.rabbitmq_url}")
        
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        
        # Declare default exchange
        self.exchange = self.channel.default_exchange
        
        # ── Setup request queue with DLX ──
        dlx = await self.channel.declare_exchange(
            name=f"{self.request_queue_name}.dlx",
            type=aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        
        dlq = await self.channel.declare_queue(
            name=self.dlq_queue_name,
            durable=True,
        )
        await dlq.bind(dlx, routing_key="dead_letter")
        
        # Request queue with DLX configuration
        request_queue = await self.channel.declare_queue(
            name=self.request_queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": f"{self.request_queue_name}.dlx",
                "x-dead-letter-routing-key": "dead_letter",
                "x-max-retries": 3,
            }
        )
        
        # Response queue (for replies)
        response_queue = await self.channel.declare_queue(
            name=self.response_queue_name,
            durable=True,
        )
        
        logger.info(f"Initialized {self.provider_namespace} queues:")
        logger.info(f"  - Request: {self.request_queue_name}")
        logger.info(f"  - Response: {self.response_queue_name}")
        logger.info(f"  - DLQ: {self.dlq_queue_name}")
    
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection:
            await self.connection.close()
            logger.info(f"Disconnected from RabbitMQ ({self.provider_namespace})")
    
    async def process_request(
        self,
        job_id: str,
        request_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a ResourceRequest message
        
        Args:
            job_id: Unique job identifier for correlation
            request_data: Request payload (ResourceRequest as dict)
            
        Returns:
            Response data (ResourceResponse as dict)
        """
        try:
            # Parse request
            request = ResourceRequest(**request_data)
            
            logger.info(
                f"[{self.provider_namespace}] Processing request {job_id}: "
                f"{request.resource_type} ({request.operation})"
            )
            
            # Dispatch to appropriate provider method
            operation = request.operation
            
            if operation == "create":
                response = await self.provider.create_or_update_resource(request)
            elif operation == "get":
                response = await self.provider.get_resource(request)
            elif operation == "list":
                response = await self.provider.list_resources(request)
            elif operation == "delete":
                response = await self.provider.delete_resource(request)
            elif operation == "action":
                response = await self.provider.execute_action(request)
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            # Convert response to dict
            result = response.model_dump() if hasattr(response, 'model_dump') else response.dict()
            
            logger.info(f"[{self.provider_namespace}] Request {job_id} processed successfully")
            return {
                "job_id": job_id,
                "status": "completed",
                "result": result,
            }
        
        except Exception as e:
            logger.error(f"[{self.provider_namespace}] Error processing request {job_id}: {e}", exc_info=True)
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
            }
    
    async def publish_response(self, response_data: Dict[str, Any]):
        """
        Publish response message to response queue
        
        Args:
            response_data: Response payload
        """
        try:
            message = aio_pika.Message(
                body=json.dumps(response_data).encode(),
                content_type="application/json",
            )
            
            await self.exchange.publish(message, routing_key=self.response_queue_name)
            
            logger.debug(f"[{self.provider_namespace}] Published response for job {response_data.get('job_id')}")
        except Exception as e:
            logger.error(f"[{self.provider_namespace}] Failed to publish response: {e}", exc_info=True)
    
    async def consume_requests(self):
        """
        Start consuming messages from request queue
        
        This is a blocking operation that processes messages continuously.
        """
        queue = await self.channel.get_queue(self.request_queue_name)
        
        logger.info(f"[{self.provider_namespace}] Consuming messages from {self.request_queue_name}")
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        request_data = json.loads(message.body.decode())
                        job_id = request_data.get("job_id", message.correlation_id or "unknown")
                        
                        # Process request
                        response = await self.process_request(job_id, request_data)
                        
                        # Publish response
                        await self.publish_response(response)
                        
                        # Message is automatically acked on successful context exit
                        logger.debug(f"[{self.provider_namespace}] Message {job_id} processed and acked")
                    
                    except Exception as e:
                        logger.error(
                            f"[{self.provider_namespace}] Error consuming message: {e}. Message will be requeued.",
                            exc_info=True
                        )
                        # Re-raise to trigger nack and requeue
                        raise
    
    async def run(self):
        """
        Run the service bus provider
        
        This is the main entry point for the service bus mode.
        """
        try:
            await self.connect()
            logger.info(f"[{self.provider_namespace}] Message consumer started")
            await self.consume_requests()
        except asyncio.CancelledError:
            logger.info(f"[{self.provider_namespace}] Message consumer cancelled")
        except KeyboardInterrupt:
            logger.info(f"[{self.provider_namespace}] Message consumer interrupted")
        except Exception as e:
            logger.error(f"[{self.provider_namespace}] Message consumer error: {e}", exc_info=True)
            raise
        finally:
            await self.disconnect()
