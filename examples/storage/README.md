# Storage Examples

Storage account and data management handlers.

## Files

### `big_3_examples.py` - StorageAccountHandler
Demonstrates the Big 3 handler patterns with global storage scoping:
- Validation: Storage account naming (3-24 chars, lowercase alphanumeric)
- Type validation: Standard_LRS, Standard_GRS, Standard_RAGRS, Premium_LRS
- Access tier: Hot or Cool
- **Global scoping**: Names must be globally unique (DNS names)
- Timestamps and provisioning state management

**Key example:**
```python
class StorageAccountHandler(ValidatedResourceHandler, ProvisioningStateHandler, 
                             TimestampedResourceHandler, ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]  # Globally unique!
    RESOURCE_TYPE = "storageaccounts"
    SCHEMA_CLASS = StorageAccountSchema
```

**Run:** `python big_3_examples.py`

### `scoped_resource_examples.py` - StorageAccountHandler
Demonstrates global uniqueness enforcement:
- Storage account names are globally unique (DNS resolution)
- Cannot reuse name even in different subscriptions
- Global scope patterns and error handling

**Run:** `python scoped_resource_examples.py`

## Concepts

### Storage Account Scoping
- **Scope**: GLOBAL
- **Uniqueness**: Must be unique across entire system (DNS names)
- **Cannot reuse**: Even in different subscriptions
- **Example**: `proddata2025` is taken globally, cannot be used anywhere

### Storage Account Handler Pattern
```python
handler = StorageAccountHandler(storage)
resource_id, config = handler.create_resource(
    "mydata2025",
    {
        "account_name": "mydata2025",
        "account_type": "Standard_GRS",
        "access_tier": "Cool"
    },
    "Microsoft.Storage/storageAccounts",
    {
        "subscription_id": "prod-sub",
        "resource_group": "storage-rg",
        "user_id": "admin@company.com"
    }
)
```

### Storage Account Types
- **Standard_LRS**: Locally redundant storage (single region)
- **Standard_GRS**: Geo-redundant storage (replication to paired region)
- **Standard_RAGRS**: Read-access geo-redundant storage
- **Premium_LRS**: Premium performance (SSD)

### Access Tiers
- **Hot**: Frequently accessed data (higher cost)
- **Cool**: Infrequently accessed data (lower cost)

## Use Cases

- Data lakes: `datalake2025`, `datalake-prod`
- Logging: `logs2025`, `audit-logs`
- Backups: `backup-storage-prod`
- Media: `media-assets-cdn`

## Important Notes

**Global Uniqueness**: Storage account names are globally unique DNS names. This is different from most Azure resources!

```python
# This will fail if "proddata2025" already exists anywhere
handler.create_resource(
    "proddata2025",  # Already taken globally!
    {...}
)
# ValueError: Resource already exists globally
```

**Global scope means**: No scope context needed
```python
# Unlike RG-scoped resources that need subscription_id + resource_group,
# storage accounts only have global context
handler.create_resource(
    "uniquename",
    {...},
    "Microsoft.Storage/storageAccounts",
    {}  # No scope context needed!
)
```
