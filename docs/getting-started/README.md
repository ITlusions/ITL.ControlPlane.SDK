# Getting Started with ITL ControlPlane SDK

Welcome to the ITL ControlPlane SDK! This guide will get you up and running in minutes.

## What is the SDK?

The ITL ControlPlane SDK is a framework for managing cloud resources (VMs, resource groups, policies, etc.) through a unified Python interface. It handles:

- **Resource Management**: Create, read, update, delete resources
- **Multi-Tenancy**: Scope resources to tenants and subscriptions
- **Validation**: Automatic schema validation
- **State Tracking**: Provisioning states and timestamps
- **Database Persistence**: SQL + Graph database support

---

## Installation

### Quick Install (Core Only)

```bash
pip install itl-controlplane-sdk
```

### With Optional Features

```bash
# With FastAPI web integration
pip install itl-controlplane-sdk[fastapi]

# With all features
pip install itl-controlplane-sdk[all]

# For development
git clone https://github.com/ITlusions/ITL.ControlPlane.SDK.git
cd ITL.ControlPlane.SDK
pip install -e ".[all,dev]"
```

---

## 5-Minute Example: Create a Resource Group

### Step 1: Import & Setup

```python
from itl_controlplane_sdk import (
    ResourceGroupHandler,
    UniquenessScope,
)

# Create handler with storage
storage = {}  # In-memory storage (or use database)
handler = ResourceGroupHandler(storage)
```

### Step 2: Create a Resource Group

```python
# Define the resource
resource_id, config = handler.create_resource(
    name="prod-rg",                    # Resource name
    data={
        "location": "westeurope",      # Azure region
        "tags": {                       # Metadata tags
            "environment": "production",
            "team": "platform"
        }
    },
    resource_type="ITL.Core/resourcegroups",
    scope_context={
        "subscription_id": "sub-prod-001",
        "user_id": "admin@company.com"
    }
)

print(f"✓ Created: {resource_id}")
print(f"  Location: {config['location']}")
print(f"  Status: {config['provisioning_state']}")
```

### Step 3: Retrieve It

```python
# Get the resource
result = handler.get_resource(
    name="prod-rg",
    scope_context={"subscription_id": "sub-prod-001"}
)

if result:
    resource_id, resource_data = result
    print(f"Found: {resource_data['name']} ({resource_data['location']})")
```

### Step 4: Delete It

```python
# Delete the resource
deleted = handler.delete_resource(
    name="prod-rg",
    scope_context={"subscription_id": "sub-prod-001"}
)

print(f"✓ Deleted" if deleted else "✗ Not found")
```

---

## Key Concepts

### Resource IDs

Resources have hierarchical IDs following Azure conventions:

```
/subscriptions/{subscription_id}/resourceGroups/{name}
/subscriptions/{subscription_id}/resourceGroups/{rg}/locations/{location}
```

### Provisioning States

Resources have states that track their lifecycle:
- `Accepted` - Creation initiated
- `Provisioning` - Being created
- `Succeeded` - Ready to use
- `Failed` - Error occurred

### Scoping

Resources are scoped to **subscriptions** to enforce uniqueness:

```python
# Two subscriptions can have RGs with same name
sub1: prod-rg (allowed)
sub2: prod-rg (also allowed - different subscription)

# Same subscription cannot have duplicate names
sub1: prod-rg (exists)
sub1: prod-rg (ERROR - duplicate)
```

### Timestamps

Every resource automatically tracks:
- `createdTime` - When created
- `createdBy` - Who created it
- `modifiedTime` - When last updated
- `modifiedBy` - Who modified it

---

## Using with a Web API

### With FastAPI

```python
from fastapi import FastAPI
from itl_controlplane_sdk.fastapi import create_app

# Create app with SDK integration
app = create_app(title="My Control Plane")

# Use at localhost:8000
# Docs at localhost:8000/docs
```

### With Your Own Router

```python
from fastapi import FastAPI, HTTPException
from itl_controlplane_sdk import ResourceGroupHandler

app = FastAPI()
handler = ResourceGroupHandler({})

@app.post("/resourceGroups")
async def create_rg(name: str, location: str):
    try:
        resource_id, config = handler.create_resource(
            name=name,
            data={"location": location},
            resource_type="ITL.Core/resourcegroups",
            scope_context={"subscription_id": "default"}
        )
        return {
            "id": resource_id,
            "name": config["name"],
            "location": config["location"]
        }
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
```

---

## Database Persistence

### With PostgreSQL

The SDK includes Alembic migrations:

```bash
# Create PostgreSQL database
createdb controlplane

# Run migrations
alembic upgrade head

# Now your resources persist to database
```

Database tables:
- `resource_groups` - Resource group records
- `subscriptions` - Subscription records
- `management_groups` - Management groups
- `locations` - Available regions
- `tenants` - Multi-tenant support

### With Neo4j (Optional)

For graph queries and relationships:

```bash
# Neo4j handles relationships
# (ResourceGroup)-[:BELONGS_TO]->(Subscription)
# (Subscription)-[:IN_TENANT]->(Tenant)
```

---

## Common Tasks

### Validate a Location

```python
from itl_controlplane_sdk.providers import LocationsHandler

locations = LocationsHandler()
if locations.is_valid("westeurope"):
    print("✓ Valid location")
else:
    print("✗ Invalid location")
```

### List Available Locations

```python
from itl_controlplane_sdk.core import DEFAULT_LOCATIONS

for loc in DEFAULT_LOCATIONS:
    print(f"  {loc['name']:20} - {loc['display_name']}")
```

### Handle Errors

```python
try:
    resource_id, config = handler.create_resource(...)
except ValueError as e:
    print(f"Validation error: {e}")  # Duplicate, invalid location, etc.
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Add Tags to Resources

```python
rg_id, config = handler.create_resource(
    name="prod-rg",
    data={
        "location": "westeurope",
        "tags": {
            "environment": "production",
            "cost-center": "CC-001",
            "team": "platform",
            "owner": "admin@company.com"
        }
    },
    resource_type="ITL.Core/resourcegroups",
    scope_context={"subscription_id": "sub-001"}
)
```

---

## Next Steps

1. **Explore Examples**
   - See [`examples/`](../examples/) for complete examples
   - Read [`docs/`](../) for detailed architecture

2. **Build a Provider**
   - See [Provider Guide](../02-RESOURCE_ID_STRATEGY.md)
   - Implement your own resource types

3. **Set Up Web API**
   - Read [FastAPI Guide](../05-FASTAPI_MODULE.md)
   - Create REST endpoints

4. **Add Database**
   - Set up PostgreSQL + Neo4j
   - Run Alembic migrations

5. **Deploy**
   - Containerize with Docker
   - Deploy to Kubernetes

---

## Troubleshooting

### Port Already in Use

```bash
# Change port
uvicorn main:app --port 8001
```

### Database Connection Error

```bash
# Check PostgreSQL is running
psql -U controlplane -d controlplane -c "SELECT 1"

# Check Neo4j is running
curl http://localhost:7474
```

### Duplicate Resource Error

```python
# This raises ValueError (409 Conflict)
handler.create_resource("prod-rg", ...)
handler.create_resource("prod-rg", ...)  # ✗ ERROR

# Use different name or delete first
handler.delete_resource("prod-rg", ...)
handler.create_resource("prod-rg", ...)  # ✓ OK
```

### Validation Error

```python
# Invalid location raises ValueError
handler.create_resource(
    "my-rg",
    {"location": "invalid-region"},  # ✗ Not in DEFAULT_LOCATIONS
    ...
)

# Use valid location
handler.create_resource(
    "my-rg",
    {"location": "westeurope"},  # ✓ Valid
    ...
)
```

---

## Need Help?

- **API Reference**: `python -c "from itl_controlplane_sdk import *; help()"`
- **Examples**: [`examples/`](../examples/)
- **Docs**: [`docs/`](../)
- **GitHub**: https://github.com/ITlusions/ITL.ControlPlane.SDK
- **Issues**: https://github.com/ITlusions/ITL.ControlPlane.SDK/issues

---

## What's Next?

Now that you've completed the basics, explore:

- **[Scoped Resources](../01-SCOPED_RESOURCE_HANDLER.md)** - Advanced scoping patterns
- **[Big 3 Handler Mixins](../12-RESOURCE_GROUP_BIG_3_INTEGRATION.md)** - Validation, timestamps, state
- **[FastAPI Integration](../06-FASTAPI_INTEGRATION.md)** - Build web APIs
- **[Custom Providers](../17-BIG_3_IMPLEMENTATION.md)** - Implement your resource types

Happy coding! 
