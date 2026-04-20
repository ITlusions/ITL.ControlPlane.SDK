# Data Modeling and Schema Design

Guide to designing resource schemas and data models for the ITL ControlPlane.

---

## Resource Schema Fundamentals

### Base Resource Structure

Every resource must have this structure:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class ResourceBase(BaseModel):
    """Base model for all resources"""
    
    # Required for all resources
    id: str = Field(..., description="Fully qualified resource ID")
    name: str = Field(..., description="Resource name")
    type: str = Field(..., description="Resource type (provider/resourceType)")
    location: str = Field(..., description="Azure region")
    
    # Optional but recommended
    provisioning_state: Optional[str] = Field(
        default="Succeeded",
        description="State: Accepted, Provisioning, Succeeded, Failed"
    )
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Common metadata
    tags: Dict[str, str] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)
```

---

## Defining Resource Properties

### Use Pydantic for Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum

class VMSize(str, Enum):
    SMALL = "Standard_B2s"
    MEDIUM = "Standard_D2s_v3"
    LARGE = "Standard_D4s_v3"

class VirtualMachineProperties(BaseModel):
    """Properties specific to VMs"""
    
    size: VMSize = Field(
        ...,
        description="VM size",
        example="Standard_D2s_v3"
    )
    
    image: str = Field(
        ...,
        description="OS image",
        example="Ubuntu20.04"
    )
    
    os_disk_size_gb: Optional[int] = Field(
        default=128,
        ge=32,  # Greater than or equal
        le=4096,  # Less than or equal
        description="OS disk size in GB"
    )
    
    data_disks: Optional[List[int]] = Field(
        default=[],
        max_items=16,
        description="Data disk sizes in GB"
    )
    
    public_ip_enabled: bool = Field(
        default=False,
        description="Whether to assign public IP"
    )
    
    @validator('image')
    def image_format_valid(cls, v):
        valid_images = ["Ubuntu20.04", "Windows2019", "CentOS8"]
        if v not in valid_images:
            raise ValueError(f"Image must be one of {valid_images}")
        return v
```

### Custom Validators

```python
from pydantic import validator, root_validator

class ResourceProperties(BaseModel):
    min_size: int
    max_size: int
    
    @root_validator
    def validate_sizes(cls, values):
        min_size = values.get('min_size')
        max_size = values.get('max_size')
        
        if min_size > max_size:
            raise ValueError("min_size cannot be greater than max_size")
        
        return values

class ResourceName(BaseModel):
    name: str
    
    @validator('name')
    def name_length(cls, v):
        if len(v) < 3 or len(v) > 80:
            raise ValueError("Name must be 3-80 characters")
        return v
    
    @validator('name')
    def name_format(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9-]+$', v):
            raise ValueError("Name must contain only alphanumeric and hyphens")
        return v
```

---

## Nested Objects

### Parent-Child Relationships

```python
class StorageAccount(BaseModel):
    name: str
    tier: str  # Standard, Premium
    replication: str  # GRS, LRS, etc

class DatabaseProperties(BaseModel):
    name: str
    engine: str  # PostgreSQL, MySQL, etc
    version: str
    storage: StorageAccount  # Nested object
    replicas: Optional[List[StorageAccount]] = []
```

### Flattened vs Nested

```python
# Option 1: Flattened (easier to query)
class FlatVM(BaseModel):
    name: str
    disk_0_size: int
    disk_0_type: str
    disk_1_size: int
    disk_1_type: str

# Option 2: Nested (more structured)
class Disk(BaseModel):
    size: int
    type: str

class NestedVM(BaseModel):
    name: str
    disks: List[Disk]

# Recommendation: Use nested for clarity, flatten only when necessary for performance
```

---

## Relationships Between Resources

### Direct References

```python
class VMProperties(BaseModel):
    size: str
    network_interface_id: str  # Reference to network interface
    storage_account_id: str     # Reference to storage

# Usage
vm_request = ResourceRequest(
    resource_type="virtualmachines",
    resource_name="vm-001",
    properties={
        "size": "Standard_D2s_v3",
        "network_interface_id": "/subscriptions/.../networkInterfaces/nic-001",
        "storage_account_id": "/subscriptions/.../storageAccounts/storage001"
    }
)
```

### Parent-Child Relationships

```python
# NetworkInterface is a child of VirtualNetwork
# Naming convention includes parent

class NetworkInterface(BaseModel):
    # Virtual network this belongs to
    vnet_id: str
    subnet_id: str

# In API
PUT /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks/vnet-001
PUT /subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Network/virtualNetworks/vnet-001/networkInterfaces/nic-001
```

---

## Choosing Storage

### In-Memory Storage (Development Only)

```python
class DevProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.Dev")
        self.resources = {}  # Simple dict
```

**Pros:** Simple, fast  
**Cons:** Lost on restart, not scalable

---

### Relational Database (PostgreSQL)

```python
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ResourceModel(Base):
    __tablename__ = "resources"
    
    id = Column(String, primary_key=True)
    subscription_id = Column(String, index=True)
    resource_group = Column(String, index=True)
    resource_name = Column(String, index=True)
    resource_type = Column(String)
    "location = Column(String)
    provisioning_state = Column(String, index=True)
    properties = Column(JSON)
    tags = Column(JSON)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

# Usage
async def create_or_update_resource(self, request):
    resource = ResourceModel(
        id=resource_id,
        subscription_id=request.subscription_id,
        resource_group=request.resource_group,
        resource_name=request.resource_name,
        properties=request.properties,
        tags=request.tags
    )
    
    async with AsyncSession(self.engine) as session:
        session.add(resource)
        await session.commit()
```

**Pros:** ACID transactions, reliable, mature  
**Cons:** More setup required

---

### Document Database (MongoDB)

```python
from motor.motor_asyncio import AsyncMongoClient
from pymongo import ASCENDING

class DocumentProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.Documents")
        self.client = AsyncMongoClient("mongodb://localhost:27017")
        self.db = self.client["itl_resources"]
        self.collection = self.db["resources"]
    
    async def initialize(self):
        """Create indexes"""
        await self.collection.create_index([("subscription_id", ASCENDING)])
        await self.collection.create_index([("resource_group", ASCENDING)])
    
    async def create_or_update_resource(self, request):
        resource = {
            "_id": resource_id,
            "subscription_id": request.subscription_id,
            "properties": request.properties,
            "tags": request.tags
        }
        
        await self.collection.update_one(
            {"_id": resource_id},
            {"$set": resource},
            upsert=True
        )
```

**Pros:** Flexible schema, easy scaling  
**Cons:** Eventually consistent, larger storage needs

---

### Graph Database (Neo4j)

```python
from neo4j import AsyncGraphDatabase

class GraphProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.Graph")
        self.driver = AsyncGraphDatabase.driver(
            "neo4j://localhost:7687",
            auth=("neo4j", "password")
        )
    
    async def create_or_update_resource(self, request):
        async with self.driver.session() as session:
            # Create resource node and relationships
            await session.run("""
                CREATE (r:Resource {
                    id: $id,
                    name: $name,
                    type: $type
                })
                -[:IN_SUBSCRIPTION]-> (s:Subscription {id: $sub_id})
                -[:IN_RESOURCE_GROUP]-> (rg:ResourceGroup {id: $rg_id})
            """, {
                "id": resource_id,
                "name": request.resource_name,
                "type": request.resource_type,
                "sub_id": request.subscription_id,
                "rg_id": request.resource_group
            })
```

**Pros:** Excellent for relationships and traversal  
**Cons:** Specialized use case

---

## Migration Strategy

### Versioning Schema

```python
class ResourceV1(BaseModel):
    name: str
    size: str

class ResourceV2(BaseModel):
    name: str
    size: str
    region: str  # New field

# Support both versions
async def create_or_update_resource(self, request):
    schema_version = request.headers.get("X-Schema-Version", "v1")
    
    if schema_version == "v2":
        properties = ResourceV2(**request.properties)
    else:
        properties = ResourceV1(**request.properties)
        # Add default for new field
        properties = ResourceV2(**properties.dict(), region="us-east-1")
    
    return await self._create(properties)
```

### Database Migration Steps

```bash
# 1. Create migration file
alembic revision --autogenerate -m "Add region field"

# 2. Review generated migration
# migrations/versions/xxx_add_region_field.py

# 3. Test migration
alembic upgrade head
alembic downgrade base
alembic upgrade head

# 4. Apply in production
alembic upgrade head
```

---

## Query Patterns

### Simple Lookup by ID

```python
async def get_resource(self, request):
    async with AsyncSession(self.engine) as session:
        stmt = select(ResourceModel).where(ResourceModel.id == resource_id)
        resource = await session.scalar(stmt)
        return resource
```

### Filter and Sort

```python
async def list_resources(self, request):
    async with AsyncSession(self.engine) as session:
        stmt = select(ResourceModel).where(
            ResourceModel.subscription_id == sub_id,
            ResourceModel.resource_group == rg_name
        ).order_by(ResourceModel.created_at.desc()).limit(20)
        
        resources = await session.scalars(stmt)
        return resources.all()
```

### Join Related Resources

```python
from sqlalchemy import ForeignKey, relationship

class VirtualNetworkModel(Base):
    __tablename__ = "virtual_networks"
    id = Column(String, primary_key=True)
    name = Column(String)

class NetworkInterfaceModel(Base):
    __tablename__ = "network_interfaces"
    id = Column(String, primary_key=True)
    vnet_id = Column(String, ForeignKey("virtual_networks.id"))
    vnet = relationship("VirtualNetworkModel")

# Query with join
async def get_nic_with_vnet(self, nic_id):
    stmt = select(NetworkInterfaceModel).where(
        NetworkInterfaceModel.id == nic_id
    )
    nic = await session.scalar(stmt)
    # Access related vnet
    vnet = nic.vnet
```

---

## Best Practices

 **Use Pydantic** - Validate all input data  
 **Index common queries** - Fast lookups  
 **Version schemes early** - Easier evolution  
 **Normalize relationships** - Avoid duplication  
 **Document schema changes** - Future developers  
 **Test migrations** - Prevent data loss  
 **Use appropriate database** - Match requirements  
 **Plan for scale** - From day one  

---

## Related Documentation

- [03-CORE_CONCEPTS.md](../architecture/core-concepts.md) - Scoped handlers
- [06-HANDLER_MIXINS.md](../features/handler-mixins.md) - Handler features
- [13-DEPLOYMENT.md](deployment.md) - Database setup
- [17-REST_API_REFERENCE.md](rest-api-reference.md) - API contracts

---

Well-designed schemas are the foundation for reliable, scalable providers.
