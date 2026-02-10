"""
Worker infrastructure for offloading provider operations to backend workers

This module provides:
- WorkerRole: Base class for worker implementations
- WorkerRegistry: Registry for managing multiple workers
- JobQueue: Async job queue for task distribution
- OffloadingProviderRegistry: Provider registry that offloads to workers
"""

from .base import WorkerRole
from .registry import WorkerRegistry
from .queue import JobQueue, JobResult, JobStatus
from .offloading_registry import OffloadingProviderRegistry

__all__ = [
    "WorkerRole",
    "WorkerRegistry",
    "JobQueue",
    "JobResult",
    "JobStatus",
    "OffloadingProviderRegistry",
]
