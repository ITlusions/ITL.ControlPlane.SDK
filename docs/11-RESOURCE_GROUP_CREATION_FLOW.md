# What Happens When a User Creates a Resource Group

## Complete End-to-End Flow

When a user creates a resource group using the SDK, here's exactly what happens:

---

## 1️⃣ User Initiates Create Request

```python
handler = ResourceGroupHandler(storage_dict)

resource_id, rg_config = handler.create_resource(
    name="prod-rg",
    config={
        "location": "eastus",
        "tags": {"environment": "production"}
    },
    resource_type="Microsoft.Resources/resourceGroups",
    scope_context={"subscription_id": "sub-prod-001", "user_id": "admin@company.com"}
)
```

**Input Parameters:**
- `name`: "prod-rg" - Resource group name
- `config`: location + tags properties
- `resource_type`: Standard Azure type identifier
- `scope_context`: Who is creating it & where (subscription + user)

---

## 2️⃣ Schema Validation (ValidatedResourceHandler)

**What happens:** The `ResourceGroupSchema` validator runs

```
Input: location="eastus", tags={"environment": "production"}
                ↓
        [LocationsHandler.validate_location()]
                ↓
Check: Is "eastus" in the enum of 30+ valid Azure regions?
  ✓ YES → return "eastus"
  ✗ NO  → raise ValueError("'invalid-region' is not a valid Azure location...")
                ↓
Check: Are tags a dictionary with string keys/values?
  ✓ YES → return tags
  ✗ NO  → raise ValueError("Tags must be...")
                ↓
Result: All validation passed ✓
```

**If validation fails:**
- Raises `ValueError` immediately
- User sees detailed error message
- Resource is NOT created
- Process stops here

**Example error message if location is invalid:**
```
ValueError: Value error, 'invalid-region' is not a valid Azure location. 
Valid options: australiaeast, australiasoutheast, brazilsouth, canadacentral, 
canadaeast, centralus, chinaeast, chinanorth, eastasia, eastus, eastus2, 
germanywestcentral, indiacentral, indiasouth, indiawest, japaneast, japanwest, 
northcentralus, northeurope, southafricanorth, southcentralus, southeastasia, 
uaenorth, uksouth, ukwest, usgovarizona, usgoviowa, usgovtexas, usgovvirginia, 
westeurope, westus, westus2
```

---

## 3️⃣ Uniqueness Check (ScopedResourceHandler)

**What happens:** Check if a resource group with this name already exists IN THIS SUBSCRIPTION

```
Input: name="prod-rg", subscription_id="sub-prod-001"
              ↓
Look up storage: Does "sub-prod-001_prod-rg" already exist?
              ↓
  ✓ NOT FOUND → Continue to next step
  ✗ FOUND     → raise ValueError("RG 'prod-rg' already exists in subscription")
```

**Key Detail:** Two subscriptions CAN have resource groups with same name, but within ONE subscription, names are unique.

```
Example:
✓ sub-prod-001 has "prod-rg"
✓ sub-dev-001  has "prod-rg"  ← ALLOWED (different subscription)
✗ sub-prod-001 has "prod-rg"  
✗ sub-prod-001 has "prod-rg"  ← DENIED (same subscription)
```

---

## 4️⃣ Generate Resource ID (ResourceGroupHandler Override)

**What happens:** Create the Azure-standard resource ID

```
Input: name="prod-rg", subscription_id="sub-prod-001"
              ↓
Result: /subscriptions/sub-prod-001/resourceGroups/prod-rg

Format: /subscriptions/{subscription}/resourceGroups/{name}
```

This becomes the unique identifier for this resource group.

---

## 5️⃣ Add Automatic Timestamps (TimestampedResourceHandler)

**What happens:** The system automatically records WHEN and WHO created this

```
User creates at: 2026-02-01 14:30:45.123456Z
Created by: admin@company.com

System automatically adds to config:
{
    "createdTime": "2026-02-01T14:30:45.123456Z",  ← ISO 8601 format
    "createdBy": "admin@company.com",
    "modifiedTime": "2026-02-01T14:30:45.123456Z", ← Initially same as createdTime
    "modifiedBy": "admin@company.com"
}
```

**Why This Matters:**
- Audit trail: Know who created what and when
- Immutable creation record: `createdTime` and `createdBy` never change
- Modifiable updates: `modifiedTime` and `modifiedBy` update when resource changes

---

## 6️⃣ Initialize Provisioning State (ProvisioningStateHandler)

**What happens:** Resource moves through state machine

```
State Progression:
"Accepted"      → "Provisioning"  →  "Succeeded"
(initial state)    (in progress)      (complete)

For RG creation, it's typically:
Accepted → Succeeded (fast operation)

For long-running operations:
Accepted → Provisioning → Succeeded (or Failed)
```

**In this case:**
```
config["provisioning_state"] = "Succeeded"
```

Since creating a resource group is synchronous/fast, it goes straight to "Succeeded".

---

## 7️⃣ Store in Dictionary (ScopedResourceHandler)

**What happens:** Everything is stored in the in-memory storage dictionary

```
Storage structure:
{
    "sub-prod-001_prod-rg": {
        "id": "/subscriptions/sub-prod-001/resourceGroups/prod-rg",
        "name": "prod-rg",
        "location": "eastus",
        "tags": {"environment": "production"},
        "provisioning_state": "Succeeded",
        "createdTime": "2026-02-01T14:30:45.123456Z",
        "createdBy": "admin@company.com",
        "modifiedTime": "2026-02-01T14:30:45.123456Z",
        "modifiedBy": "admin@company.com"
    }
}
```

Key: `"{subscription_id}_{resource_name}"` for subscription-scoped lookup

---

## 8️⃣ Return Response to User

**What happens:** User gets back the complete resource details

```python
Return Tuple:
(
    resource_id,  # String
    rg_config     # Dict
)

Example:
resource_id = "/subscriptions/sub-prod-001/resourceGroups/prod-rg"

rg_config = {
    "location": "eastus",
    "tags": {"environment": "production"},
    "provisioning_state": "Succeeded",
    "createdTime": "2026-02-01T14:30:45.123456Z",
    "createdBy": "admin@company.com",
    "modifiedTime": "2026-02-01T14:30:45.123456Z",
    "modifiedBy": "admin@company.com"
}
```

**User can now use:**
```python
print(f"Created: {resource_id}")
print(f"Location: {rg_config['location']}")
print(f"Created by: {rg_config['createdBy']}")
print(f"Created at: {rg_config['createdTime']}")
print(f"Status: {rg_config['provisioning_state']}")
```

---

## Complete Validation Flow Diagram

```
┌─────────────────────────────────────┐
│ User calls create_resource()        │
│ name: "prod-rg"                     │
│ location: "eastus"                  │
│ subscription_id: "sub-prod-001"    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ ValidatedResourceHandler             │
│ Schema Validation                    │
├─────────────────────────────────────┤
│ ✓ Location in 30+ regions?          │
│ ✓ Tags dict with strings?           │
│ ✓ Valid Azure format?               │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ ScopedResourceHandler               │
│ Uniqueness Check                    │
├─────────────────────────────────────┤
│ ✓ Not already in subscription?      │
│ ✓ Can exist in other subscriptions? │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ ResourceGroupHandler                │
│ Generate Azure Resource ID          │
├─────────────────────────────────────┤
│ /subscriptions/{sub}/resourceGroups/name
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ TimestampedResourceHandler           │
│ Auto-Add Timestamps                 │
├─────────────────────────────────────┤
│ createdTime: ISO 8601               │
│ createdBy: from scope_context       │
│ modifiedTime: initial               │
│ modifiedBy: initial                 │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ ProvisioningStateHandler            │
│ Set Initial State                   │
├─────────────────────────────────────┤
│ provisioning_state: "Succeeded"     │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Store in Dictionary                 │
├─────────────────────────────────────┤
│ Key: "sub-prod-001_prod-rg"        │
│ Value: Complete rg_config           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Return (resource_id, rg_config)     │
│ to User                             │
└─────────────────────────────────────┘
```

---

## What Gets Returned to User

```python
resource_id = "/subscriptions/sub-prod-001/resourceGroups/prod-rg"

rg_config = {
    'location': 'eastus',
    'tags': {'environment': 'production'},
    'provisioning_state': 'Succeeded',
    'createdTime': '2026-02-01T14:30:45.123456Z',
    'createdBy': 'admin@company.com',
    'modifiedTime': '2026-02-01T14:30:45.123456Z',
    'modifiedBy': 'admin@company.com'
}
```

---

## Error Scenarios (What Can Go Wrong)

### ❌ Scenario 1: Invalid Location

```python
handler.create_resource(
    "bad-rg",
    {"location": "invalid-region"},
    ...
)

ERROR: ValueError: 'invalid-region' is not a valid Azure location. 
Valid options: australiaeast, australiasoutheast, ... (30+ options)

IMPACT: Resource NOT created. User must specify valid location.
WHEN: Immediately at validation step #2
```

### ❌ Scenario 2: Invalid Tags

```python
handler.create_resource(
    "bad-rg",
    {"tags": [1, 2, 3]},  # Not a dict!
    ...
)

ERROR: ValueError: Tags must be a dictionary

IMPACT: Resource NOT created.
WHEN: Validation step #2
```

### ❌ Scenario 3: Duplicate in Same Subscription

```python
# First call - SUCCEEDS
handler.create_resource("prod-rg", {...}, {"subscription_id": "sub-001"})

# Second call - FAILS
handler.create_resource("prod-rg", {...}, {"subscription_id": "sub-001"})

ERROR: ValueError: Resource 'prod-rg' already exists in subscription 'sub-001'

IMPACT: Resource NOT created. Must use different name or different subscription.
WHEN: Uniqueness check step #3
```

### ✅ Scenario 4: Same Name, Different Subscription (ALLOWED)

```python
# First call in sub-001 - SUCCEEDS
handler.create_resource("prod-rg", {...}, {"subscription_id": "sub-001"})
# Result: /subscriptions/sub-001/resourceGroups/prod-rg

# Second call in sub-002 - SUCCEEDS ✓
handler.create_resource("prod-rg", {...}, {"subscription_id": "sub-002"})
# Result: /subscriptions/sub-002/resourceGroups/prod-rg

ALLOWED: Different subscriptions have separate namespaces
WHEN: Uniqueness check step #3 (allows it)
```

---

## Real Test Example Output

From the actual test run (5/5 tests passing):

```
======================================================================
TEST 1: Resource Group Creation with Validation
======================================================================

[->] Creating resource group 'prod-rg'...
[OK] Created: /subscriptions/sub-prod-001/resourceGroups/prod-rg
    State: Succeeded
    Location: eastus
    Created by: admin@company.com
    Created at: 2026-02-01T03:27:42.010814Z
    Tags: {'env': 'production', 'team': 'platform'}
[OK] All Big 3 features present!

[->] Attempting to create RG with invalid location...
[OK] Validation caught: 'invalid-region' is not a valid Azure location

[->] Attempting to create duplicate RG in same subscription...
[OK] Correctly blocked duplicate

======================================================================
TEST SUMMARY
======================================================================
PASS: Creation & Validation
PASS: Timestamps on Creation
PASS: State Management
PASS: Subscription Scoping
PASS: Convenience Methods

Total: 5/5 tests passed

[SUCCESS] ResourceGroupHandler with Big 3 is fully functional!
```

---

## Summary: The Big 3 in Action

When you create a resource group, you automatically get:

| Feature | What It Does | Example |
|---------|-------------|---------|
| **TimestampedResourceHandler** | Records WHEN and WHO created it | `createdTime: "2026-02-01T14:30:45Z"` |
| **ProvisioningStateHandler** | Tracks progress through state machine | `provisioning_state: "Succeeded"` |
| **ValidatedResourceHandler** | Ensures only valid data is stored | `location: "eastus"` (validated against 30+ regions) |

**All three work together** to create a robust, auditable, validated resource that follows Azure standards.

---

## What Happens After Creation

Once created, users can:

```python
# Get specific resource group
result = handler.get_resource("prod-rg", {"subscription_id": "sub-prod-001"})

# List all RGs in subscription
resources = handler.list_resources({"subscription_id": "sub-prod-001"})

# Delete resource group
deleted = handler.delete_resource("prod-rg", {"subscription_id": "sub-prod-001"})
```

Each of these operations also goes through the same validation and timestamp logic!
