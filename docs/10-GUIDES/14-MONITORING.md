# Monitoring and Observability

Comprehensive guide to monitoring, logging, and observing resource provider performance.

---

## Three Pillars of Observability

### 1. Logs
Event-based records of what happened in your provider.

### 2. Metrics
Numerical time-series data about provider health and performance.

### 3. Traces
Distributed request traces showing flow through your system.

---

## Structured Logging

### Configure Logging

```python
# config/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add custom fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_logging(log_level="INFO"):
    """Configure structured logging"""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler with JSON formatting
    handler = logging.StreamHandler()
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    return root_logger

logger = logging.getLogger(__name__)
```

### Use Logging in Provider

```python
from config.logging import logger

class MyProvider(ResourceProvider):
    async def create_or_update_resource(self, request: ResourceRequest):
        logger.info(
            "Creating resource",
            extra={
                "request_id": request.id,
                "resource_name": request.resource_name,
                "subscription_id": request.subscription_id,
            }
        )
        
        try:
            # ... create resource ...
            logger.info(
                "Resource created successfully",
                extra={
                    "request_id": request.id,
                    "resource_id": resource.id,
                    "duration_ms": elapsed_ms,
                }
            )
            return response
        
        except ValueError as e:
            logger.error(
                "Validation error creating resource",
                extra={
                    "request_id": request.id,
                    "error": str(e),
                },
                exc_info=True
            )
            raise
```

### Log Levels Guide

```
DEBUG  : Detailed diagnostic information (developer only)
INFO   : General informational messages (normal operation)
WARNING: Unusual but handled situations (may need action)
ERROR  : Error conditions (requires immediate attention)
CRITICAL: System cannot continue (emergency response)
```

---

## Metrics and Prometheus

### Export Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry
from fastapi import FastAPI, Response

# Create registry
registry = CollectorRegistry()

# Define metrics
requests_created = Counter(
    'provider_resource_create_requests_total',
    'Total resource creation requests',
    ['provider', 'resource_type', 'status'],
    registry=registry
)

request_duration = Histogram(
    'provider_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.1, 0.5, 1, 2, 5, 10),
    registry=registry
)

active_resources = Gauge(
    'provider_active_resources',
    'Number of active resources',
    ['provider', 'resource_type'],
    registry=registry
)

errors_total = Counter(
    'provider_errors_total',
    'Total errors encountered',
    ['provider', 'error_type'],
    registry=registry
)

# Use in FastAPI
app = FastAPI()

@app.post("/subscriptions/{sub_id}/create")
async def create_resource(request: ResourceRequest):
    with request_duration.labels(method="POST", endpoint="/create").time():
        try:
            # ... create resource ...
            requests_created.labels(
                provider="my-provider",
                resource_type=request.resource_type,
                status="success"
            ).inc()
            
        except Exception as e:
            requests_created.labels(
                provider="my-provider",
                resource_type=request.resource_type,
                status="error"
            ).inc()
            
            errors_total.labels(
                provider="my-provider",
                error_type=type(e).__name__
            ).inc()

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(registry),
        media_type="text/plain; charset=utf-8"
    )
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'my-provider'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
        replacement: $1
```

---

## Health Checks

### Implement Health Endpoints

```python
from pydantic import BaseModel
from datetime import datetime

class HealthStatus(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    version: str
    checks: dict

@app.get("/health")
async def health_check() -> HealthStatus:
    """Liveness check - is the provider running?"""
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        checks={}
    )

@app.get("/ready")
async def readiness_check() -> HealthStatus:
    """Readiness check - can it handle requests?"""
    checks = {
        "database": await check_database(),
        "disk_space": await check_disk_space(),
        "memory": await check_memory(),
    }
    
    # Unhealthy if any check fails
    status = "healthy"
    if any(not c["ok"] for c in checks.values()):
        status = "degraded"
    
    return HealthStatus(
        status=status,
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        checks=checks
    )

async def check_database() -> dict:
    try:
        # Try to execute simple query
        await db.first("SELECT 1")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def check_disk_space() -> dict:
    import shutil
    total, used, free = shutil.disk_usage("/")
    percent_used = (used / total) * 100
    
    if percent_used > 90:
        return {"ok": False, "error": f"Disk {percent_used}% full"}
    return {"ok": True, "bytes_free": free}

async def check_memory() -> dict:
    import psutil
    memory = psutil.virtual_memory()
    
    if memory.percent > 90:
        return {"ok": False, "error": f"Memory {memory.percent}% used"}
    return {"ok": True, "percent_available": 100 - memory.percent}
```

---

## Distributed Tracing

### Add Tracing with OpenTelemetry

```python
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# Configure Jaeger exproter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)

resource = Resource(attributes={
    SERVICE_NAME: "my-provider"
})

tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(tracer_provider)

# Instrument FastAPI
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# Instrument database
from sqlalchemy import create_engine
engine = create_engine("postgresql://...")
SQLAlchemyInstrumentor().instrument(engine=engine)

# Create tracer for custom spans
tracer = trace.get_tracer(__name__)

class MyProvider(ResourceProvider):
    async def create_or_update_resource(self, request):
        with tracer.start_as_current_span("create_resource") as span:
            span.set_attribute("resource.name", request.resource_name)
            span.set_attribute("resource.type", request.resource_type)
            
            # This span is automatically linked to parent traces
            # ... implementation ...
```

### Jaeger Docker Compose

```yaml
# docker-compose.yml
jaeger:
  image: jaegertracing/all-in-one:latest
  ports:
    - "6831:6831/udp"  # Jaeger agent
    - "16686:16686"    # Jaeger UI (http://localhost:16686)
  environment:
    - COLLECTOR_ZIPKIN_HOST_PORT=:9411
```

---

## Alerting Rules

### Define Prometheus Rules

```yaml
# prometheus-rules.yml
groups:
  - name: provider_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(provider_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in {{ $labels.provider }}"
          description: "Error rate is {{ $value }} per second"

      - alert: HighLatency
        expr: histogram_quantile(0.95, provider_request_duration_seconds) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency in {{ $labels.endpoint }}"
          description: "P95 latency is {{ $value }}s"

      - alert: PodNotReady
        expr: kube_pod_status_ready{pod=~"my-provider.*"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Pod {{ $labels.pod }} not ready"
```

### Send to Alert Manager

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical'
      continue: true
    - match:
        severity: warning
      receiver: 'warning'

receivers:
  - name: 'default'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/T.../B.../K...'
        channel: '#alerts'

  - name: 'critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'

  - name: 'warning'
    email_configs:
      - to: 'team@example.com'
```

---

## Dashboards

### Grafana Dashboard Template

```json
{
  "dashboard": {
    "title": "My Provider",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(provider_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(provider_errors_total[5m])"
          }
        ]
      },
      {
        "title": "P95 Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, provider_request_duration_seconds)"
          }
        ]
      },
      {
        "title": "Active Resources",
        "targets": [
          {
            "expr": "provider_active_resources"
          }
        ]
      }
    ]
  }
}
```

---

## Key Metrics to Track

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error Rate | >1% | Page on-call engineer |
| P95 Latency | >1s | Investigate performance |
| Health Check Failures | Any | Immediate investigation |
| CPU Usage | >80% | Scale up |
| Memory Usage | >85% | Scale up |
| Disk Usage | >90% | Emergency cleanup |

---

## Best Practices

✅ **Structured logging** - JSON format for aggregation  
✅ **Meaningful metrics** - Track business and technical metrics  
✅ **Health checks** - Both liveness and readiness  
✅ **Distributed tracing** - Understand request flow  
✅ **Alert thresholds** - Actionable alerts only  
✅ **Dashboards** - Real-time visibility  
✅ **Retention policies** - Control storage costs  
✅ **Testing alerts** - Verify they work before deploying

---

## Stack Setup

```yaml
# Complete monitoring stack
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  jaeger:
    image: jaegertracing/all-in-one
    ports:
      - "6831:6831/udp"
      - "16686:16686"

  alertmanager:
    image: prom/alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
```

---

## Related Documentation

- [13-DEPLOYMENT.md](13-DEPLOYMENT.md) - Deployment guide
- [SDK Getting Started](../01-GETTING_STARTED.md) - Quick start
- [Troubleshooting](14-TROUBLESHOOTING.md) - Common issues

---

Effective monitoring ensures your providers stay healthy and performants in production.
