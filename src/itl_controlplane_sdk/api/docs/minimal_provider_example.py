"""
Minimal Resource Provider Example with CRUD Operations

This shows the simplest possible provider implementation that handles
Create, Read, Update, Delete operations properly.

Run with: python -m uvicorn minimal_provider:app --reload
Visit: http://localhost:8000/docs for interactive API docs
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from contextlib import asynccontextmanager


# ══════════════════════════════════════════════════════════════════════════════
# 1. DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

class ResourceProperties(BaseModel):
    """Resource-specific properties."""
    provisioning_state: str = "Succeeded"
    description: Optional[str] = None


class CreateResourceRequest(BaseModel):
    """Request to create a resource."""
    location: str = Field(..., description="Azure region")
    properties: Optional[ResourceProperties] = None
    tags: Optional[dict] = Field(default_factory=dict)


class Resource(BaseModel):
    """Resource response object."""
    id: str
    name: str
    type: str
    location: str
    properties: ResourceProperties
    tags: dict
    resource_guid: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "/subscriptions/sub-1/resourceGroups/rg-1/providers/ITL.Demo/resources/my-resource",
                "name": "my-resource",
                "type": "ITL.Demo/resources",
                "location": "westeurope",
                "properties": {
                    "provisioning_state": "Succeeded",
                    "description": "My test resource"
                },
                "tags": {"environment": "dev"},
                "resource_guid": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class PaginatedResourceList(BaseModel):
    """List response."""
    value: List[Resource]
    next_link: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# 2. SIMPLE IN-MEMORY STORAGE
# ══════════════════════════════════════════════════════════════════════════════

class Storage:
    """Super simple in-memory storage."""
    def __init__(self):
        self.resources: dict[str, Resource] = {}


storage = Storage()


# ══════════════════════════════════════════════════════════════════════════════
# 3. HELPER FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def build_resource_id(sub_id: str, rg: str, resource_name: str) -> str:
    """Build ARM-compliant resource ID."""
    return f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/ITL.Demo/resources/{resource_name}"


# ══════════════════════════════════════════════════════════════════════════════
# 4. STARTUP/SHUTDOWN
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown."""
    # STARTUP
    print("🚀 Provider starting...")
    print("📝 Docs: http://localhost:8000/docs")
    
    yield
    
    # SHUTDOWN
    print("🛑 Provider shutting down...")
    storage.resources.clear()


# ══════════════════════════════════════════════════════════════════════════════
# 5. CREATE APP WITH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ITL Demo Resource Provider",
    version="1.0.0",
    lifespan=lifespan
)


# ──────────────────────────────────────────────────────────────────────────────
# CREATE — PUT /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Demo/resources/{name}
# ──────────────────────────────────────────────────────────────────────────────

@app.put(
    "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.Demo/resources/{resource_name}",
    response_model=Resource,
    tags=["Resources"]
)
async def create_or_update_resource(
    subscription_id: str,
    resource_group: str,
    resource_name: str,
    request: CreateResourceRequest
):
    """Create or update a resource (idempotent).
    
    **Parameters:**
    - `subscription_id`: Subscription ID
    - `resource_group`: Resource group name
    - `resource_name`: Resource name
    
    **Body:**
    - `location`: Required. Azure region (e.g., 'westeurope')
    - `properties`: Resource properties (optional)
    - `tags`: Resource tags (optional)
    
    **Returns:** Fully created/updated resource
    """
    resource_id = build_resource_id(subscription_id, resource_group, resource_name)
    
    response = Resource(
        id=resource_id,
        name=resource_name,
        type="ITL.Demo/resources",
        location=request.location,
        properties=request.properties or ResourceProperties(),
        tags=request.tags or {},
        resource_guid=str(uuid.uuid4())
    )
    
    storage.resources[resource_id] = response
    return response


# ──────────────────────────────────────────────────────────────────────────────
# READ SINGLE — GET /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Demo/resources/{name}
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.Demo/resources/{resource_name}",
    response_model=Resource,
    tags=["Resources"]
)
async def get_resource(
    subscription_id: str,
    resource_group: str,
    resource_name: str
):
    """Get a specific resource.
    
    **Returns:** Resource details or 404 if not found
    """
    resource_id = build_resource_id(subscription_id, resource_group, resource_name)
    
    if resource_id not in storage.resources:
        raise HTTPException(
            status_code=404,
            detail=f"Resource '{resource_name}' not found"
        )
    
    return storage.resources[resource_id]


# ──────────────────────────────────────────────────────────────────────────────
# LIST — GET /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Demo/resources
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.Demo/resources",
    response_model=PaginatedResourceList,
    tags=["Resources"]
)
async def list_resources(
    subscription_id: str,
    resource_group: str
):
    """List all resources in a resource group.
    
    **Returns:** Paginated list of resources
    """
    matching = [
        r for r in storage.resources.values()
        if subscription_id in r.id and resource_group in r.id
    ]
    
    return PaginatedResourceList(value=matching)


# ──────────────────────────────────────────────────────────────────────────────
# DELETE — DELETE /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Demo/resources/{name}
# ──────────────────────────────────────────────────────────────────────────────

@app.delete(
    "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.Demo/resources/{resource_name}",
    tags=["Resources"]
)
async def delete_resource(
    subscription_id: str,
    resource_group: str,
    resource_name: str
):
    """Delete a resource.
    
    **Returns:** Deletion confirmation or 404 if not found
    """
    resource_id = build_resource_id(subscription_id, resource_group, resource_name)
    
    if resource_id not in storage.resources:
        raise HTTPException(
            status_code=404,
            detail=f"Resource '{resource_name}' not found"
        )
    
    del storage.resources[resource_id]
    return {"status": "deleted", "resource_id": resource_id}


# ──────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "resources_count": len(storage.resources)
    }


# ══════════════════════════════════════════════════════════════════════════════
# THAT'S IT!
# ══════════════════════════════════════════════════════════════════════════════

"""
This minimal provider includes:

✅ CREATE/UPDATE (PUT) — idempotent resource creation
✅ READ (GET) — retrieve single resource
✅ LIST (GET) — list resources in resource group
✅ DELETE — remove resource
✅ proper ARM-compliant resource IDs
✅ proper error handling (404)
✅ automatic interactive API docs at /docs
✅ Pydantic validation on all inputs
✅ Lifecycle management (startup/shutdown)

To use:

1. Start the provider:
   python -m uvicorn minimal_provider:app --reload

2. Open docs:
   http://localhost:8000/docs

3. Try a PUT request:
   PUT /subscriptions/my-sub/resourceGroups/my-rg/providers/ITL.Demo/resources/my-resource
   
   Body:
   {
     "location": "westeurope",
     "tags": {"env": "dev"},
     "properties": {"description": "Test resource"}
   }

4. Then try GET, LIST, DELETE

That's how CRUD operations work in ITL ControlPlane providers!
"""
