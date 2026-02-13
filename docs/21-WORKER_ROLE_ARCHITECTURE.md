# Worker Role Architecture

## Overview

The Worker Role system enables **horizontal scaling and asynchronous processing** of provider operations in the ITL ControlPlane. Instead of processing all requests synchronously in the API server, operations are offloaded to backend worker pods that process them from a job queue.

## Architecture

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
│              Redis/Store for Job Results                     │
│  (Clients poll this for job completion)                      │
└─────────────────────────────────────────────────────────────┘
```

## Key Benefits

1. **Horizontal Scaling**: Add or remove workers without affecting the API server
2. **Async Processing**: Client gets immediate response with job_id; results ready when complete
3. **Resilience**: Failures in one worker don't impact the API or other workers
4. **Load Distribution**: Multiple workers share the workload
5. **Resource Optimization**: Separate resource limits for API vs workers
6. **Dead-Letter Queue**: Failed jobs are captured for analysis and retry

## Components

### 1. JobQueue
**Location**: `itl_controlplane_sdk.workers.JobQueue`

Handles message distribution and job lifecycle:

```python
# Submit a job to the queue
job_id = await job_queue.submit_job(
    provider_namespace="ITL.Core",
    resource_type="ResourceGroup",
    operation="create",
    request=request,
    priority=7  # Higher value = more urgent
)

# Get queue statistics
stats = await job_queue.get_queue_stats()
# Returns message counts, consumer counts per queue
```

### 2. WorkerRole (Abstract Base Class)
**Location**: `itl_controlplane_sdk.workers.WorkerRole`

Base class for all worker implementations:

```python
class WorkerRole(abc.ABC):
    async def start()          # Start the worker
    async def stop()           # Stop gracefully
    async def process_job()    # Process a single job
    def get_status()           # Get worker status
```

### 3. ProviderWorker (Concrete Implementation)
**Location**: `itl_controlplane_sdk.workers.ProviderWorker`

Processes provider operations by consuming jobs and executing them:

```python
worker = ProviderWorker(
    worker_id="worker-1",
    provider_registry=registry,
    job_queue=job_queue
)

await worker.start_consuming_jobs()
```

### 4. OffloadingProviderRegistry
**Location**: `itl_controlplane_sdk.workers.OffloadingProviderRegistry`

Extends `ResourceProviderRegistry` to submit jobs instead of executing directly:

```python
# Use instead of standard registry
offloading_registry = OffloadingProviderRegistry(job_queue)

# Returns immediately with job_id
response = await offloading_registry.create_or_update_resource(...)
# response.job_id can be used to poll for results
```

### 5. WorkerRegistry
**Location**: `itl_controlplane_sdk.workers.WorkerRegistry`

Manages multiple worker instances and their lifecycle:

```python
registry = WorkerRegistry()

# Register worker
registry.register_worker(worker)

# Get status of all workers
status = registry.get_registry_status()
# {
#   "total_workers": 3,
#   "active_workers": 3,
#   "total_jobs_processed": 1542,
#   "workers": { ... }
# }
```

## Usage Examples

### 1. Simple Worker Setup

```python
import asyncio
from itl_controlplane_sdk.workers import (
    ProviderWorker, JobQueue, OffloadingProviderRegistry
)
from itl_controlplane_sdk.providers import ResourceProviderRegistry

async def main():
    # Create components
    job_queue = JobQueue(rabbitmq_url="amqp://guest:guest@localhost/")
    provider_registry = ResourceProviderRegistry()
    
    # Register your providers
    provider_registry.register_provider("ITL.Core", "ResourceGroup", core_provider)
    
    # Create worker
    worker = ProviderWorker(
        worker_id="worker-1",
        provider_registry=provider_registry,
        job_queue=job_queue
    )
    
    # Start consuming jobs
    await worker.start_consuming_jobs()

asyncio.run(main())
```

### 2. API Server with Offloading

```python
from fastapi import FastAPI
from itl_controlplane_sdk.workers import OffloadingProviderRegistry, JobQueue

app = FastAPI()

# Create offloading registry
job_queue = JobQueue(rabbitmq_url=os.getenv("RABBITMQ_URL"))
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

### 3. Kubernetes Deployment

```bash
# Deploy with worker enabled
helm install core-provider ./charts \
  --set workers.enabled=true \
  --set workers.replicaCount=5
```

## Configuration

### Environment Variables

**API Server**:
- `OFFLOADING_ENABLED`: Set to `true` to use OffloadingProviderRegistry
- `RABBITMQ_URL`: RabbitMQ connection URL
- `JOB_TIMEOUT`: Default timeout for job results (seconds)

**Worker Process**:
- `WORKER_ID`: Unique identifier for this worker (auto-generated if not set)
- `RABBITMQ_URL`: RabbitMQ connection URL
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)
- `HEALTH_CHECK_PORT`: Port for health checks (default: 8001)

### Helm Values

```yaml
workers:
  enabled: true
  replicaCount: 3
  
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
  
  logLevel: INFO
  jobTimeout: 300
  
  rabbitmq:
    enabled: false
    externalUrl: "amqp://guest:guest@rabbitmq:5672/"
  
  podDisruptionBudget:
    enabled: true
    minAvailable: 1
```

## Health Checks and Monitoring

### Worker Health Endpoint

Each worker exposes a health check endpoint:

```bash
# Check worker health
curl http://worker-pod:8001/health
# {"status": "healthy", "worker_id": "worker-1"}

# Get worker status
curl http://worker-pod:8001/status
# {
#   "worker_id": "worker-1",
#   "is_running": true,
#   "jobs_processed": 1542,
#   "jobs_failed": 3,
#   "uptime_seconds": 3600
# }

# Get Prometheus metrics
curl http://worker-pod:8001/metrics
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

## Scaling Considerations

### Horizontal Scaling

```bash
# Increase workers
kubectl scale deployment core-provider-worker --replicas=10

# With Helm autoscaling (future enhancement)
helm upgrade core-provider ./charts \
  --set workers.autoscaling.enabled=true \
  --set workers.autoscaling.minReplicas=3 \
  --set workers.autoscaling.maxReplicas=20
```

### Job Priority

Submit higher-priority jobs with higher priority values:

```python
# Urgent job (priority 9)
await job_queue.submit_job(..., priority=9)

# Low-priority job (priority 1)
await job_queue.submit_job(..., priority=1)
```

## Error Handling and Retries

### Dead-Letter Queue (DLQ)

Failed jobs are automatically moved to DLQ:

```
provider.jobs → [Processing] → SUCCESS ✓
                            → FAILURE → provider.jobs.dlq
```

To manually retry a failed job:

```python
# Check DLQ
dlq_stats = await job_queue.get_queue_stats()
print(dlq_stats['queues']['provider.jobs.dlq'])

# Resubmit job from DLQ
await job_queue.submit_job(...)
```

### Custom Error Handling

```python
class CustomWorker(ProviderWorker):
    async def _process_job_impl(self, job_id, ...):
        try:
            # Process job
            result = await self._execute_provider_operation(...)
            return result
        except ValueError as e:
            # Log and skip (don't retry)
            logger.warning(f"Invalid request {job_id}: {e}")
            raise
        except Exception as e:
            # Log for retry
            logger.error(f"Unexpected error {job_id}: {e}")
            raise
```

## Security Considerations

### RBAC for Workers

```yaml
# Worker role has minimal permissions
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
  
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]
```

### RabbitMQ Credentials

```bash
# Create secret with RabbitMQ credentials
kubectl create secret generic core-provider-rabbitmq \
  --from-literal=url="amqp://user:password@rabbitmq:5672/"

# Reference in Helm values
workers:
  rabbitmq:
    enabled: true
    secretName: core-provider-rabbitmq
```

### Network Policies

```yaml
# Only allow worker ↔ RabbitMQ communication
networkPolicy:
  enabled: true
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app.kubernetes.io/component: worker
      ports:
      - port: 5672  # RabbitMQ port
```

## Troubleshooting

### Check Worker Status

```bash
# Check all workers
kubectl get pods -l app.kubernetes.io/component=worker

# Check specific worker logs
kubectl logs core-provider-worker-abc123

# Check worker health
kubectl exec core-provider-worker-abc123 -- curl localhost:8001/health
```

### Check Job Queue

```bash
# Port-forward to RabbitMQ management UI
kubectl port-forward svc/rabbitmq 15672:15672
# Visit http://localhost:15672

# Check queue stats from worker
kubectl exec core-provider-worker-abc123 -- \
  curl localhost:8001/queue-stats
```

### Common Issues

**Workers not processing jobs**:
- Check RabbitMQ connection: `kubectl exec worker -- printenv | grep RABBITMQ`
- Verify queue connectivity: `kubectl logs worker | grep "Connecting to RabbitMQ"`
- Check for errors: `kubectl logs worker --tail=100`

**Job timeout**:
- Increase job timeout: `--set workers.jobTimeout=600`
- Check worker resource limits: `kubectl top pods -l app=worker`
- Scale up workers: `kubectl scale deployment core-provider-worker --replicas=10`

**Jobs in DLQ**:
- Check error logs: `kubectl logs worker | grep "failed"`
- Inspect DLQ message: Use RabbitMQ management UI
- Review resource provider implementation for bugs

## Performance Tuning

### Concurrency Settings

```yaml
workers:
  maxConcurrentJobs: 10  # Increase for parallelism
  jobTimeout: 300       # Decrease to fail fast, increase for long ops
```

### Resource Allocation

```yaml
workers:
  resources:
    requests:
      cpu: 500m        # Allocate more for CPU-bound operations
      memory: 512Mi    # Allocate more for memory-intensive operations
    limits:
      cpu: 1000m
      memory: 1Gi
```

### Autoscaling (Future)

```yaml
workers:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
```

## See Also

- [ResourceProvider API](../SDK_PROTECTION_STRATEGY.md)
- [Kubernetes Deployment Guide](./06-DEPLOYMENT.md)
- [RabbitMQ Setup Guide](../audit/rabbitmq_setup.md)
