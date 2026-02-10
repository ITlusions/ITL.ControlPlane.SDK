"""
Provider Worker - Concrete implementation of WorkerRole for provider operations

Processes provider requests from the job queue and executes them using registered providers.
Includes automatic retry logic for transient failures and unavailable providers.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from .base import WorkerRole
from .queue import JobQueue
from itl_controlplane_sdk.core import ResourceRequest
from itl_controlplane_sdk.providers import ResourceProviderRegistry

logger = logging.getLogger(__name__)


class ProviderWorker(WorkerRole):
    """
    Worker that processes provider operations
    
    Consumes jobs from the queue and executes them using the provider registry.
    Includes automatic retry logic for transient failures and unavailable providers.
    """
    
    def __init__(self, worker_id: str, provider_registry: ResourceProviderRegistry,
                 job_queue: JobQueue, max_retries: int = 3, retry_delay: float = 5.0):
        """
        Initialize provider worker
        
        Args:
            worker_id: Unique worker identifier
            provider_registry: ResourceProviderRegistry instance
            job_queue: JobQueue instance
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 5.0)
        """
        super().__init__(worker_id, worker_type="provider")
        self.provider_registry = provider_registry
        self.job_queue = job_queue
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._consumer_task = None
    
    async def _start_impl(self):
        """Start consuming jobs from the queue"""
        logger.info(f"ProviderWorker {self.worker_id} starting job consumption")
        
        try:
            await self.job_queue.connect()
        except Exception as e:
            logger.error(f"Failed to connect to job queue: {e}")
            raise
    
    async def _stop_impl(self):
        """Stop consuming jobs and clean up"""
        logger.info(f"ProviderWorker {self.worker_id} stopping")
        
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except Exception:
                pass
        
        try:
            await self.job_queue.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting from job queue: {e}")
    
    async def _process_job_impl(self, job_id: str, provider_namespace: str,
                               resource_type: str, operation: str,
                               request: ResourceRequest) -> Dict[str, Any]:
        """
        Process a provider operation job with automatic retry logic
        
        Args:
            job_id: Unique job identifier
            provider_namespace: Provider namespace (e.g., 'ITL.Core')
            resource_type: Resource type (e.g., 'ResourceGroup')
            operation: Operation type ('create', 'get', 'delete', 'list', 'action')
            request: Resource request
            
        Returns:
            Job result as dictionary
            
        Raises:
            Exception: After max retries are exhausted (causes message requeue)
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Processing job {job_id}: {provider_namespace}/{resource_type} "
                    f"({operation}) [attempt {attempt + 1}/{self.max_retries}]"
                )
                
                # Get the provider
                provider = self.provider_registry.get_provider(provider_namespace, resource_type)
                if not provider:
                    raise ValueError(f"No provider found for {provider_namespace}/{resource_type}")
                
                # Execute the operation
                if operation == "create":
                    response = await provider.create_or_update_resource(request)
                elif operation == "get":
                    response = await provider.get_resource(request)
                elif operation == "list":
                    response = await provider.list_resources(request)
                elif operation == "delete":
                    response = await provider.delete_resource(request)
                elif operation == "action":
                    response = await provider.execute_action(request)
                else:
                    raise ValueError(f"Unknown operation: {operation}")
                
                # Convert response to dict
                result = response.model_dump() if hasattr(response, 'model_dump') else response.dict()
                
                logger.info(f"Job {job_id} completed successfully on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                is_retryable = self._is_retryable_error(e)
                is_last_attempt = attempt == self.max_retries - 1
                
                if is_retryable and not is_last_attempt:
                    logger.warning(
                        f"Job {job_id} failed with retryable error: {e}. "
                        f"Retrying in {self.retry_delay}s... "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    # Not retryable or last attempt - raise to mark as failed
                    logger.error(
                        f"Job {job_id} failed (attempt {attempt + 1}/{self.max_retries}): {e}",
                        exc_info=True
                    )
                    raise
    
    def _is_retryable_error(self, exception: Exception) -> bool:
        """
        Determine if an error is retryable
        
        Retryable errors:
        - Provider not found (likely starting up)
        - Connection errors
        - Timeouts
        
        Non-retryable errors:
        - Validation errors
        - Authorization errors
        - Resource not found (non-transient)
        
        Args:
            exception: The exception to check
            
        Returns:
            True if error is retryable, False otherwise
        """
        error_str = str(exception).lower()
        
        # Retryable patterns
        retryable_patterns = [
            "no provider found",
            "provider not available",
            "connection",
            "timeout",
            "temporarily unavailable",
            "service unavailable",
            "busy",
        ]
        
        # Non-retryable patterns
        non_retryable_patterns = [
            "validation",
            "invalid",
            "unauthorized",
            "forbidden",
            "unknown operation",
            "unsupported",
        ]
        
        # Check non-retryable first (higher priority)
        for pattern in non_retryable_patterns:
            if pattern in error_str:
                return False
        
        # Check retryable patterns
        for pattern in retryable_patterns:
            if pattern in error_str:
                return True
        
        # Default: treat as retryable (transient errors)
        return True
    
    async def start_consuming_jobs(self):
        """Start consuming and processing jobs"""
        if not self.is_running:
            await self.start()
        
        # Consume jobs
        await self.job_queue.consume_jobs(self._job_callback)
    
    async def _job_callback(self, job_id: str, job_payload: Dict[str, Any]):
        """
        Callback for processing jobs from the queue
        
        Automatically retries on transient failures.
        Returns success or raises exception to trigger message requeue.
        """
        try:
            provider_namespace = job_payload.get("provider_namespace")
            resource_type = job_payload.get("resource_type")
            operation = job_payload.get("operation")
            request_data = job_payload.get("request")
            
            # Reconstruct request from dict
            request = ResourceRequest(**request_data)
            
            # Process the job (includes retry logic)
            result = await self.process_job(
                job_id, provider_namespace, resource_type, operation, request
            )
            
            return result
            
        except Exception as e:
            # Log and re-raise - JobQueue will requeue message on exception
            logger.error(
                f"Job {job_id} exhausted all retries and will be moved to DLQ: {e}",
                exc_info=True
            )
            raise
