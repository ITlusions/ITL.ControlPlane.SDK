"""
CRUD Operations Quick Reference Cheat Sheet

Quick lookup for implementing Create, Read, Update, Delete operations
in ITL ControlPlane resource providers.
"""

# ══════════════════════════════════════════════════════════════════════════════
# RESOURCE ID FORMAT (REQUIRED)
# ══════════════════════════════════════════════════════════════════════════════

"""
ALWAYS use ARM-compliant resource IDs in this format:

Resource Group Scoped (MOST COMMON):
  /subscriptions/{subscriptionId}/resourceGroups/{resourceGroup}/
  providers/ITL.{Domain}/{resourceType}/{resourceName}

Subscription Scoped:
  /subscriptions/{subscriptionId}/providers/ITL.{Domain}/{resourceType}/{resourceName}

Global/Tenant Scoped:
  /providers/ITL.{Domain}/{resourceType}/{resourceName}

EXAMPLES:
  ✓ /subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-prod
  ✓ /subscriptions/sub-prod-001/providers/ITL.StorageAccount/storageAccounts/appstg001
  ✓ /providers/ITL.IAM/realms/default-realm
"""


# ══════════════════════════════════════════════════════════════════════════════
# ROUTE PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

"""
HTTP Method  Verb                Path
──────────────────────────────────────────────────────────────────────────────
PUT          Create (idempotent) /subscriptions/{sub}/resourceGroups/{rg}/
                                  providers/ITL.{Domain}/{type}/{name}

GET          Read (single)       /subscriptions/{sub}/resourceGroups/{rg}/
                                  providers/ITL.{Domain}/{type}/{name}

GET          List (collection)   /subscriptions/{sub}/resourceGroups/{rg}/
                                  providers/ITL.{Domain}/{type}

PATCH        Update (partial)    /subscriptions/{sub}/resourceGroups/{rg}/
                                  providers/ITL.{Domain}/{type}/{name}

DELETE       Delete              /subscriptions/{sub}/resourceGroups/{rg}/
                                  providers/ITL.{Domain}/{type}/{name}
"""


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE SHAPE (STANDARD)
# ══════════════════════════════════════════════════════════════════════════════

"""
Every resource MUST respond with this standard shape:

{
  "id": "/subscriptions/.../providers/ITL.{Domain}/{type}/{name}",
  "name": "resource-name",
  "type": "ITL.{Domain}/{resourceType}",
  "location": "westeurope",
  "properties": {
    "provisioningState": "Succeeded",
    "customField1": "value1",
    "customField2": "value2"
    // domain-specific fields here
  },
  "tags": {
    "environment": "production",
    "team": "platform"
  },
  "resource_guid": "550e8400-e29b-41d4-a716-446655440000"  // optional
}

Fields:
  id ............................ ARM-compliant resource ID (REQUIRED)
  name .......................... Short name (REQUIRED)
  type .......................... ITL.{Domain}/{resourceType} (REQUIRED)
  location ...................... Azure region (REQUIRED), except subscriptions
  properties .................... Domain-specific fields (REQUIRED)
  properties.provisioningState .. Succeeded|Failed|Running|Accepted|Canceled
  tags .......................... Key-value metadata (optional)
  resource_guid ................ UUID (optional)
"""


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST SHAPES
# ══════════════════════════════════════════════════════════════════════════════

"""
CREATE/UPDATE REQUEST (PUT):
{
  "location": "westeurope",           // REQUIRED
  "tags": {...},                      // optional
  "properties": {
    "field1": "value1",               // domain-specific
    "field2": 123,
    ...
  }
}

PARTIAL UPDATE REQUEST (PATCH) — optional:
{
  "tags": {                           // optional
    "new-tag": "value"
  },
  "properties": {                     // optional
    "updatingField": "newValue"
  }
}

LIST RESPONSE:
{
  "value": [                          // array of resources
    { ... full resource ... },
    { ... full resource ... }
  ],
  "next_link": "https://..."          // optional, for pagination
}
"""


# ══════════════════════════════════════════════════════════════════════════════
# ERROR CODES & HTTP STATUS MAPPING
# ══════════════════════════════════════════════════════════════════════════════

"""
SDK Exception              HTTP Status  Meaning
──────────────────────────────────────────────────────────────────────────────
ResourceNotFoundError      404          Resource doesn't exist
ResourceAlreadyExistsError 409          Resource already exists
ValidationError            400          Invalid input
AuthorizationError         403          No permission
ConfigurationError         500          Server config issue
ServiceUnavailableError    503          Service temporarily down
UpstreamServiceError       502          Dependent service error
DependencyError            409          Can't delete, has dependencies

EXAMPLE ERROR RESPONSE:
{
  "error": {
    "code": "ResourceNotFound",
    "message": "Virtual network 'vnet-1' not found"
  }
}
"""


# ══════════════════════════════════════════════════════════════════════════════
# CODE TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

"""
MINIMAL CREATE/UPDATE ROUTE:

@app.put("/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.{Domain}/{type}/{resource_name}")
async def create_or_update(
    subscription_id: str,
    resource_group: str,
    resource_name: str,
    request: CreateRequest
):
    # Build resource ID
    resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.{Domain}/{type}/{resource_name}"
    
    # Create response object
    response = ResourceResponse(
        id=resource_id,
        name=resource_name,
        type="ITL.{Domain}/{type}",
        location=request.location,
        properties=request.properties,
        tags=request.tags or {},
        resource_guid=str(uuid.uuid4())
    )
    
    # Save to storage
    storage.create_or_update(response)
    
    return response


MINIMAL GET ROUTE:

@app.get("/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.{Domain}/{type}/{resource_name}")
async def get_resource(subscription_id: str, resource_group: str, resource_name: str):
    resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.{Domain}/{type}/{resource_name}"
    
    resource = storage.get(resource_id)
    if not resource:
        raise HTTPException(404, detail=f"Resource '{resource_name}' not found")
    
    return resource


MINIMAL LIST ROUTE:

@app.get("/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.{Domain}/{type}")
async def list_resources(subscription_id: str, resource_group: str):
    resources = storage.list(subscription_id, resource_group)
    return {"value": resources}


MINIMAL DELETE ROUTE:

@app.delete("/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.{Domain}/{type}/{resource_name}")
async def delete_resource(subscription_id: str, resource_group: str, resource_name: str):
    resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.{Domain}/{type}/{resource_name}"
    
    if not storage.exists(resource_id):
        raise HTTPException(404, detail=f"Resource '{resource_name}' not found")
    
    storage.delete(resource_id)
    return {"status": "deleted"}
"""


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODEL TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

"""
REQUEST MODEL:

from pydantic import BaseModel, Field
from typing import Optional, List

class ResourceProperties(BaseModel):
    field1: str
    field2: Optional[int] = None

class CreateResourceRequest(BaseModel):
    location: str = Field(..., description="Azure region")
    properties: ResourceProperties
    tags: Optional[dict] = Field(default_factory=dict)


RESPONSE MODEL:

class ResourceResponse(BaseModel):
    id: str = Field(..., description="ARM resource ID")
    name: str
    type: str = "ITL.{Domain}/{resourceType}"
    location: str
    properties: ResourceProperties
    tags: dict = Field(default_factory=dict)
    resource_guid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "/subscriptions/sub-1/resourceGroups/rg-1/providers/ITL.Domain/type/name",
                "name": "my-resource",
                ...
            }
        }
"""


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI DECORATOR TEMPLATE
# ══════════════════════════════════════════════════════════════════════════════

"""
@app.{METHOD}(
    "{path}",
    response_model=ResponseModel,        # Pydantic model for validation
    status_code=200,                     # or 201 for create
    summary="User-friendly title",
    description="Detailed description",
    tags=["Resource Type"]               # Swagger grouping
)
async def handler_name(
    path_param1: str,                    # From URL path
    path_param2: str,
    query_param: Optional[str] = None,   # From query string
    body: RequestModel = None            # From request body
):
    \"\"\"Docstring for Swagger docs.\"\"\"
    ...
"""


# ══════════════════════════════════════════════════════════════════════════════
# COMMON PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

"""
IDEMPOTENT CREATE (PUT):
  Use PUT, not POST. Same request = same result, safe to retry.
  Response: 200 if updating, 201 if creating (both OK)

LOCATION IS ALWAYS REQUIRED:
  All resources must have a location (Azure region).
  Only exception: subscriptions, tenants (global-scoped).

TAGS ARE OPTIONAL BUT RECOMMENDED:
  Use for cost tracking, environment marking, team organization.

RESOURCE GUIDs MUST BE UNIQUE:
  Generate with `str(uuid.uuid4())`, store if needed for auditing.

ALWAYS VALIDATE INPUT:
  Use Pydantic models, raise ValidationError for bad data.

ALWAYS RETURN FULL RESOURCE:
  After create/update, return complete resource object.

LIST RESPONSES USE PAGINATION:
  Return {"value": [...], "next_link": "url"} format.

ERRORS HAVE CONSISTENT SHAPE:
  {"error": {"code": "ErrorCode", "message": "..."}}
"""


# ══════════════════════════════════════════════════════════════════════════════
# CURL QUICK REFERENCE
# ══════════════════════════════════════════════════════════════════════════════

"""
CREATE:
  curl -X PUT https://api/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.{D}/{t}/{n} \
    -H "Content-Type: application/json" \
    -d '{"location":"west", "properties":{...}, "tags":{...}}'

READ:
  curl -X GET https://api/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.{D}/{t}/{n}

LIST:
  curl -X GET https://api/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.{D}/{t}

UPDATE:
  curl -X PUT https://api/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.{D}/{t}/{n} \
    -H "Content-Type: application/json" \
    -d '{"location":"west", "properties":{...}, "tags":{...}}'

DELETE:
  curl -X DELETE https://api/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.{D}/{t}/{n}
"""


# ══════════════════════════════════════════════════════════════════════════════
# PROVISIONING STATES
# ══════════════════════════════════════════════════════════════════════════════

"""
Use from SDK: from itl_controlplane_sdk.core.models.base import ProvisioningState

ProvisioningState.ACCEPTED   # Request received, processing will start
ProvisioningState.RUNNING    # Currently being processed
ProvisioningState.SUCCEEDED  # Completed successfully
ProvisioningState.FAILED     # Processing failed
ProvisioningState.CANCELED   # User cancelled

Typical flow: ACCEPTED → RUNNING → SUCCEEDED (or FAILED)
"""


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE BACKENDS (EXAMPLES)
# ══════════════════════════════════════════════════════════════════════════════

"""
SIMPLE (In-Memory) — Development/Testing:
  resources: dict[str, ResourceObject] = {}
  
PostgreSQL (Production) — Use SDK SQLAlchemyStorageEngine:
  from itl_controlplane_sdk.storage.engine import SQLAlchemyStorageEngine
  engine = SQLAlchemyStorageEngine(database_url="postgresql://...")
  
SQLite (Development):
  from itl_controlplane_sdk.storage.engine import SQLAlchemyStorageEngine
  engine = SQLAlchemyStorageEngine(database_url="sqlite:///provider.db")
"""


# ══════════════════════════════════════════════════════════════════════════════
# DO'S & DON'Ts
# ══════════════════════════════════════════════════════════════════════════════

"""
✅ DO:
  - Use PUT for create/update (idempotent)
  - Validate with Pydantic models
  - Return full resource objects
  - Use ARM-compliant resource IDs
  - Include location in all requests
  - Use SDK exceptions for errors
  - Set proper HTTP status codes (201 for create, 404 for not found)
  - Implement async/await properly
  - Test with httpx.AsyncClient or curl
  - Document with docstrings on routes

❌ DON'T:
  - Use POST for create (not idempotent)
  - Skip validation
  - Return partial objects
  - Use custom ID formats
  - Omit location
  - Use plain string errors
  - Return wrong status codes
  - Use sync code in async context
  - Hardcode URLs in client code
  - Leave routes without docstrings
"""


# ══════════════════════════════════════════════════════════════════════════════
# TESTING EXAMPLES
# ══════════════════════════════════════════════════════════════════════════════

"""
PYTEST + HTTPX:

import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_resource(client):
    response = await client.put(
        "/subscriptions/sub-1/resourceGroups/rg-1/providers/ITL.Domain/type/name",
        json={"location": "westeurope", "properties": {...}, "tags": {...}}
    )
    assert response.status_code == 201 or 200
    data = response.json()
    assert data["name"] == "name"
    assert data["type"] == "ITL.Domain/type"

@pytest.mark.asyncio
async def test_get_nonexistent_returns_404(client):
    response = await client.get(
        "/subscriptions/sub-1/resourceGroups/rg-1/providers/ITL.Domain/type/nope"
    )
    assert response.status_code == 404
"""


# ══════════════════════════════════════════════════════════════════════════════
# REFERENCES
# ══════════════════════════════════════════════════════════════════════════════

"""
📖 Full CRUD Examples:
   See CRUD_EXAMPLES.md in this directory

🏃 Minimal Working Example:
   See minimal_provider_example.py in this directory

📋 Full Implementation Template:
   See examples_crud_operations.py in this directory

🔗 Azure ARM Documentation:
   https://learn.ITL.com/en-us/azure/azure-resource-manager/

📚 FastAPI Docs:
   https://fastapi.tiangolo.com/

🔐 SDK Repository:
   d:\\repos\\ITL.ControlPanel.SDK
"""
