# Storage - Advanced Level

Global scoping and multi-account management patterns.

## Files
- **`scoped_resource_examples.py`** - Advanced storage handler patterns
  - StorageAccountHandler with global uniqueness enforcement
  - Global scope conflict detection
  - Multi-account provider patterns
  - Real-world storage scenarios

**Run:** `python scoped_resource_examples.py`

## Key Pattern: Global Uniqueness Enforcement

### First Creation Succeeds
```python
handler.create_resource(
    "mydata2025",
    {"account_type": "Standard_GRS"},
    "Microsoft.Storage/storageAccounts",
    {"subscription_id": "sub-1"}
)
# Result: Created successfully
```

### Duplicate in Different Subscription FAILS
```python
handler.create_resource(
    "mydata2025",  # Same name, different subscription
    {"account_type": "Standard_GRS"},
    "Microsoft.Storage/storageAccounts",
    {"subscription_id": "sub-2"}  # Different subscription!
)
# Result: ValueError - Resource already exists globally
```

## Why No Scope Context?

Global resources don't need scope context:

```python
# RG-scoped (VMs) - need scope context
vm_context = {
    "subscription_id": "...",
    "resource_group": "..."  # Needed for uniqueness check
}

# Global (Storage) - no context needed
sa_context = {}  # Global is global!
```

## Real-World Scenario: Data Lake Strategy

```python
# Production data lake - globally unique name
prod_lake = handler.create_resource(
    "prodlake2025",  # This name is now taken globally
    {"account_type": "Standard_GRS"}
)

# Development data lake - different name
dev_lake = handler.create_resource(
    "devlake2025",  # Different name required
    {"account_type": "Standard_LRS"}  # Can use cheaper option
)

# Cannot create "prodlake2025" again anywhere
# ValueError: Resource already exists globally
```

## Multi-Storage Patterns

### Pattern 1: Regional Storage Accounts
```python
for region in ["eu-west-1", "us-east-1"]:
    handler.create_resource(
        f"data-{region}",  # Different names per region
        {"region": region}
    )
```

### Pattern 2: Tiered Storage
```python
# Hot storage for active data
handler.create_resource(
    "activedata2025",
    {"access_tier": "Hot"}
)

# Cool storage for archived data
handler.create_resource(
    "archivedata2025",
    {"access_tier": "Cool"}
)
```

### Pattern 3: Backup Strategy
```python
# Primary account
handler.create_resource(
    "proddata2025",
    {"account_type": "Standard_GRS"}  # Geo-redundant
)

# Backup account (different storage, different name)
handler.create_resource(
    "backup2025",
    {"account_type": "Standard_LRS"}  # Local backup
)
```

## Concepts

### Global Scope Implications

| Aspect | Impact |
|--------|--------|
| **Naming** | Must be globally unique (DNS names) |
| **Deletion** | Deleting frees up the name globally |
| **Recovery** | Cannot recreate deleted account for 30 days |
| **Replication** | Often uses geo-replication across regions |
| **Context** | No scope context needed for uniqueness check |

## Prerequisites
- Complete [intermediate/](../intermediate/) level
- Understand global vs. RG scoping
- Understand DNS naming requirements

## Comparison: Storage vs. Compute

```python
# COMPUTE (RG-scoped)
vm = handler.create_resource(
    "webserver",
    {...},
    "Microsoft.Compute/virtualMachines",
    {
        "subscription_id": "sub",
        "resource_group": "app-rg"  # Scope needed
    }
)
# Can create "webserver" in different RG

# STORAGE (Global)
sa = handler.create_resource(
    "datastorage2025",
    {...},
    "Microsoft.Storage/storageAccounts",
    {}  # No scope context!
)
# Cannot create "datastorage2025" anywhere else
```

## Next Steps
→ **[Deployment](../../deployment/intermediate/)** - Deploy storage with Pulumi
