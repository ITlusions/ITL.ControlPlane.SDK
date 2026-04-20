# Tenant-Realm ID Integration (Updated)

## Overview

The tenant model now integrates **realm_id as tenant_id** for complete 1:1 mapping.

```
Core Provider Tenant          Keycloak Realm
├─ id = /providers/.../      ├─ realm_id = "abc-def-123"
│  tenants/acme-corp         └─ realm_name = "acme-corp"
│
├─ tenant_id = "abc-def-123" ◄─── SAME (1:1 mapping)
│  (initially UUID, updated
│   when realm created)
│
└─ name = "acme-corp"
```

---

## Architecture

### 1. Tenant Creation Flow

```
Step 1: Create Tenant (Core Provider)
├─ POST /providers/ITL.Core/tenants
├─ id = "/providers/ITL.Management/tenants/acme-corp" (ARM ID)
├─ tenant_id = "uuid-1234-temporary" (temporary UUID)
└─ Publish cluster.tenant.created event

Step 2: Realm Creation (IAM Provider)
├─ Listen to cluster.tenant.created
├─ Create realm in Keycloak
├─ realm_id = "abc-def-123" (from Keycloak API)
└─ Publish cluster.realm.created with realm_id

Step 3: Update Tenant ID (Core Provider)
├─ Listen to cluster.realm.created
├─ Call TenantRepository.set_realm_id()
├─ Update tenant.tenant_id = "abc-def-123"
└─ Sync to Neo4j ✓

Result: tenant_id == realm_id ✓
```

---

## Implementation Changes

### SDK Layer

**File**: `src/itl_controlplane_sdk/persistence/repositories/repositories.py`

#### New Method: `set_realm_id()`

```python
async def set_realm_id(self, tenant_id_or_name: str, realm_id: str) -> Optional[TenantModel]:
    """Update tenant's tenant_id to the Keycloak realm_id.
    
    Called after realm is successfully created in Keycloak.
    Updates tenant_id field to match realm_id for 1:1 mapping.
    
    Args:
        tenant_id_or_name: Either the tenant's ARM ID or name
        realm_id: The Keycloak realm ID
        
    Returns:
        Updated TenantModel or None if tenant not found
    """
    # Find tenant by ARM ID or name
    tenant = await self.get_by_id(tenant_id_or_name) or await self.get_by_name(tenant_id_or_name)
    
    if not tenant:
        return None
    
    # Update tenant_id to realm_id
    tenant.tenant_id = realm_id
    
    # Mark sync timestamp
    tenant.properties["realm_synced_at"] = datetime.utcnow().isoformat()
    tenant.properties["realm_id"] = realm_id
    
    await repo.update(tenant)
    return tenant
```

### Core Provider Event Handler

**File**: `src/infrastructure/event_handlers.py`

#### Updated: `_handle_realm_created()`

```python
async def _handle_realm_created(self, event_data: Dict[str, Any]) -> None:
    """Handle cluster.realm.created event from IAM Provider.
    
    Updates the Core Provider tenant.tenant_id with the Keycloak realm_id
    for 1:1 tenant-realm mapping.
    """
    tenant_id = event_data.get("tenant_id")  # ARM ID
    realm_id = event_data.get("realm_id")    # Keycloak realm ID
    
    async with core_provider.engine.session() as session:
        repo = core_provider.engine.tenants(session)
        
        # Use new set_realm_id() method
        tenant = await repo.set_realm_id(tenant_id, realm_id)
        
        if tenant:
            # Now: tenant.tenant_id == realm_id ✓
            logger.info(f"Tenant {tenant_id} updated: tenant_id={realm_id}")
```

---

## Key Benefits

✅ **1:1 Mapping**: `tenant.tenant_id == realm.realm_id` always
✅ **Single Source of Truth**: No separate tracking needed
✅ **Direct Lookups**: Can find tenant by realm_id directly
✅ **No ID Translation**: No need for slug conversion or mapping tables
✅ **Neo4j Sync**: Automatically updated via `_sync_to_neo4j()`
✅ **Idempotent**: Multiple calls with same realm_id don't duplicate

---

## Usage Examples

### Lookup Tenant by Realm ID

```python
async with engine.session() as session:
    repo = engine.tenants(session)
    
    # Find by tenant_id (which is now the realm_id)
    tenant = await repo.get_by_tenant_id("abc-def-123")
    
    # Both return the same tenant
    assert tenant.tenant_id == "abc-def-123"
    assert tenant.name == "acme-corp"
```

### Update After Realm Creation

```python
# In event handler after realm is created
realm_id = "abc-def-123"  # From Keycloak

tenant = await repo.set_realm_id(
    tenant_id_or_name="/providers/ITL.Management/tenants/acme-corp",
    realm_id=realm_id
)

print(f"Updated: {tenant.tenant_id} == {realm_id}")
```

### Properties Reference

After update, tenant.properties contains:

```python
{
    "realm_id": "abc-def-123",           # For reference
    "realm_synced_at": "2026-02-14T...", # Timestamp of sync
    ...other_properties...
}
```

---

## Data Model

### Before Event Handler Processes

```
TenantModel:
  id: "/providers/ITL.Management/tenants/acme-corp"
  name: "acme-corp"
  tenant_id: "uuid-1234"  ◄─ Temporary
  properties: {
    "realm_id": null,
    "realm_status": "pending"
  }
```

### After Event Handler Processes

```
TenantModel:
  id: "/providers/ITL.Management/tenants/acme-corp"  (unchanged)
  name: "acme-corp"  (unchanged)
  tenant_id: "abc-def-123"  ◄─ Updated to Keycloak realm_id
  properties: {
    "realm_id": "abc-def-123",
    "realm_synced_at": "2026-02-14T10:30:05Z",
    "realm_status": "created"
  }
```

---

## Neo4j Sync

The `set_realm_id()` method automatically syncs to Neo4j:

```python
await self._sync_to_neo4j(tenant)
```

This ensures:
- ✓ Neo4j node updated with new tenant_id
- ✓ Relationships updated if needed
- ✓ Graph consistency maintained

---

## Database Constraints

The TenantModel maintains a **unique constraint** on `tenant_id`:

```sql
-- Enforced by SQLAlchemy model
UNIQUE(tenant_id)
```

This means:
- Once set to a realm_id, it cannot be changed
- Each realm maps to exactly one tenant
- No duplicate realm mappings

---

## Testing

### Unit Test Example

```python
@pytest.mark.asyncio
async def test_set_realm_id():
    """Test updating tenant_id to realm_id."""
    
    # Create tenant with temporary UUID
    tenant = await repo.create_or_update(
        name="test-tenant",
        display_name="Test Tenant",
    )
    
    original_uuid = tenant.tenant_id
    print(f"Initial tenant_id: {original_uuid}")
    
    # Update to realm_id
    realm_id = "keycloak-realm-xyz"
    updated = await repo.set_realm_id(
        tenant_id_or_name=tenant.id,  # Use ARM ID
        realm_id=realm_id
    )
    
    # Verify
    assert updated.tenant_id == realm_id
    assert updated.tenant_id != original_uuid
    assert updated.properties["realm_id"] == realm_id
    assert "realm_synced_at" in updated.properties
```

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_tenant_realm_id_integration():
    """Test full tenant creation with realm_id update."""
    
    # 1. Create tenant
    tenant = await core_provider._create_tenant(
        "acme", 
        {"display_name": "ACME Corp"}
    )
    temp_id = tenant.tenant_id
    
    # 2. Simulate realm creation event
    event = {
        "event_type": "cluster.realm.created",
        "tenant_id": tenant.id,  # ARM ID
        "realm_id": "realm-abc123",
    }
    
    # 3. Handle event
    await core_handler._handle_realm_created(event)
    
    # 4. Verify tenant updated
    updated_tenant = await repo.get_by_id(tenant.id)
    assert updated_tenant.tenant_id == "realm-abc123"
    assert updated_tenant.tenant_id != temp_id
```

---

## Migration Path (if needed)

If existing tenants have old UUIDs as `tenant_id`, they can be migrated:

```python
async def migrate_tenant_realm_ids():
    """One-time migration to set realm_ids from properties."""
    
    async with engine.session() as session:
        repo = engine.tenants(session)
        
        for tenant in await repo.list_all():
            realm_id = tenant.properties.get("realm_id")
            
            if realm_id and tenant.tenant_id != realm_id:
                await repo.set_realm_id(tenant.id, realm_id)
                print(f"Migrated {tenant.name}: {tenant.tenant_id} → {realm_id}")
```

---

## Summary

✅ **tenant_id is realm_id**: 1:1 mapping maintained
✅ **SDK method**: `set_realm_id()` handles the update
✅ **Event-driven**: Updated via cluster.realm.created event
✅ **Neo4j synced**: Automatic graph database update
✅ **Idempotent**: Multiple updates safe
✅ **Type-safe**: Proper validation and logging
