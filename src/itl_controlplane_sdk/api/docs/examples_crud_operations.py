"""
Example: CRUD operations for a Network Provider resource type.

This example demonstrates the standard patterns for implementing Create, Read,
Update, Delete operations in an ITL ControlPlane resource provider.

Resource Type: virtualNetworks (ITL.Network namespace)
"""

import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

from itl_controlplane_sdk.core.models.base import ProvisioningState
from itl_controlplane_sdk.core.exceptions import (
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1. REQUEST/RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class VirtualNetworkProperties(BaseModel):
    """Properties specific to virtualNetwork resource."""
    address_space: List[str] = Field(..., description="Address space (CIDR blocks)")
    dns_servers: Optional[List[str]] = Field(None, description="Custom DNS servers")
    enable_ddos_protection: bool = Field(False, description="Enable DDoS protection")
    provisioning_state: str = Field(default=ProvisioningState.SUCCEEDED)


class CreateVirtualNetworkRequest(BaseModel):
    """Request to create a virtualNetwork resource."""
    location: str = Field(..., description="Azure region (e.g., 'westeurope')")
    properties: VirtualNetworkProperties
    tags: Optional[dict] = Field(default_factory=dict)


class VirtualNetworkResponse(BaseModel):
    """Response for virtualNetwork resource."""
    id: str = Field(..., description="ARM-compliant resource ID")
    name: str = Field(..., description="Resource name")
    type: str = Field(default="ITL.Network/virtualNetworks")
    location: str
    properties: VirtualNetworkProperties
    tags: dict = Field(default_factory=dict)
    resource_guid: str = Field(..., description="Unique resource GUID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-1",
                "name": "vnet-1",
                "type": "ITL.Network/virtualNetworks",
                "location": "westeurope",
                "properties": {
                    "address_space": ["10.0.0.0/16"],
                    "dns_servers": None,
                    "enable_ddos_protection": False,
                    "provisioning_state": "Succeeded"
                },
                "tags": {"environment": "production"},
                "resource_guid": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class PaginatedVirtualNetworkList(BaseModel):
    """Paginated list of virtualNetworks."""
    value: List[VirtualNetworkResponse]
    next_link: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# 2. IN-MEMORY STORAGE (replace with database in production)
# ══════════════════════════════════════════════════════════════════════════════

class VirtualNetworkStore:
    """Simple in-memory storage for virtualNetwork resources."""
    
    def __init__(self):
        self.resources: dict[str, VirtualNetworkResponse] = {}
    
    def exists(self, resource_id: str) -> bool:
        """Check if resource exists."""
        return resource_id in self.resources
    
    def create(self, resource: VirtualNetworkResponse) -> VirtualNetworkResponse:
        """Create a new resource."""
        if self.exists(resource.id):
            raise ResourceAlreadyExistsError(
                resource_type="ITL.Network/virtualNetworks",
                resource_name=resource.name
            )
        self.resources[resource.id] = resource
        logger.info(f"Created virtualNetwork: {resource.id}")
        return resource
    
    def get(self, resource_id: str) -> VirtualNetworkResponse:
        """Get a resource by ID."""
        if not self.exists(resource_id):
            raise ResourceNotFoundError(
                resource_type="ITL.Network/virtualNetworks",
                resource_name=resource_id
            )
        return self.resources[resource_id]
    
    def list(self, subscription_id: str, resource_group: str) -> List[VirtualNetworkResponse]:
        """List resources for a subscription/RG."""
        return [
            r for r in self.resources.values()
            if subscription_id in r.id and resource_group in r.id
        ]
    
    def update(self, resource_id: str, resource: VirtualNetworkResponse) -> VirtualNetworkResponse:
        """Update an existing resource."""
        if not self.exists(resource_id):
            raise ResourceNotFoundError(
                resource_type="ITL.Network/virtualNetworks",
                resource_name=resource_id
            )
        self.resources[resource_id] = resource
        logger.info(f"Updated virtualNetwork: {resource_id}")
        return resource
    
    def delete(self, resource_id: str) -> None:
        """Delete a resource."""
        if not self.exists(resource_id):
            raise ResourceNotFoundError(
                resource_type="ITL.Network/virtualNetworks",
                resource_name=resource_id
            )
        del self.resources[resource_id]
        logger.info(f"Deleted virtualNetwork: {resource_id}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. CRUD ROUTE HANDLER
# ══════════════════════════════════════════════════════════════════════════════

class VirtualNetworkHandler:
    """Handler for virtualNetwork CRUD operations."""
    
    def __init__(self, store: VirtualNetworkStore):
        self.store = store
    
    def generate_resource_id(
        self,
        subscription_id: str,
        resource_group: str,
        resource_name: str
    ) -> str:
        """Generate ARM-compliant resource ID."""
        return (
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/ITL.Network/virtualNetworks/{resource_name}"
        )
    
    async def create_or_update(
        self,
        subscription_id: str,
        resource_group: str,
        resource_name: str,
        request: CreateVirtualNetworkRequest
    ) -> VirtualNetworkResponse:
        """Create or update a virtualNetwork resource (idempotent)."""
        # Validate request
        if not request.properties.address_space:
            raise ValidationError(
                code="INVALID_ADDRESS_SPACE",
                message="address_space is required"
            )
        
        # Generate resource ID
        resource_id = self.generate_resource_id(subscription_id, resource_group, resource_name)
        
        # Create response object
        response = VirtualNetworkResponse(
            id=resource_id,
            name=resource_name,
            type="ITL.Network/virtualNetworks",
            location=request.location,
            properties=request.properties,
            tags=request.tags or {},
            resource_guid=str(uuid.uuid4())
        )
        
        # Save (create or update)
        if self.store.exists(resource_id):
            # Update: merge tags from existing
            existing = self.store.get(resource_id)
            if request.tags:
                existing.tags.update(request.tags)
            return self.store.update(resource_id, response)
        else:
            # Create: new resource
            return self.store.create(response)
    
    async def get(
        self,
        subscription_id: str,
        resource_group: str,
        resource_name: str
    ) -> VirtualNetworkResponse:
        """Get a virtualNetwork resource by name."""
        resource_id = self.generate_resource_id(subscription_id, resource_group, resource_name)
        return self.store.get(resource_id)
    
    async def list(
        self,
        subscription_id: str,
        resource_group: str
    ) -> PaginatedVirtualNetworkList:
        """List virtualNetworks in a resource group."""
        resources = self.store.list(subscription_id, resource_group)
        return PaginatedVirtualNetworkList(value=resources)
    
    async def delete(
        self,
        subscription_id: str,
        resource_group: str,
        resource_name: str
    ) -> dict:
        """Delete a virtualNetwork resource."""
        resource_id = self.generate_resource_id(subscription_id, resource_group, resource_name)
        self.store.delete(resource_id)
        return {"status": "deleted", "resource_id": resource_id}


# ══════════════════════════════════════════════════════════════════════════════
# 4. ROUTE SETUP FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def setup_virtualnetwork_routes(app: FastAPI, store: VirtualNetworkStore) -> None:
    """Register virtualNetwork CRUD routes.
    
    Registers 4 ARM-compliant endpoints:
    - POST   /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks
    - GET    /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks
    - GET    /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks/{name}
    - DELETE /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks/{name}
    - PATCH  /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks/{name}
    """
    
    handler = VirtualNetworkHandler(store)
    
    # ── CREATE OR UPDATE (PUT) ──
    @app.put(
        "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.Network/virtualNetworks/{resource_name}",
        response_model=VirtualNetworkResponse,
        summary="Create or Update Virtual Network",
        tags=["Network - Virtual Networks"]
    )
    async def create_or_update_vnet(
        subscription_id: str,
        resource_group: str,
        resource_name: str,
        request: CreateVirtualNetworkRequest
    ):
        """Create a new or update an existing virtualNetwork resource.
        
        This operation is **idempotent**: calling it multiple times with the same
        parameters will return the same result without errors.
        
        **Parameters:**
        - `subscription_id`: Azure subscription ID
        - `resource_group`: Resource group name
        - `resource_name`: Virtual network name
        
        **Request Body:**
        - `location`: Azure region (e.g., 'westeurope', 'eastus')
        - `properties.address_space`: List of CIDR blocks (e.g., ['10.0.0.0/16'])
        - `properties.dns_servers`: Optional custom DNS servers
        - `properties.enable_ddos_protection`: Enable DDos protection (default: false)
        - `tags`: Optional resource tags for organization
        
        **Returns:** Full virtualNetwork resource object
        """
        logger.info(
            f"Creating/updating virtualNetwork: "
            f"{subscription_id}/{resource_group}/{resource_name}"
        )
        return await handler.create_or_update(
            subscription_id, resource_group, resource_name, request
        )
    
    # ── READ SINGLE ──
    @app.get(
        "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.Network/virtualNetworks/{resource_name}",
        response_model=VirtualNetworkResponse,
        summary="Get Virtual Network",
        tags=["Network - Virtual Networks"]
    )
    async def get_vnet(
        subscription_id: str,
        resource_group: str,
        resource_name: str
    ):
        """Get a specific virtualNetwork resource by name.
        
        **Returns:** Full virtualNetwork resource object
        
        **Errors:**
        - 404: Virtual network not found
        """
        logger.info(
            f"Getting virtualNetwork: "
            f"{subscription_id}/{resource_group}/{resource_name}"
        )
        return await handler.get(subscription_id, resource_group, resource_name)
    
    # ── LIST ──
    @app.get(
        "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.Network/virtualNetworks",
        response_model=PaginatedVirtualNetworkList,
        summary="List Virtual Networks",
        tags=["Network - Virtual Networks"]
    )
    async def list_vnets(
        subscription_id: str,
        resource_group: str
    ):
        """List all virtualNetworks in a resource group.
        
        **Returns:** Paginated list of virtualNetwork resources
        """
        logger.info(
            f"Listing virtualNetworks: {subscription_id}/{resource_group}"
        )
        return await handler.list(subscription_id, resource_group)
    
    # ── DELETE ──
    @app.delete(
        "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/ITL.Network/virtualNetworks/{resource_name}",
        summary="Delete Virtual Network",
        tags=["Network - Virtual Networks"]
    )
    async def delete_vnet(
        subscription_id: str,
        resource_group: str,
        resource_name: str
    ):
        """Delete a virtualNetwork resource.
        
        **Errors:**
        - 404: Virtual network not found
        """
        logger.info(
            f"Deleting virtualNetwork: "
            f"{subscription_id}/{resource_group}/{resource_name}"
        )
        return await handler.delete(subscription_id, resource_group, resource_name)


# ══════════════════════════════════════════════════════════════════════════════
# 5. USAGE IN A PROVIDER SERVER
# ══════════════════════════════════════════════════════════════════════════════

"""
Example of integrating into a provider server:

from itl_controlplane_sdk.api import BaseProviderServer, AppFactory

class NetworkProviderServer(BaseProviderServer):
    def __init__(self):
        self.engine = SQLAlchemyStorageEngine()
        self.provider = NetworkProvider(engine=self.engine)
        self.registry = ResourceProviderRegistry()
        self.app = None
        self.audit_publisher = None
        self.vnet_store = VirtualNetworkStore()
    
    def create_app(self):
        # ... setup lifespan, middleware, etc ...
        
        app = factory.create_app(cors_origins=["*"], lifespan=lifespan)
        
        # Register virtualNetwork CRUD routes
        setup_virtualnetwork_routes(app, self.vnet_store)
        
        return app
"""
