# Lifecycle Hooks - Quick Reference Card

**One-page reference for hook signatures and common patterns**

---

## Hook Signatures

### Pre-Hooks (Can abort with exception)

```python
async def on_creating(self, request: ResourceRequest, context: ProviderContext) -> None:
    """Called before resource creation. Can raise exception to abort."""

async def on_getting(self, request: ResourceRequest, context: ProviderContext) -> None:
    """Called before resource retrieval. Can raise exception to deny access."""

async def on_updating(self, request: ResourceRequest, context: ProviderContext) -> None:
    """Called before resource update. Can raise exception to abort."""

async def on_deleting(self, request: ResourceRequest, context: ProviderContext) -> None:
    """Called before resource deletion. Can raise exception to abort."""
```

### Post-Hooks (Cannot abort, exceptions logged)

```python
async def on_created(self, request: ResourceRequest, response: ResourceResponse, context: ProviderContext) -> None:
    """Called after successful resource creation."""

async def on_updated(self, request: ResourceRequest, response: ResourceResponse, context: ProviderContext) -> None:
    """Called after successful resource update."""

async def on_deleted(self, request: ResourceRequest, context: ProviderContext) -> None:
    """Called after successful resource deletion."""
```

### Customization Points

```python
async def _audit_log(self, **details) -> None:
    """Default: logs to Python logger. Override to send to external system."""

async def _record_metric(self, **metric) -> None:
    """Default: logs to Python logger. Override to send to monitoring system."""

async def _publish_event(self, **event) -> None:
    """Default: logs to Python logger. Override to send to event broker."""
```

---

## Common Patterns

### Pattern 1: Validation (Pre-Hook)

```python
class ValidatedProvider(CoreProvider):
    async def on_creating(self, request, context):
        # Check quota
        if self.get_quota(context.tenant_id) >= limit:
            raise ValueError(f"Quota exceeded for {context.tenant_id}")
        
        # Check policy
        if not self.is_policy_compliant(request.body):
            raise ValueError("Request violates policy")
        
        # Keep defaults
        await super().on_creating(request, context)
```

### Pattern 2: Audit Logging (Override _audit_log)

```python
class AuditingProvider(CoreProvider):
    async def _audit_log(self, **details):
        # Send to ClickHouse
        await self.clickhouse.insert('audit_logs', {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': details.get('operation'),
            'resource_id': details.get('resource_id'),
            'user_id': details.get('user_id'),
            'status': details.get('status')
        })
```

### Pattern 3: Metrics Recording (Override _record_metric)

```python
class MetricProvider(CoreProvider):
    async def _record_metric(self, **metric):
        # Send to Prometheus
        self.resources_created.inc(
            labels={'resource_type': metric.get('resource_type')}
        )
        self.hook_duration.observe(
            metric.get('duration_ms')
        )
```

### Pattern 4: Event Publishing (Override _publish_event)

```python
class EventProvider(CoreProvider):
    async def _publish_event(self, **event):
        # Send to Kafka
        await self.kafka.send('control-plane-events', {
            'event_type': event.get('event_type'),
            'resource_id': event.get('resource_id'),
            'timestamp': datetime.utcnow().isoformat(),
            'data': event.get('data')
        })
```

### Pattern 5: Multiple Customizations (Combine)

```python
class FullProvider(ValidatedProvider, AuditingProvider, MetricProvider, EventProvider):
    """Combines all features via multiple inheritance and MRO."""
    pass
```

---

## Usage Examples

### Default Behavior (No Customization)

```python
provider = CoreProvider()
request = ResourceRequest(resource_name="rg-prod", ...)
response = await provider.create_or_update_resource(request, context)
# ✅ Automatically logs to console
```

### With Validation

```python
provider = ValidatedProvider()
response = await provider.create_or_update_resource(request, context)
# ✅ Checks quota before creating
# ❌ Returns 400 if quota exceeded
```

### With Audit + Metrics + Events

```python
provider = EventProvider(
    clickhouse_host="ch.company.com",
    prometheus_pushgateway="http://prom:9091",
    kafka_brokers=["kafka:9092"]
)
response = await provider.create_or_update_resource(request, context)
# ✅ Sends audit log to ClickHouse
# ✅ Records metric to Prometheus
# ✅ Publishes event to Kafka
```

### Full Enterprise Setup

```python
provider = FullProvider(
    # Validation
    # Monitoring
)
response = await provider.create_or_update_resource(request, context)
# ✅ Validates quota
# ✅ Logs to ClickHouse
# ✅ Records to Prometheus
# ✅ Publishes to Kafka
```

---

## Default Implementations (SDK Base)

### on_creating Default

```python
async def on_creating(self, request, context):
    await self._audit_log(
        operation='creating',
        resource_name=request.resource_name,
        resource_type=request.resource_type
    )
```

### on_created Default

```python
async def on_created(self, request, response, context):
    await self._audit_log(
        operation='created',
        resource_id=response.id,
        status=response.provisioning_state
    )
    await self._record_metric(
        operation='create',
        resource_type=request.resource_type,
        status='succeeded',
        duration_ms=elapsed_time
    )
    await self._publish_event(
        event_type='resource.created',
        resource_id=response.id,
        resource_type=request.resource_type
    )
```

### _audit_log Default

```python
async def _audit_log(self, **details):
    logger.info(f"AUDIT: {details}")
```

### _record_metric Default

```python
async def _record_metric(self, **metric):
    logger.info(f"METRIC: {metric}")
```

### _publish_event Default

```python
async def _publish_event(self, **event):
    logger.info(f"EVENT: {event}")
```

---

## Resource Types

Common resource types that trigger hooks:

```
ResourceGroups
Subscriptions
ManagementGroups
Deployments
Tags
Policies
Locations
Tenants
ExtendedLocations
```

All resource types automatically call hooks in create/get/update/delete operations.

---

## Backend Options

### Audit Logging Backends

| Backend | Queryable | Searchable | Real-time | Cost |
|---------|-----------|-----------|-----------|------|
| ClickHouse | ✅ | ❌ | ❌ | Low |
| Elasticsearch | ✅ | ✅ | ⚠️ | Medium |
| Splunk | ✅ | ✅ | ✅ | High |

### Metrics Backends

| Backend | Dashboards | Alerts | Retention | Cost |
|---------|-----------|--------|-----------|------|
| Prometheus | ✅ | ✅ | 15 days | Low |
| Datadog | ✅ | ✅ | Flexible | High |
| New Relic | ✅ | ✅ | Flexible | High |

### Event Backends

| Backend | Streaming | Processing | Retention | Cost |
|---------|-----------|------------|-----------|------|
| Kafka | ✅ | ✅ | Configurable | Low |
| Event Hub | ✅ | ✅ | Configurable | Medium |
| SNS | ❌ | ✅ | Immediate | Low |

---

## Type Definitions

### ResourceRequest

```python
class ResourceRequest:
    resource_type: str              # e.g., "ResourceGroups"
    resource_name: str              # e.g., "rg-prod"
    subscription_id: str            # e.g., "sub-123"
    resource_group: Optional[str]   # e.g., "rg-parent"
    location: Optional[str]         # e.g., "eastus"
    body: Dict[str, Any]            # Custom properties
    tags: Dict[str, str]            # Tags
```

### ResourceResponse

```python
class ResourceResponse:
    id: str                         # Full resource ID
    name: str                       # Resource name
    type: str                       # Full resource type
    location: Optional[str]         # Location
    provisioning_state: str         # "Succeeded", "Failed", etc.
    properties: Dict[str, Any]      # Resource properties
    tags: Dict[str, str]            # Tags
```

### ProviderContext

```python
class ProviderContext:
    user_id: str                    # "user@company.com"
    tenant_id: str                  # Subscription/tenant
    request_id: str                 # Unique request ID
    operation: str                  # "create", "get", "delete"
```

---

## Testing

### Unit Test Template

```python
@pytest.mark.asyncio
async def test_on_creating_called():
    provider = ValidatedProvider()
    provider.on_creating = AsyncMock()
    
    await provider.create_or_update_resource(request, context)
    
    provider.on_creating.assert_called_once()
```

### Integration Test Template

```python
@pytest.mark.asyncio
async def test_create_with_validation():
    provider = ValiatedProvider()
    request = ResourceRequest(resource_name="rg-prod", ...)
    
    response = await provider.create_or_update_resource(request, context)
    
    assert response.provisioning_state == "Succeeded"
    # Verify validation was checked
    # Verify audit log was recorded
    # Verify metric was sent
```

---

## Deployment Checklist

- [ ] SDK base class has default implementations
- [ ] CustomProvider classes created (ValidatedCoreProvider, etc.)
- [ ] Tests pass (20+ tests recommended)
- [ ] Docker image builds successfully
- [ ] Environment variables configured
- [ ] Backend systems reachable (ClickHouse, Prometheus, Kafka)
- [ ] Monitoring dashboards created
- [ ] Load tests pass (100+ concurrent requests)
- [ ] Production deployment complete

---

## Key Commands

```bash
# Build Docker image
docker build -t itl-core-provider:latest .

# Start with docker-compose
docker-compose up -d

# Check service health
curl http://localhost:8000/health

# View audit logs
curl -X GET "http://clickhouse:8123/?query=SELECT%20*%20FROM%20audit_logs%20LIMIT%2010"

# View metrics
curl http://prometheus:9090/api/v1/query?query=resources_created_total

# List Kafka events
kafka-console-consumer --bootstrap-servers kafka:9092 --topic control-plane-events --from-beginning
```

---

**Reference:** For complete details, see the full documentation in the docs/LIFECYCLE_HOOKS folder.
