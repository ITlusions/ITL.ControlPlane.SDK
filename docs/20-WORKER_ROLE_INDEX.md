# Worker Role System Documentation Index

## Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| [Quick Start Guide](./22-WORKER_ROLE_QUICK_START.md) | 5-minute setup guide | DevOps, Platform Engineers |
| [Architecture Guide](./21-WORKER_ROLE_ARCHITECTURE.md) | Deep dive into design | Architects, Senior Developers |
| [API Reference](./23-WORKER_ROLE_API_REFERENCE.md) | Complete API documentation | Developers, SDK Users |
| [Deployment Guide](../charts/WORKER_DEPLOYMENT_GUIDE.md) | Production deployment steps | DevOps, Platform Engineers |
| [Example Code](../examples/worker_role_example.py) | Working examples | Developers |

## What Is the Worker Role System?

The **Worker Role system** enables the ITL ControlPlane to **offload provider operations to backend workers**. Instead of processing all requests synchronously in the main API server, operations are submitted to a job queue and processed by scalable worker pods.

### Before (Synchronous)
```
Client Request
    ↓
API Server ─→ Provider Logic (blocking) ─→ Response
```

### After (With Workers)
```
Client Request
    ↓
API Server ─→ Submit to Queue (instant) ─→ Response with job_id
                    ↓
            Worker Pod (async processing)
                    ↓
            Result stored for polling
```

## Key Features

✅ **Async Processing** - Client gets immediate response with job tracking ID  
✅ **Horizontal Scaling** - Scale workers independently from API  
✅ **Load Distribution** - Multiple workers share workload  
✅ **Resilience** - Failed jobs captured in dead-letter queue  
✅ **Kubernetes Native** - Full RBAC, health checks, monitoring  
✅ **Production Ready** - Used in ITL ControlPlane core infrastructure  

## Getting Started (30 seconds)

### 1. Enable workers in Helm
```bash
helm install core-provider ./charts \
  --set workers.enabled=true \
  --set workers.replicaCount=3
```

### 2. Use OffloadingProviderRegistry in API
```python
from itl_controlplane_sdk.workers import OffloadingProviderRegistry

registry = OffloadingProviderRegistry(job_queue)

# Client gets immediate response with job_id
response = await registry.create_or_update_resource(...)
```

### 3. Monitor workers
```bash
kubectl logs -f deployment/core-provider-worker
curl http://worker-pod:8001/health
```

## Architecture Overview

### Components

1. **JobQueue** - RabbitMQ-based message broker
   - Reliable job distribution
   - Priority-based queuing
   - Dead-letter queue for failures

2. **WorkerRole** - Abstract base class
   - Lifecycle management (start/stop)
   - Health reporting
   - Job processing interface

3. **ProviderWorker** - Concrete worker implementation
   - Consumes jobs from queue
   - Executes provider operations
   - Publishes results

4. **OffloadingProviderRegistry** - Provider registry with offloading
   - Submits jobs instead of executing directly
   - Returns job_id for client tracking
   - Polls for results

5. **WorkerRegistry** - Manages worker fleet
   - Tracks active workers
   - Monitors health
   - Provides statistics

### Message Flow

```
┌─────────────────────────────────┐
│   HTTP Request (POST /resource) │
└──────────────┬──────────────────┘
               │
        ┌──────▼──────┐
        │  API Server │◄──────────────────────────────┐
        └──────┬──────┘                               │
               │ submit_job()                         │
               │                                      │
        ┌──────▼─────────────────┐                   │
        │  RabbitMQ Job Queue    │                   │
        │  provider.jobs         │                   │
        └──────┬─────────────────┘                   │
               │                                      │
         ┌─────┴─────┬──────┐                        │
         │     │     │      │                        │
    ┌────▼──┐ ┌─▼──┐┌─▼──┐│                        │
    │Worker1│ │W2  ││W3  ││ consume_jobs()         │
    └────┬──┘ └─┬──┘└─┬──┘│                        │
         │     │     │   │ process_job()            │
        ┌▼──┬──▼──┬──▼───┘ execute_provider()      │
        │Provider Operations (parallel)             │
        └┬──┬────┬────────────────────────────────┐ │
         │  │    │ publish_result()               │ │
    ┌────▼──▼────▼─────────────────┐              │ │
    │ RabbitMQ Result Queue         │◄─────────────┘ │
    │ provider.results              │                │
    └───────┬──────────────────────┘                │
            │                                       │
            │ get_job_result() / polling            │
            └───────────────────────────────────────┘
```

## Common Use Cases

### Use Case 1: High-Volume API
**Problem**: API gets hammered with requests for long-running operations
**Solution**: Offload to workers, return job_id immediately

```python
# Before: Each request blocks for minutes
response = await provider.create_large_deployment(request)

# After: Instant response, processing happens asynchronously
response = await offloading_registry.create_or_update_resource(...)
job_id = response.job_id
# Client can check job_id for progress
```

### Use Case 2: Resource-Intensive Operations
**Problem**: Creating complex resources requires significant CPU/memory
**Solution**: Run on dedicated worker pods with higher resource limits

```yaml
api:
  resources:
    limits:
      cpu: 500m
      memory: 512Mi

workers:
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
```

### Use Case 3: Multi-Tenant Isolation
**Problem**: One tenant's heavy operation shouldn't impact others
**Solution**: Workers provide processing isolation

```
API Server → Fast-path operations (validation, caching)
    ↓
JobQueue → Heavy operations isolated to workers
    ↓
Tenant A's operation doesn't block Tenant B's requests
```

## Configuration Examples

### Development (1 worker)
```yaml
workers:
  enabled: true
  replicaCount: 1
  logLevel: DEBUG
```

### Production (5 workers, HA)
```yaml
workers:
  enabled: true
  replicaCount: 5
  logLevel: INFO
  podDisruptionBudget:
    enabled: true
    minAvailable: 3
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - topologyKey: kubernetes.io/hostname
```

### High-Throughput (20 workers)
```yaml
workers:
  enabled: true
  replicaCount: 20
  maxConcurrentJobs: 10
```

## Monitoring & Observability

### Health Checks
```bash
# Worker health
curl http://worker:8001/health
# → {"status": "healthy", "worker_id": "worker-1"}

# Worker status
curl http://worker:8001/status
# → {jobs_processed: 1542, jobs_failed: 3, uptime_seconds: 3600}

# Prometheus metrics
curl http://worker:8001/metrics
# → worker_jobs_processed{worker_id="worker-1"} 1542
```

### Queue Monitoring
```bash
# Port-forward to RabbitMQ management UI
kubectl port-forward svc/rabbitmq 15672:15672
# Visit http://localhost:15672
# Check queue depths, consumer counts, etc.
```

### Logging
```bash
# Check worker logs
kubectl logs -f deployment/core-provider-worker

# Filter by error
kubectl logs deployment/core-provider-worker | grep ERROR

# Real-time streaming
kubectl logs -f deployment/core-provider-worker --tail=50
```

## Scaling Strategies

### Horizontal Scaling (Number of Workers)
```bash
# Scale to 10 workers
kubectl scale deployment core-provider-worker --replicas=10

# Auto-scaling (future enhancement)
kubectl autoscale deployment core-provider-worker --min=3 --max=20
```

### Vertical Scaling (Worker Resources)
```yaml
workers:
  resources:
    requests:
      cpu: 2000m
      memory: 2Gi
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

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Workers not consuming jobs | Check RabbitMQ connectivity, worker logs |
| High job failure rate | Increase worker resources, check error logs |
| Jobs stuck in queue | Scale up workers, check queue depth |
| Worker crashes | Check memory/CPU usage, review logs |
| Slow job processing | Add more workers, increase job priority |

See [Deployment Guide](../charts/WORKER_DEPLOYMENT_GUIDE.md) for detailed troubleshooting.

## Security Considerations

✅ **RBAC** - Workers have minimal permissions via ClusterRole  
✅ **Secrets** - RabbitMQ credentials in Kubernetes Secrets  
✅ **Network Policies** - Restrict traffic to RabbitMQ  
✅ **Security Context** - Non-root user, read-only filesystem  
✅ **Resource Limits** - Prevent resource exhaustion  

## Next Steps

1. **[Quick Start (5 min)](./22-WORKER_ROLE_QUICK_START.md)** - Get running immediately
2. **[Architecture (20 min)](./21-WORKER_ROLE_ARCHITECTURE.md)** - Understand how it works
3. **[API Reference (ongoing)](./23-WORKER_ROLE_API_REFERENCE.md)** - Look up specific classes/methods
4. **[Deployment Guide](../charts/WORKER_DEPLOYMENT_GUIDE.md)** - Deploy to production
5. **[Example Code](../examples/worker_role_example.py)** - See working implementation

## FAQ

**Q: Will this improve my API's latency?**
A: For synchronous operations, yes - clients get immediate response with job_id. Processing happens async.

**Q: How many workers do I need?**
A: Start with 3-5, scale based on queue depth and job processing time.

**Q: Can I use a different message broker?**
A: Currently RabbitMQ only, but architecture supports pluggable message brokers.

**Q: What happens if a job fails?**
A: It's moved to dead-letter queue for analysis and manual retry.

**Q: Can I mix sync and async operations?**
A: Yes! Use OffloadingProviderRegistry for async, standard registry for sync.

## Support & Resources

- **Issues**: [GitHub Issues](https://github.com/itlusions/controlplane-sdk)
- **Documentation**: This guide + API Reference
- **Examples**: `examples/worker_role_example.py`
- **RabbitMQ Docs**: https://www.rabbitmq.com/documentation.html

## Related Topics

- [Resource Provider Architecture](./04-ARCHITECTURE.md)
- [FastAPI Integration](./05-FASTAPI_MODULE.md)
- [Kubernetes Deployment](./06-DEPLOYMENT.md)
- [Audit & Logging](./audit/audit_architecture.md)

---

**Last Updated**: February 2025  
**Version**: 1.0.0  
**Status**: Production Ready
