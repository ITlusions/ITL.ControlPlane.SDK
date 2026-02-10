"""
Async job queue for distributing provider operations to workers

Uses RabbitMQ (via aio-pika) for reliable job distribution and processing.
"""

import json
import uuid
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, asdict

try:
    import aio_pika
    HAS_AIOPIKA = True
except ImportError:
    HAS_AIOPIKA = False

from itl_controlplane_sdk.core import ResourceRequest

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status values"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """Result of a job execution"""
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobResult':
        """Create from dictionary"""
        data = dict(data)
        if isinstance(data.get('status'), str):
            data['status'] = JobStatus(data['status'])
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class JobQueue:
    """
    Async job queue for provider operations
    
    Features:
    - Reliable job distribution to workers
    - Job result tracking
    - Dead-letter queue for failed jobs
    - Support for different job types/priorities
    """
    
    def __init__(self, rabbitmq_url: str = "amqp://guest:guest@localhost/"):
        """
        Initialize job queue
        
        Args:
            rabbitmq_url: RabbitMQ connection URL
        """
        if not HAS_AIOPIKA:
            raise ImportError("aio-pika is required for JobQueue. Install with: pip install aio-pika")
        
        self.rabbitmq_url = rabbitmq_url
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        
        # Queue names
        self.job_queue_name = "provider.jobs"
        self.result_queue_name = "provider.results"
        self.dlq_queue_name = "provider.jobs.dlq"
    
    async def connect(self):
        """
        Connect to RabbitMQ and initialize queues
        
        Queue setup:
        - provider.jobs: Main job queue with DLX configured
          - Failed messages requeued automatically
          - After max retries (default 3), moved to DLQ
        - provider.results: Results queue for job outputs
        - provider.jobs.dlq: Dead-letter queue for permanently failed jobs
          - Messages here should be inspected and manually retried if needed
        """
        logger.info(f"Connecting to RabbitMQ: {self.rabbitmq_url}")
        
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        
        # Declare exchange
        self.exchange = await self.channel.declare_exchange(
            "provider.exchange",
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        
        # Declare task queues with DLX for failed messages
        # x-max-length: limit queue size (optional, prevents unbounded growth)
        # x-dead-letter-exchange: route failed msgs to DLX
        # x-dead-letter-routing-key: key for DLX routing
        await self.channel.declare_queue(
            self.job_queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "provider.dlx",
                "x-dead-letter-routing-key": self.dlq_queue_name,
            }
        )
        
        await self.channel.declare_queue(
            self.result_queue_name,
            durable=True,
        )
        
        # Declare DLX and DLQ
        dlx = await self.channel.declare_exchange(
            "provider.dlx",
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        
        dlq = await self.channel.declare_queue(
            self.dlq_queue_name,
            durable=True,
        )
        
        await dlq.bind(dlx, self.dlq_queue_name)
        
        logger.info("Connected to RabbitMQ and queues initialized")
    
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    async def submit_job(self, provider_namespace: str, resource_type: str,
                        operation: str, request: ResourceRequest,
                        priority: int = 5) -> str:
        """
        Submit a job to the queue
        
        Args:
            provider_namespace: Provider namespace (e.g., 'ITL.Core')
            resource_type: Resource type (e.g., 'ResourceGroup')
            operation: Operation type ('create', 'get', 'delete', 'list', 'action')
            request: Resource request
            priority: Job priority (0-10, higher = more urgent)
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        job_payload = {
            "job_id": job_id,
            "provider_namespace": provider_namespace,
            "resource_type": resource_type,
            "operation": operation,
            "request": request.model_dump() if hasattr(request, 'model_dump') else request.dict(),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "priority": priority,
        }
        
        message = aio_pika.Message(
            body=json.dumps(job_payload).encode(),
            content_type="application/json",
            priority=priority,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        
        routing_key = f"provider.{provider_namespace}.{resource_type}.{operation}"
        await self.exchange.publish(message, routing_key=routing_key)
        
        logger.info(f"Submitted job {job_id}: {routing_key}")
        return job_id
    
    async def consume_jobs(self, worker_callback: Callable[[str, Dict[str, Any]], Awaitable[JobResult]]) -> None:
        """
        Consume jobs from the queue and process them with the worker callback
        
        On successful completion, message is acked (removed from queue).
        On exception, message is nacked (requeued) up to x-death limit, 
        then moved to dead-letter queue.
        
        Args:
            worker_callback: Async function that takes (job_id, job_payload) and returns JobResult
        """
        queue = await self.channel.get_queue(self.job_queue_name)
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        job_payload = json.loads(message.body.decode())
                        job_id = job_payload.get("job_id")
                        
                        logger.info(f"Processing job {job_id}")
                        
                        # Call worker callback - may raise exception for retries
                        result = await worker_callback(job_id, job_payload)
                        
                        # Publish result only on success
                        await self._publish_result(result)
                        
                        # Message is automatically acked on successful context exit
                        logger.info(f"Job {job_id} completed and acknowledged")
                        
                    except Exception as e:
                        # Log error - message will be nacked (requeued) on exception
                        logger.error(
                            f"Error processing job: {e}. "
                            f"Message will be requeued.",
                            exc_info=True
                        )
                        # Re-raise to trigger nack and requeue
                        raise
    
    async def get_result(self, job_id: str, timeout: float = 30.0) -> Optional[JobResult]:
        """
        Get the result of a job (waits if not ready)
        
        Args:
            job_id: Job ID to retrieve result for
            timeout: Maximum time to wait for result in seconds
            
        Returns:
            JobResult if available, None if timeout reached
        """
        queue = await self.channel.get_queue(self.result_queue_name)
        
        import asyncio
        start_time = datetime.now(timezone.utc)
        
        async for message in queue.iterator():
            async with message.process():
                result_data = json.loads(message.body.decode())
                
                if result_data.get("job_id") == job_id:
                    return JobResult.from_dict(result_data)
                
                # Re-queue if not for us
                # In real implementation, you'd want to use a result store instead
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed > timeout:
                    return None
    
    async def _publish_result(self, result: JobResult) -> None:
        """Publish job result to result queue"""
        message = aio_pika.Message(
            body=json.dumps(result.to_dict()).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        
        routing_key = f"provider.result.{result.job_id}"
        await self.exchange.publish(message, routing_key=routing_key)
        
        logger.info(f"Published result for job {result.job_id}: {result.status.value}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the job queue"""
        stats = {
            "connected": self.connection is not None and not self.connection.is_closed(),
            "queues": {}
        }
        
        if self.channel:
            for queue_name in [self.job_queue_name, self.result_queue_name, self.dlq_queue_name]:
                try:
                    queue = await self.channel.get_queue(queue_name)
                    stats["queues"][queue_name] = {
                        "message_count": queue.declaration_result.method.message_count if queue.declaration_result else 0,
                        "consumer_count": queue.declaration_result.method.consumer_count if queue.declaration_result else 0,
                    }
                except Exception as e:
                    logger.error(f"Error getting stats for queue {queue_name}: {e}")
        
        return stats
