# Storage - Intermediate Level

Storage Account handler with the "Big 3" patterns and **GLOBAL SCOPING**.

## Files
- **`big_3_examples.py`** - StorageAccountHandler implementation
  - Pydantic validation for account names (3-24 chars, lowercase)
  - Account type validation (Standard_LRS, Standard_GRS, etc.)
  - Access tier (Hot or Cool)
  - **GLOBAL uniqueness** - names must be unique across entire system
  - Provisioning state management
  - Automatic timestamps

**Run:** `python big_3_examples.py`

## Key Difference: GLOBAL Scope

Unlike VMs (RG-scoped), storage accounts are **globally unique**:

```python
class StorageAccountHandler(...):
    # Globally unique - not just within RG!
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
```

## Why Global?
Storage account names become **DNS names** (e.g., `myaccount.blob.core.windows.net`). DNS names must be globally unique!

### Storage Account Naming Rules
- 3-24 characters
- Lowercase alphanumeric only
- No hyphens allowed
- Examples: `mydata2025`, `prodlogs`, `backupstore`

## Storage Types
- **Standard_LRS** - Locally redundant (single region)
- **Standard_GRS** - Geo-redundant (paired region replication)
- **Standard_RAGRS** - Read-access geo-redundant
- **Premium_LRS** - Premium performance (SSD)

## Use Cases
- Data lakes: `datalake2025`
- Logging: `prodlogs2025`
- Backups: `backupstore`
- Media: `mediarepo`

## Key Learning: Global vs. RG Scoping

| Resource | Scope | Can Reuse Name? |
|----------|-------|---|
| VM | RG-scoped | Yes, in different RG |
| Storage Account | Global | No, never |

## Prerequisites
- Understand SDK basics (see [core/beginner/](../../core/beginner/))
- Understand RG scoping (see [compute/intermediate/](../../compute/intermediate/))

## Next Steps
→ **[Advanced](../advanced/)** - Learn global scoping enforcement
