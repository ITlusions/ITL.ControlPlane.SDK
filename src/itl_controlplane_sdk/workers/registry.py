"""
Registry for managing multiple worker instances

Tracks active workers, their status, and workload distribution.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from .base import WorkerRole

logger = logging.getLogger(__name__)


class WorkerRegistry:
    """
    Registry for managing multiple worker instances
    
    Features:
    - Track active workers
    - Health monitoring
    - Workload statistics
    - Worker lifecycle management
    """
    
    def __init__(self):
        """Initialize worker registry"""
        self._workers: Dict[str, WorkerRole] = {}
        self._created_at = datetime.now(timezone.utc)
    
    def register_worker(self, worker: WorkerRole) -> None:
        """
        Register a worker instance
        
        Args:
            worker: WorkerRole instance to register
        """
        if worker.worker_id in self._workers:
            raise ValueError(f"Worker with ID {worker.worker_id} is already registered")
        
        self._workers[worker.worker_id] = worker
        logger.info(f"Registered worker: {worker.worker_id} (type: {worker.worker_type})")
    
    def unregister_worker(self, worker_id: str) -> bool:
        """
        Unregister a worker instance
        
        Args:
            worker_id: ID of worker to unregister
            
        Returns:
            True if worker was unregistered, False if not found
        """
        if worker_id in self._workers:
            del self._workers[worker_id]
            logger.info(f"Unregistered worker: {worker_id}")
            return True
        return False
    
    def get_worker(self, worker_id: str) -> Optional[WorkerRole]:
        """
        Get a specific worker instance
        
        Args:
            worker_id: ID of worker to retrieve
            
        Returns:
            WorkerRole instance or None if not found
        """
        return self._workers.get(worker_id)
    
    def get_workers_by_type(self, worker_type: str) -> List[WorkerRole]:
        """
        Get all workers of a specific type
        
        Args:
            worker_type: Type of workers to retrieve
            
        Returns:
            List of WorkerRole instances
        """
        return [w for w in self._workers.values() if w.worker_type == worker_type]
    
    def get_active_workers(self) -> List[WorkerRole]:
        """
        Get all currently active workers (running=True)
        
        Returns:
            List of active WorkerRole instances
        """
        return [w for w in self._workers.values() if w.is_running]
    
    def list_workers(self) -> List[str]:
        """
        List all registered worker IDs
        
        Returns:
            List of worker IDs
        """
        return list(self._workers.keys())
    
    def get_worker_status(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific worker
        
        Args:
            worker_id: ID of worker
            
        Returns:
            Worker status dict or None if not found
        """
        worker = self.get_worker(worker_id)
        if worker:
            return worker.get_status()
        return None
    
    def get_all_worker_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all workers
        
        Returns:
            Dict mapping worker_id to status dict
        """
        return {worker_id: worker.get_status() for worker_id, worker in self._workers.items()}
    
    def get_registry_status(self) -> Dict[str, Any]:
        """
        Get overall registry status and statistics
        
        Returns:
            Dict containing registry stats and all worker statuses
        """
        all_statuses = self.get_all_worker_statuses()
        
        total_jobs_processed = sum(s.get("jobs_processed", 0) for s in all_statuses.values())
        total_jobs_failed = sum(s.get("jobs_failed", 0) for s in all_statuses.values())
        active_count = sum(1 for s in all_statuses.values() if s.get("is_running"))
        
        return {
            "created_at": self._created_at.isoformat(),
            "total_workers": len(self._workers),
            "active_workers": active_count,
            "total_jobs_processed": total_jobs_processed,
            "total_jobs_failed": total_jobs_failed,
            "workers": all_statuses,
        }
    
    async def start_all_workers(self) -> None:
        """Start all registered workers"""
        logger.info(f"Starting {len(self._workers)} workers")
        
        for worker_id, worker in self._workers.items():
            try:
                await worker.start()
            except Exception as e:
                logger.error(f"Failed to start worker {worker_id}: {e}")
    
    async def stop_all_workers(self) -> None:
        """Stop all registered workers"""
        logger.info(f"Stopping {len(self._workers)} workers")
        
        for worker_id, worker in self._workers.items():
            try:
                await worker.stop()
            except Exception as e:
                logger.error(f"Failed to stop worker {worker_id}: {e}")
    
    async def stop_worker(self, worker_id: str) -> bool:
        """
        Stop a specific worker
        
        Args:
            worker_id: ID of worker to stop
            
        Returns:
            True if stopped, False if not found
        """
        worker = self.get_worker(worker_id)
        if worker:
            try:
                await worker.stop()
                return True
            except Exception as e:
                logger.error(f"Error stopping worker {worker_id}: {e}")
                return False
        
        return False
