# Worker Roles: Asynchronous Job Processing

**Status**: ✅ Production-Ready  
**Implementation**: Complete worker system with Kubernetes integration  
**Coverage**: Job queues, worker lifecycle, async offloading, scaling

Enable horizontal scaling and asynchronous processing of provider operations. Offload long-running tasks to backend worker pods while API server returns immediately with job tracking IDs.

---

## 🎯 Overview

The **Worker Role system** transforms synchronous provider operations into asynchronous, scalable jobs:

### Before (Synchronous, Blocking)
```
Client Request
    ↓
API Server ─→ Provider Logic (blocking for 5+ seconds) ─→ Response
                ↓
            Client waits for completion
```

### After (Asynchronous, Non-blocking)
```
Client Request
    ↓
API Server ─→ Submit to Queue (instant) ─→ Response with job_id
                    ↓
            Worker Pod (processes asynchronously)
                    ↓
            Result stored for polling
```

### Key Benefits

✅ **Horizontal Scaling** — Scale worker pods independently from API  
✅ **Async Processing** — Client gets immediate response with job_id  
✅ **Load Distribution** — Multiple workers share operation workload  
✅ **Resilience** — Failed jobs captured in dead-letter queue  
✅ **Kubernetes Native** — Full RBAC, health checks, Prometheus metrics  
✅ **Production Ready** — Used in ITL ControlPlane core infrastructure

---

## 🏗️ Architecture

### System Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    API Server (Main)                         │
│  - Receives HTTP requests                                    │
│  - Validates input                                           │
│  - Submits jobs to queue                                     │
│  - Returns job_id to client for tracking                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Submit Job
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              RabbitMQ Job Queue (Message Broker)             │
│  - provider.jobs: Queue for pending jobs                     │
│  - provider.results: Queue for job results                   │
│  - provider.jobs.dlq: Dead-letter queue for failures         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Consume Job
                       ▼
┌──────────────────────────────────────────────────────────────┐
│            Worker Pod #1    Worker Pod #2    Worker Pod #3   │
│  ┌────────────────────┐ ┌────────────────────┐              │
│  │ ProviderWorker     │ │ ProviderWorker     │              │
│  │ - Process jobs     │ │ - Process jobs     │              │
│  │ - Execute ops      │ │ - Execute ops      │              │
│  │ - Store results    │ │ - Store results    │              │
│  └────────────────────┘ └────────────────────┘              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Publish Result
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Result Store (Redis/Cache)                      │
│  (Clients poll this for job completion)                      │
└─────────────────────────────────────────────────────────────┘
```

### Components

| Component | Purpose | Implementation |
|-----------|---------|-----------------|
| **JobQueue** | Reliable job distribution | RabbitMQ-based message broker |
| **WorkerRole** | Abstract base class | Lifecycle + processing interface |
| **ProviderWorker** | Concrete worker | Consumes jobs, executes operations |
| **OffloadingProviderRegistry** | Async job submission | Replaces sync registry for offloading |
| **WorkerRegistry** | Worker fleet management | Tracks active workers and health |

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Enable Workers in Helm

```bash
# Development (1 worker)
helm install core-provider ./charts \
  -f charts/values-dev.yaml

# Production (5 workers with HA)
helm install core-provider ./charts \
  -f charts/values-prod.yaml
```

### Step 2: Use OffloadingProviderRegistry in API

```python
from itl_controlplane_sdk.workers import OffloadingProviderRegistry, JobQueue
from fastapi import FastAPI

app = FastAPI()
job_queue = JobQueue(rabbitmq_url="amqp://guest:guest@rabbitmq/")
registry = OffloadingProviderRegistry(job_queue)

@app.post("/resources")
async def create_resource(request: ResourceRequest):
    # Submit to workers, get immediate response
    response = await registry.create_or_update_resource(
        "ITL.Core", "ResourceGroup", request
    )
    
    # Client gets job_id to track progress
    return {
        "job_id": response.job_id,
        "status": "pending",
        "message": "Operation submitted to worker queue"
    }

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    # Poll for result
    result = await registry.get_job_result(job_id)
    return result or {"status": "pending"}
```

### Step 3: Monitor Workers

```bash
# Check workers are running
kubectl get pods -l app.kubernetes.io/component=worker

# View worker logs
kubectl logs -f deployment/core-provider-worker

# Check health
kubectl exec <worker-pod> -- curl http://localhost:8001/health

# See RabbitMQ management UI
kubectl port-forward svc/rabbitmq 15672:15672
# Visit http://localhost:15672
```

---

## 📚 Components & API Reference

### JobQueue

Handles message distribution and job lifecycle via RabbitMQ.

#### Constructor
```python
job_queue = JobQueue(
    rabbitmq_url="amqp://guest:guest@localhost/"
)
```

#### Submit Job
```python
job_id = await job_queue.submit_job(
    provider_namespace="ITL.Core",
    resource_type="ResourceGroup",
    operation="create",
    request=request,
    priority=7  # 0-10, higher = more urgent
)
```

**Returns:** Job ID (string)

#### Get Result
```python
result = await job_queue.get_result(
    job_id="abc-123",
    timeout=30.0  # Wait up to 30 seconds
)
# Returns JobResult or None if timeout
```

#### Queue Statistics
```python
stats = await job_queue.get_queue_stats()
# {
#   "connected": true,
#   "queues": {
#     "provider.jobs": {"message_count": 5, "consumer_count": 3},
#     "provider.jobs.dlq": {"message_count": 0}
#   }
# }
```

---

### WorkerRole (Abstract Base)

Base class for implementing worker processes.

#### Methods

```python
class WorkerRole:
    # Lifecycle
    async def start()           # Start worker
    async def stop()            # Stop gracefully
    
    # Job processing
    async def process_job(      # Process single job
        job_id: str,
        provider_namespace: str,
        resource_type: str,
        operation: str,
        request: ResourceRequest
    ) -> Dict[str, Any]
    
    # Status
    def get_status() -> Dict    # Get worker status
```

---

### ProviderWorker

Concrete worker implementation for provider operations.

#### Constructor
```python
worker = ProviderWorker(
    worker_id="worker-1",
    provider_registry=registry,    # ResourceProviderRegistry
    job_queue=job_queue           # JobQueue instance
)
```

#### Usage
```python
await worker.start()
await worker.start_consuming_jobs()  # Blocks, consuming jobs
```

---

### OffloadingProviderRegistry

Provider registry that submits jobs instead of executing directly.

#### Constructor
```python
registry = OffloadingProviderRegistry(job_queue)
```

#### Operations (All Async)
```python
# Create/Update
response = await registry.create_or_update_resource(
    "ITL.Core", "ResourceGroup", request
)
# Returns: ResourceResponse with job_id (status="pending")

# Get
response = await registry.get_resource(
    "ITL.Core", "ResourceGroup", request
)

# Delete
response = await registry.delete_resource(
    "ITL.Core", "ResourceGroup", request
)

# List
response = await registry.list_resources(
    "ITL.Core", "ResourceGroup", request
)

# Action
response = await registry.execute_action(
    "ITL.Core", "ResourceGroup", request
)
```

#### Poll for Results
```python
result = await registry.get_job_result(
    job_id="abc-123",
    timeout=30.0  # Wait timeout in seconds
)
```

---

### SyncOffloadingProviderRegistry

Blocking variant that waits for job completion.

```python
registry = SyncOffloadingProviderRegistry(
    job_queue=job_queue,
    default_timeout=30.0
)

# Waits for job to complete
response = await registry.create_or_update_resource_sync(
    "ITL.Core", "ResourceGroup", request,
    timeout=60  # Override default
)
# Returns completed ResourceResponse
```

---

### WorkerRegistry

Manages multiple worker instances and fleet.

```python
registry = WorkerRegistry()

# Register worker
registry.register_worker(worker)

# Get status
status = registry.get_registry_status()
# {
#   "total_workers": 3,
#   "active_workers": 3,
#   "total_jobs_processed": 1542,
#   "total_jobs_failed": 3
# }

# Start/stop all
await registry.start_all_workers()
await registry.stop_all_workers()
```

---

## ⚙️ Configuration

### Development (1 Worker)

```yaml
workers:
  enabled: true
  replicaCount: 1
  logLevel: DEBUG
  
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 250m
      memory: 256Mi
```

### Production (5 Workers, HA)

```yaml
workers:
  enabled: true
  replicaCount: 5
  logLevel: INFO
  jobTimeout: 600
  maxConcurrentJobs: 10
  
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 1Gi
  
  podDisruptionBudget:
    enabled: true
    minAvailable: 3
  
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - topologyKey: kubernetes.io/hostname
```

### High-Throughput (20 Workers)

```yaml
workers:
  enabled: true
  replicaCount: 20
  logLevel: WARNING
  maxConcurrentJobs: 10
  
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
  
  autoscaling:
    enabled: true
    minReplicas: 10
    maxReplicas: 50
    targetCPUUtilizationPercentage: 70
```

### Environment Variables

**Worker Process:**
```
WORKER_ID=worker-1                          # Auto-generated if not set
RABBITMQ_URL=amqp://guest:guest@localhost/ # RabbitMQ URL
LOG_LEVEL=INFO                              # DEBUG|INFO|WARNING|ERROR
HEALTH_CHECK_PORT=8001                      # Health check endpoint
```

**API Server:**
```
OFFLOADING_ENABLED=true                     # Enable worker offloading
RABBITMQ_URL=amqp://guest:guest@localhost/ # RabbitMQ URL
JOB_TIMEOUT=300                             # Default job timeout (seconds)
```

---

## 🚀 Deployment (Kubernetes/Helm)

### Files Created

| File | Purpose |
|------|---------|
| `worker-deployment.yaml` | Worker Pod Deployment |
| `worker-serviceaccount.yaml` | ServiceAccount for RBAC |
| `worker-clusterrole.yaml` | ClusterRole (minimal permissions) |
| `worker-clusterrolebinding.yaml` | ClusterRoleBinding binding |
| `worker-configmap.yaml` | Worker configuration |
| `worker-pdb.yaml` | PodDisruptionBudget for HA |

### Helm Install

```bash
# Development
helm install core-provider ./charts \
  -f charts/values-dev.yaml

# Production
helm install core-provider ./charts \
  -f charts/values-prod.yaml \
  --set workers.replicaCount=5

# Custom configuration
helm install core-provider ./charts \
  --set workers.enabled=true \
  --set workers.replicaCount=10 \
  --set workers.resources.limits.memory=2Gi
```

### Verify Deployment

```bash
# Check workers are running
kubectl get pods -l app.kubernetes.io/component=worker

# Check logs
kubectl logs -f deployment/core-provider-worker

# Check health
kubectl exec <worker-pod> -- curl http://localhost:8001/health
# {"status": "healthy", "worker_id": "worker-1"}
```

---

## 📊 Health & Monitoring

### Health Check Endpoints

Each worker exposes health check endpoints:

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /health` | Liveness probe | `{"status": "healthy"}` |
| `GET /status` | Detailed status | Worker metrics JSON |
| `GET /metrics` | Prometheus metrics | Metrics in Prometheus format |

### Status Endpoint Response

```json
GET /status

{
  "worker_id": "worker-1",
  "worker_type": "provider",
  "is_running": true,
  "jobs_processed": 1542,
  "jobs_failed": 3,
  "uptime_seconds": 3600,
  "started_at": "2024-02-10T12:00:00Z"
}
```

### Prometheus Metrics

```
worker_jobs_processed{worker_id="worker-1"} 1542
worker_jobs_failed{worker_id="worker-1"} 3
worker_uptime_seconds{worker_id="worker-1"} 3600
worker_running{worker_id="worker-1"} 1
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Monitor RabbitMQ

```bash
# Port-forward to RabbitMQ management UI
kubectl port-forward svc/rabbitmq 15672:15672

# Visit http://localhost:15672
# Username: guest
# Password: guest

# Check queue depths, consumer counts, message rates
```

---

## 📈 Scaling Strategies

### Horizontal Scaling (Number of Workers)

```bash
# Scale to 10 workers
kubectl scale deployment core-provider-worker --replicas=10

# Auto-scaling (via HPA)
kubectl autoscale deployment core-provider-worker \
  --min=3 --max=20 --cpu-percent=70
```

### Vertical Scaling (Worker Resources)

```yaml
workers:
  resources:
    requests:
      cpu: 2000m        # Allocate for CPU-bound operations
      memory: 2Gi       # Allocate for memory-intensive ops
    limits:
      cpu: 4000m
      memory: 4Gi
```

### Job Priority

```python
# Urgent jobs (priority 9)
await queue.submit_job(..., priority=9)

# Normal jobs (priority 5)
await queue.submit_job(..., priority=5)

# Background jobs (priority 1)
await queue.submit_job(..., priority=1)
```

### Scaling Rules of Thumb

| Workload | Workers | Max Jobs | Timeout | Resources |
|----------|---------|----------|---------|-----------|
| Light (1K jobs/day) | 1-2 | 5 | 300s | 256Mi mem |
| Medium (10K jobs/day) | 5-10 | 10 | 300s | 512Mi mem |
| Heavy (100K jobs/day) | 20+ | 20 | 600s | 2Gi mem |
| Long-running | 3-5 | 1 | 3600s | 1Gi mem |

---

## ⚠️ Error Handling & Resilience

### Dead-Letter Queue (DLQ)

Failed jobs are automatically moved to DLQ for analysis:

```
provider.jobs → [Processing]
    ├── SUCCESS ✓ → Result stored
    └── FAILURE → provider.jobs.dlq
```

### Check DLQ

```python
# Get queue statistics
stats = await job_queue.get_queue_stats()
dlq_count = stats['queues']['provider.jobs.dlq']['message_count']

if dlq_count > 0:
    # Investigate failure cause
    logger.error(f"Jobs in DLQ: {dlq_count}")
```

### JobStatus Enum

```python
class JobStatus(str, Enum):
    PENDING = "pending"      # Waiting to be processed
    PROCESSING = "processing" # Currently being processed
    COMPLETED = "completed"   # Successfully completed
    FAILED = "failed"         # Failed, moved to DLQ
    CANCELLED = "cancelled"   # Explicitly cancelled
```

### JobResult Structure

```python
@dataclass
class JobResult:
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = None
```

### Custom Error Handling

```python
class CustomWorker(ProviderWorker):
    async def _process_job_impl(self, job_id, ...):
        try:
            result = await self._execute_provider_operation(...)
            return result
        except ValueError as e:
            # Invalid request - don't retry
            logger.warning(f"Invalid request {job_id}: {e}")
            raise
        except Exception as e:
            # Unexpected error - will retry via DLQ
            logger.error(f"Job failed {job_id}: {e}")
            raise
```

---

## 🔒 Security

### RBAC (ClusterRole)

```yaml
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]

- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]
```

### RabbitMQ Credentials

```bash
# Create secret with credentials
kubectl create secret generic core-provider-rabbitmq \
  --from-literal=url="amqp://user:password@rabbitmq:5672/"

# Reference in Helm
workers:
  rabbitmq:
    secretName: core-provider-rabbitmq
```

### Security Context

```yaml
workers:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    readOnlyRootFilesystem: true
```

---

## 🆘 Troubleshooting

### Workers Not Consuming Jobs

**Problem:** Workers deployed but not processing jobs

**Solution:**
```bash
# 1. Check RabbitMQ is running
kubectl get svc rabbitmq

# 2. Check worker logs
kubectl logs deployment/core-provider-worker

# 3. Verify RABBITMQ_URL
kubectl get deployment -o yaml | grep RABBITMQ_URL

# 4. Test RabbitMQ connectivity
kubectl exec <worker-pod> -- \
  python -c "from aio_pika import connect; connect('amqp://...')"
```

### Jobs Stuck in Queue

**Problem:** Jobs submitted but never processed

**Solution:**
```bash
# 1. Check worker count
kubectl get pods -l app.kubernetes.io/component=worker

# 2. Check worker health
kubectl exec <pod> -- curl http://localhost:8001/health

# 3. Check queue stats
kubectl exec <pod> -- curl http://localhost:8001/queue-stats

# 4. Scale up workers
kubectl scale deployment core-provider-worker --replicas=10
```

### High Job Failure Rate

**Problem:** Many jobs in dead-letter queue

**Solution:**
```bash
# 1. Check worker logs
kubectl logs deployment/core-provider-worker | grep failed

# 2. Check resource usage
kubectl top pods -l app.kubernetes.io/component=worker

# 3. Increase resources
helm upgrade core-provider ./charts \
  --set workers.resources.limits.memory=2Gi

# 4. Inspect DLQ messages via RabbitMQ UI
kubectl port-forward svc/rabbitmq 15672:15672
```

### Worker Crashes

**Problem:** Workers pod keeps restarting

**Solution:**
```bash
# 1. Check logs
kubectl logs <pod-name>

# 2. Check resource limits
kubectl describe pod <pod-name>

# 3. Check RabbitMQ connection
kubectl exec <pod> -- env | grep RABBITMQ

# 4. Increase memory limit
helm upgrade --set workers.resources.limits.memory=1Gi
```

---

## 💡 Real-World Examples

### Example 1: API with Offloading

```python
from fastapi import FastAPI
from itl_controlplane_sdk.workers import OffloadingProviderRegistry, JobQueue

app = FastAPI()
job_queue = JobQueue(rabbitmq_url="amqp://guest:guest@rabbitmq/")
registry = OffloadingProviderRegistry(job_queue)

@app.post("/resources")
async def create_resource(request: ResourceRequest):
    response = await registry.create_or_update_resource(
        "ITL.Core", "ResourceGroup", request
    )
    return {
        "job_id": response.job_id,
        "status": "pending",
        "location": f"/jobs/{response.job_id}"
    }

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    result = await registry.get_job_result(job_id, timeout=0)
    if result:
        return result
    return {"status": "pending", "job_id": job_id}
```

### Example 2: Worker Pool Setup

```python
import asyncio
from itl_controlplane_sdk.workers import ProviderWorker, JobQueue, WorkerRegistry
from itl_controlplane_sdk.providers import ResourceProviderRegistry

async def main():
    # Create queue
    job_queue = JobQueue(rabbitmq_url="amqp://guest:guest@rabbitmq/")
    
    # Create provider registry
    provider_registry = ResourceProviderRegistry()
    provider_registry.register_provider("ITL.Core", "ResourceGroup", core_provider)
    
    # Create worker registry
    worker_registry = WorkerRegistry()
    
    # Start 5 workers
    for i in range(5):
        worker = ProviderWorker(
            worker_id=f"worker-{i}",
            provider_registry=provider_registry,
            job_queue=job_queue
        )
        worker_registry.register_worker(worker)
        asyncio.create_task(worker.start_consuming_jobs())
    
    # Monitor
    status = worker_registry.get_registry_status()
    print(f"Started {status['total_workers']} workers")
    
    # Keep running
    await asyncio.sleep(float('inf'))

asyncio.run(main())
```

### Example 3: Synchronous Offloading

```python
from itl_controlplane_sdk.workers import SyncOffloadingProviderRegistry, JobQueue

registry = SyncOffloadingProviderRegistry(
    job_queue=job_queue,
    default_timeout=30.0
)

# Waits for job to complete
try:
    response = await registry.create_or_update_resource_sync(
        "ITL.Core", "ResourceGroup", request,
        timeout=60
    )
    print(f"Created: {response.id}")
except asyncio.TimeoutError:
    print("Job timed out after 60 seconds")
```

---

## 👍 Best Practices

### Priority Management

```python
# Get operations (high priority, low latency SLA)
await queue.submit_job(..., priority=8)

# Create operations (normal priority)
await queue.submit_job(..., priority=5)

# Background jobs (low priority)
await queue.submit_job(..., priority=2)
```

### Timeout Configuration

```python
# Short timeout for synchronous operations
result = await queue.get_result(job_id, timeout=10)

# Longer timeout for background operations
result = await queue.get_result(job_id, timeout=300)
```

### Resource Monitoring

```python
# Monitor queue health
stats = await queue.get_queue_stats()
if stats['queues']['provider.jobs.dlq']['message_count'] > 0:
    # Investigate failures
    logger.error("Jobs in dead-letter queue")
```

### Graceful Shutdown

```python
try:
    await worker.start()
finally:
    await worker.stop()
    await job_queue.disconnect()
```

---

## 🔗 Related Documentation

- [08-API_ENDPOINTS.md](08-API_ENDPOINTS.md) - FastAPI integration
- [06-HANDLER_MIXINS.md](06-HANDLER_MIXINS.md) - Handler patterns
- [07-LOCATION_VALIDATION.md](07-LOCATION_VALIDATION.md) - Validation
- [23-BEST_PRACTICES.md](23-BEST_PRACTICES.md) - Best practices

---

## 📖 Quick Reference

### Install
```bash
pip install aio-pika  # Required for JobQueue
```

### Create Job Queue
```python
from itl_controlplane_sdk.workers import JobQueue

queue = JobQueue(rabbitmq_url="amqp://guest:guest@rabbitmq/")
```

### Submit Job
```python
job_id = await queue.submit_job(
    provider_namespace="ITL.Core",
    resource_type="ResourceGroup",
    operation="create",
    request=request,
    priority=5
)
```

### Get Result
```python
result = await queue.get_result(job_id, timeout=30)
```

### Create Registry
```python
from itl_controlplane_sdk.workers import OffloadingProviderRegistry

registry = OffloadingProviderRegistry(queue)
```

### Use in API
```python
response = await registry.create_or_update_resource(
    "ITL.Core", "ResourceGroup", request
)
return {"job_id": response.job_id, "status": "pending"}
```

---

**Document Version**: 1.0 (Consolidated from 4 docs)  
**Last Updated**: February 14, 2026  
**Status**: ✅ Production-Ready

