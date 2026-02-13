# Worker Role Implementation Summary

## What Was Implemented

A complete **Worker Role system** for offloading provider operations to backend workers. This enables:

✅ **Horizontal Scaling** - Scale worker pods independently from API  
✅ **Async Processing** - Client gets immediate response with job_id  
✅ **Load Distribution** - Multiple workers share operation workload  
✅ **Resilience** - Failed jobs captured in dead-letter queue  
✅ **Kubernetes Native** - Full Helm/K8s integration with RBAC  
✅ **Monitoring** - Health checks and Prometheus metrics  

## Files Created/Modified

### SDK Core (Python)

| File | Purpose |
|------|---------|
| `src/itl_controlplane_sdk/workers/__init__.py` | Worker module exports |
| `src/itl_controlplane_sdk/workers/base.py` | `WorkerRole` abstract base class |
| `src/itl_controlplane_sdk/workers/queue.py` | `JobQueue` RabbitMQ implementation |
| `src/itl_controlplane_sdk/workers/registry.py` | `WorkerRegistry` for managing workers |
| `src/itl_controlplane_sdk/workers/provider_worker.py` | `ProviderWorker` concrete implementation |
| `src/itl_controlplane_sdk/workers/offloading_registry.py` | `OffloadingProviderRegistry` for async job submission |
| `src/itl_controlplane_sdk/workers/worker_entrypoint.py` | Standalone worker process entry point |

### Kubernetes/Helm

| File | Purpose |
|------|---------|
| `charts/templates/worker-deployment.yaml` | Worker Pod Deployment |
| `charts/templates/worker-serviceaccount.yaml` | ServiceAccount for worker RBAC |
| `charts/templates/worker-clusterrole.yaml` | ClusterRole with minimal permissions |
| `charts/templates/worker-clusterrolebinding.yaml` | ClusterRoleBinding for ServiceAccount |
| `charts/templates/worker-configmap.yaml` | Worker configuration |
| `charts/templates/worker-pdb.yaml` | PodDisruptionBudget for HA |

### Configuration

| File | Purpose |
|------|---------|
| `charts/values.yaml` | Default worker configuration |
| `charts/values-dev.yaml` | Development worker settings |
| `charts/values-prod.yaml` | Production worker settings |

### Documentation

| File | Purpose |
|------|---------|
| `docs/21-WORKER_ROLE_ARCHITECTURE.md` | Complete architecture guide |

## Quick Start

### 1. Enable Workers in Helm

```bash
# Development
helm install core-provider ./charts \
  -f charts/values-dev.yaml

# Production (with 5 workers)
helm install core-provider ./charts \
  -f charts/values-prod.yaml \
  --set workers.replicaCount=5
```

### 2. Use OffloadingProviderRegistry in API

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
    # Returns immediately with job_id
    return {"job_id": response.job_id, "status": "pending"}
```

### 3. Monitor Workers

```bash
# Check worker status
kubectl get pods -l app.kubernetes.io/component=worker

# Check worker logs
kubectl logs -f deployment/core-provider-worker

# Check health
kubectl exec <worker-pod> -- curl http://localhost:8001/health
```

## Architecture Diagram

```
HTTP Request (POST /resources)
    ↓
API Server (main.py)
    ↓
OffloadingProviderRegistry.create_or_update_resource()
    ↓
JobQueue.submit_job() → RabbitMQ
    ↓
[Immediate Response with job_id]
    
    RabbitMQ (provider.jobs queue)
    ↓
Worker Pod #1 ──┐
Worker Pod #2 ──┼── consume_jobs()
Worker Pod #3 ──┘
    ↓
ProviderWorker.process_job()
    ↓
Provider.create_or_update_resource()
    ↓
Result → RabbitMQ (provider.results queue)
    ↓
Client polls job_id endpoint to get result
```

## Key Classes

### WorkerRole
```python
class WorkerRole(abc.ABC):
    """Abstract base for worker implementations"""
    async def start()              # Start worker
    async def stop()               # Stop gracefully
    async def process_job(...)     # Process single job
    def get_status()               # Get worker status
```

### JobQueue
```python
class JobQueue:
    """Async job queue using RabbitMQ"""
    async def submit_job(...)      # Add job to queue
    async def consume_jobs(...)    # Start consuming
    async def get_result(...)      # Get job result
    async def get_queue_stats()    # Queue statistics
```

### OffloadingProviderRegistry
```python
class OffloadingProviderRegistry(ResourceProviderRegistry):
    """Provider registry that offloads to workers"""
    async def create_or_update_resource(...)  # Submit to queue
    async def get_job_result(...)             # Poll for result
    async def get_queue_stats()               # Queue stats
```

## Configuration Examples

### Development (1 worker)
```yaml
workers:
  enabled: true
  replicaCount: 1
  logLevel: DEBUG
  resources:
    limits:
      cpu: 250m
      memory: 256Mi
```

### Production (5 workers with HA)
```yaml
workers:
  enabled: true
  replicaCount: 5
  logLevel: INFO
  jobTimeout: 600
  maxConcurrentJobs: 10
  podDisruptionBudget:
    enabled: true
    minAvailable: 3
  resources:
    limits:
      cpu: 1000m
      memory: 512Mi
```

## Security

✅ **RBAC** - Workers have minimal required permissions  
✅ **Secrets** - RabbitMQ credentials in K8s Secret  
✅ **Network Policies** - Restrict traffic to RabbitMQ  
✅ **Security Context** - Non-root, read-only filesystem  
✅ **Job Isolation** - Projects isolated via namespace  

## Health & Monitoring

Each worker exposes:
- `/health` - Liveness probe
- `/status` - Detailed worker status
- `/metrics` - Prometheus metrics

Example metrics:
```
worker_jobs_processed{worker_id="worker-1"} 1542
worker_jobs_failed{worker_id="worker-1"} 3
worker_uptime_seconds{worker_id="worker-1"} 3600
```

## Scaling

### Horizontal Scaling
```bash
# Scale up
kubectl scale deployment core-provider-worker --replicas=10

# With HPA (future)
kubectl autoscale deployment core-provider-worker \
  --min=3 --max=20 --cpu-percent=70
```

### Job Priority
```python
# Urgent
await job_queue.submit_job(..., priority=9)

# Normal
await job_queue.submit_job(..., priority=5)

# Low-priority
await job_queue.submit_job(..., priority=1)
```

## Dependencies

- `aio-pika>=9.0.0` - Async RabbitMQ client
- `aiohttp` - Health check server
- `pydantic>=2.5.0` - Data validation
- RabbitMQ 3.8+ server

## Troubleshooting

### Workers not consuming jobs
1. Check RabbitMQ is running: `kubectl get svc rabbitmq`
2. Check worker logs: `kubectl logs deployment/core-provider-worker`
3. Verify RABBITMQ_URL: `kubectl get deployment -o yaml | grep RABBITMQ`

### Jobs stuck in queue
1. Check worker count: `kubectl get pods -l app.kubernetes.io/component=worker`
2. Check worker health: `kubectl exec <pod> -- curl localhost:8001/health`
3. Check queue stats: `kubectl exec <pod> -- curl localhost:8001/queue-stats`

### High job failure rate
1. Check worker logs: `kubectl logs deployment/core-provider-worker | grep failed`
2. Check resource usage: `kubectl top pods`
3. Increase resources: `helm upgrade --set workers.resources.limits.memory=1Gi`

## Next Steps

1. **Deploy**: Enable workers in your cluster
2. **Configure**: Adjust replicas and resources for your workload
3. **Monitor**: Set up Prometheus scraping of `/metrics` endpoint
4. **Test**: Submit some jobs and verify async processing
5. **Scale**: Use HPA or manual scaling as load increases

## Documentation

See [Worker Role Architecture Guide](./21-WORKER_ROLE_ARCHITECTURE.md) for:
- Detailed architecture
- Configuration reference
- Performance tuning
- Advanced use cases
- Complete API documentation
