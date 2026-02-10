"""
Standalone Worker Process

Run this script to start a backend worker that processes provider operations.
Can be deployed as a separate service/pod in Kubernetes.

Usage:
    python -m itl_controlplane_sdk.workers.worker_entrypoint [options]

Environment variables:
    WORKER_ID: Unique worker identifier (auto-generated if not set)
    RABBITMQ_URL: RabbitMQ connection URL (default: amqp://guest:guest@localhost/)
    LOG_LEVEL: Logging level (default: INFO)
    PROVIDER_REGISTRY_TYPE: Type of provider registry to use (local or remote)
"""

import asyncio
import os
import sys
import logging
import signal
from typing import Optional
import uuid

# Configure logging before imports
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from itl_controlplane_sdk.providers import ResourceProviderRegistry
from itl_controlplane_sdk.workers import ProviderWorker, JobQueue, WorkerRegistry

# Global state
worker: Optional[ProviderWorker] = None
job_queue: Optional[JobQueue] = None
registry: Optional[WorkerRegistry] = None


async def cleanup(signum, frame):
    """Handle graceful shutdown on signals"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    
    if worker and worker.is_running:
        await worker.stop()
    
    if job_queue:
        await job_queue.disconnect()
    
    sys.exit(0)


async def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown"""
    loop = asyncio.get_event_loop()
    
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            signum,
            lambda s=signum: asyncio.create_task(cleanup(s, None))
        )


async def initialize_worker():
    """Initialize worker components"""
    global worker, job_queue, registry
    
    logger.info("Initializing worker components...")
    
    # Configuration from environment
    worker_id = os.getenv("WORKER_ID", f"worker-{uuid.uuid4().hex[:8]}")
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    
    logger.info(f"Worker ID: {worker_id}")
    logger.info(f"RabbitMQ URL: {rabbitmq_url.split('@')[0]}@...[redacted]")
    
    # Initialize job queue
    job_queue = JobQueue(rabbitmq_url=rabbitmq_url)
    
    # Initialize provider registry
    # In a real deployment, this would load providers from a service registry
    # or connect to a provider service. For now, use local registry.
    provider_registry = ResourceProviderRegistry()
    
    # Initialize worker registry
    registry = WorkerRegistry()
    
    # Create and register provider worker
    worker = ProviderWorker(worker_id, provider_registry, job_queue)
    registry.register_worker(worker)
    
    logger.info("Worker components initialized successfully")
    
    return worker, job_queue, registry


async def health_check_server():
    """
    Run a simple HTTP server for health checks
    
    Kubernetes can probe this for liveness/readiness checks.
    """
    import aiohttp
    from aiohttp import web
    
    async def health_handler(request):
        """Handle /health requests"""
        if worker and worker.is_running:
            return web.json_response({"status": "healthy", "worker_id": worker.worker_id})
        else:
            return web.json_response({"status": "unhealthy"}, status=503)
    
    async def status_handler(request):
        """Handle /status requests"""
        if worker:
            return web.json_response(worker.get_status())
        else:
            return web.json_response({"status": "not_initialized"}, status=503)
    
    app = web.Application()
    app.router.add_get('/health', health_handler)
    app.router.add_get('/status', status_handler)
    app.router.add_get('/metrics', metrics_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    health_port = int(os.getenv("HEALTH_CHECK_PORT", "8001"))
    site = web.TCPSite(runner, "0.0.0.0", health_port)
    
    logger.info(f"Health check server starting on port {health_port}")
    await site.start()
    
    return runner


async def metrics_handler(request):
    """Prometheus-style metrics endpoint"""
    from aiohttp import web
    
    if not worker:
        return web.Response(status=503)
    
    status = worker.get_status()
    metrics = f"""# HELP worker_jobs_processed Total jobs processed
# TYPE worker_jobs_processed counter
worker_jobs_processed{{{to_labels(worker.worker_id)}}} {status['jobs_processed']}

# HELP worker_jobs_failed Total jobs failed
# TYPE worker_jobs_failed counter
worker_jobs_failed{{{to_labels(worker.worker_id)}}} {status['jobs_failed']}

# HELP worker_uptime_seconds Worker uptime in seconds
# TYPE worker_uptime_seconds gauge
worker_uptime_seconds{{{to_labels(worker.worker_id)}}} {status['uptime_seconds']}

# HELP worker_running Worker is running
# TYPE worker_running gauge
worker_running{{{to_labels(worker.worker_id)}}} {1 if status['is_running'] else 0}
"""
    return web.Response(text=metrics, content_type='text/plain')


def to_labels(worker_id: str) -> str:
    """Convert worker_id to Prometheus label format"""
    return f'worker_id="{worker_id}"'


async def main():
    """Main worker process"""
    try:
        logger.info("Starting ITL ControlPlane Provider Worker")
        
        # Set up signal handlers
        await setup_signal_handlers()
        
        # Initialize worker components
        worker_inst, queue, reg = await initialize_worker()
        
        # Start health check server
        health_runner = await health_check_server()
        
        try:
            # Start worker and begin consuming jobs
            logger.info("Starting job consumption...")
            await worker_inst.start_consuming_jobs()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except asyncio.CancelledError:
            logger.info("Task cancelled")
        finally:
            # Cleanup
            logger.info("Cleaning up...")
            await health_runner.cleanup()
            
            if worker_inst and worker_inst.is_running:
                await worker_inst.stop()
            
            if queue:
                await queue.disconnect()
            
            logger.info("Worker stopped")
    
    except Exception as e:
        logger.error(f"Fatal error in worker: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║      ITL ControlPlane Provider Worker                      ║
║                                                            ║
║  Backend worker for processing provider operations         ║
║  Environment variables:                                   ║
║    - WORKER_ID: Worker identifier                         ║
║    - RABBITMQ_URL: RabbitMQ connection URL                ║
║    - LOG_LEVEL: Logging level (DEBUG/INFO/WARNING/ERROR)  ║
║    - HEALTH_CHECK_PORT: Health check server port          ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # Run main
    asyncio.run(main())
