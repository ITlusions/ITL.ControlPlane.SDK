# CRUD Operations Side-by-Side Comparison

Quick reference showing the exact same CRUD operations in curl, Python, and PowerShell.

---

## CREATE (PUT)

### curl
```bash
curl -X PUT \
  http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod \
  -H "Content-Type: application/json" \
  -d '{
    "location": "westeurope",
    "tags": {
      "environment": "production",
      "team": "platform"
    },
    "properties": {
      "address_space": ["10.0.0.0/16"],
      "dns_servers": null,
      "enable_ddos_protection": false
    }
  }'
```

### Python (httpx)
```python
import httpx
import asyncio

async def create_vnet():
    async with httpx.AsyncClient() as client:
        response = await client.put(
            "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod",
            json={
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
        )
        print(f"Status: {response.status_code}")
        print(f"Created: {response.json()['id']}")

asyncio.run(create_vnet())
```

### PowerShell
```powershell
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

$response = Invoke-RestMethod `
    -Uri "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod" `
    -Method PUT `
    -Headers @{"Content-Type" = "application/json"} `
    -Body $body

Write-Host "Created: $($response.id)"
```

---

## READ SINGLE (GET)

### curl
```bash
curl -X GET \
  http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod
```

### Python (httpx)
```python
import httpx
import asyncio

async def get_vnet():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod"
        )
        vnet = response.json()
        print(f"Name: {vnet['name']}")
        print(f"Location: {vnet['location']}")
        print(f"Address Space: {vnet['properties']['address_space']}")

asyncio.run(get_vnet())
```

### PowerShell
```powershell
$vnet = Invoke-RestMethod `
    -Uri "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod" `
    -Method GET

Write-Host "Name: $($vnet.name)"
Write-Host "Location: $($vnet.location)"
Write-Host "Address Space: $($vnet.properties.address_space -join ', ')"
```

---

## LIST (GET collection)

### curl
```bash
curl -X GET \
  http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks
```

### Python (httpx)
```python
import httpx
import asyncio

async def list_vnets():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks"
        )
        data = response.json()
        vnets = data.get("value", [])
        
        print(f"Found {len(vnets)} virtual networks:")
        for vnet in vnets:
            print(f"  - {vnet['name']} ({vnet['location']})")

asyncio.run(list_vnets())
```

### PowerShell
```powershell
$response = Invoke-RestMethod `
    -Uri "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks" `
    -Method GET

$response.value | ForEach-Object {
    Write-Host "Name: $($_.name), Location: $($_.location)"
}
```

---

## UPDATE (PUT with modified values)

### curl
```bash
curl -X PUT \
  http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod \
  -H "Content-Type: application/json" \
  -d '{
    "location": "westeurope",
    "tags": {
      "environment": "production",
      "team": "platform",
      "cost-center": "cc-123"
    },
    "properties": {
      "address_space": ["10.0.0.0/16", "10.1.0.0/16"],
      "dns_servers": ["1.1.1.1", "8.8.8.8"],
      "enable_ddos_protection": true
    }
  }'
```

### Python (httpx)
```python
import httpx
import asyncio

async def update_vnet():
    async with httpx.AsyncClient() as client:
        # Get current state
        get_resp = await client.get(
            "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod"
        )
        current = get_resp.json()
        
        # Merge changes
        updated = {
            "location": current["location"],
            "tags": {**current.get("tags", {}), "cost-center": "cc-123"},
            "properties": {
                **current["properties"],
                "address_space": ["10.0.0.0/16", "10.1.0.0/16"],
                "dns_servers": ["1.1.1.1", "8.8.8.8"],
                "enable_ddos_protection": True
            }
        }
        
        # Update
        response = await client.put(
            "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod",
            json=updated
        )
        print(f"Updated: {response.json()['name']}")

asyncio.run(update_vnet())
```

### PowerShell
```powershell
# Get current state
$current = Invoke-RestMethod `
    -Uri "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod" `
    -Method GET

# Prepare update
$body = @{
    location = $current.location
    tags = $current.tags + @{"cost-center" = "cc-123"}
    properties = @{
        address_space = @("10.0.0.0/16", "10.1.0.0/16")
        dns_servers = @("1.1.1.1", "8.8.8.8")
        enable_ddos_protection = $true
    }
} | ConvertTo-Json

# Update
$response = Invoke-RestMethod `
    -Uri "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod" `
    -Method PUT `
    -Headers @{"Content-Type" = "application/json"} `
    -Body $body

Write-Host "Updated: $($response.name)"
```

---

## DELETE

### curl
```bash
curl -X DELETE \
  http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod
```

### Python (httpx)
```python
import httpx
import asyncio

async def delete_vnet():
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod"
        )
        print(f"Status: {response.status_code}")
        print(f"Deleted: {response.json()['resource_id']}")

asyncio.run(delete_vnet())
```

### PowerShell
```powershell
$response = Invoke-RestMethod `
    -Uri "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/vnet-prod" `
    -Method DELETE

Write-Host "Deleted: $($response.status)"
```

---

## Error Handling

### Python (httpx)
```python
import httpx
import asyncio

async def handle_errors():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/nonexistent"
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                print("Resource not found")
            elif exc.response.status_code == 400:
                print("Invalid request")
                print(f"Error: {exc.response.json()}")
            else:
                print(f"Error {exc.response.status_code}: {exc.response.text}")

asyncio.run(handle_errors())
```

### PowerShell
```powershell
try {
    $response = Invoke-RestMethod `
        -Uri "http://localhost:8000/subscriptions/sub-001/resourceGroups/my-rg/providers/ITL.Network/virtualNetworks/nonexistent" `
        -ErrorAction Stop
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    switch ($statusCode) {
        404 { Write-Host "Resource not found" }
        400 { Write-Host "Invalid request" }
        default { Write-Host "Error: $statusCode" }
    }
}
```

---

## Summary Table

| Operation | HTTP Method | Path | Status Code |
|-----------|-----------|------|-------------|
| Create | PUT | `/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks/{name}` | 200-201 |
| Read | GET | `/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks/{name}` | 200 |
| List | GET | `/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks` | 200 |
| Update | PUT | `/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks/{name}` | 200 |
| Delete | DELETE | `/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks/{name}` | 200 |

---

## Key Patterns Across All Languages

✅ **Location is REQUIRED** in every create/update request  
✅ **Tags are optional** but recommended for organization  
✅ **PUT is idempotent** — same request = same result, safe to retry  
✅ **GET for list** — no `/{name}` at the end  
✅ **Proper error handling** — check status codes, handle failures  
✅ **URL format never varies** — always use `/{name}` at the end for single resource operations  

---

## Copy-Paste Ready

All examples above are copy-paste ready:
- **curl**: Just paste into terminal
- **Python**: Just paste into script, run with `python script.py`
- **PowerShell**: Just paste into PowerShell, run with `.\script.ps1`

No modifications needed for basic usage!
