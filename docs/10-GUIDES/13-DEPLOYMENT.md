# Deployment Guide: From Development to Production

Complete guide to containerizing and deploying resource providers.

---

## Development Environment

### Local Setup with Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  provider:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=DEBUG
      - PROVIDER_NAME=my-provider
    volumes:
      - ./src:/app/src  # Live reload
    networks:
      - itl-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=provider_db
      - POSTGRES_USER=provider
      - POSTGRES_PASSWORD=dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - itl-network

  api-gateway:
    image: itl-api-gateway:latest
    ports:
      - "9050:9050"
    environment:
      - PROVIDER_URL=http://provider:8000
    depends_on:
      - provider
    networks:
      - itl-network

networks:
  itl-network:
    driver: bridge

volumes:
  postgres_data:
```

### Run Locally

```bash
# Start all services
docker-compose up

# Start with live logs
docker-compose up --follow-log-starts

# Stop
docker-compose down

# Clean up volumes
docker-compose down -v
```

---

## Containerization

### Dockerfile for Python Provider

```dockerfile
# Multi-stage build for smaller images

# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /tmp
COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-dev --no-interaction

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /tmp/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY README.md entrypoint.py ./

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
EXPOSE 8000
ENTRYPOINT ["python", "entrypoint.py"]
```

### .dockerignore

```
__pycache__
*.pyc
*.pyo
.git
.github
.gitignore
.vscode
.env
.env.local
.pytest_cache
.coverage
dist
build
*.egg-info
venv/
.venv/
node_modules/
tests/
README.md
LICENSE
```

### Build Image

```bash
# Build with tag
docker build -t my-provider:1.0.0 .

# Build with multiple tags
docker build -t my-provider:1.0.0 -t my-provider:latest .

# Build with build args
docker build --build-arg PYTHON_VERSION=3.11 -t my-provider:1.0.0 .

# Check image size
docker images my-provider

# Run locally
docker run -p 8000:8000 my-provider:1.0.0
```

---

## Kubernetes Deployment

### Helm Chart

```yaml
# Chart.yaml
apiVersion: v2
name: my-provider
description: Custom resource provider
type: application
version: 1.0.0
appVersion: "1.0.0"

# values.yaml
replicaCount: 3

image:
  repository: my-provider
  tag: "1.0.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: provider.itl.local
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

database:
  host: postgres-service
  port: 5432
  name: provider_db
  username: provider
  # Use secrets for password

env:
  - name: LOG_LEVEL
    value: INFO
  - name: PROVIDER_NAME
    value: my-provider
```

### Deployment YAML

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-provider
  namespace: itl-providers
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  
  selector:
    matchLabels:
      app: my-provider
  
  template:
    metadata:
      labels:
        app: my-provider
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    
    spec:
      serviceAccountName: my-provider
      
      containers:
      - name: provider
        image: my-provider:1.0.0
        imagePullPolicy: IfNotPresent
        
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        
        env:
        - name: LOG_LEVEL
          value: INFO
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: provider-secrets
              key: database-url
        
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 2
        
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi

---
apiVersion: v1
kind: Service
metadata:
  name: my-provider
  namespace: itl-providers
spec:
  type: ClusterIP
  selector:
    app: my-provider
  ports:
  - name: http
    port: 80
    targetPort: 8000
    protocol: TCP

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: provider-config
  namespace: itl-providers
data:
  log_level: INFO
  provider_name: my-provider

---
apiVersion: v1
kind: Secret
metadata:
  name: provider-secrets
  namespace: itl-providers
type: Opaque
stringData:
  database-url: postgresql://user:password@postgres:5432/provider_db

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-provider
  namespace: itl-providers
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-provider
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 85
```

### Deploy to Kubernetes

```bash
# Using Helm
helm repo add itl-providers https://charts.itl.local
helm install my-provider itl-providers/my-provider \
  --namespace itl-providers \
  --values values.yaml

# Using kubectl
kubectl apply -f deployment.yaml

# Check deployment
kubectl get deployments -n itl-providers
kubectl get pods -n itl-providers
kubectl logs -n itl-providers deployment/my-provider

# Port forward for testing
kubectl port-forward -n itl-providers svc/my-provider 8000:80
```

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Image security scan (`trivy image my-provider:1.0.0`)
- [ ] Resource limits defined
- [ ] Logging configured
- [ ] Metrics exposed
- [ ] Health checks configured
- [ ] Database migrations tested
- [ ] Secrets managed (not in image)
- [ ] Environment-specific configs
- [ ] Load testing passed
- [ ] failover scenarios tested

### Deployment

- [ ] Gradual rollout (not all replicas at once)
- [ ] Health checks passing
- [ ] No error spikes in logs
- [ ] API Gateway recognizes provider
- [ ] Metrics flowing to monitoring
- [ ] Database backups configured
- [ ] SSH access for debugging
- [ ] Alerting rules configured

### Post-Deployment

- [ ] Smoke tests passed
- [ ] All replicas healthy
- [ ] Resource usage as expected
- [ ] No memory leaks (monitor 1-2 hours)
- [ ] Customer operations working
- [ ] Runbook documented
- [ ] On-call team briefed

---

## Rolling Update Strategy

### Blue-Green Deployment

```yaml
# Keep two deployments, switch traffic between them

apiVersion: v1
kind: Service
metadata:
  name: my-provider
spec:
  selector:
    app: my-provider
    version: blue  # Current

# Deploy "green" version
# Test "green"
# Switch service selector to "green"
# Keep "blue" for rollback
```

### Canary Deployment

```yaml
# Start with 10% traffic to new version, gradually increase

apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: my-provider
spec:
  hosts:
  - my-provider
  http:
  - match:
    - headers:
        user-agent:
          regex: ".*Chrome.*"
    route:
    - destination:
        host: my-provider
        subset: v2
      weight: 100
  - route:
    - destination:
        host: my-provider
        subset: v1
      weight: 90
    - destination:
        host: my-provider
        subset: v2
      weight: 10
```

---

## Environment Configuration

### Environment Variables

```python
# config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    provider_name: str = os.getenv("PROVIDER_NAME", "my-provider")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost/provider_db")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Dev vs Prod
    is_production: bool = environment == "production"
    enable_debug: bool = not is_production

# Usage
from config import Config
config = Config()
```

### Secrets Management

```bash
# Create secret from file
kubectl create secret generic provider-secrets \
  --from-file=.env.production \
  -n itl-providers

# Create secret from literal
kubectl create secret generic provider-secrets \
  --from-literal=database-url=postgresql://user:pass@host/db \
  -n itl-providers

# Update secret
kubectl patch secret provider-secrets -p '{"data":{"database-url":"<base64-encoded>"}}'
```

---

## Monitoring and Observability

### Prometheus Metrics Endpoint

```python
from prometheus_client import Counter, Histogram, Gauge
from fastapi import FastAPI

app = FastAPI()

# Metrics
requests_total = Counter(
    'provider_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'provider_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

resources_count = Gauge(
    'provider_resources_total',
    'Total resources managed'
)

@app.middleware("http")
async def add_metrics(request, call_next):
    with request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).time():
        response = await call_next(request)
    
    requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    return response

@app.get("/metrics")
async def metrics():
    # Return Prometheus format
    from prometheus_client import generate_latest
    return generate_latest()
```

### ServiceMonitor for Prometheus

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-provider
  namespace: itl-providers
spec:
  selector:
    matchLabels:
      app: my-provider
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

---

## Related Documentation

- [13-MONITORING.md](13-MONITORING.md) - Detailed monitoring guide
- [SDK Installation](../02-INSTALLATION.md) - SDK setup
- [Getting Started](../01-GETTING_STARTED.md) - Quick start

---

Production deployments ensure reliability, scalability, and maintainability of resource providers.
