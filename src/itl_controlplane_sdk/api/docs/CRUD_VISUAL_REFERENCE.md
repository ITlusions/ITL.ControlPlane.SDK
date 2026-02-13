# CRUD Operations Visual Reference

## HTTP Method to Operation Mapping

```
┌─────────────────────────────────────────────────────────────────────┐
│                  CRUD Operations in ITL ControlPlane                 │
└─────────────────────────────────────────────────────────────────────┘

DEFAULT BASE PATH:
/subscriptions/{subscriptionId}/resourceGroups/{resourceGroup}/providers/ITL.{Domain}/{resourceType}

┌──────────┬──────────┬───────────────────────┬──────────────┐
│ Operation│  Method  │        Path           │  Status Code │
├──────────┼──────────┼───────────────────────┼──────────────┤
│  CREATE  │   PUT    │  {base}/{name}        │     200-201  │
│  READ    │   GET    │  {base}/{name}        │      200     │
│  LIST    │   GET    │  {base}               │      200     │
│  UPDATE  │   PUT    │  {base}/{name}        │      200     │
│  DELETE  │  DELETE  │  {base}/{name}        │      200     │
└──────────┴──────────┴───────────────────────┴──────────────┘
```

---

## Request/Response Flow

### CREATE (idempotent PUT)

```
CLIENT REQUEST:
┌─────────────────────────────────────────────────────────┐
│ PUT /subscriptions/sub-001/resourceGroups/rg-1/         │
│     providers/ITL.Network/virtualNetworks/vnet-prod    │
│                                                          │
│ Headers:                                                 │
│   Content-Type: application/json                        │
│                                                          │
│ Body:                                                    │
│ {                                                        │
│   "location": "westeurope",                             │
│   "tags": {...},                                        │
│   "properties": {                                       │
│     "address_space": ["10.0.0.0/16"],                   │
│     ...                                                 │
│   }                                                     │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
                         ↓
              SERVER PROCESSING
                         ↓
SERVER RESPONSE:
┌─────────────────────────────────────────────────────────┐
│ Status: 200 OK OR 201 Created                           │
│                                                          │
│ Body:                                                    │
│ {                                                        │
│   "id": "/subscriptions/sub-001/resourceGroups/rg-1/    │
│          providers/ITL.Network/virtualNetworks/         │
│          vnet-prod",                                    │
│   "name": "vnet-prod",                                  │
│   "type": "ITL.Network/virtualNetworks",               │
│   "location": "westeurope",                             │
│   "properties": {                                       │
│     "address_space": ["10.0.0.0/16"],                   │
│     "provisioning_state": "Succeeded",                  │
│     ...                                                 │
│   },                                                    │
│   "tags": {...},                                        │
│   "resource_guid": "550e8400-e29b-..."                 │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
```

### READ (GET by name)

```
CLIENT REQUEST:
┌─────────────────────────────────────────────────────────┐
│ GET /subscriptions/sub-001/resourceGroups/rg-1/         │
│     providers/ITL.Network/virtualNetworks/vnet-prod     │
└─────────────────────────────────────────────────────────┘
                         ↓
              SERVER RETURNS RESOURCE
                         ↓
SERVER RESPONSE:
┌─────────────────────────────────────────────────────────┐
│ Status: 200 OK                                          │
│                                                          │
│ Body: [Full resource object - same as CREATE]          │
└─────────────────────────────────────────────────────────┘
```

### LIST (GET collection)

```
CLIENT REQUEST:
┌─────────────────────────────────────────────────────────┐
│ GET /subscriptions/sub-001/resourceGroups/rg-1/         │
│     providers/ITL.Network/virtualNetworks               │
│                                                          │
│ (NO {name} at the end!)                                 │
└─────────────────────────────────────────────────────────┘
                         ↓
           SERVER RETURNS ALL MATCHING RESOURCES
                         ↓
SERVER RESPONSE:
┌─────────────────────────────────────────────────────────┐
│ Status: 200 OK                                          │
│                                                          │
│ Body:                                                    │
│ {                                                        │
│   "value": [                                            │
│     { "id": "...", "name": "vnet-prod", ... },         │
│     { "id": "...", "name": "vnet-staging", ... },      │
│     { "id": "...", "name": "vnet-dev", ... }           │
│   ],                                                    │
│   "next_link": null                                     │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
```

### DELETE

```
CLIENT REQUEST:
┌─────────────────────────────────────────────────────────┐
│ DELETE /subscriptions/sub-001/resourceGroups/rg-1/      │
│         providers/ITL.Network/virtualNetworks/          │
│                                              vnet-prod   │
└─────────────────────────────────────────────────────────┘
                         ↓
              SERVER DELETES RESOURCE
                         ↓
SERVER RESPONSE:
┌─────────────────────────────────────────────────────────┐
│ Status: 200 OK or 204 No Content                        │
│                                                          │
│ Body (optional):                                        │
│ {                                                        │
│   "status": "deleted",                                  │
│   "resource_id": "..."                                  │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
```

---

## Error Responses

```
ERROR CODES:

┌──────┬──────────────────┬─────────────────────────┐
│ Code │ Exception Class   │ Meaning                 │
├──────┼──────────────────┼─────────────────────────┤
│ 400  │ ValidationError   │ Invalid input           │
│ 403  │ AuthorizationErr. │ No permission           │
│ 404  │ ResourceNotFound  │ Resource doesn't exist  │
│ 409  │ ResourceExistsErr │ Already exists / conflict
│ 500  │ ConfigurationErr  │ Server configuration    │
│ 502  │ UpstreamService   │ Dependent service error │
│ 503  │ ServiceUnavailable│ Temporarily unavailable │
└──────┴──────────────────┴─────────────────────────┘

EXAMPLE 404 RESPONSE:

┌─────────────────────────────────────────────────────────┐
│ Status: 404 Not Found                                   │
│                                                          │
│ Body:                                                    │
│ {                                                        │
│   "error": {                                            │
│     "code": "ResourceNotFound",                         │
│     "message": "Virtual network 'vnet-xxx' not found"  │
│   }                                                     │
│ }                                                        │
└─────────────────────────────────────────────────────────┘

EXAMPLE 409 RESPONSE (already exists):

┌─────────────────────────────────────────────────────────┐
│ Status: 409 Conflict                                    │
│                                                          │
│ Body:                                                    │
│ {                                                        │
│   "error": {                                            │
│     "code": "ResourceAlreadyExists",                    │
│     "message": "Virtual network 'vnet-xxx' already exists"
│   }                                                     │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
```

---

## Complete Request/Response Lifecycle

```
USER ACTION                    HTTP REQUEST              SERVER                   RESPONSE
──────────────────────────────────────────────────────────────────────────────────────────

[User wants to             PUT /subscriptions/···/    1. Validate input      {"id": "...",
 create a virtual        /virtualNetworks/vnet-1     2. Check if exists     "name": "vnet-1",
 network]              + Request body               3. Create resource     "type": "ITL.Network
                                                     4. Store in DB         /virtualNetworks",
                                                     5. Return full obj     "location": "...",
                                                                           "properties": {...},
                                                     Status: 200 OK        "tags": {...}}
                         ────────────────────────────────────────────
                         
[User wants to             GET /subscriptions/···/    1. Check if exists     {"id": "...",
 read that virtual        /virtualNetworks/vnet-1    2. Retrieve from DB    "name": "vnet-1",
 network]                                             3. Return object       ...}
                                                     
                         Status: 200 OK
                         ────────────────────────────────────────────

[User wants to list        GET /subscriptions/···/    1. Query all in RG      {"value": [
 all virtual              /virtualNetworks           2. Filter by sub/rg     {"id": "...",
 networks in RG]                                     3. Return paginated     "name": "vnet-1", ...},
                                                                           {"id": "...",
                                                     Status: 200 OK        "name": "vnet-2", ...}
                                                                           ],
                                                                           "next_link": null}
                         ────────────────────────────────────────────

[User wants to             PUT /subscriptions/···/    1. Validate input      {"id": "...",
 update tags +             /virtualNetworks/vnet-1   2. Check if exists     "name": "vnet-1",
 DNS servers]            + Updated body              3. Update in DB        "tags": {...,
                                                     4. Return new obj      "cost-center": "..."},
                                                                           "properties": {
                                                     Status: 200 OK        "dns_servers": [...]}}
                         ────────────────────────────────────────────

[User wants to             DELETE /subscriptions/···/ 1. Check if exists      {"status": "deleted",
 delete the virtual       /virtualNetworks/vnet-1    2. Delete from DB      "resource_id": "..."}
 network]                                            3. Return confirmation
                                                     
                                                     Status: 200 OK
```

---

## State Transitions

```
RESOURCE LIFECYCLE:

┌─────────────┐
│  NOT EXIST  │
└──────┬──────┘
       │ PUT (create)
       ↓
┌──────────────────┐
│  CREATING        │  ← provisioningState = "Accepted"
└──────┬───────────┘
       │ (processing)
       ↓
┌──────────────────┐
│  PROCESSING      │  ← provisioningState = "Running"
└──────┬───────────┘
       │ (done)
       ↓
┌──────────────────┐
│  EXISTS          │  ← provisioningState = "Succeeded"
│  (can GET, LIST) │
└──────┬──────────────┬──────────────┐
       │ PUT(update)  │ DELETE       │ GET/LIST
       │              │              │
       ↓              ↓              ↓
   [UPDATING]    [DELETING]    [RETURNED]
       │              │              │
       ↓              ↓              ↓
   [EXISTS]      [NOT EXIST]   [EXISTS]
```

---

## Testing the Flow

```
STEP-BY-STEP TEST:

1. CREATE
   curl -X PUT http://localhost:8000/...virtualNetworks/test \
     -d '{"location":"westeurope", "properties":{...}, "tags":{}}'
   ✓ Should return 200-201
   ✓ Response should have "id", "name", "type", "location", "properties", "tags"

2. READ
   curl -X GET http://localhost:8000/...virtualNetworks/test
   ✓ Should return 200
   ✓ Response should match what was created

3. LIST
   curl -X GET http://localhost:8000/...virtualNetworks
   ✓ Should return 200
   ✓ Response should have "value" array with your resource

4. UPDATE
   curl -X PUT http://localhost:8000/...virtualNetworks/test \
     -d '{"location":"westeurope", "properties":{...}, "tags":{"new":"tag"}}'
   ✓ Should return 200
   ✓ Tags should be updated

5. DELETE
   curl -X DELETE http://localhost:8000/...virtualNetworks/test
   ✓ Should return 200

6. VERIFY DELETED
   curl -X GET http://localhost:8000/...virtualNetworks/test
   ✗ Should return 404 (not found)
```

---

## Key Takeaways

✅ **PUT = Create or Update (idempotent)**  
✅ **GET with {name} = Read single**  
✅ **GET without {name} = List all**  
✅ **DELETE = Remove resource**  
✅ **Always return complete resource object (except DELETE)**  
✅ **Always include id, name, type, location, properties, tags**  
✅ **provisioningState tells you the operation status**  
✅ **Error responses always have "error" object with "code" and "message"**  
✅ **Idempotent means: same request = same result = safe to retry**  

