# Management - Advanced Level

Management group hierarchies and complex governance patterns.

## Files
- **`scoped_resource_examples.py`** - Advanced management handler patterns
  - Management group hierarchies
  - Policy inheritance patterns
  - Cross-RG governance
  - Real-world compliance scenarios

**Run:** `python scoped_resource_examples.py`

## Key Pattern: Management Group Hierarchy

Management Groups organize subscriptions into hierarchies:

```
Tenant Root Group
├── Production
│   ├── prod-subscription
│   └── staging-subscription
├── Development
│   └── dev-subscription
└── Security
    └── compliance-subscription
```

### Creating Hierarchy

```python
# Root management group
root = handler.create_resource(
    "root-mg",
    {"name": "Organization Root"},
    "Microsoft.Management/managementGroups",
    {}  # MGs don't have RG/subscription scope
)

# Production folder
prod_mg = handler.create_resource(
    "prod-mg",
    {
        "name": "Production",
        "parent_id": root.id
    },
    "Microsoft.Management/managementGroups",
    {}
)

# Dev folder
dev_mg = handler.create_resource(
    "dev-mg",
    {
        "name": "Development",
        "parent_id": root.id
    },
    "Microsoft.Management/managementGroups",
    {}
)

# Assign subscriptions
prod_sub = handler.assign_subscription(
    prod_mg.id,
    "subscription-prod-id"
)

dev_sub = handler.assign_subscription(
    dev_mg.id,
    "subscription-dev-id"
)
```

## Policy Inheritance

Policies inherit down the hierarchy:

```python
# Policy at Production level affects all prod subscriptions
prod_policy = handler.create_resource(
    "prod-encryption-policy",
    {
        "effect": "Deny",
        "condition": '{"field": "Microsoft.Compute/disks/encryption", "equals": "None"}'
    },
    "Microsoft.Authorization/policyAssignments",
    {"management_group": "prod-mg"}  # Inherited by all prod subs!
)

# More restrictive policy at root affects everything
root_policy = handler.create_resource(
    "org-data-residency",
    {
        "effect": "Deny",
        "condition": '{"field": "location", "notIn": ["westeurope", "northeurope"]}'
    },
    "Microsoft.Authorization/policyAssignments",
    {"management_group": "root-mg"}  # Inherited everywhere!
)
```

## Real-World Scenario: Multi-Tenant Organization

```python
class GovernanceProvider:
    async def setup_organization(self):
        # Create MG hierarchy
        tenant = await self.mg_handler.create_resource(
            "org-root", {"name": "ACME Corp"}
        )
        
        # Business units
        engineering = await self.mg_handler.create_resource(
            "eng-mg",
            {"name": "Engineering", "parent_id": tenant.id}
        )
        
        finance = await self.mg_handler.create_resource(
            "fin-mg",
            {"name": "Finance", "parent_id": tenant.id}
        )
        
        # Policies for engineering (cheaper SKUs)
        eng_policy = await self.policy_handler.create_resource(
            "eng-cost-control",
            {
                "effect": "Deny",
                "condition": '{"field": "Microsoft.Compute/virtualMachines/sku", "notIn": ["Standard_B2s", "Standard_B4ms"]}'
            },
            {...},
            {"management_group": "eng-mg"}
        )
        
        # Policies for finance (premium SKUs + encryption)
        fin_policy = await self.policy_handler.create_resource(
            "fin-security",
            {
                "effect": "Deny",
                "condition": '{"field": "Microsoft.Storage/storageAccounts/encryption", "equals": "None"}'
            },
            {...},
            {"management_group": "fin-mg"}
        )
        
        # Data residency at root (applies to all)
        residency = await self.policy_handler.create_resource(
            "eu-only",
            {
                "effect": "Deny",
                "condition": '{"field": "location", "notIn": ["westeurope", "northeurope", "germanywest"]}'
            },
            {...},
            {"management_group": tenant.id}  # Inherited by all
        )
        
        return {
            "tenant_mg": tenant,
            "business_units": [engineering, finance],
            "policies": [eng_policy, fin_policy, residency]
        }
```

## Multi-Level Governance

```python
# Level 1: Organization-wide (Root MG)
# - Data residency (EU/US only)
# - Encryption mandatory
# - Audit logging required

# Level 2: Department (Prod/Dev/Test MGs)
# - Prod: Premium SKUs, HA, backups
# - Dev: Basic SKUs, optional backups
# - Test: Temporary resources only

# Level 3: Team (Subscriptions)
# - Team A: Allows compute + storage
# - Team B: Allows databases only
# - Team C: Cost limits by resource type
```

## Database Governance

```python
# Production databases must be:
prod_db_policy = {
    "must_enable_encryption": True,
    "minimum_backup_retention": 35,
    "minimum_edition": "Premium",
    "require_availability_group": True,
    "require_point_in_time_restore": True
}

# Development databases can be:
dev_db_policy = {
    "must_enable_encryption": False,  # Optional
    "minimum_backup_retention": 7,
    "minimum_edition": "Basic",
    "require_availability_group": False,
    "require_point_in_time_restore": False
}
```

## Concepts

### Management Groups vs. Subscriptions
| Aspect | MG | Subscription | RG |
|--------|-----|-------------|-----|
| **Scope** | Tenant-wide | Account | Subscription |
| **Purpose** | Organize subs | Billing | Group resources |
| **Hierarchy** | Tree | Flat | Flat within sub |
| **Policy Scope** | Inherited down | Applied directly | Applied directly |
| **Cost** | No cost | Costs money | No cost |

### Policy Evaluation Order
1. Root MG policies evaluated first
2. Intermediate MG policies
3. Subscription-level policies
4. RG-level policies (most specific)

## Prerequisites
- Complete [intermediate/](../intermediate/) level
- Understand policy effects (Allow, Deny, Audit)
- Understand hierarchical inheritance

## Next Steps
→ **[Deployment](../../deployment/advanced/)** - Deploy governance with Pulumi
