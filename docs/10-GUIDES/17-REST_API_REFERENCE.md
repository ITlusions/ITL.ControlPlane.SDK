# REST API Contract Reference

Complete HTTP REST API contract for resource providers following Azure Resource Manager (ARM) REST conventions.

---

## Base URL Pattern

```
https://{gateway-host}:{port}/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{providerNamespace}/{resourceType}/{resourceName}
```

### Path Parameters

| Parameter | Type | Required | Format |
|-----------|------|----------|--------|
| `subscriptionId` | string | Yes | UUID format (e.g., `sub-123`) |
| `resourceGroupName` | string | Yes | 1-90 alphanumeric + hyphens |
| `providerNamespace` | string | Yes | Format: `ITL.{Provider}` |
| `resourceType` | string | Yes | Lowercase, plural (e.g., `virtualmachines`) |
| `resourceName` | string | Yes | 1-80 alphanumeric + hyphens |

---

## HTTP Methods

### PUT: Create or Update Resource

Create a new resource or update an existing one. **Idempotent** - safe to call multiple times.

```
PUT /subscriptions/{subId}/resourceGroups/{rgName}/providers/{ns}/{type}/{name}
```

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "location": "westus2",
  "properties": {
    "size": "Standard_D2s_v3"
  },
  "tags": {
    "environment": "production"
  }
}
```

**Success Response (200 OK):**
```json
{
  "id": "/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001",
  "name": "vm-001",
  "type": "ITL.Compute/virtualmachines",
  "location": "westus2",
  "provisioning_state": "Accepted",
  "properties": {
    "size": "Standard_D2s_v3",
    "vmId": "abc-123"
  },
  "tags": {
    "environment": "production"
  }
}
```

**Long-Running Response (202 Accepted):**
```
HTTP/1.1 202 Accepted
Location: /subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/operations/op-123

{
  "id": "/subscriptions/.../operations/op-123",
  "provisioning_state": "Provisioning"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": {
    "code": "BadRequest",
    "message": "Invalid resource name format"
  }
}
```

---

### GET: Retrieve Resource

Get a single resource by name.

```
GET /subscriptions/{subId}/resourceGroups/{rgName}/providers/{ns}/{type}/{name}
```

**Request Headers:**
```
Accept: application/json
```

**Success Response (200 OK):**
```json
{
  "id": "/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001",
  "name": "vm-001",
  "type": "ITL.Compute/virtualmachines",
  "location": "westus2",
  "provisioning_state": "Succeeded",
  "properties": {
    "size": "Standard_D2s_v3"
  }
}
```

**Error Response (404 Not Found):**
```json
{
  "error": {
    "code": "NotFound",
    "message": "Resource not found"
  }
}
```

---

### DELETE: Remove Resource

Delete a resource. **Idempotent** - safe to call multiple times.

```
DELETE /subscriptions/{subId}/resourceGroups/{rgName}/providers/{ns}/{type}/{name}
```

**Success Response (204 No Content):**
```
HTTP/1.1 204 No Content
```

**Long-Running Response (202 Accepted):**
```
HTTP/1.1 202 Accepted
Location: /subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/operations/op-456
```

**Error Response (404 Not Found):**
```json
{
  "error": {
    "code": "NotFound",
    "message": "Resource not found"
  }
}
```

---

### GET: List Resources in Resource Group

List all resources of a specific type in a resource group.

```
GET /subscriptions/{subId}/resourceGroups/{rgName}/providers/{ns}/{type}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `$filter` | string | OData filter expression |
| `$select` | string | Comma-separated list of properties |
| `$top` | integer | Number of results to return |
| `$skip` | integer | Number of results to skip |

**Examples:**
```
GET .../providers/ITL.Compute/virtualmachines?$top=10&$skip=0
GET .../providers/ITL.Compute/virtualmachines?$filter=provisioning_state eq 'Succeeded'
GET .../providers/ITL.Compute/virtualmachines?$select=name,properties
```

**Success Response (200 OK):**
```json
{
  "value": [
    {
      "id": "/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001",
      "name": "vm-001",
      "type": "ITL.Compute/virtualmachines",
      "location": "westus2",
      "provisioning_state": "Succeeded"
    },
    {
      "id": "/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-002",
      "name": "vm-002",
      "type": "ITL.Compute/virtualmachines",
      "location": "westus2",
      "provisioning_state": "Succeeded"
    }
  ],
  "nextLink": "/subscriptions/.../providers/ITL.Compute/virtualmachines?$skip=20"
}
```

---

## Resource Properties

### Required Properties

Every resource response must include:

```json
{
  "id": "string",           // Fully qualified resource ID
  "name": "string",         // Resource name
  "type": "string",         // Resource type (provider/resourceType)
  "location": "string"      // Azure region
}
```

### Optional Properties

```json
{
  "tags": {                 // Custom key-value pairs
    "environment": "prod"
  },
  "provisioning_state": "string",  // Current state
  "properties": {           // Resource-specific properties
    "custom": "value"
  }
}
```

---

## Provisioning States

Resources transition through states during operation:

```
         ┌──────────────────────────────────┐
         │      ACCEPTED                    │
         │ (initial state on create)        │
         └──────────────┬───────────────────┘
                        │
         ┌──────────────▼───────────────────┐
         │      PROVISIONING                │
         │ (async work in progress)         │
         └──────────────┬───────────────────┘
                        │
          ┌─────────────┴──────────────┐
          │                            │
    ┌─────▼──────────┐         ┌─────▼──────────┐
    │   SUCCEEDED   │         │   FAILED       │
    │ (all good)    │         │ (error state)  │
    └────────────────┘         └────────────────┘
          ▲                    
          │ (retry)            
    ┌─────┴──────────┐         
    │    DELETING    │         
    │ (cleanup)      │         
    └────────────────┘         
```

### Valid State Transitions

| From | To | Allowed | Reason |
|------|----|---------|----|
| ACCEPTED | PROVISIONING | ✅ | Normal flow |
| ACCEPTED | SUCCEEDED | ✅ | Immediate completion |
| ACCEPTED | FAILED | ✅ | Validation error |
| PROVISIONING | SUCCEEDED | ✅ | Async completed |
| PROVISIONING | FAILED | ✅ | Async error |
| SUCCEEDED | DELETING | ✅ | Delete initiated |
| DELETING | SUCCEEDED | ✅ | Cleanup complete |
| FAILED | ACCEPTED | ✅ | Retry |

---

## Query Parameters

### OData Filter Syntax

```
$filter=propertyName operator value

Operators:
- eq  : equals
- ne  : not equals
- gt  : greater than
- lt  : less than
- ge  : greater than or equal
- le  : less than or equal
- and : logical AND
- or  : logical OR

Examples:
$filter=provisioning_state eq 'Succeeded'
$filter=tags/environment eq 'production'
$filter=name startswith 'vm-'
$filter=provisioning_state eq 'Succeeded' and tags/team eq 'platform'
```

### Pagination

```
$top=20     : Return max 20 results
$skip=40    : Skip first 40 results
$skip=0&$top=20  : First page (items 0-19)
$skip=20&$top=20   : Second page (items 20-39)

If more results: response includes "nextLink"
{
  "value": [...],
  "nextLink": ".../providers/.../virtualmachines?$skip=20"
}
```

---

## Common Request/Response Patterns

### Create and Poll for Completion

```bash
# 1. Create resource (returns 202 Accepted)
PUT /subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001
→ 202 Accepted, operation ID in body/location

# 2. Poll operation status
GET /subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/operations/op-123
→ 200 OK, check provisioning_state

# 3. Repeat step 2 until provisioning_state != "Provisioning"

# 4. Optionally get final resource
GET /subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001
→ 200 OK, final state
```

### List and Filter

```bash
# List all VMs
GET .../providers/ITL.Compute/virtualmachines
→ 200 OK, value array

# List only succeeded VMs
GET ".../providers/ITL.Compute/virtualmachines?$filter=provisioning_state eq 'Succeeded'"
→ 200 OK, filtered results

# Paginate results
GET ".../providers/ITL.Compute/virtualmachines?$skip=0&$top=10"
→ 200 OK, first 10, includes nextLink
```

---

## HTTP Headers

### Request Headers

| Header | Values | Purpose |
|--------|--------|---------|
| `Content-Type` | `application/json` | Request body format |
| `Accept` | `application/json` | Response format |
| `Authorization` | `Bearer {token}` | Authentication |
| `If-Match` | `{etag}` | Optimistic concurrency |

### Response Headers

| Header | Purpose |
|--------|---------|
| `Content-Type` | Response format |
| `Location` | URL of operation (202 responses) |
| `Retry-After` | Seconds to wait before retry (429) |
| `ETag` | Resource version for concurrency |
| `X-Request-Id` | Request tracking ID |

---

## Status Codes Reference

### Success Codes

| Code | Meaning | Used For | Example |
|------|---------|----------|---------|
| 200 | OK | Successful operation | GET, PUT, DELETE (sync) |
| 201 | Created | Resource created | Not typically used (use 200) |
| 202 | Accepted | Long-running operation started | PUT, DELETE (async) |
| 204 | No Content | Success, no response body | DELETE (immediate) |

### Error Codes

| Code | Meaning | When | Example |
|------|---------|------|---------|
| 400 | Bad Request | Invalid input | Malformed JSON, invalid name |
| 401 | Unauthorized | Missing authentication | No API key |
| 403 | Forbidden | Not authorized | User doesn't have permission |
| 404 | Not Found | Resource doesn't exist | Non-existent resource |
| 409 | Conflict | Duplicate or invalid state | Resource already exists |
| 429 | Too Many Requests | Rate limit exceeded | Too many requests/minute |
| 500 | Internal Server Error | Unexpected error | Unhandled exception |
| 503 | Service Unavailable | Provider down | Provider crashed |

---

## Example: Complete CRUD Flow

### 1. Create (PUT)

```bash
curl -X PUT \
  'http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001' \
  -H 'Content-Type: application/json' \
  -d '{
    "location": "westus2",
    "properties": {
      "size": "Standard_D2s_v3",
      "image": "Ubuntu20.04"
    },
    "tags": {
      "environment": "production"
    }
  }'
```

**Response:**
```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001",
  "name": "vm-001",
  "type": "ITL.Compute/virtualmachines",
  "location": "westus2",
  "provisioning_state": "Accepted",
  "properties": {
    "size": "Standard_D2s_v3",
    "vmId": "abc-123-def-456"
  }
}
```

### 2. Read (GET)

```bash
curl -X GET \
  'http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001'
```

**Response:**
```json
{
  "id": "/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001",
  "name": "vm-001",
  "provisioning_state": "Succeeded",
  "properties": {
    "vmId": "abc-123-def-456",
    "powerState": "Running"
  }
}
```

### 3. Update (PUT)

```bash
curl -X PUT \
  'http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001' \
  -H 'Content-Type: application/json' \
  -d '{
    "tags": {
      "environment": "production",
      "version": "2.0"
    }
  }'
```

### 4. List (GET)

```bash
curl -X GET \
  'http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines?$top=10'
```

### 5. Delete (DELETE)

```bash
curl -X DELETE \
  'http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/vm-001'
```

**Response:**
```
HTTP/1.1 204 No Content
```

---

## Client Libraries

### Python SDK

```python
from itl_controlplane_sdk import ResourceRequest, ResourceResponse

# Create
response = await provider.create_or_update_resource(
    ResourceRequest(
        resource_type="virtualmachines",
        resource_name="vm-001",
        subscription_id="sub-123",
        resource_group="rg-prod",
        location="westus2",
        properties={"size": "Standard_D2s_v3"}
    )
)

# Read
resource = await provider.get_resource(request)

# Update
await provider.create_or_update_resource(updated_request)

# List
resources = await provider.list_resources(list_request)

# Delete
await provider.delete_resource(request)
```

### REST Client Examples

**Python requests:**
```python
import requests

resp = requests.put(
    'http://localhost:9050/subscriptions/sub-123/.../virtualmachines/vm-001',
    json={
        "location": "westus2",
        "properties": {"size": "Standard_D2s_v3"}
    }
)
```

**JavaScript fetch:**
```javascript
const response = await fetch(
  'http://localhost:9050/subscriptions/sub-123/.../virtualmachines/vm-001',
  {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      location: 'westus2',
      properties: { size: 'Standard_D2s_v3' }
    })
  }
);
```

---

## Related Documentation

- [02-INSTALLATION.md](../02-INSTALLATION.md) - SDK setup
- [03-API_REFERENCE.md](../03-API_REFERENCE.md) - Detailed API methods
- [16-ERROR_HANDLING.md](16-ERROR_HANDLING.md) - Error codes
- [15-TROUBLESHOOTING.md](15-TROUBLESHOOTING.md) - Common issues

---

This REST API contract ensures consistency with Azure Resource Manager standards while being easy to implement.
