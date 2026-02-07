# Management - Intermediate Level

Policy and Management handler with the "Big 3" patterns: Validation, Provisioning States, and Timestamps.

## Files
- **`big_3_examples.py`** - PolicyHandler and DatabaseHandler implementation
  - Policy name validation and assignment
  - Lifecycle state management (Draft → Assigned → Enforced)
  - Compliance tracking
  - Database resource management
  - Storage configuration validation
  - Automatic audit timestamps
  - RG-scoped uniqueness

**Run:** `python big_3_examples.py`

## Key Patterns

### Policy Handler
Policies enforce compliance across resources:

```python
class PolicyHandler(...):
    # Policies are RG-scoped
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]

class PolicySchema(BaseModel):
    policy_name: str
    effect: str  # Allow, Deny, Audit
    condition: str  # JSON condition
    assigned_to: List[str]  # Resource types
```

### Database Handler
Database resources with configuration management:

```python
class DatabaseHandler(...):
    # Databases are RG-scoped
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]

class DatabaseSchema(BaseModel):
    db_name: str
    db_type: str  # SQL, PostgreSQL, MySQL
    edition: str  # Basic, Standard, Premium
    backup_retention: int  # Days
```

## Policy Examples

```python
# Allow only Premium storage
allow_premium = handler.create_resource(
    "require-premium-storage",
    {
        "policy_name": "require-premium-storage",
        "effect": "Deny",
        "condition": '{"field": "Microsoft.Storage/storageAccounts/sku/name", "like": "Standard*"}',
        "assigned_to": ["Microsoft.Storage/storageAccounts"]
    },
    "Microsoft.Authorization/policies",
    {"subscription_id": "sub", "resource_group": "policies-rg"}
)

# Audit unencrypted databases
audit_encryption = handler.create_resource(
    "audit-db-encryption",
    {
        "policy_name": "audit-db-encryption",
        "effect": "Audit",
        "condition": '{"field": "Microsoft.Sql/servers/databases/transparentDataEncryption", "equals": "Disabled"}',
        "assigned_to": ["Microsoft.Sql/servers/databases"]
    },
    "Microsoft.Authorization/policies",
    {"subscription_id": "sub", "resource_group": "policies-rg"}
)
```

## Database Examples

```python
# Production database
prod_db = handler.create_resource(
    "appdb-prod",
    {
        "db_name": "appdb-prod",
        "db_type": "SQL",
        "edition": "Premium",
        "backup_retention": 35  # 35 days
    },
    "Microsoft.Sql/servers/databases",
    {"subscription_id": "prod", "resource_group": "data-rg"}
)

# Development database
dev_db = handler.create_resource(
    "appdb-dev",
    {
        "db_name": "appdb-dev",
        "db_type": "SQL",
        "edition": "Basic",
        "backup_retention": 7  # 7 days
    },
    "Microsoft.Sql/servers/databases",
    {"subscription_id": "dev", "resource_group": "data-rg"}
)
```

## Lifecycle States

```
Draft  → Assigned  → Enforced
  ↓         ↓           ↓
Creating  Assigning   Active
```

Each state has:
- Timestamp when entered
- Who made the change (audit)
- Current configuration

## Prerequisites
- Understand SDK basics (see [core/beginner/](../../core/beginner/))
- Understand RG scoping (see [compute/intermediate/](../../compute/intermediate/))

## Next Steps
→ **[Advanced](../advanced/)** - Learn management group hierarchies
