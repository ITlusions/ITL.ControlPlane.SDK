"""
Provider registry that offloads operations to backend workers

Extends the standard ResourceProviderRegistry to submit jobs to a job queue
instead of processing them directly in the main API server.
"""

import logging
from typing import Dict, Optional, Any
import asyncio
from itl_controlplane_sdk.core import ResourceRequest, ResourceResponse, ResourceListResponse
from itl_controlplane_sdk.providers import ResourceProviderRegistry
from .queue import JobQueue, JobStatus

logger = logging.getLogger(__name__)


class OffloadingProviderRegistry(ResourceProviderRegistry):
    """
    Provider registry that offloads operations to backend workers
    
    Instead of executing provider operations directly, submits them to a job queue
    for processing by backend workers. Supports:
    - Async job submission
    - Result polling with timeout
    - Different operation types (create, get, delete, list, action)
    - Priority-based job queuing
    """
    
    def __init__(self, job_queue: JobQueue):
        """
        Initialize offloading registry
        
        Args:
            job_queue: JobQueue instance for submitting jobs
        """
        super().__init__()
        self.job_queue = job_queue
        self._result_cache: Dict[str, Any] = {}
    
    async def create_or_update_resource(self, provider_namespace: str, resource_type: str,
                                       request: ResourceRequest) -> ResourceResponse:
        """
        Create or update a resource by offloading to a worker
        
        Args:
            provider_namespace: Provider namespace (e.g., 'ITL.Core')
            resource_type: Resource type (e.g., 'ResourceGroup')
            request: Resource creation/update request
            
        Returns:
            Immediate ResourceResponse with job_id for tracking
        """
        job_id = await self.job_queue.submit_job(
            provider_namespace=provider_namespace,
            resource_type=resource_type,
            operation="create",
            request=request,
            priority=7,
        )
        
        return self._create_pending_response(job_id, "create", provider_namespace, resource_type)
    
    async def get_resource(self, provider_namespace: str, resource_type: str,
                         request: ResourceRequest) -> ResourceResponse:
        """
        Get a resource by offloading to a worker
        
        Args:
            provider_namespace: Provider namespace
            resource_type: Resource type
            request: Resource retrieval request
            
        Returns:
            Immediate ResourceResponse with job_id for tracking
        """
        job_id = await self.job_queue.submit_job(
            provider_namespace=provider_namespace,
            resource_type=resource_type,
            operation="get",
            request=request,
            priority=8,
        )
        
        return self._create_pending_response(job_id, "get", provider_namespace, resource_type)
    
    async def list_resources(self, provider_namespace: str, resource_type: str,
                           request: ResourceRequest) -> ResourceListResponse:
        """
        List resources by offloading to a worker
        
        Args:
            provider_namespace: Provider namespace
            resource_type: Resource type
            request: Resource list request
            
        Returns:
            Immediate ResourceListResponse with job_id for tracking
        """
        job_id = await self.job_queue.submit_job(
            provider_namespace=provider_namespace,
            resource_type=resource_type,
            operation="list",
            request=request,
            priority=5,
        )
        
        return ResourceListResponse(
            value=[],
            job_id=job_id,
            status="pending",
        )
    
    async def delete_resource(self, provider_namespace: str, resource_type: str,
                            request: ResourceRequest) -> ResourceResponse:
        """
        Delete a resource by offloading to a worker
        
        Args:
            provider_namespace: Provider namespace
            resource_type: Resource type
            request: Resource deletion request
            
        Returns:
            Immediate ResourceResponse with job_id for tracking
        """
        job_id = await self.job_queue.submit_job(
            provider_namespace=provider_namespace,
            resource_type=resource_type,
            operation="delete",
            request=request,
            priority=6,
        )
        
        return self._create_pending_response(job_id, "delete", provider_namespace, resource_type)
    
    async def execute_action(self, provider_namespace: str, resource_type: str,
                           request: ResourceRequest) -> ResourceResponse:
        """
        Execute an action by offloading to a worker
        
        Args:
            provider_namespace: Provider namespace
            resource_type: Resource type
            request: Resource action request
            
        Returns:
            Immediate ResourceResponse with job_id for tracking
        """
        job_id = await self.job_queue.submit_job(
            provider_namespace=provider_namespace,
            resource_type=resource_type,
            operation="action",
            request=request,
            priority=5,
        )
        
        return self._create_pending_response(job_id, "action", provider_namespace, resource_type)
    
    async def get_job_result(self, job_id: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """
        Retrieve the result of a job with optional wait
        
        Args:
            job_id: Job ID to retrieve
            timeout: How long to wait for result in seconds (0 for no wait)
            
        Returns:
            Job result dict or None if not available
        """
        if timeout > 0:
            # For real implementation, would need result store/persistence
            # This is a placeholder - in production use Redis or similar
            result = await asyncio.wait_for(
                self.job_queue.get_result(job_id, timeout),
                timeout=timeout
            )
            return result.to_dict() if result else None
        
        return None
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the job queue and workers"""
        return await self.job_queue.get_queue_stats()
    
    def _create_pending_response(self, job_id: str, operation: str,
                                provider_namespace: str, resource_type: str) -> ResourceResponse:
        """
        Create a pending response with job ID
        
        The client can use this job_id to poll for results or subscribe to updates.
        """
        return ResourceResponse(
            id=None,  # Will be populated once job completes
            type=resource_type,
            properties={
                "status": "pending",
                "job_id": job_id,
                "operation": operation,
            },
            name=None,
            location=None,
            job_id=job_id,
            status="pending",
        )


class SyncOffloadingProviderRegistry(OffloadingProviderRegistry):
    """
    Provider registry that blocks until worker completes (synchronous offloading)
    
    Useful for operations that must return results immediately.
    Falls back to direct provider execution if available, otherwise polls for results.
    """
    
    def __init__(self, job_queue: JobQueue, default_timeout: float = 30.0):
        """
        Initialize sync offloading registry
        
        Args:
            job_queue: JobQueue instance for submitting jobs
            default_timeout: Default timeout for waiting on results in seconds
        """
        super().__init__(job_queue)
        self.default_timeout = default_timeout
    
    async def create_or_update_resource_sync(self, provider_namespace: str, resource_type: str,
                                            request: ResourceRequest, timeout: Optional[float] = None) -> ResourceResponse:
        """
        Synchronously create or update a resource (waits for completion)
        
        Args:
            provider_namespace: Provider namespace
            resource_type: Resource type
            request: Resource request
            timeout: Override default timeout
            
        Returns:
            Completed ResourceResponse
        """
        timeout = timeout or self.default_timeout
        response = await super().create_or_update_resource(provider_namespace, resource_type, request)
        
        if response.job_id:
            result = await self.get_job_result(response.job_id, timeout)
            if result:
                # Update response with actual result
                response.properties = result.get("result", {})
                response.status = "completed"
        
        return response
