# Worker Role API Reference

## Overview

Complete API reference for the ITL ControlPlane Worker Role system.

## Module Structure

```
itl_controlplane_sdk.workers
├── WorkerRole              # Abstract base class
├── ProviderWorker          # Concrete implementation
├── JobQueue                # Message-based job distribution
├── JobStatus               # Job status enumeration
├── JobResult               # Job result dataclass
├── WorkerRegistry          # Worker instance management
├── OffloadingProviderRegistry  # Provider registry with offloading
└── SyncOffloadingProviderRegistry  # Synchronous offloading
```

## Classes & Functions

### WorkerRole (Abstract Base Class)

Base class for implementing worker processes.

#### Constructor
```python
class WorkerRole(abc.ABC):
    def __init__(self, worker_id: str, worker_type: str = "generic")
```

**Parameters:**
- `worker_id` (str): Unique identifier for this worker instance
- `worker_type` (str): Type of work this worker handles (default: "generic")

#### Methods

##### async start()
```python
async def start()
```
Start the worker and initialize resources.

**Raises:**
- `Exception`: If worker initialization fails

**Example:**
```python
worker = MyWorker("worker-1")
await worker.start()
```

##### async stop()
```python
async def stop()
```
Stop the worker and clean up resources gracefully.

**Example:**
```python
await worker.stop()
```

##### async process_job()
```python
async def process_job(
    job_id: str,
    provider_namespace: str,
    resource_type: str,
    operation: str,
    request: ResourceRequest
) -> Dict[str, Any]
```

Process a single job.

**Parameters:**
- `job_id` (str): Unique job identifier
- `provider_namespace` (str): Provider namespace (e.g., "ITL.Core")
- `resource_type` (str): Resource type (e.g., "ResourceGroup")
- `operation` (str): Operation type: "create", "get", "delete", "list", "action"
- `request` (ResourceRequest): The resource request

**Returns:**
- Dict with keys: job_id, status, result, timestamp, (or) error

**Example:**
```python
result = await worker.process_job(
    job_id="123",
    provider_namespace="ITL.Core",
    resource_type="ResourceGroup",
    operation="create",
    request=request
)
```

##### get_status()
```python
def get_status() -> Dict[str, Any]
```

Get current worker status.

**Returns:**
- Dict with: worker_id, worker_type, is_running, jobs_processed, jobs_failed, uptime_seconds, started_at

**Example:**
```python
status = worker.get_status()
print(f"Jobs processed: {status['jobs_processed']}")
```

##### async _start_impl() [Abstract]
```python
async def _start_impl()
```
Subclass-specific initialization. Must be implemented by subclasses.

##### async _stop_impl() [Abstract]
```python
async def _stop_impl()
```
Subclass-specific cleanup. Must be implemented by subclasses.

##### async _process_job_impl() [Abstract]
```python
async def _process_job_impl(
    job_id: str,
    provider_namespace: str,
    resource_type: str,
    operation: str,
    request: ResourceRequest
) -> Dict[str, Any]
```
Subclass-specific job processing. Must be implemented by subclasses.

---

### ProviderWorker

Concrete implementation of WorkerRole for provider operations.

#### Constructor
```python
class ProviderWorker(WorkerRole):
    def __init__(
        self,
        worker_id: str,
        provider_registry: ResourceProviderRegistry,
        job_queue: JobQueue
    )
```

**Parameters:**
- `worker_id` (str): Unique worker identifier
- `provider_registry` (ResourceProviderRegistry): Provider registry with loaded providers
- `job_queue` (JobQueue): Job queue instance

**Example:**
```python
provider_registry = ResourceProviderRegistry()
provider_registry.register_provider("ITL.Core", "ResourceGroup", provider)

job_queue = JobQueue("amqp://localhost/")

worker = ProviderWorker(
    worker_id="worker-1",
    provider_registry=provider_registry,
    job_queue=job_queue
)
```

#### Methods

##### async start_consuming_jobs()
```python
async def start_consuming_jobs()
```

Start consuming and processing jobs from the queue.

**Example:**
```python
await worker.start()
await worker.start_consuming_jobs()
```

---

### JobQueue

Manages job distribution via RabbitMQ.

#### Constructor
```python
class JobQueue:
    def __init__(self, rabbitmq_url: str = "amqp://guest:guest@localhost/")
```

**Parameters:**
- `rabbitmq_url` (str): RabbitMQ connection URL

**Example:**
```python
queue = JobQueue(rabbitmq_url="amqp://guest:guest@rabbitmq:5672/")
await queue.connect()
```

#### Methods

##### async connect()
```python
async def connect()
```

Connect to RabbitMQ.

**Raises:**
- `ImportError`: If aio-pika is not installed
- `Exception`: If connection fails

##### async disconnect()
```python
async def disconnect()
```

Disconnect from RabbitMQ gracefully.

##### async submit_job()
```python
async def submit_job(
    provider_namespace: str,
    resource_type: str,
    operation: str,
    request: ResourceRequest,
    priority: int = 5
) -> str
```

Submit a job to the queue.

**Parameters:**
- `provider_namespace` (str): Provider namespace
- `resource_type` (str): Resource type
- `operation` (str): Operation: "create", "get", "delete", "list", "action"
- `request` (ResourceRequest): Resource request
- `priority` (int): Priority 0-10 (higher = more urgent, default: 5)

**Returns:**
- Job ID (str)

**Example:**
```python
job_id = await queue.submit_job(
    provider_namespace="ITL.Core",
    resource_type="ResourceGroup",
    operation="create",
    request=request,
    priority=7
)
print(f"Submitted job: {job_id}")
```

##### async consume_jobs()
```python
async def consume_jobs(
    worker_callback: Callable[[str, Dict[str, Any]], Awaitable[JobResult]]
)
```

Consume jobs and process with callback.

**Parameters:**
- `worker_callback` (Callable): Async function taking (job_id, job_payload) → JobResult

**Example:**
```python
async def my_worker(job_id, payload):
    # Process job
    return JobResult(job_id=job_id, status=JobStatus.COMPLETED)

await queue.consume_jobs(my_worker)
```

##### async get_result()
```python
async def get_result(
    job_id: str,
    timeout: float = 30.0
) -> Optional[JobResult]
```

Get job result (waits if not ready).

**Parameters:**
- `job_id` (str): Job ID
- `timeout` (float): Max wait time in seconds

**Returns:**
- JobResult or None if timeout

##### async get_queue_stats()
```python
async def get_queue_stats() -> Dict[str, Any]
```

Get queue statistics.

**Returns:**
- Dict with: connected, queues (mapping queue name to stats)

**Example:**
```python
stats = await queue.get_queue_stats()
# {
#   "connected": true,
#   "queues": {
#     "provider.jobs": {"message_count": 5, "consumer_count": 3},
#     "provider.results": {"message_count": 2, "consumer_count": 0}
#   }
# }
```

---

### JobStatus (Enum)

Job status values.

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

---

### JobResult (Dataclass)

Result of a job execution.

#### Constructor
```python
@dataclass
class JobResult:
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = None
```

#### Methods

##### to_dict()
```python
def to_dict() -> Dict[str, Any]
```

Convert to dictionary for serialization.

##### from_dict()
```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'JobResult'
```

Create JobResult from dictionary.

**Example:**
```python
result = JobResult(
    job_id="123",
    status=JobStatus.COMPLETED,
    result={"id": "rg-123"}
)

data = result.to_dict()
restored = JobResult.from_dict(data)
```

---

### WorkerRegistry

Manages multiple worker instances.

#### Constructor
```python
class WorkerRegistry:
    def __init__()
```

#### Methods

##### register_worker()
```python
def register_worker(worker: WorkerRole) -> None
```

Register a worker instance.

**Parameters:**
- `worker` (WorkerRole): Worker to register

**Raises:**
- `ValueError`: If worker_id already registered

##### unregister_worker()
```python
def unregister_worker(worker_id: str) -> bool
```

Unregister a worker.

**Returns:**
- True if unregistered, False if not found

##### get_worker()
```python
def get_worker(worker_id: str) -> Optional[WorkerRole]
```

Get a specific worker instance.

**Returns:**
- WorkerRole or None

##### get_workers_by_type()
```python
def get_workers_by_type(worker_type: str) -> List[WorkerRole]
```

Get all workers of a specific type.

**Returns:**
- List of WorkerRole instances

##### get_active_workers()
```python
def get_active_workers() -> List[WorkerRole]
```

Get all currently running workers.

##### list_workers()
```python
def list_workers() -> List[str]
```

List all registered worker IDs.

##### get_worker_status()
```python
def get_worker_status(worker_id: str) -> Optional[Dict[str, Any]]
```

Get status of specific worker.

##### get_all_worker_statuses()
```python
def get_all_worker_statuses() -> Dict[str, Dict[str, Any]]
```

Get status of all workers.

##### get_registry_status()
```python
def get_registry_status() -> Dict[str, Any]
```

Get overall registry status and statistics.

**Returns:**
- Dict with: created_at, total_workers, active_workers, total_jobs_processed, total_jobs_failed, workers

**Example:**
```python
status = registry.get_registry_status()
print(f"Active workers: {status['active_workers']}/{status['total_workers']}")
```

##### async start_all_workers()
```python
async def start_all_workers() -> None
```

Start all registered workers.

##### async stop_all_workers()
```python
async def stop_all_workers() -> None
```

Stop all registered workers.

##### async stop_worker()
```python
async def stop_worker(worker_id: str) -> bool
```

Stop specific worker.

**Returns:**
- True if stopped, False if not found

---

### OffloadingProviderRegistry

Provider registry that offloads to workers.

#### Constructor
```python
class OffloadingProviderRegistry(ResourceProviderRegistry):
    def __init__(self, job_queue: JobQueue)
```

**Parameters:**
- `job_queue` (JobQueue): Job queue instance

#### Methods

All methods from ResourceProviderRegistry plus:

##### async create_or_update_resource()
```python
async def create_or_update_resource(
    provider_namespace: str,
    resource_type: str,
    request: ResourceRequest
) -> ResourceResponse
```

Create/update resource via worker (async).

**Returns:**
- ResourceResponse with job_id (status="pending")

##### async get_resource()
```python
async def get_resource(
    provider_namespace: str,
    resource_type: str,
    request: ResourceRequest
) -> ResourceResponse
```

Get resource via worker (async).

##### async list_resources()
```python
async def list_resources(
    provider_namespace: str,
    resource_type: str,
    request: ResourceRequest
) -> ResourceListResponse
```

List resources via worker (async).

##### async delete_resource()
```python
async def delete_resource(
    provider_namespace: str,
    resource_type: str,
    request: ResourceRequest
) -> ResourceResponse
```

Delete resource via worker (async).

##### async execute_action()
```python
async def execute_action(
    provider_namespace: str,
    resource_type: str,
    request: ResourceRequest
) -> ResourceResponse
```

Execute action via worker (async).

##### async get_job_result()
```python
async def get_job_result(
    job_id: str,
    timeout: float = 30.0
) -> Optional[Dict[str, Any]]
```

Get job result with optional wait.

**Parameters:**
- `job_id` (str): Job ID
- `timeout` (float): Wait timeout in seconds (0 = no wait)

**Returns:**
- Job result dict or None

##### async get_queue_stats()
```python
async def get_queue_stats() -> Dict[str, Any]
```

Get queue statistics.

---

### SyncOffloadingProviderRegistry

Offloading registry that blocks until job completes.

#### Constructor
```python
class SyncOffloadingProviderRegistry(OffloadingProviderRegistry):
    def __init__(
        self,
        job_queue: JobQueue,
        default_timeout: float = 30.0
    )
```

**Parameters:**
- `job_queue` (JobQueue): Job queue instance
- `default_timeout` (float): Default timeout for results (seconds)

#### Additional Methods

##### async create_or_update_resource_sync()
```python
async def create_or_update_resource_sync(
    provider_namespace: str,
    resource_type: str,
    request: ResourceRequest,
    timeout: Optional[float] = None
) -> ResourceResponse
```

Synchronously create/update resource (waits for completion).

**Parameters:**
- `timeout` (Optional[float]): Override default timeout

**Returns:**
- Completed ResourceResponse

**Example:**
```python
registry = SyncOffloadingProviderRegistry(job_queue)

response = await registry.create_or_update_resource_sync(
    "ITL.Core", "ResourceGroup", request, timeout=60
)
# Waits up to 60 seconds for job to complete
```

---

## Environment Variables

### Worker Process
```
WORKER_ID=worker-1                          # Auto-generated if not set
RABBITMQ_URL=amqp://guest:guest@localhost/ # RabbitMQ URL
LOG_LEVEL=INFO                              # DEBUG|INFO|WARNING|ERROR
HEALTH_CHECK_PORT=8001                      # Health check endpoint port
```

### API Server
```
OFFLOADING_ENABLED=true                     # Enable worker offloading
RABBITMQ_URL=amqp://guest:guest@localhost/ # RabbitMQ URL
JOB_TIMEOUT=300                             # Default job timeout (seconds)
```

## Health Check Endpoints

### /health
```json
GET /health

200 OK:
{
  "status": "healthy",
  "worker_id": "worker-1"
}

503 Service Unavailable:
{
  "status": "unhealthy"
}
```

### /status
```json
GET /status

200 OK:
{
  "worker_id": "worker-1",
  "worker_type": "provider",
  "is_running": true,
  "jobs_processed": 1542,
  "jobs_failed": 3,
  "uptime_seconds": 3600,
  "started_at": "2024-02-10T12:00:00+00:00"
}
```

### /metrics
```
GET /metrics

# HELP worker_jobs_processed Total jobs processed
# TYPE worker_jobs_processed counter
worker_jobs_processed{worker_id="worker-1"} 1542

# HELP worker_jobs_failed Total jobs failed
# TYPE worker_jobs_failed counter
worker_jobs_failed{worker_id="worker-1"} 3

# HELP worker_uptime_seconds Worker uptime in seconds
# TYPE worker_uptime_seconds gauge
worker_uptime_seconds{worker_id="worker-1"} 3600

# HELP worker_running Worker is running
# TYPE worker_running gauge
worker_running{worker_id="worker-1"} 1
```

## Error Handling

### Common Exceptions

**ImportError**
```python
# When aio-pika is not installed
raise ImportError("aio-pika is required for JobQueue. Install with: pip install aio-pika")
```

**ValueError**
```python
# When provider not found
raise ValueError(f"No provider found for {provider_namespace}/{resource_type}")

# When worker_id already registered
raise ValueError(f"Worker with ID {worker_id} is already registered")
```

**Exception**
```python
# Job processing errors
# Caught and returned as JobResult with status=FAILED
```

## Best Practices

1. **Always call disconnect()** before shutdown
   ```python
   try:
       await worker.start()
   finally:
       await worker.stop()
       await job_queue.disconnect()
   ```

2. **Use appropriate job priority**
   ```python
   # Get operations (high priority, low latency)
   await queue.submit_job(..., priority=8)
   
   # Create operations (normal priority)
   await queue.submit_job(..., priority=5)
   
   # Background jobs (low priority)
   await queue.submit_job(..., priority=2)
   ```

3. **Set reasonable timeouts**
   ```python
   # Short timeout for synchronous operations
   result = await queue.get_result(job_id, timeout=10)
   
   # Longer timeout for background operations
   result = await queue.get_result(job_id, timeout=300)
   ```

4. **Monitor queue health**
   ```python
   stats = await queue.get_queue_stats()
   if stats['queues']['provider.jobs.dlq']['message_count'] > 0:
       # Dead-letter queue has items - investigate failures
   ```

5. **Scale appropriately**
   ```python
   # High throughput
   workers.replicaCount = 20
   workers.maxConcurrentJobs = 10
   
   # Long-running jobs
   workers.replicaCount = 3
   workers.maxConcurrentJobs = 1
   workers.jobTimeout = 600
   ```

## See Also

- [Worker Role Architecture](./21-WORKER_ROLE_ARCHITECTURE.md)
- [Quick Start Guide](./22-WORKER_ROLE_QUICK_START.md)
- [Deployment Guide](../charts/WORKER_DEPLOYMENT_GUIDE.md)
- [Example Implementation](./examples/worker_role_example.py)
