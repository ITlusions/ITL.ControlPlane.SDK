"""
Base class for Worker Roles in the ITL ControlPlane

A WorkerRole processes provider requests that have been offloaded
from the main API server via a job queue.
"""

import abc
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from itl_controlplane_sdk.core import ResourceRequest, ResourceResponse

logger = logging.getLogger(__name__)


class WorkerRole(abc.ABC):
    """
    Abstract base class for worker implementations
    
    Workers process provider operations offloaded from the main API server.
    They receive jobs from a queue and execute them independently.
    """
    
    def __init__(self, worker_id: str, worker_type: str = "generic"):
        """
        Initialize a worker role
        
        Args:
            worker_id: Unique identifier for this worker instance
            worker_type: Type of work this worker handles (e.g., 'provider', 'deployment')
        """
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.started_at = datetime.now(timezone.utc)
        self.is_running = False
        self.jobs_processed = 0
        self.jobs_failed = 0
    
    async def start(self):
        """Start the worker and begin processing jobs"""
        logger.info(f"Starting {self.worker_type} worker: {self.worker_id}")
        self.is_running = True
        try:
            await self._start_impl()
        except Exception as e:
            logger.error(f"Failed to start worker {self.worker_id}: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the worker gracefully"""
        logger.info(f"Stopping worker: {self.worker_id}")
        self.is_running = False
        try:
            await self._stop_impl()
        except Exception as e:
            logger.error(f"Error stopping worker {self.worker_id}: {e}")
    
    async def process_job(self, job_id: str, provider_namespace: str, 
                         resource_type: str, operation: str, 
                         request: ResourceRequest) -> Dict[str, Any]:
        """
        Process a job from the queue
        
        Args:
            job_id: Unique job identifier
            provider_namespace: Provider namespace (e.g., 'ITL.Core')
            resource_type: Resource type (e.g., 'ResourceGroup')
            operation: Operation type ('create', 'get', 'delete', 'list', 'action')
            request: Resource request
            
        Returns:
            Dict containing job result and status
        """
        try:
            logger.info(f"Processing job {job_id}: {provider_namespace}/{resource_type} {operation}")
            
            result = await self._process_job_impl(
                job_id, provider_namespace, resource_type, operation, request
            )
            
            self.jobs_processed += 1
            
            return {
                "job_id": job_id,
                "status": "completed",
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            self.jobs_failed += 1
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of this worker"""
        uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        
        return {
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "is_running": self.is_running,
            "jobs_processed": self.jobs_processed,
            "jobs_failed": self.jobs_failed,
            "uptime_seconds": uptime,
            "started_at": self.started_at.isoformat(),
        }
    
    # Abstract methods for subclasses
    
    @abc.abstractmethod
    async def _start_impl(self):
        """
        Subclass-specific initialization
        
        This is called after basic initialization.
        Subclasses should override this to set up queue connections, etc.
        """
        pass
    
    @abc.abstractmethod
    async def _stop_impl(self):
        """
        Subclass-specific cleanup
        
        Subclasses should override this to gracefully close connections.
        """
        pass
    
    @abc.abstractmethod
    async def _process_job_impl(self, job_id: str, provider_namespace: str,
                               resource_type: str, operation: str,
                               request: ResourceRequest) -> Dict[str, Any]:
        """
        Subclass-specific job processing implementation
        
        This is the core work - subclasses implement actual provider logic here.
        
        Args:
            job_id: Unique job identifier
            provider_namespace: Provider namespace
            resource_type: Resource type
            operation: Operation type
            request: Resource request
            
        Returns:
            Job result as dictionary
        """
        pass
