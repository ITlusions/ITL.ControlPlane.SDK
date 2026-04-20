# Asynchronous Patterns: Service Bus & Message-Based Processing

**Status**:  Production-Ready  
**Implementation**: Generic SDK components + three operating modes  
**Coverage**: ServiceBus provider, mode management, message queuing

Enable message-based asynchronous processing for resource providers. Run providers in API mode (REST), ServiceBus mode (message consumer), or hybrid mode (both simultaneously).

---

## Overview

The ITL ControlPlane SDK provides **generic, reusable service bus utilities** that enable any resource provider to operate in multiple modes:

### Three Operating Modes

| Mode | Usage | API | Message Queue | Use Case |
|------|-------|-----|---------------|----------|
| **API** | Traditional HTTP REST |  Yes |  No | Development, backward compatibility |
| **ServiceBus** | Message-driven consumer |  No |  Yes | Production, horizontal scaling |
| **Hybrid** | Both simultaneously |  Yes |  Yes | Migration, testing both patterns |

### Architecture Comparison

**Synchronous (API Mode):**
```
Client Request → API Server --> Provider Logic (blocking) → Response
                    ↓
                Clear latency SLA (users wait)
```

**Asynchronous (ServiceBus Mode):**
```
Client Request → API Server --> Submit to Queue (instant) → Response
                     ↓
                 RabbitMQ --> Worker Pods process async
                     ↓
                Client polls for results when ready
```

### Key Benefits

 **Zero Code Duplication** — Generic components work with any provider  
 **Three Operating Modes** — API, ServiceBus, Hybrid  
 **Automatic Queue Naming** — Generated from provider namespace  
 **Request/Response Correlation** — Via job_id tracking  
 **Error Resilience** — Dead-letter queue for failed messages  
 **Production-Ready** — Core Provider actively uses it

---

## Quick Start (3 Minutes)

### Minimal ServiceBus Implementation

```python
import asyncio
from itl_controlplane_sdk import run_generic_servicebus_provider
from my_provider import ComputeProvider

async def main():
    provider = ComputeProvider()
    await provider.initialize()
    
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
-  Listens to `provider.compute.requests` RabbitMQ queue
-  Processes ResourceRequest messages
-  Publishes responses to `provider.compute.responses`
-  Handles failures with automatic dead-letter queue

---

## Architecture & Components

### System Overview

```mermaid
flowchart TD
    A["API Server or ServiceBus Consumer<br>Receives HTTP requests OR RabbitMQ messages<br>Validates input, delegates to provider"]
    B["RabbitMQ Queues"]
    C["Request Queue"]
    D["Response Queue"]
    E["Worker Pods<br>(Consume requests)"]
    A --> B
    B --> C
    B --> D
    C --> E
    E -->|Publish| D
```

### Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **GenericServiceBusProvider** | Message consumer for any provider | `itl_controlplane_sdk.messaging.servicebus` |
| **ProviderModeManager** | Handles API/ServiceBus/Hybrid modes | `itl_controlplane_sdk.messaging.servicebus` |
| **run_generic_servicebus_provider()** | Quick function to start ServiceBus mode | `itl_controlplane_sdk.messaging.servicebus` |

---

## Three Operating Modes

### Mode 1: API Mode (Default)

Traditional synchronous HTTP REST API.

```python
import os
from fastapi import FastAPI
from my_provider import ComputeProvider

async def main():
    app = FastAPI(title="Compute Provider")
    provider = ComputeProvider()
    
    @app.post("/resources")
    async def create_resource(request: ResourceRequest):
        response = await provider.create_or_update_resource(request)
        return response
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Environment:**
```
PROVIDER_MODE=api
PROVIDER_PORT=8000
```

**Use Case:** Development, backward compatibility

---

### Mode 2: ServiceBus Mode (Async Worker)

Message-driven consumer listening to RabbitMQ.

```python
import asyncio
import os
from itl_controlplane_sdk import run_generic_servicebus_provider
from my_provider import ComputeProvider

async def main():
    provider = ComputeProvider()
    await provider.initialize()
    
    # Run as message consumer (no HTTP server)
    await run_generic_servicebus_provider(
        provider=provider,
        provider_namespace="ITL.Compute",
        rabbitmq_url=os.getenv("RABBITMQ_URL")
    )

if __name__ == "__main__":
    asyncio.run(main())
```

**Environment:**
```
PROVIDER_MODE=servicebus
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

**Use Case:** Production scaling, message-driven architecture

---

### Mode 3: Hybrid Mode (Both)

Both HTTP API and message consumer running simultaneously.

```python
import asyncio
import os
from fastapi import FastAPI
from itl_controlplane_sdk import ProviderModeManager
from my_provider import ComputeProvider

async def main():
    # Setup FastAPI app
    app = FastAPI(title="Compute Provider")
    provider = ComputeProvider()
    
    @app.post("/resources")
    async def create_resource(request: ResourceRequest):
        return await provider.create_or_update_resource(request)
    
    # Create mode manager
    manager = ProviderModeManager(
        provider=provider,
        provider_namespace="ITL.Compute",
        app=app,
        mode=os.getenv("PROVIDER_MODE", "api")
    )
    
    # Runs in configured mode (auto-selects API/ServiceBus/Hybrid)
    await manager.run(
        host="0.0.0.0",
        port=8000,
        init_func=async_storage_init
    )

if __name__ == "__main__":
    asyncio.run(main())
```

**Environment:**
```
PROVIDER_MODE=hybrid
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
PROVIDER_PORT=8000
```

**Use Case:** Migration testing, gradual rollouts

---

## Queue Naming & Message Format

### Automatic Queue Naming

Queues are automatically generated from provider namespace:

```
Provider Namespace    → Queue Prefix       → Queue Names
---
ITL.Core             → provider.core       → provider.core.{requests|responses|dlq}
ITL.Compute          → provider.compute    → provider.compute.{requests|responses|dlq}
ITL.IAM              → provider.iam        → provider.iam.{requests|responses|dlq}
ITL.Identity         → provider.identity   → provider.identity.{requests|responses|dlq}
MyCustom.Provider    → provider.mycustom   → provider.mycustom.{requests|responses|dlq}
```

Each provider gets three queues:
- `{prefix}.requests` — Incoming operation requests
- `{prefix}.responses` — Operation responses
- `{prefix}.dlq` — Dead-letter queue for failures

### Request Message Format

```json
{
  "job_id": "abc-123-def-456",
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
      "os": "windows"
    }
  }
}
```

### Response Message Format

**Success:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "completed",
  "result": {
    "id": "/subscriptions/sub-123/resourceGroups/my-rg/...",
    "name": "my-vm",
    "location": "eastus",
    "properties": {
      "vm_size": "Standard_D2s_v3",
      "os": "windows"
    }
  }
}
```

**Failure:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "failed",
  "error": "Validation failed: vm_size is required"
}
```

---

## Implementation Examples

### Example 1: Compute Provider (ServiceBus Only)

```python
# compute_provider/src/main.py
import asyncio
import os
from itl_controlplane_sdk import run_generic_servicebus_provider
from .compute_provider import ComputeProvider

async def main():
    provider = ComputeProvider()
    await provider.initialize()
    
    await run_generic_servicebus_provider(
        provider=provider,
        provider_namespace="ITL.Compute",
        rabbitmq_url=os.getenv(
            "RABBITMQ_URL",
            "amqp://guest:guest@rabbitmq:5672/"
        )
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 2: IAM Provider (API or ServiceBus or Hybrid)

```python
# iam_provider/src/main.py
import asyncio
import os
from fastapi import FastAPI
from itl_controlplane_sdk import ProviderModeManager
from .iam_provider import IAMProvider

async def setup_storage():
    """Initialize storage, audit, database"""
    # ... custom initialization ...

async def main():
    # Create FastAPI app
    app = FastAPI(title="ITL IAM Provider")
    
    # Initialize provider
    provider = IAMProvider()
    await setup_storage()
    
    # Setup routes (omitted for brevity)
    # setup_routes(app, provider)
    
    # Create mode manager handles all three modes
    manager = ProviderModeManager(
        provider=provider,
        provider_namespace="ITL.IAM",
        app=app,
        mode=os.getenv("PROVIDER_MODE", "api")  # api | servicebus | hybrid
    )
    
    # Run in configured mode
    await manager.run(
        host="0.0.0.0",
        port=8000,
        init_func=setup_storage
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 3: Custom Provider (All Modes)

```python
# custom_provider/src/main.py
import asyncio
import os
from fastapi import FastAPI
from itl_controlplane_sdk import (
    GenericServiceBusProvider,
    ProviderModeManager
)
from .custom_provider import CustomProvider

async def initialize_storage():
    # Custom initialization logic
    pass

async def main():
    mode = os.getenv("PROVIDER_MODE", "api").lower()
    provider = CustomProvider()
    
    if mode == "api":
        # HTTP API only
        app = FastAPI(title="Custom Provider")
        # setup_routes(app, provider)
        
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    
    elif mode == "servicebus":
        # Message consumer only
        await initialize_storage()
        
        bus = GenericServiceBusProvider(
            provider=provider,
            provider_namespace="MyCustom.Provider",
            rabbitmq_url=os.getenv("RABBITMQ_URL")
        )
        await bus.run()
    
    elif mode == "hybrid":
        # Both API and message consumer
        app = FastAPI(title="Custom Provider")
        # setup_routes(app, provider)
        
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
    asyncio.run(main())
```

---

## Configuration

### Environment Variables

```bash
# Mode selection (default: api)
PROVIDER_MODE=api           # HTTP REST API
PROVIDER_MODE=servicebus    # Message consumer only
PROVIDER_MODE=hybrid        # Both simultaneously

# RabbitMQ connection
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# HTTP settings (API/Hybrid modes)
PROVIDER_HOST=0.0.0.0
PROVIDER_PORT=8000

# Optional
AUDIT_ENABLED=true
LOG_LEVEL=INFO
```

### Configuration Class

```python
from itl_controlplane_sdk.messaging.servicebus import GenericServiceBusProvider

provider = GenericServiceBusProvider(
    provider=my_provider,
    provider_namespace="ITL.Compute",        # Auto-generates queue names
    rabbitmq_url="amqp://guest:guest@rabbitmq/",
    queue_prefix="provider.compute",         # Optional override
    request_queue="provider.compute.requests",  # Optional override
    response_queue="provider.compute.responses",
    dlq_queue="provider.compute.dlq"
)
```

---

## Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  rabbitmq:
    image: rabbitmq:3.11-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest

  # Mode 1: API Server
  compute-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      PROVIDER_MODE: api
      PROVIDER_PORT: 8000
    depends_on:
      - rabbitmq

  # Mode 2: ServiceBus Worker
  compute-worker:
    build: .
    environment:
      PROVIDER_MODE: servicebus
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
    depends_on:
      - rabbitmq
    deploy:
      replicas: 3

  # Mode 3: Hybrid (API + ServiceBus)
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

### Kubernetes Deployment

**ServiceBus Mode (Worker Role):**

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
              name: rabbitmq-credentials
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
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

---

## Monitoring & Health

### Health Endpoints

Each provider exposes health checks during operation:

```bash
# Liveness probe
GET /health
→ {"status": "healthy"}

# Readiness probe
GET /ready
→ {"status": "ready"}

# Metrics
GET /metrics
→ Prometheus-formatted metrics
```

### Monitor RabbitMQ

```bash
# Access RabbitMQ management UI
kubectl port-forward svc/rabbitmq 15672:15672
# Visit http://localhost:15672 (guest/guest)

# Check queue depth
RabbitMQ UI → Queues tab → See message counts

# Monitor dead-letter queue
Alert if provider.{name}.dlq > 0
```

### Logging

The SDK provides structured logging:

```
[ITL.Compute] Processing request abc-123: virtualmachines (create)
[ITL.Compute] Request abc-123 validated successfully
[ITL.Compute] Request abc-123 processed in 0.234s
[ITL.Compute] Publishing response to provider.compute.responses
[ITL.IAM] Error processing request: provider not found
[ITL.IAM] Moving request to dead-letter queue
```

---

## Migration Path

### Phase 1: API Mode (Current)
```
All providers run HTTP REST API
Workers call providers via HTTP
Status:  Production
```

### Phase 2: Hybrid Mode (Testing)
```
PROVIDER_MODE=hybrid
Both HTTP API and message consumer active
Validate message-based flow works
Status:  Optional (for migration)
```

### Phase 3: ServiceBus Mode (Scalable)
```
PROVIDER_MODE=servicebus
No HTTP API exposed
Full message-based communication
Status:  Future (full scale)
```

---

## Troubleshooting

### Queues Not Created?

**Problem:** RabbitMQ queues not appearing

**Solution:**
```bash
# Verify RabbitMQ is accessible
docker exec rabbitmq rabbitmq-diagnostics ping

# Check logs
docker logs compute-provider | grep "Connecting to RabbitMQ"
```

### Messages Stuck in DLQ?

**Problem:** Failed messages accumulating in dead-letter queue

**Solution:**
```bash
# 1. Check provider logs
docker logs compute-provider | grep ERROR

# 2. Inspect DLQ message
# Via RabbitMQ UI: Queues → provider.compute.dlq → Get Messages

# 3. Find root cause and fix provider implementation

# 4. Resubmit message (manual recovery)
```

### Requests Not Being Processed?

**Problem:** Messages submitted but no responses

**Solution:**
1. Verify RABBITMQ_URL is correct
2. Check queue names: `docker exec rabbitmq rabbitmqctl list_queues`
3. Review provider logs: `docker logs compute-provider | tail -50`
4. Ensure provider implementation handles resource type
5. Verify provider is running: `docker ps | grep compute-provider`

---

## Best Practices

### 1. Development
Use API mode for simplicity:
```bash
PROVIDER_MODE=api
```

### 2. Testing
Use Hybrid mode to validate both patterns:
```bash
PROVIDER_MODE=hybrid
```

### 3. Production
Use ServiceBus mode for scalability:
```bash
PROVIDER_MODE=servicebus
# Run multiple replicas
```

### 4. Monitoring
Alert on dead-letter queue:
```
Alert if DLQ message count > 0
Action: Investigate failure cause
```

### 5. Graceful Shutdown
Implement SIGTERM handlers:
```python
import signal

def handle_shutdown():
    # Cleanup resources
    # Disconnect from RabbitMQ
    pass

signal.signal(signal.SIGTERM, handle_shutdown)
```

### 6. Configuration
Use environment variables, not hardcoding:
```python
rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://localhost/")
mode = os.getenv("PROVIDER_MODE", "api")
```

---

## Related Documentation

- [11-WORKER_ROLES.md](worker-roles.md) — Job-based async processing
- [08-API_ENDPOINTS.md](api-endpoints.md) — FastAPI integration
- [24-WORKER_RETRY_AND_DLQ.md](../archive/24-WORKER_RETRY_AND_DLQ.md) — Retry strategies
- [23-BEST_PRACTICES.md](../quick-reference.md) — Architecture patterns

---

## Quick Reference

### Run in API Mode
```bash
PROVIDER_MODE=api python main.py
# HTTP server on port 8000
```

### Run in ServiceBus Mode
```bash
PROVIDER_MODE=servicebus RABBITMQ_URL=amqp://... python main.py
# Listens to provider.{name}.requests queue
```

### Run in Hybrid Mode
```bash
PROVIDER_MODE=hybrid RABBITMQ_URL=amqp://... python main.py
# Both HTTP server and message consumer
```

### Import Classes
```python
from itl_controlplane_sdk import (
    GenericServiceBusProvider,
    ProviderModeManager,
    run_generic_servicebus_provider
)
```

### Submit Message to Queue
```python
from aio_pika import connect

connection = await connect("amqp://guest:guest@rabbitmq/")
channel = await connection.channel()
exchange = await channel.get_exchange('provider.compute')

# Publish request
await exchange.publish(
    Message(body=json.dumps(request).encode()),
    routing_key="provider.compute.requests"
)
```

---

**Document Version**: 1.0 (Consolidated from 2 docs)  
**Last Updated**: February 14, 2026  
**Status**:  Production-Ready

