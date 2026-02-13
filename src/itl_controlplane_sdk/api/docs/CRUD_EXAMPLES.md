"""
CRUD Operations Examples — Practical Usage Guide

This guide shows how to create, read, update, and delete resources using
the ITL ControlPlane API patterns. Examples use curl, Python httpx, and PowerShell.
"""

# ══════════════════════════════════════════════════════════════════════════════
# SETUP
# ══════════════════════════════════════════════════════════════════════════════

BASE_URL = "http://localhost:8000"
SUBSCRIPTION_ID = "sub-prod-001"
RESOURCE_GROUP = "app-rg"
RESOURCE_NAME = "vnet-1"

ARM_RESOURCE_PATH = (
    f"/subscriptions/{SUBSCRIPTION_ID}"
    f"/resourceGroups/{RESOURCE_GROUP}"
    f"/providers/ITL.Network/virtualNetworks"
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. CREATE — PUT /subscriptions/.../providers/ITL.Network/virtualNetworks/{name}
# ══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# CURL EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

"""
curl -X PUT \
  http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1 \
  -H "Content-Type: application/json" \
  -d '{
    "location": "westeurope",
    "tags": {
      "environment": "production",
      "team": "platform"
    },
    "properties": {
      "address_space": [
        "10.0.0.0/16"
      ],
      "dns_servers": null,
      "enable_ddos_protection": false
    }
  }'

# RESPONSE (201 Created or 200 OK if updating):
{
  "id": "/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1",
  "name": "vnet-1",
  "type": "ITL.Network/virtualNetworks",
  "location": "westeurope",
  "properties": {
    "address_space": ["10.0.0.0/16"],
    "dns_servers": null,
    "enable_ddos_protection": false,
    "provisioning_state": "Succeeded"
  },
  "tags": {
    "environment": "production",
    "team": "platform"
  },
  "resource_guid": "550e8400-e29b-41d4-a716-446655440000"
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# PYTHON HTTPX EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

import httpx
import asyncio

async def create_virtualnetwork():
    async with httpx.AsyncClient() as client:
        payload = {
            "location": "westeurope",
            "tags": {
                "environment": "production",
                "team": "platform"
            },
            "properties": {
                "address_space": ["10.0.0.0/16"],
                "dns_servers": None,
                "enable_ddos_protection": False
            }
        }
        
        response = await client.put(
            f"{BASE_URL}{ARM_RESOURCE_PATH}/{RESOURCE_NAME}",
            json=payload
        )
        
        if response.status_code in (200, 201):
            print("✓ Virtual Network created:")
            print(response.json())
        else:
            print(f"✗ Error {response.status_code}: {response.text}")

# Run: asyncio.run(create_virtualnetwork())

# ─────────────────────────────────────────────────────────────────────────────
# POWERSHELL EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

"""
$body = @{
    location = "westeurope"
    tags = @{
        environment = "production"
        team = "platform"
    }
    properties = @{
        address_space = @("10.0.0.0/16")
        dns_servers = $null
        enable_ddos_protection = $false
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1" `
    -Method PUT `
    -Headers @{"Content-Type" = "application/json"} `
    -Body $body | ConvertTo-Json -Depth 5
"""


# ══════════════════════════════════════════════════════════════════════════════
# 2. READ SINGLE — GET /subscriptions/.../virtualNetworks/{name}
# ══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# CURL EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

"""
curl -X GET \
  http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1 \
  -H "Content-Type: application/json"

# RESPONSE (200 OK):
{
  "id": "/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1",
  "name": "vnet-1",
  "type": "ITL.Network/virtualNetworks",
  "location": "westeurope",
  ...
}

# ERROR RESPONSE (404 Not Found):
{
  "error": {
    "code": "ResourceNotFound",
    "message": "Virtual network 'vnet-nonexistent' not found"
  }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# PYTHON HTTPX EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

async def get_virtualnetwork():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}{ARM_RESOURCE_PATH}/{RESOURCE_NAME}"
        )
        
        if response.status_code == 200:
            print("✓ Virtual Network retrieved:")
            vnet = response.json()
            print(f"  Name: {vnet['name']}")
            print(f"  Location: {vnet['location']}")
            print(f"  Address Space: {vnet['properties']['address_space']}")
        else:
            print(f"✗ Error {response.status_code}: {response.text}")

# ─────────────────────────────────────────────────────────────────────────────
# POWERSHELL EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

"""
$vnet = Invoke-RestMethod -Uri "http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1"
$vnet | ConvertTo-Json -Depth 5
"""


# ══════════════════════════════════════════════════════════════════════════════
# 3. LIST — GET /subscriptions/.../virtualNetworks (no {name})
# ══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# CURL EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

"""
curl -X GET \
  http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks \
  -H "Content-Type: application/json"

# RESPONSE (200 OK):
{
  "value": [
    {
      "id": "/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1",
      "name": "vnet-1",
      ...
    },
    {
      "id": "/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-2",
      "name": "vnet-2",
      ...
    }
  ],
  "next_link": null
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# PYTHON HTTPX EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

async def list_virtualnetworks():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}{ARM_RESOURCE_PATH}"
        )
        
        if response.status_code == 200:
            data = response.json()
            vnets = data.get("value", [])
            print(f"✓ Found {len(vnets)} virtual networks:")
            for vnet in vnets:
                print(f"  - {vnet['name']} ({vnet['location']})")
        else:
            print(f"✗ Error {response.status_code}: {response.text}")

# ─────────────────────────────────────────────────────────────────────────────
# POWERSHELL EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

"""
$response = Invoke-RestMethod -Uri "http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks"
$response.value | Format-Table -Property name, location, @{Name="AddressSpace"; Expression={$_.properties.address_space -join ', '}}
"""


# ══════════════════════════════════════════════════════════════════════════════
# 4. UPDATE — PUT /subscriptions/.../virtualNetworks/{name} (with new values)
# ══════════════════════════════════════════════════════════════════════════════

"""
Update is done using the same PUT endpoint as CREATE, but with different values.
This is idempotent — same result regardless of how many times you call it.

EXAMPLE: Update address space and tags
"""

# ─────────────────────────────────────────────────────────────────────────────
# CURL EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

"""
curl -X PUT \
  http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1 \
  -H "Content-Type: application/json" \
  -d '{
    "location": "westeurope",
    "tags": {
      "environment": "production",
      "team": "platform",
      "cost-center": "cc-123"
    },
    "properties": {
      "address_space": [
        "10.0.0.0/16",
        "10.1.0.0/16"
      ],
      "dns_servers": ["1.1.1.1", "8.8.8.8"],
      "enable_ddos_protection": true
    }
  }'

# NOTE: This returns 200 OK if resource existed before
"""

# ─────────────────────────────────────────────────────────────────────────────
# PYTHON HTTPX EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

async def update_virtualnetwork():
    async with httpx.AsyncClient() as client:
        # First, GET to see current state (optional)
        get_resp = await client.get(
            f"{BASE_URL}{ARM_RESOURCE_PATH}/{RESOURCE_NAME}"
        )
        current_vnet = get_resp.json()
        
        # Modify properties
        updated_payload = {
            "location": current_vnet["location"],
            "tags": {
                **current_vnet.get("tags", {}),
                "cost-center": "cc-123"  # Add new tag
            },
            "properties": {
                "address_space": [
                    "10.0.0.0/16",
                    "10.1.0.0/16"  # Add additional address space
                ],
                "dns_servers": ["1.1.1.1", "8.8.8.8"],
                "enable_ddos_protection": True
            }
        }
        
        # PUT to update
        response = await client.put(
            f"{BASE_URL}{ARM_RESOURCE_PATH}/{RESOURCE_NAME}",
            json=updated_payload
        )
        
        if response.status_code == 200:
            print("✓ Virtual Network updated")
        else:
            print(f"✗ Error {response.status_code}: {response.text}")

# ─────────────────────────────────────────────────────────────────────────────
# PATCH — Azure ARM also supports PATCH for partial updates
# ─────────────────────────────────────────────────────────────────────────────

"""
Some providers support PATCH for partial updates (only send changed fields).
This is OPTIONAL but recommended.

curl -X PATCH \
  http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1 \
  -H "Content-Type: application/json" \
  -d '{
    "tags": {
      "cost-center": "cc-456"
    }
  }'
"""


# ══════════════════════════════════════════════════════════════════════════════
# 5. DELETE — DELETE /subscriptions/.../virtualNetworks/{name}
# ══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# CURL EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

"""
curl -X DELETE \
  http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1

# RESPONSE (200 OK or 202 Accepted):
{
  "status": "deleted",
  "resource_id": "/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1"
}

# ERROR RESPONSE (404 Not Found if already deleted):
{
  "error": {
    "code": "ResourceNotFound",
    "message": "Virtual network 'vnet-1' not found"
  }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# PYTHON HTTPX EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

async def delete_virtualnetwork():
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{BASE_URL}{ARM_RESOURCE_PATH}/{RESOURCE_NAME}"
        )
        
        if response.status_code == 200:
            print("✓ Virtual Network deleted")
        else:
            print(f"✗ Error {response.status_code}: {response.text}")

# ─────────────────────────────────────────────────────────────────────────────
# POWERSHELL EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

"""
Invoke-RestMethod -Uri "http://localhost:8000/subscriptions/sub-prod-001/resourceGroups/app-rg/providers/ITL.Network/virtualNetworks/vnet-1" `
    -Method DELETE
"""


# ══════════════════════════════════════════════════════════════════════════════
# FULL CRUD WORKFLOW EXAMPLE
# ══════════════════════════════════════════════════════════════════════════════

async def full_crud_example():
    """Complete example: create → read → list → update → delete."""
    async with httpx.AsyncClient() as client:
        base = f"{BASE_URL}{ARM_RESOURCE_PATH}"
        
        print("\n1️⃣  CREATE")
        create_resp = await client.put(
            f"{base}/demo-vnet",
            json={
                "location": "westeurope",
                "tags": {"env": "demo"},
                "properties": {
                    "address_space": ["10.0.0.0/16"],
                    "dns_servers": None,
                    "enable_ddos_protection": False
                }
            }
        )
        vnet_id = create_resp.json()["id"]
        print(f"✓ Created: {vnet_id}")
        
        print("\n2️⃣  READ")
        read_resp = await client.get(f"{base}/demo-vnet")
        print(f"✓ Retrieved: {read_resp.json()['name']}")
        
        print("\n3️⃣  LIST")
        list_resp = await client.get(base)
        count = len(list_resp.json()["value"])
        print(f"✓ Listed: {count} networks")
        
        print("\n4️⃣  UPDATE")
        update_resp = await client.put(
            f"{base}/demo-vnet",
            json={
                "location": "westeurope",
                "tags": {"env": "demo", "updated": "true"},
                "properties": {
                    "address_space": ["10.0.0.0/16", "10.1.0.0/16"],
                    "dns_servers": None,
                    "enable_ddos_protection": True
                }
            }
        )
        print(f"✓ Updated address space: {update_resp.json()['properties']['address_space']}")
        
        print("\n5️⃣  DELETE")
        delete_resp = await client.delete(f"{base}/demo-vnet")
        print(f"✓ Deleted: {delete_resp.json()['status']}")

# Run: asyncio.run(full_crud_example())


# ══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLING
# ══════════════════════════════════════════════════════════════════════════════

"""
SDK exceptions map to HTTP status codes automatically:

ResourceNotFoundError        → 404 Not Found
ResourceAlreadyExistsError   → 409 Conflict
ValidationError              → 400 Bad Request
AuthorizationError           → 403 Forbidden
ConfigurationError           → 500 Internal Server Error
ServiceUnavailableError      → 503 Service Unavailable

EXAMPLE ERROR HANDLING:
"""

async def handle_errors_example():
    from httpx import HTTPStatusError
    
    async with httpx.AsyncClient() as client:
        try:
            # Try to get non-existent resource
            response = await client.get(
                f"{BASE_URL}{ARM_RESOURCE_PATH}/nonexistent"
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                print("✗ Resource not found")
            elif exc.response.status_code == 400:
                print("✗ Invalid request")
            else:
                print(f"✗ Error {exc.response.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
# KEY PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

"""
✓ ALWAYS use ARM-compliant resource IDs:
  /subscriptions/{id}/resourceGroups/{rg}/providers/ITL.{Domain}/{type}/{name}

✓ CREATE/UPDATE always use PUT (not POST)
  PUT is idempotent — safe to retry

✓ LOCATION is REQUIRED in every request
  Azure standard — resources must have a location

✓ TAGS are optional but recommended
  Use for billing, organization, automation

✓ PROPERTIES are resource-type-specific
  Define per resource type (address_space for vnet, etc)

✓ RESPONSE always includes:
  - id (ARM-compliant resource ID)
  - name (short name)
  - type (ITL.{Domain}/{resourceType})
  - location
  - properties (with provisioningState)
  - tags
  - resource_guid (optional but recommended)

✓ LISTS always use pagination:
  - value: List of resources
  - next_link: URL for next page (if applicable)

✓ ERRORS use standard error response:
  {
    "error": {
      "code": "ErrorCode",
      "message": "Human-readable message"
    }
  }
"""
