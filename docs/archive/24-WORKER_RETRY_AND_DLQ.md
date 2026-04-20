# Worker Retry Logic & Dead-Letter Queue

## Overview

The Worker Role system now includes **automatic retry logic** for transient failures. Jobs that fail are automatically retried according to configurable policies before being moved to the Dead-Letter Queue (DLQ).

## Retry Behavior

### Default Retry Policy

```python
worker = ProviderWorker(
    worker_id="worker-1",
    provider_registry=registry,
    job_queue=queue,
    max_retries=3,        # Retry up to 3 times
    retry_delay=5.0       # Wait 5 seconds between retries
)
```

### Retry Flow

```
Job Arrives
    ↓
Attempt 1: Try to process
    ↓
  ✓ Success → Job acked, removed from queue
  ✗ Retryable error → Wait 5s, retry
    ↓
Attempt 2: Try to process
    ↓
  ✓ Success → Job acked
  ✗ Retryable error → Wait 5s, retry
    ↓
Attempt 3: Try to process
    ↓
  ✓ Success → Job acked
  ✗ Non-retryable or last attempt → Job nacked
    ↓
Message requeued by RabbitMQ
    ↓
After x-death limit → Moved to Dead-Letter Queue (DLQ)
    ↓
Operator reviews failed job for manual retry
```

## Error Classification

### Retryable Errors (Will Retry)

These errors are temporary and likely to resolve on retry:

- **Provider not found** - Provider starting up or being deployed
- **Provider not available** - Provider temporarily unavailable
- **Connection errors** - Network issues
- **Timeout errors** - Slow response, retry may help
- **Service unavailable** - Provider overloaded
- **Busy errors** - Transient resource contention

Example:
```python
# Provider hasn't started yet
error: "No provider found for ITL.Core/ResourceGroup"
→ Worker retries every 5 seconds until provider available
```

### Non-Retryable Errors (Immediate Failure)

These errors won't resolve on retry:

- **Validation errors** - Invalid request format
- **Authorization errors** - Permission denied
- **Forbidden** - Access denied
- **Unknown operation** - Unsupported operation
- **Unsupported** - Feature not supported
- **Invalid input** - Malformed parameters

Example:
```python
# User provided invalid JSON
error: "Validation error: missing required field 'name'"
→ Worker fails immediately, moves to DLQ
→ Operator fixes request and resubmits
```

## Dead-Letter Queue (DLQ)

### What Is It?

The **Dead-Letter Queue** (`provider.jobs.dlq`) is where jobs go after:
1. All retry attempts exhausted, OR
2. Non-retryable error occurs

### How to Monitor DLQ

```bash
# Check number of jobs in DLQ
kubectl port-forward -n infrastructure svc/rabbitmq 15672:15672
# Visit http://localhost:15672 (user/pass from RabbitMQ secret)
# Navigate to Queues → provider.jobs.dlq

# Or check via API
curl http://localhost:8001/queue-stats
```

### Manual Retry of DLQ Jobs

```python
# Get message from DLQ
dlq_messages = await queue.get_dlq_messages(limit=10)

# Fix the issue (e.g., deploy missing provider)
# Then resubmit to main queue
for msg in dlq_messages:
    await queue.submit_job(
        provider_namespace=msg['provider_namespace'],
        resource_type=msg['resource_type'],
        operation=msg['operation'],
        request=msg['request'],
        priority=msg.get('priority', 5)
    )
```

## Configuration Examples

### Conservative Retries (Fail Fast)
```python
worker = ProviderWorker(
    worker_id="worker-1",
    provider_registry=registry,
    job_queue=queue,
    max_retries=1,      # Only 1 attempt
    retry_delay=2.0     # Quick retry
)
```
Use when: Fast feedback needed, errors are usually not transient

### Aggressive Retries (Wait for Provider)
```python
worker = ProviderWorker(
    worker_id="worker-1",
    provider_registry=registry,
    job_queue=queue,
    max_retries=10,     # Try 10 times
    retry_delay=30.0    # Wait 30 seconds (5 min total wait)
)
```
Use when: Provider takes time to start, want to absorb startup delays

### Custom Error Classification
```python
class CustomProviderWorker(ProviderWorker):
    def _is_retryable_error(self, exception: Exception) -> bool:
        error_str = str(exception).lower()
        
        # Custom patterns for your provider
        if "deploy in progress" in error_str:
            return True  # Retry while deployment happening
        
        if "quota exceeded" in error_str:
            return True  # Eventually quota will free up
        
        # Use default classification for others
        return super()._is_retryable_error(exception)
```

## Logging & Observability

### Retry Logs

```
WARNING: Job abc123 failed with retryable error: No provider found...
         Retrying in 5.0s... (attempt 1/3)

WARNING: Job abc123 failed with retryable error: Connection timeout...
         Retrying in 5.0s... (attempt 2/3)

INFO: Job abc123 completed successfully on attempt 3

---

ERROR: Job def456 failed (attempt 1/3): Validation error...
       This is non-retryable, moving to DLQ

ERROR: Job ghi789 exhausted all retries and will be moved to DLQ...
```

### Metrics

```
worker_jobs_processed{worker_id="worker-1"} 1542     # Total successful
worker_jobs_failed{worker_id="worker-1"} 3          # Total failed (in DLQ)
worker_job_retries{worker_id="worker-1"} 127        # Total retry attempts
```

### Query Failed Jobs

```bash
# Check DLQ depth
kubectl exec -n infrastructure rabbitmq-0 -- \
  rabbitmqctl list_queues name messages | grep dlq

# Get details of failed job
kubectl port-forward -n infrastructure svc/rabbitmq 15672 &
# UI → Queues → provider.jobs.dlq → Get Messages
```

## Kubernetes Deployment

### Enable Retries
```yaml
workers:
  enabled: true
  replicaCount: 3
  
  # Retry configuration
  maxRetries: 3
  retryDelaySeconds: 5
```

### Monitor DLQ Health
```yaml
# Alert when DLQ has messages
alert: DLQHasMessages
  condition: |
    rabbitmq_queue_messages_ready{queue="provider.jobs.dlq"} > 0
  action: notify_on_call
  message: "Provider jobs in DLQ - check failed providers"
```

## Best Practices

### 1. Set Appropriate Retry Counts
```python
# Microservices that start on-demand
max_retries = 5      # Give them time to start

# Services with quota/rate limits
max_retries = 3      # Usually reset quickly

# User input validation
max_retries = 1      # Will never pass
```

### 2. Vary Retry Delay by Operation
```python
if operation == "create":
    retry_delay = 10.0  # Creation takes time
elif operation == "get":
    retry_delay = 2.0   # Reads should be fast
elif operation == "delete":
    retry_delay = 5.0   # Deletion is medium
```

### 3. Monitor DLQ Regularly
```bash
# Daily check
kubectl exec -n infrastructure rabbitmq-0 -- \
  rabbitmqctl list_queues name messages | grep dlq

# Set up alerts for DLQ > 0
```

### 4. Handle DLQ Systematically
```python
async def process_dlq():
    """Daily process to handle DLQ items"""
    
    dlq_items = await queue.get_dlq_messages(limit=100)
    
    for item in dlq_items:
        # Categorize by error
        if "provider not found" in item['error']:
            # Provider deployment issue - wait and retry
            await asyncio.sleep(300)  # Wait 5 minutes
            await queue.submit_job(...)
        
        elif "validation error" in item['error']:
            # User input issue - log and discard
            logger.warning(f"Invalid request in DLQ: {item}")
        
        else:
            # Unknown - escalate to team
            await notify_team(f"Unknown DLQ error: {item}")
```

## Troubleshooting

### Jobs in DLQ Growing

**Problem**: `provider.jobs.dlq` message count increasing

**Causes & Solutions**:
1. **Provider not deployed**
   ```bash
   kubectl get deployment -A | grep provider
   # If missing, deploy it
   helm install provider ./charts
   ```

2. **Provider repeatedly crashing**
   ```bash
   kubectl logs deployment/provider --tail=100
   # Check for startup errors
   ```

3. **Non-retryable errors from users**
   ```bash
   # Review DLQ messages - likely invalid input
   # Ask users to fix request and resubmit
   ```

### High Retry Rate

**Problem**: Many job retries happening

**Solutions**:
1. **Reduce max_retries if transient errors**
   ```python
   # Failing on every retry means non-transient
   max_retries = 1
   ```

2. **Increase retry_delay if timeout-related**
   ```python
   # Provider needs more time
   retry_delay = 15.0
   ```

3. **Scale provider if overloaded**
   ```bash
   kubectl scale deployment provider --replicas=10
   ```

### Jobs Never Complete

**Problem**: Job keeps retrying but never succeeds

**Solution**:
```bash
# Check last error in logs
kubectl logs deployment/worker | grep "Job XYZ" | tail -20

# If provider not found, check deployment
kubectl get deployment -A | grep provider

# If other error, check error classification
# May need custom _is_retryable_error implementation
```

## See Also

- [Worker Role Architecture](./21-WORKER_ROLE_ARCHITECTURE.md)
- [API Reference](./23-WORKER_ROLE_API_REFERENCE.md)
- [Deployment Guide](../charts/WORKER_DEPLOYMENT_GUIDE.md)
