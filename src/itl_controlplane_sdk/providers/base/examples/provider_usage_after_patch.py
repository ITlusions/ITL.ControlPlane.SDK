"""
AFTER THE PATCH: How Providers Work with Default Hooks

This shows what happens before/after you apply the patch to provider.py
"""

# ============================================================================
# SCENARIO 1: Provider That Uses All Defaults (No Code Changes)
# ============================================================================

SCENARIO_1_CODE = """
# Example: Simple compute provider that accepts all defaults

from itl_controlplane_sdk import ResourceProvider, ResourceRequest, ResourceResponse

class SimpleVMProvider(ResourceProvider):
    '''A provider that automatically gets audit logging, metrics, and events.'''
    
    async def create_or_update_resource(self, request, context):
        # Framework calls hooks automatically:
        # 1. self.on_creating(request, context)  <-- Logs request
        # 2. [actual create code from provider subclass]
        # 3. self.on_created(request, response, context)  <-- Audit + metrics + events
        
        # YOUR CODE HERE - just the business logic
        vm = await self._create_vm_in_cloud(request.spec)
        return ResourceResponse(id=vm.id, name=vm.name)
    
    async def _create_vm_in_cloud(self, spec):
        # Implementation details...
        pass

# Usage:
provider = SimpleVMProvider()
result = await provider.create_or_update_resource(request, context)

# What happens automatically:
# 1. [2025-01-15 10:00:00] INFO: Creating vm: name=my-vm user=user123 request_id=req-456
# 2. [VM creation happens...]
# 3. [2025-01-15 10:00:01] INFO: AUDIT_LOG: {operation=ResourceCreated, resource_id=vm-789, ...}
# 4. [2025-01-15 10:00:01] DEBUG: METRIC: {metric_name=resources_created_total, value=1, ...}
# 5. [2025-01-15 10:00:01] DEBUG: EVENT: {event_type=resource.created, resource_id=vm-789, ...}

# ZERO additional provider code needed!
"""

# ============================================================================
# SCENARIO 2: Provider That Overrides a Hook (Keeps Defaults)
# ============================================================================

SCENARIO_2_CODE = """
# Example: Provider that adds custom logic while keeping defaults

from itl_controlplane_sdk import ResourceProvider

class PoliciedVMProvider(ResourceProvider):
    '''A provider that enforces policies + keeps default logging/metrics.'''
    
    async def on_creating(self, request, context):
        # Custom: Check user quota first
        quota = await self.check_quota(context.tenant_id)
        if quota.remaining <= 0:
            raise QuotaExceededError("No VMs remaining in quota")
        
        # Keep defaults: Log the request
        await super().on_creating(request, context)
    
    async def on_created(self, request, response, context):
        # Custom: Notify team that VM was created
        await self.send_notification(f"VM {response.name} created by {context.user_id}")
        
        # Keep defaults: Audit log + metrics + events
        await super().on_created(request, response, context)
    
    async def create_or_update_resource(self, request, context):
        # Framework calls hooks:
        # 1. self.on_creating() calls super() -> logs + checks quota
        # 2. [actual create code]
        # 3. self.on_created() calls super() -> audits + metrics + events + notifies
        
        vm = await self._create_vm_in_cloud(request.spec)
        return ResourceResponse(id=vm.id, name=vm.name)
    
    async def check_quota(self, tenant_id):
        # Your quota logic...
        pass
    
    async def send_notification(self, message):
        # Your notification logic...
        pass
    
    async def _create_vm_in_cloud(self, spec):
        pass

# Usage:
provider = PoliciedVMProvider()
result = await provider.create_or_update_resource(request, context)

# What happens:
# 1. [10:00:00] INFO: Creating vm: name=my-vm user=user123  <-- default logging
# 2. [Custom] Checking quota for tenant-999
# 3. [VM creation happens...]
# 4. [Custom] Sent notification to team
# 5. [10:00:01] INFO: AUDIT_LOG: ... <-- default audit
# 6. [10:00:01] DEBUG: METRIC: ... <-- default metrics
# 7. [10:00:01] DEBUG: EVENT: ... <-- default events

# You added 2 custom actions + kept all defaults!
"""

# ============================================================================
# SCENARIO 3: Provider That Customizes the Helper Methods
# ============================================================================

SCENARIO_3_CODE = """
# Example: Provider that sends to Elasticsearch, Prometheus, Kafka

from itl_controlplane_sdk import ResourceProvider
from elasticsearch import Elasticsearch
from prometheus_client import Counter
import aiokafka

class EnterpriseVMProvider(ResourceProvider):
    '''A provider that uses enterprise systems for audit/metrics/events.'''
    
    def __init__(self):
        self.es = Elasticsearch(['https://elasticsearch.company.com'])
        self.kafka = aiokafka.AIOKafkaProducer()
    
    async def _audit_log(self, **details):
        # Override: Send to Elasticsearch instead of logging
        await self.es.index(
            index="audit-logs",
            doc_type="_doc",
            body=details
        )
    
    async def _record_metric(self, **metric):
        # Override: Send to Prometheus instead of logging
        counter = Counter(
            metric['metric_name'],
            'Resource operations',
            labelnames=list(metric.get('tags', {}).keys())
        )
        counter.labels(**metric.get('tags', {})).inc(metric['value'])
    
    async def _publish_event(self, **event):
        # Override: Send to Kafka instead of logging
        await self.kafka.send_and_wait(
            "resource-events",
            value=json.dumps(event).encode('utf-8')
        )
    
    async def on_created(self, request, response, context):
        # All calls to _audit_log/_record_metric/_publish_event
        # now go to your enterprise systems!
        await super().on_created(request, response, context)
    
    async def create_or_update_resource(self, request, context):
        vm = await self._create_vm_in_cloud(request.spec)
        return ResourceResponse(id=vm.id, name=vm.name)
    
    async def _create_vm_in_cloud(self, spec):
        pass

# Usage:
provider = EnterpriseVMProvider()
result = await provider.create_or_update_resource(request, context)

# What happens:
# 1. on_created is called
# 2. super().on_created() calls _audit_log → Elasticsearch
# 3. super().on_created() calls _record_metric → Prometheus
# 4. super().on_created() calls _publish_event → Kafka
# 5. Your enterprise dashboards light up automatically!

# Your provider code: 30 lines
# All defaults configured for your systems: ✓ Automatic
"""

# ============================================================================
# SCENARIO 4: Provider Using Optional Mixins (Composition)
# ============================================================================

SCENARIO_4_CODE = """
# Example: Provider that composes behaviors with mixins

from itl_controlplane_sdk import ResourceProvider
from itl_controlplane_sdk.mixins import (
    RateLimitingHook,
    QuotaEnforcementHook,
    DependencyCheckHook
)

class SecureVMProvider(
    RateLimitingHook,  # Rate limit all operations
    QuotaEnforcementHook,  # Check quota before create
    DependencyCheckHook,  # Verify dependencies before delete
    ResourceProvider  # Must be last!
):
    '''A provider with multiple capabilities via mixins.'''
    
    # Each mixin adds its own on_creating, on_deleting, etc.
    # All call super() so they chain together
    # MRO: SecureVMProvider → RateLimitingHook → QuotaEnforcementHook 
    #     → DependencyCheckHook → ResourceProvider
    
    async def create_or_update_resource(self, request, context):
        vm = await self._create_vm_in_cloud(request.spec)
        return ResourceResponse(id=vm.id, name=vm.name)
    
    async def _create_vm_in_cloud(self, spec):
        pass

# Usage:
provider = SecureVMProvider()
result = await provider.create_or_update_resource(request, context)

# What happens in on_creating:
# 1. RateLimitingHook.on_creating → check rate limit → super()
# 2. QuotaEnforcementHook.on_creating → check quota → super()
# 3. DependencyCheckHook.on_creating → no-op (only on delete) → super()
# 4. ResourceProvider.on_creating → log request

# What happens in on_deleting:
# 1. RateLimitingHook.on_deleting → check rate limit → super()
# 2. QuotaEnforcementHook.on_deleting → no-op (only on create) → super()
# 3. DependencyCheckHook.on_deleting → check dependencies → super()
# 4. ResourceProvider.on_deleting → log request

# All behaviors automatic! Mix and match as needed!
"""

# ============================================================================
# COMPARISON TABLE: Before and After Patch
# ============================================================================

COMPARISON = """
╔════════════════════════════════════════════════════════════════════════════╗
║               BEFORE PATCH vs AFTER PATCH                                  ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║ BEFORE: Base class hooks are empty (pass)                                 ║
║ ────────────────────────────────────────────────────────────────────────  ║
║   class ResourceProvider:                                                 ║
║       async def on_created(self, request, response, context):             ║
║           pass  # Empty! Providers must add all logic                     ║
║                                                                            ║
║   Every provider must duplicate:                                          ║
║   • Audit logging code                                                    ║
║   • Metrics recording code                                                ║
║   • Event publishing code                                                 ║
║   • Logging for all hook points                                           ║
║                                                                            ║
║   Result: Code duplication, inconsistency, bugs                           ║
║                                                                            ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║ AFTER: Base class hooks have working implementations                      ║
║ ────────────────────────────────────────────────────────────────────────  ║
║   class ResourceProvider:                                                 ║
║       async def on_created(self, request, response, context):             ║
║           await self._audit_log(...)  # Has implementation!               ║
║           await self._record_metric(...)                                  ║
║           await self._publish_event(...)                                  ║
║                                                                            ║
║   Every provider AUTOMATICALLY gets:                                      ║
║   ✓ Audit logging (to logger by default, override _audit_log)            ║
║   ✓ Metrics recording (to logger by default, override _record_metric)    ║
║   ✓ Event publishing (to logger by default, override _publish_event)     ║
║   ✓ Request logging in all pre-hooks (on_creating, on_getting, etc.)    ║
║                                                                            ║
║   Providers can:                                                          ║
║   • Use all defaults (zero code changes)                                  ║
║   • Override hooks and call super() (add custom logic + keep defaults)   ║
║   • Override _audit_log/_record_metric (_publish_event (customize systems) ║
║   • Compose with optional mixins (layer behaviors)                        ║
║                                                                            ║
║   Result: Single source of truth, consistent, extensible, no duplication ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

# ============================================================================
# AFTER PATCH: Hook Call Chains
# ============================================================================

HOOK_CHAINS = """
CREATE OPERATION FLOW (after patch):
═══════════════════════════════════════════════════════════════════════════

Request: POST /resources (create VM)
           │
           ▼
framework calls create_or_update_resource()
           │
           ▼
framework calls on_creating(request, context)
           │
           ├─→ ResourceProvider.on_creating() [DEFAULT]
           │       └─→ logger.info(f"Creating {type}: ...")
           │
           ├─→ YOUR PROVIDER OVERRIDE (if exists)
           │       └─→ Custom logic (validate quota, check policy, etc.)
           │       └─→ await super().on_creating()  [KEEPS DEFAULT]
           │
           └─→ if exception raised: ABORT, return error

           ↓ [Only if on_creating succeeds]

[YOUR BUSINESS LOGIC - actual create_or_update_resource]
           │
           ├─→ await self._create_vm_in_cloud(spec)
           │
           └─→ return response

           ▼ [Only if creation succeeds]

framework calls on_created(request, response, context)
           │
           ├─→ ResourceProvider.on_created() [DEFAULT]
           │       ├─→ await _audit_log(...)  [default: logger]
           │       ├─→ await _record_metric(...)  [default: logger]
           │       └─→ await _publish_event(...)  [default: logger]
           │
           ├─→ YOUR PROVIDER OVERRIDE (if exists)
           │       └─→ Custom logic (send notification, update cache, etc.)
           │       └─→ await super().on_created()  [KEEPS AUDIT+METRICS+EVENTS]
           │
           └─→ exception logged but NOT raised (operation succeeded)

           ▼

Return response to client (201 Created)

═══════════════════════════════════════════════════════════════════════════

KEY FACTS:
─────────

1. DEFAULTS ARE AUTOMATIC
   Every provider gets audit + metrics + events without any code

2. OPTIONAL CUSTOMIZATION
   Override _audit_log, _record_metric, _publish_event to change systems
   (send to Elasticsearch, Prometheus, Kafka instead of logger)

3. OPTIONAL MIXINS
   RateLimitingHook, QuotaEnforcementHook, DependencyCheckHook provide
   pre-built behaviors you can compose

4. SUPER() PATTERN
   Override hook + call super() to add custom logic while keeping defaults

5. PRE-HOOKS CAN ABORT
   Exceptions in on_creating/on_updating/on_deleting/on_getting abort operation

6. POST-HOOKS NEVER ABORT
   Exceptions in on_created/on_updated/on_deleted are logged but don't affect
   that the operation succeeded

═══════════════════════════════════════════════════════════════════════════
"""

# ============================================================================
# TESTING AFTER PATCH
# ============================================================================

TESTING_AFTER_PATCH = """
UNIT TESTS: Verify Default Behavior

import pytest
from unittest.mock import AsyncMock, patch

class TestDefaultHooks:
    
    @pytest.mark.asyncio
    async def test_on_creating_logs_request(self):
        '''Verify on_creating logs the request.'''
        
        provider = SimpleVMProvider()
        request = ResourceRequest(resource_type="vm", spec={"name": "test"})
        context = ProviderContext(user_id="user1", tenant_id="tenant1")
        
        with patch('logging.getLogger') as mock_logger:
            await provider.on_creating(request, context)
            
            # Verify logged
            log_call = mock_logger().info.call_args[0][0]
            assert "Creating vm" in log_call
            assert "test" in log_call
    
    @pytest.mark.asyncio
    async def test_on_created_calls_audit_metrics_events(self):
        '''Verify on_created calls all default handlers.'''
        
        provider = SimpleVMProvider()
        request = ResourceRequest(resource_type="vm", spec={"name": "test"})
        response = ResourceResponse(id="vm-123", name="test")
        context = ProviderContext(user_id="user1", tenant_id="tenant1")
        
        provider._audit_log = AsyncMock()
        provider._record_metric = AsyncMock()
        provider._publish_event = AsyncMock()
        
        await provider.on_created(request, response, context)
        
        # Verify all called
        provider._audit_log.assert_called_once()
        provider._record_metric.assert_called_once()
        provider._publish_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_override_hook_calls_super(self):
        '''Verify provider can override and call super().'''
        
        class CustomProvider(SimpleVMProvider):
            async def on_creating(self, request, context):
                # Custom logic
                self.custom_called = True
                # Keep defaults
                await super().on_creating(request, context)
        
        provider = CustomProvider()
        request = ResourceRequest(resource_type="vm", spec={"name": "test"})
        context = ProviderContext(user_id="user1", tenant_id="tenant1")
        
        with patch('logging.getLogger'):
            await provider.on_creating(request, context)
        
        # Verify custom logic ran
        assert provider.custom_called == True
        # Verify logs were written (super() was called)
    
    @pytest.mark.asyncio
    async def test_custom_audit_log_system(self):
        '''Verify provider can override _audit_log for custom system.'''
        
        class ElasticsearchProvider(SimpleVMProvider):
            async def _audit_log(self, **details):
                # Send to Elasticsearch instead of logger
                self.es_logs.append(details)
            
            def __init__(self):
                super().__init__()
                self.es_logs = []
        
        provider = ElasticsearchProvider()
        
        await provider._audit_log(operation="test", user="user1")
        
        assert len(provider.es_logs) == 1
        assert provider.es_logs[0]["operation"] == "test"

INTEGRATION TESTS: Verify Full Hook Chain

    @pytest.mark.asyncio
    async def test_create_order_of_hooks(self):
        '''Verify correct order: on_creating → create → on_created.'''
        
        class TrackedProvider(SimpleVMProvider):
            def __init__(self):
                super().__init__()
                self.call_order = []
            
            async def on_creating(self, request, context):
                self.call_order.append('on_creating')
                await super().on_creating(request, context)
            
            async def on_created(self, request, response, context):
                self.call_order.append('on_created')
                await super().on_created(request, response, context)
            
            async def _create_vm_in_cloud(self, spec):
                self.call_order.append('create')
                return MagicMock(id="vm-123", name="test")
        
        provider = TrackedProvider()
        request = ResourceRequest(resource_type="vm", spec={"name": "test"})
        context = ProviderContext(user_id="user1", tenant_id="tenant1")
        
        response = await provider.create_or_update_resource(request, context)
        
        # Verify correct order
        assert provider.call_order == ['on_creating', 'create', 'on_created']
        assert response.id == "vm-123"
"""

# Print all the scenarios and testing guide
print("=" * 80)
print("AFTER PATCH: How Providers Work")
print("=" * 80)
print()
print("SCENARIO 1: Use All Defaults (Zero Code Changes)")
print("-" * 80)
print(SCENARIO_1_CODE)
print()
print("SCENARIO 2: Override Hook + Keep Defaults (super() Pattern)")
print("-" * 80)
print(SCENARIO_2_CODE)
print()
print("SCENARIO 3: Customize Helper Methods (Enterprise Systems)")
print("-" * 80)
print(SCENARIO_3_CODE)
print()
print("SCENARIO 4: Compose with Mixins (Layered Behaviors)")
print("-" * 80)
print(SCENARIO_4_CODE)
print()
print(COMPARISON)
print()
print(HOOK_CHAINS)
print()
print(TESTING_AFTER_PATCH)
