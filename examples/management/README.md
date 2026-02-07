# Management Examples

Governance, policies, and resource management handlers.

## Files

### `big_3_examples.py` - DatabaseHandler
Demonstrates validation patterns for management resources:
- Database validation (name, edition, size)
- RG-scoped uniqueness
- Provisioning states and timestamps

**Run:** `python big_3_examples.py`

### `scoped_resource_examples.py` - PolicyHandler, ManagementGroupHandler
Demonstrates management resource patterns:
- **PolicyHandler**: Management Group scoped policies
  - Same policy name allowed in different management groups
  - Unique within a management group
  
- **ManagementGroupHandler**: Globally unique management groups
  - Management group hierarchies
  - Parent-child relationships
  - Global uniqueness enforcement

**Key examples:**
```python
class PolicyHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.MANAGEMENT_GROUP]
    RESOURCE_TYPE = "policies"

class ManagementGroupHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
    RESOURCE_TYPE = "managementgroups"
```

**Run:** `python scoped_resource_examples.py`

## Concepts

### Policy Scoping
- **Scope**: Management Group
- **Uniqueness**: Unique within management group
- **Reuse**: Can have same policy name in different MGs
- **Example**: `prod-mg/audit-policy` and `dev-mg/audit-policy` coexist

### Management Group Scoping
- **Scope**: GLOBAL
- **Uniqueness**: Globally unique
- **Hierarchical**: Can have parent/child relationships
- **Example**: Only one `prod-management-group` across entire tenant

### Policy Handler Pattern
```python
handler = PolicyHandler(storage)
policy_id, config = handler.create_from_definition(
    "audit-policy",
    {
        "type": "BuiltIn",
        "mode": "Indexed",
        "rules": [...],
        "parameters": {...}
    },
    "prod-management-group"
)
```

### Management Group Handler Pattern
```python
handler = ManagementGroupHandler(storage)
mg_id, config = handler.create_hierarchy(
    "prod-management-group",
    parent_id=None,  # Top level
    display_name="Production Management Group"
)

# Create child management group
child_mg_id, child_config = handler.create_hierarchy(
    "prod-subscriptions",
    parent_id=mg_id,  # Under prod-management-group
    display_name="Production Subscriptions"
)
```

## Use Cases

### Policies
- Compliance policies: `require-tagging`, `allowed-locations`
- Security policies: `require-encryption`, `enforce-https`
- Cost policies: `restrict-vm-sizes`, `auto-shutdown`
- Audit policies: `log-to-storage`, `enable-monitoring`

### Management Groups
- Organizational hierarchy: `root`, `company`, `division`, `team`
- Environment grouping: `production`, `staging`, `development`
- Cost centers: `engineering`, `operations`, `finance`
- Compliance domains: `pci-dss`, `hipaa`, `sox`

## Policy Types

**BuiltIn Policies**
- Microsoft-provided, predefined policies
- Examples: Allowed locations, required tags, encryption required

**Custom Policies**
- User-defined policies
- Custom compliance rules
- Business-specific requirements

## Management Group Hierarchy Example

```
root (default)
├── prod-management-group
│   ├── prod-subscriptions (policy: prod-policy)
│   └── prod-data (policy: data-policy)
├── dev-management-group
│   ├── dev-subscriptions (policy: dev-policy)
│   └── dev-sandbox (policy: sandbox-policy)
└── shared-management-group
    └── shared-resources (policy: shared-policy)
```

## Policy Assignment Pattern

While not directly in examples, policies are typically assigned to:
- Management groups (inherited by all children)
- Subscriptions
- Resource groups
- Individual resources

Assignment scoping follows the management group hierarchy.

## Database Handler

For SQL database management within resource groups:
```python
class DatabaseHandler(ValidatedResourceHandler, ProvisioningStateHandler,
                      TimestampedResourceHandler, ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "sqldatabases"
    SCHEMA_CLASS = DatabaseSchema
```

Database editions: Basic, Standard, Premium
Size: 1-1024 GB

## Related Resources

- See `compute/` for VM examples
- See `storage/` for storage examples
- See `network/` for networking examples
- See `tests/` for validation patterns
