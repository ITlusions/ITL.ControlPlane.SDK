# Service Bus Provider Mode (SDK Guide)

## Overview

The ITL ControlPlane SDK provides **generic, reusable service bus utilities** that enable any resource provider to run in multiple modes:

- **API Mode** (default): Traditional HTTP REST API
- **ServiceBus Mode**: RabbitMQ message consumer (no HTTP)
- **Hybrid Mode**: Both simultaneously (for migration)

This guide shows how to use these utilities in your provider (Compute, IAM, Keycloak, Identity, or custom).

---

## Quick Start

### 1. Import from SDK

```python
from itl_controlplane_sdk import (
    GenericServiceBusProvider,
    ProviderModeManager,
    run_generic_servicebus_provider,
)
```

### 2. Run Your Provider in ServiceBus Mode

```python
import asyncio
from my_provider import ComputeProvider

async def main():
    provider = ComputeProvider(engine=storage_engine)
    
    # Run as message consumer
    await run_generic_servicebus_provider(
        provider=provider,
        provider_namespace="ITL.Compute",
        rabbitmq_url="amqp://guest:guest@rabbitmq:5672/"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

That's it! Your provider now:
- ✅ Listens to `provider.compute.requests` RabbitMQ queue
- ✅ Processes ResourceRequest messages
- ✅ Publishes responses to `provider.compute.responses`
- ✅ Handles failures with automatic DLQ

---

## Architecture

### Mode Selection

The SDK automatically detects mode from `PROVIDER_MODE` environment variable:

```bash
PROVIDER_MODE=api         # HTTP REST API (default)
PROVIDER_MODE=servicebus  # RabbitMQ message consumer only
PROVIDER_MODE=hybrid      # Both API + message consumer
```

### Queue Naming Convention

Queues are automatically named from provider namespace:

```
Provider Namespace   →   Queue Prefix   →   Queue Names
────────────────────────────────────────────────────────
ITL.Core            →   provider.core   →   provider.core.requests
ITL.Compute         →   provider.compute  →   provider.compute.requests
ITL.IAM             →   provider.iam    →   provider.iam.requests
MyCustom.Provider   →   provider.mycustom  →   provider.mycustom.requests
```

All queues include:
- `{prefix}.requests` - Incoming requests
- `{prefix}.responses` - Responses (for correlation)
- `{prefix}.dlq` - Dead-letter queue (failed after retries)

---

## Class Reference

### GenericServiceBusProvider

Base class for running any provider as a message consumer.

**Constructor Parameters:**

```python
GenericServiceBusProvider(
    provider: ResourceProvider,          # Your provider instance
    provider_namespace: str,             # e.g., "ITL.Compute"
    rabbitmq_url: str,                   # RabbitMQ connection
    queue_prefix: Optional[str] = None,  # Auto-generated if not provided
    request_queue: Optional[str] = None, # Override request queue name
    response_queue: Optional[str] = None,# Override response queue name
    dlq_queue: Optional[str] = None,     # Override DLQ queue name
)
```

**Methods:**

```python
# Connect to RabbitMQ
async def connect():
    """Initialize RabbitMQ and declare queues"""

# Process a message
async def process_request(
    job_id: str,
    request_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Process ResourceRequest and return response"""

# Publish response
async def publish_response(
    response_data: Dict[str, Any]
):
    """Publish response to response queue"""

# Main entry point
async def run():
    """Start consuming and processing messages"""

# Cleanup
async def disconnect():
    """Close RabbitMQ connection"""
```

### ProviderModeManager

High-level manager for API/ServiceBus/Hybrid modes.

**Constructor:**

```python
ProviderModeManager(
    provider: ResourceProvider,     # Your provider
    provider_namespace: str,        # e.g., "ITL.Compute"
    app=None,                       # FastAPI app (required for API/Hybrid)
    rabbitmq_url: str = "...",     # RabbitMQ URL
    mode: Optional[str] = None,    # Override mode
)
```

**Methods:**

```python
# Run in configured mode
async def run(
    host: str = "0.0.0.0",
    port: int = 8000,
    init_func=None,  # Storage initialization
    **kwargs
):
    """Run provider in configured mode (api/servicebus/hybrid)"""

# Individual mode methods
async def run_api_mode(host: str, port: int, **kwargs)
async def run_servicebus_mode()
async def run_hybrid_mode(host: str, port: int, **kwargs)
```

### Utility Function

```python
async def run_generic_servicebus_provider(
    provider: ResourceProvider,
    provider_namespace: str,
    rabbitmq_url: str = "amqp://guest:guest@localhost/"
):
    """Quick function to run any provider in ServiceBus mode"""
```

---

## Implementation Examples

### Compute Provider (ServiceBus Mode)

```python
import asyncio
import logging
from itl_controlplane_sdk import run_generic_servicebus_provider
from my_compute_provider import ComputeProvider

logger = logging.getLogger(__name__)

async def main():
    # Initialize provider
    provider = ComputeProvider()
    await provider.initialize()
    
    # Run as message consumer
    await run_generic_servicebus_provider(
        provider=provider,
        provider_namespace="ITL.Compute",
        rabbitmq_url="amqp://guest:guest@rabbitmq:5672/"
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

### IAM Provider (Hybrid Mode with FastAPI)

```python
import asyncio
import os
from fastapi import FastAPI
from itl_controlplane_sdk import ProviderModeManager
from my_iam_provider import IAMProvider

async def main():
    # Create FastAPI app
    app = FastAPI(title="ITL IAM Provider")
    
    # Initialize provider with storage
    provider = IAMProvider()
    await provider.initialize()
    
    # Setup API routes (omitted for brevity)
    # ...
    
    # Create mode manager
    manager = ProviderModeManager(
        provider=provider,
        provider_namespace="ITL.IAM",
        app=app,
        mode=os.getenv("PROVIDER_MODE", "api")
    )
    
    # Run in configured mode
    await manager.run(
        host="0.0.0.0",
        port=8000,
        init_func=async_storage_init
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Provider (All Three Modes)

```python
import asyncio
import os
import logging
from fastapi import FastAPI
from itl_controlplane_sdk import (
    GenericServiceBusProvider,
    ProviderModeManager,
)
from my_custom_provider import MyProvider

logger = logging.getLogger(__name__)

async def initialize_storage():
    """Initialize storage and audit system"""
    logger.info("Initializing storage...")
    # ... custom initialization logic ...

async def main():
    mode = os.getenv("PROVIDER_MODE", "api").lower()
    
    # Initialize provider
    provider = MyProvider()
    await initialize_storage()
    
    if mode == "api":
        # Run FastAPI server only
        app = FastAPI(title="My Custom Provider")
        # ... setup routes ...
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    
    elif mode == "servicebus":
        # Run message consumer only
        bus = GenericServiceBusProvider(
            provider=provider,
            provider_namespace="MyCustom.Provider",
            rabbitmq_url=os.getenv("RABBITMQ_URL")
        )
        await bus.run()
    
    elif mode == "hybrid":
        # Run both using ProviderModeManager
        app = FastAPI(title="My Custom Provider")
        # ... setup routes ...
        
        manager = ProviderModeManager(
            provider=provider,
            provider_namespace="MyCustom.Provider",
            app=app,
            mode="hybrid"
        )
        await manager.run(
            host="0.0.0.0",
            port=8000,
            init_func=initialize_storage
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

---

## Message Format

### Request Message (provider.{name}.requests queue)

```json
{
  "job_id": "abc123",
  "provider_namespace": "ITL.Compute",
  "resource_type": "virtualmachines",
  "operation": "create",
  "request": {
    "subscription_id": "sub-123",
    "resource_group": "my-rg",
    "resource_name": "my-vm",
    "location": "eastus",
    "body": {
      "vm_size": "Standard_D2s_v3",
      "os": "windows",
      "image": "Windows-2019"
    }
  }
}
```

### Success Response (provider.{name}.responses queue)

```json
{
  "job_id": "abc123",
  "status": "completed",
  "result": {
    "id": "/subscriptions/sub-123/resourceGroups/my-rg/...",
    "name": "my-vm",
    "properties": { ... },
    "location": "eastus"
  }
}
```

### Error Response

```json
{
  "job_id": "abc123",
  "status": "failed",
  "error": "Validation failed: vm_size is required"
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROVIDER_MODE` | `api` | `api`, `servicebus`, or `hybrid` |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost/` | RabbitMQ connection |
| `PROVIDER_HOST` | `0.0.0.0` | HTTP bind host (API/Hybrid) |
| `PROVIDER_PORT` | `8000` | HTTP bind port (API/Hybrid) |

---

## Docker Examples

### Run Compute Provider in ServiceBus Mode

```dockerfile
FROM python:3.11

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PROVIDER_MODE=servicebus
ENV RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

CMD ["python", "-m", "src.main"]
```

### Docker Compose (All three modes)

```yaml
version: '3.8'

services:
  rabbitmq:
    image: rabbitmq:3.11-management
    ports:
      - "5672:5672"
      - "15672:15672"

  # Mode 1: API
  compute-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      PROVIDER_MODE: api
      PROVIDER_PORT: 8000

  # Mode 2: ServiceBus
  compute-worker:
    build: .
    environment:
      PROVIDER_MODE: servicebus
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
    depends_on:
      - rabbitmq

  # Mode 3: Hybrid
  compute-hybrid:
    build: .
    ports:
      - "8001:8000"
    environment:
      PROVIDER_MODE: hybrid
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
    depends_on:
      - rabbitmq
```

---

## Kubernetes Deployment

### ServiceBus Mode (Worker Role)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compute-provider-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: compute-provider
      mode: servicebus
  template:
    metadata:
      labels:
        app: compute-provider
        mode: servicebus
    spec:
      containers:
      - name: compute-provider
        image: compute-provider:1.0
        env:
        - name: PROVIDER_MODE
          value: "servicebus"
        - name: RABBITMQ_URL
          valueFrom:
            secretKeyRef:
              name: rabbitmq
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

---

## Logging

SDK provides structured logging with provider namespace prefixing:

```
[ITL.Core] Processing request abc123: resourcegroups (create)
[ITL.Core] Request abc123 processed successfully
[ITL.Compute] Consumed task: virtualmachines creation
[ITL.IAM] Error processing request: provider not found
```

---

## Monitoring & Observability

### Check Message Queue Status

```bash
# List all queues
docker exec rabbitmq rabbitmqctl list_queues

# Check specific queue depth
docker exec rabbitmq rabbitmqctl list_queues | grep provider.compute
```

### Monitor DLQ (Dead-Letter Queue)

```bash
# View DLQ messages
docker exec rabbitmq rabbitmqctl list_queue_contents provider.compute.dlq

# Setup alerts for DLQ > 0 (indicates systematic failures)
```

### Prometheus Metrics (Optional)

```python
from prometheus_client import Counter, Histogram

request_count = Counter(
    'provider_requests_total',
    'Total requests processed',
    ['provider', 'status']
)

request_duration = Histogram(
    'provider_request_seconds',
    'Request processing time',
    ['provider']
)
```

---

## Migration Path

### Phase 1: API Mode (Current)
```
Provider exposes HTTP API
Workers call provider directly
```

### Phase 2: Hybrid Mode (Testing)
```
PROVIDER_MODE=hybrid
Both HTTP API and message consumer active
Validate message-based flow works
```

### Phase 3: ServiceBus Mode (Production)
```
PROVIDER_MODE=servicebus
No HTTP API exposed
Full message-based communication
```

---

## Best Practices

1. **Development:** Use `PROVIDER_MODE=api` for simplicity
2. **Testing:** Use `PROVIDER_MODE=hybrid` to validate both patterns
3. **Production:** Use `PROVIDER_MODE=servicebus` for scalability
4. **Monitoring:** Alert on DLQ size > 0
5. **Graceful Shutdown:** Implement SIGTERM handlers in CLI
6. **Logging:** Use structured logging with provider namespace
7. **Configuration:** Use environment variables, not hardcoding

---

## Troubleshooting

### Queues Not Declared?

Ensure RabbitMQ is accessible:
```bash
docker exec rabbitmq rabbitmq-diagnostics ping
```

### Messages Stuck in DLQ?

Messages move to DLQ after 3 retries. Check logs for errors:
```bash
docker logs compute-provider-worker | grep ERROR
```

### Requests Not Processed?

1. Verify RABBITMQ_URL is correct
2. Check queue names: `docker exec rabbitmq rabbitmqctl list_queues`
3. Review provider logs for exceptions
4. Ensure provider implementation handles the resource type

---

## See Also

- [Worker Role Architecture](../ITL.ControlPanel.SDK/docs/21-WORKER_ROLE_ARCHITECTURE.md)
- [Hybrid Provider Mode (Core)](../ITL.ControlPlane.ResourceProvider.Core/docs/HYBRID_PROVIDER_MODE.md)
- [Retry & DLQ Handling](../ITL.ControlPanel.SDK/docs/24-WORKER_RETRY_AND_DLQ.md)
