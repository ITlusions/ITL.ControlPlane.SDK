# Mixin Design Roadmap: Advanced Resource Handlers for ITL SDK

**Status**: Design Document  
**Version**: 1.0  
**Created**: 2026-02-13  
**Last Updated**: 2026-02-13

---

## Strategic Overview

This document outlines 11 advanced resource handler mixins that would significantly enhance the ITL Control Plane SDK.

These go **beyond the Big 3** (TimestampedResourceHandler, ProvisioningStateHandler, ValidatedResourceHandler) to address enterprise needs:
- **Audit & Compliance**: Track changes, prove regulatory compliance (BIO, PQC)
- **Data Governance**: Enforce tagging, require metadata
- **Performance**: Cache expensive queries, reduce N+1 patterns
- **Safety**: Soft deletes, cascading updates, immutability
- **Operational**: Batch operations, lifecycle hooks

The design is grounded in actual codebase needs:
- Policy framework already defines compliance and tagging requirements
- AuditEventPublisher infrastructure exists but needs handler integration
- Neo4j queries need optimization for LIST operations (caching)
- Soft delete patterns appear in multiple providers

---

## The 11 Proposed Mixins

### Tier 1: High Priority (Weeks 1-2)

These address critical enterprise needs. Each has clear ROI and straightforward implementation.

#### 1. **AuditedResourceHandler**

**Problem**: Handlers create/update resources but don't generate audit events. Compliance systems (BIO, PQC) need proof of who changed what, when, and why.

**What it does**:
- Auto-publishes audit events on create/update/delete
- Calculates deltas (what changed between versions)
- Captures context (user, requestId, IP, subscription)
- Sends to AuditEventPublisher service

**Example**:
```python
class ResourceGroupHandler(
    AuditedResourceHandler,
    TimestampedResourceHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    validator_model = ResourceGroupModel
    
    async def create(self, request: ResourceRequest) -> ResourceResponse:
        response = await super().create(request)
        # AuditedResourceHandler automatically published:
        # {
        #   "operation": "Create",
        #   "resource_id": response.id,
        #   "changed_fields": {"name", "location", "tags"},
        #   "new_values": {"name": "rg-prod", ...},
        #   "user": "alice@company.com",
        #   "timestamp": "2026-02-13T10:30:00Z"
        # }
        return response
```

**Why build it?**
- AuditEventPublisher already exists - handlers just need to use it
- Compliance frameworks (BIO, PQC) require audit trails
- Log forwarding (Elasticsearch, Splunk, ClickHouse) already configured
- Handlers are the authoritative source of change

**Implementation complexity**: [Medium] (4-6 hours)

---

#### 2. **TagRequiredResourceHandler**

**Problem**: Policy framework defines RequireOwnerTagPolicy, AuditMissingTagPolicy. But these run in downstream evaluation. Handler should enforce early.

**What it does**:
- Validates required tags present before accepting create/update
- Returns 400 Bad Request with missing tags list
- Configurable tags per resource type
- Short-circuits invalid requests ASAP

**Example**:
```python
class ResourceGroupHandler(
    TagRequiredResourceHandler,
    ScopedResourceHandler
):
    required_tags = ["Owner", "CostCenter", "Environment"]
    
    async def create(self, request: ResourceRequest) -> ResourceResponse:
        # Handler automatically validates:
        # - Owner tag present
        # - CostCenter tag present
        # - Environment in ["prod", "staging", "dev"]
        # Returns 400 if any missing
        return await super().create(request)
```

**Why build it?**
- Your policy builder defines extensive tagging requirements
- Policies like RequireOwnerTagPolicy, AuditMissingTagPolicy prove this matters
- Tags drive compliance (BIO requirements, cost allocation, security controls)
- Handlers should enforce this early, not in downstream policy evaluation

**Implementation complexity**: [Simple] (2-3 hours)

---

#### 3. **ComplianceTagResourceHandler**

**Problem**: Some resources need compliance metadata (PQC readiness, encryption status, backup status) tracked via tags.

**What it does**:
- Auto-adds compliance tags on creation
- Updates tags based on resource state
- reads from policy framework
- Tracks PQC migration status, encryption mode, backup config

**Example**:
```python
class VirtualMachineHandler(
    ComplianceTagResourceHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    compliance_tags = {
        "PQC-Status": "NotReady",
        "Encryption": "TBD",
        "BackupPolicy": "Standard"
    }
    
    async def create(self, request: ResourceRequest) -> ResourceResponse:
        # Handler automatically adds:
        # tags["PQC-Status"] = "NotReady"
        # tags["Encryption"] = "TBD"
        # tags["BackupPolicy"] = "Standard"
        return await super().create(request)
```

**Why build it?**
- Policy framework already defines PQC readiness tiers
- Compliance metadata is immutable after creation (audit requirement)
- Handler-managed tags avoid policy race conditions
- Policy framework can't intercept creation - handlers are first defense

**Implementation complexity**: [Medium] (4-6 hours)

---

#### 4. **SoftDeleteResourceHandler**

**Problem**: Hard delete loses audit trail and breaks foreign keys. Need soft delete with recovery grace period (default 30-90 days before purge).

**What it does**:
- DELETE marks resource as "Soft Deleted" instead of removing
- Hidden from LIST/GET by default (transparent to clients)
- Recoverable via PATCH within grace period
- Auto-purged after grace period expires

**Example**:
```python
class ResourceGroupHandler(
    SoftDeleteResourceHandler,
    AuditedResourceHandler,
    ScopedResourceHandler
):
    soft_delete_grace_days = 30
    
    async def delete(self, request: ResourceRequest) -> None:
        # Handler marks as deleted but keeps data:
        # resource.properties["deleteTimestamp"] = now()
        # resource.properties["recoveryDeadline"] = now() + 30 days
        # Hidden from LIST queries
        # Still queryable via direct ID lookup with ?include=deleted
        await super().delete(request)
```

**Why build it?**
- Audit trail must be preserved (compliance requirement)
- Foreign key references must be resolved before hard delete
- Soft delete must be transparent to most code paths
- Common pattern in enterprise systems (Stripe, Azure, AWS)

**Implementation complexity**: [Medium] (4-6 hours)

---

#### 5. **ResourceVersioningHandler**

**Problem**: Need to track all configuration changes with versions and rollback support. Currently "who changed what" but not "what was the old config".

**What it does**:
- Snapshots full resource config on each change
- Maintains version history (100 most recent by default)
- Enables rollback to previous versions
- Paired with AuditedResourceHandler for "why"

**Example**:
```python
class VirtualMachineHandler(
    ResourceVersioningHandler,
    AuditedResourceHandler,
    ScopedResourceHandler
):
    max_versions = 100
    
    async def update(self, request: ResourceRequest) -> ResourceResponse:
        # Handler automatically snapshots:
        # version_history[2] = {config from 1 hour ago}
        # version_history[1] = {config from 30 min ago}
        # version_history[0] = {current config}
        # Users can PATCH with ?rollback_to_version=2
        return await super().update(request)
```

**Why build it?**
- History provides audit trail + rollback capability
- Paired with AuditedResourceHandler (operation) + VersioningHandler (data)
- Use case: "VM was misconfigured, rollback to last known good"
- Neo4j already has version tracking infrastructure

**Implementation complexity**: [Medium] (4-6 hours)

---

#### 6. **CachedResourceHandler**

**Problem**: LIST operations on large resource groups query Neo4j for every request. Metadata doesn't change frequently (hours/days, not seconds).

**What it does**:
- Caches resource metadata (5/15/30 minute TTL configurable)
- Invalidates on create/update/delete
- Reduces Neo4j query load for LIST operations
- Smart pre-fetching reduces N+1 queries

**Example**:
```python
class ResourceGroupHandler(
    CachedResourceHandler,
    ScopedResourceHandler
):
    cache_ttl_minutes = 15
    prefetch_related = ["dependents", "tags", "compliance_metadata"]
    
    async def list_resources(self, request: ListRequest) -> ListResponse:
        # Handler checks cache first:
        # If cache hit && !expired, return cached list
        # If cache miss or expired, query Neo4j && cache result
        # DELETE/UPDATE operations invalidate cache
        return await super().list_resources(request)
```

**Why build it?**
- LIST operations are high-frequency (dashboards, CLIs, discovery)
- Metadata is relatively static (rarely changes within same hour)
- Neo4j query latency is bottleneck for large result sets
- Smart pre-fetching reduces N+1 queries

**Implementation complexity**: [Complex] (6-8 hours)

---

### Tier 2: Medium Priority (Weeks 3-4)

These are valuable but can be deferred. Medium complexity, clear use cases.

#### 7. **CascadingResourceHandler**

**Problem**: Parent resource deleted should cascade to children (ResourceGroup → Resources). Currently manual cleanup required.

**What it does**:
- On parent delete, automatically deletes/marks children
- Maintains referential integrity without foreign keys
- Handles deep hierarchies (Subscription → RG → VM → Disk)
- Audit events for each cascade deletion

**Example**:
```python
class ResourceGroupHandler(
    CascadingResourceHandler,
    AuditedResourceHandler,
    ScopedResourceHandler
):
    cascade_delete_children = ["virtualmachines", "storageaccounts"]
    
    async def delete(self, request: ResourceRequest) -> None:
        # Handler automatically deletes children:
        # FOR each VM in resource_group.virtualmachines:
        #   DELETE VM (triggers its own cascades)
        # FOR each storage in resource_group.storageaccounts:
        #   DELETE storage
        # Finally DELETE the resource group
        await super().delete(request)
```

**Why build it?**
- Referential integrity without traditional foreign keys
- Cascades are common in hierarchical systems
- Must generate audit events for each cascade
- Reduces orphaned resources

**Implementation complexity**: [Medium] (4-5 hours)

---

#### 8. **LifecycleHookResourceHandler**

**Problem**: Some handlers need custom logic before/after operations (e.g., "notify team before delete", "initialize VM after create").

**What it does**:
- Hook methods: on_creating, on_created, on_updating, on_updated, on_deleting, on_deleted
- Handler subclasses override hooks for custom logic
- Hooks run in transaction context (can abort)
- Async-friendly

**Example**:
```python
class VirtualMachineHandler(
    LifecycleHookResourceHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    async def on_created(self, request: ResourceRequest, response: ResourceResponse):
        # Custom logic after VM created:
        await notify_team(f"VM {response.name} created")
        await initialize_monitoring(response.id)
        await configure_network(response.id)
    
    async def on_deleting(self, request: ResourceRequest):
        # Custom logic before VM deleted:
        if not request.force_delete:
            await drain_connections(request.resource_id)
            await backup_config(request.resource_id)
```

**Why build it?**
- Pre/post hooks are common in many frameworks (Django, SQLAlchemy)
- Enables custom initialization, cleanup, notifications
- Keeps handler logic isolated and testable

**Implementation complexity**: [Medium] (4-5 hours)

---

#### 9. **ImmutableResourceHandler**

**Problem**: Some resources (compliance configs, policy bindings) should never change after creation. UPDATE should fail, not silently ignore.

**What it does**:
- After creation, all PATCH/PUT requests fail with 405 Method Not Allowed
- Optional: Allow specific fields (tags, compliance status)
- Clear error message: "Resource immutable, delete and recreate"

**Example**:
```python
class PolicyBindingHandler(
    ImmutableResourceHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    immutable_after_creation = True
    allow_tag_updates = True  # Tags can change but not properties
    
    async def update(self, request: ResourceRequest) -> ResourceResponse:
        # Handler rejects UPDATE:
        # if resource exists:
        #   if request.properties != current.properties:
        #     raise 405: "Policy binding is immutable"
        #   if request.tags != current.tags:
        #     update tags (allowed)
        return await super().update(request)
```

**Why build it?**
- "Immutable after creation" is a common pattern in cloud APIs
- Compliance configs must never change silently
- Forces explicit delete-and-recreate for audit trail
- Prevents accidental overwrites

**Implementation complexity**: [Simple] (2-3 hours)

---

#### 10. **BatchResourceHandler**

**Problem**: Multiple CREATE/UPDATE operations sent as separate requests. Batch support enables:
- Single transaction for all operations
- Better audit trail (single batch ID)
- Reduced request overhead

**What it does**:
- Accept POST with array of resources
- Create all in single transaction
- Return array of responses (200 for success, 400 for failures)
- Single audit event for batch (with count)

**Example**:
```python
class ResourceGroupHandler(
    BatchResourceHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    max_batch_size = 100
    
    async def batch_create(self, batch_request: BatchCreateRequest) -> BatchCreateResponse:
        # Handler creates all resources:
        # for each resource in batch:
        #   validate
        #   create in transaction
        # if any fails, rollback all
        # return Array<ResourceResponse | ErrorResponse>
        return await super().batch_create(batch_request)
```

**Why build it?**
- Batch operations reduce API call overhead
- Single transaction ensures consistency
- Dashboard/Portal need bulk upload support
- Reduces network latency for multiple operations

**Implementation complexity**: [Complex] (8-10 hours)

---

### Tier 3: Lower Priority (Future Consideration)

#### 11. **QuotaAwareResourceHandler**

**Problem**: Subscriptions have quotas (max 100 VMs, max 50 resource groups). Handlers should enforce early.

**What it does**:
- Checks subscription quota before allowing create
- Returns 429 Too Many Requests when quota exceeded
- Integrates with quota service for current usage
- Decrements quota on delete

**Example**:
```python
class VirtualMachineHandler(
    QuotaAwareResourceHandler,
    ScopedResourceHandler
):
    quota_key = "vm_count"
    
    async def create(self, request: ResourceRequest) -> ResourceResponse:
        # Handler checks quota:
        # current_usage = await quota_service.get_usage(subscription, "vm_count")
        # if current_usage >= quota:
        #   raise 429: "Quota exceeded"
        # create VM
        # quota_service.increment_usage(subscription, "vm_count", 1)
        return await super().create(request)
```

**Why build it?**
- Quota enforcement prevents runaway costs
- Catches mistakes early (better UX than billing surprises)
- Common in all cloud providers (Azure, AWS, GCP)
- Can be added later (lower priority)

**Implementation complexity**: [Simple] to [Medium] (3-5 hours)

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Priority Mixins**: AuditedResourceHandler, TagRequiredResourceHandler, ComplianceTagResourceHandler

**Deliverables**:
- Mixin base classes with 80% test coverage
- Integration tests with real database
- Documentation with code examples
- PR with code review

**Success Criteria**:
- All 3 mixins working independently
- Composable with Big 3 (any order)
- No performance regression

---

### Phase 2: Safety & History (Weeks 2-3)

**Priority Mixins**: SoftDeleteResourceHandler, ResourceVersioningHandler

**Deliverables**:
- Soft delete implementation + recovery mechanism
- Version history with rollback
- Cleanup jobs for expired soft deletes
- Migration guide for existing handlers

**Success Criteria**:
- Soft deletes transparent to existing code
- Rollback feature tested with real scenarios
- Cleanup job runs without errors

---

### Phase 3: Performance & Hooks (Weeks 4-5)

**Priority Mixins**: CachedResourceHandler, LifecycleHookResourceHandler, CascadingResourceHandler

**Deliverables**:
- Cache layer with configurable TTL
- Hook framework with async support
- Cascade implementation with hierarchy testing
- Performance benchmarks (LIST improvement)

**Success Criteria**:
- LIST operations 30% faster with cache
- Hooks execute reliably
- Cascades maintain referential integrity

---

### Phase 4: Advanced Features (Weeks 6+)

**Priority Mixins**: ImmutableResourceHandler, BatchResourceHandler, QuotaAwareResourceHandler

**Deliverables**:
- Immutability enforcement
- Batch API with atomic transactions
- Quota integration with service
- Complete documentation

**Success Criteria**:
- Batch operations 50% faster than individual requests
- Quota enforcement working end-to-end
- All 11 mixins documented and tested

---

## Composition Examples

### Example 1: Audit-Compliant Resource Group Handler

```python
from itl_sdk.handlers import (
    ResourceHandler,
    ScopedResourceHandler,
    TimestampedResourceHandler,
    ValidatedResourceHandler,
    AuditedResourceHandler,
    TagRequiredResourceHandler,
    LifecycleHookResourceHandler
)

class ResourceGroupHandler(
    AuditedResourceHandler,
    TagRequiredResourceHandler,
    TimestampedResourceHandler,
    ValidatedResourceHandler,
    LifecycleHookResourceHandler,
    ScopedResourceHandler
):
    """Compliance-ready resource group handler.
    
    Features:
    - Automatic audit event publishing
    - Required tag enforcement (Owner, CostCenter)
    - Timestamps on all operations
    - Schema validation (Pydantic)
    - Pre/post operation hooks
    - Scope-aware resource partitioning
    """
    
    required_tags = ["Owner", "CostCenter", "Environment"]
    validator_model = ResourceGroupModel
    
    async def on_created(self, request, response):
        print(f"Resource group {response.name} created")
        # Custom notification, monitoring setup, etc.
```

### Example 2: Safety-Critical VM Handler

```python
class VirtualMachineHandler(
    SoftDeleteResourceHandler,
    ResourceVersioningHandler,
    AuditedResourceHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    """Safety-critical VM handler.
    
    Features:
    - Soft deletes with 30-day recovery window
    - Full config version history (100 versions)
    - Audit trail of all changes
    - Schema validation
    """
    
    soft_delete_grace_days = 30
    max_versions = 100
    validator_model = VirtualMachineModel
```

### Example 3: High-Performance List Operations

```python
class StorageAccountHandler(
    CachedResourceHandler,
    AuditedResourceHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    """High-performance storage account handler.
    
    Features:
    - Metadata caching (15 min TTL)
    - Automatic audit events
    - Smart prefetching (reduces N+1)
    """
    
    cache_ttl_minutes = 15
    prefetch_related = ["containers", "compliance_metadata"]
    validator_model = StorageAccountModel
```

---

## Technical Notes

### Compatibility

All mixins are:
- **Independent**: Each provides specific functionality
- **Composable**: Stack in any order with MRO
- **Non-breaking**: Existing handlers continue to work
- **Testable**: Unit testable in isolation

### Performance Impact

| Mixin | Latency Impact | Memory Impact | Notes |
|-------|---|---|---|
| AuditedResourceHandler | +5ms | +2KB | Async publish, negligible |
| TagRequiredResourceHandler | +2ms | Negligible | Simple validation |
| ComplianceTagResourceHandler | +3ms | Negligible | Tag injection |
| SoftDeleteResourceHandler | Negligible | +500B | Extra flag in resource |
| ResourceVersioningHandler | +10ms | +200KB/resource | Version history storage |
| CachedResourceHandler | -50ms (LIST) | +5MB | Cache size configurable |
| CascadingResourceHandler | +20ms | Negligible | Recursive deletes |
| LifecycleHookResourceHandler | Variable | Negligible | User hook-dependent |
| ImmutableResourceHandler | +1ms | Negligible | Single check |
| BatchResourceHandler | -200ms (bulk) | Negligible | Transactional benefit |
| QuotaAwareResourceHandler | +5ms. | Negligible | Service call |

---

## Integration Points

### With Existing Infrastructure

- **AuditEventPublisher**: AuditedResourceHandler publishes events
- **Policy Framework**: ComplianceTagResourceHandler, TagRequiredResourceHandler
- **Neo4j**: CachedResourceHandler, ResourceVersioningHandler
- **Service Bus**: LifecycleHookResourceHandler, CascadingResourceHandler
- **Database**: SoftDeleteResourceHandler, ResourceVersioningHandler

### Future Possibilities

- Webhook support (lifecycle hooks -> webhooks)
- Change Data Capture (CDC) integration
- Cross-subscription operations support
- Multi-tenant isolation validation

---

## Getting Help

For questions about mixin design:
1. See [Big 3 Handler Mixins](../features/handler-mixins.md) for production patterns
2. Review code examples above for composition strategies
3. Check integration tests for real-world scenarios
4. Post questions in #sdk-development Slack channel

---

**Status**: Design Document (v1.0)  
**Next Review**: After Phase 1 completion  
**Maintainer**: SDK Team
