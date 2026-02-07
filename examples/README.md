# Examples - ITL ControlPlane SDK

Production-ready examples organized by **resource type** and **difficulty level**, following Azure's resource provider model.

---

## Complete Index

### core/
| Level | File | Description |
|-------|------|-------------|
| — | [quickstart.py](core/quickstart.py) | Basic SDK concepts: registry, resource requests, CRUD |
| Intermediate | [resource_id_example.py](core/intermediate/resource_id_example.py) | ARM-style IDs, GUID-enhanced IDs, parsing, `ResourceIdentity` |
| Intermediate | [registry_example.py](core/intermediate/registry_example.py) | `ResourceProviderRegistry` with multi-provider registration, discovery, CRUD proxy |

### compute/
| Level | File | Description |
|-------|------|-------------|
| Intermediate | [big_3_examples.py](compute/intermediate/big_3_examples.py) | `VirtualMachineHandler` — Validation + Provisioning States + Timestamps |
| Advanced | [scoped_resource_examples.py](compute/advanced/scoped_resource_examples.py) | VM scoping patterns, resource group uniqueness |

### storage/
| Level | File | Description |
|-------|------|-------------|
| Intermediate | [big_3_examples.py](storage/intermediate/big_3_examples.py) | `StorageAccountHandler` — Big 3 with global uniqueness |
| Intermediate | [storage_account_example.py](storage/intermediate/storage_account_example.py) | Global scoping, schema validation, scope comparison (Global vs RG) |
| Advanced | [scoped_resource_examples.py](storage/advanced/scoped_resource_examples.py) | Advanced global scoping patterns |

### network/
| Level | File | Description |
|-------|------|-------------|
| Intermediate | [big_3_examples.py](network/intermediate/big_3_examples.py) | `NetworkInterfaceHandler` — Big 3 with resource group scoping |
| Advanced | [scoped_resource_examples.py](network/advanced/scoped_resource_examples.py) | Network scoping patterns |

### management/
| Level | File | Description |
|-------|------|-------------|
| Intermediate | [big_3_examples.py](management/intermediate/big_3_examples.py) | `PolicyHandler`, `DatabaseHandler` — Big 3 patterns |
| Intermediate | [resource_group_handler_example.py](management/intermediate/resource_group_handler_example.py) | `ResourceGroupHandler` — Big 3 + subscription scoping, schema validation, full CRUD |
| Advanced | [scoped_resource_examples.py](management/advanced/scoped_resource_examples.py) | `ManagementGroupHandler` scoping patterns |

### providers/
| Level | File | Description |
|-------|------|-------------|
| Intermediate | [custom_provider_example.py](providers/intermediate/custom_provider_example.py) | Custom `ResourceProvider` with actions, safety checks, registry integration |

### identity/
| Level | File | Description |
|-------|------|-------------|
| Beginner | [tenant_example.py](identity/beginner/tenant_example.py) | `TenantSpec`, validation, lifecycle states, multi-tenant setup |
| Beginner | [organization_example.py](identity/beginner/organization_example.py) | `OrganizationSpec`, admin users/roles, custom domains, DNS verification |
| Intermediate | [identity_provider_factory_example.py](identity/intermediate/identity_provider_factory_example.py) | `IdentityProviderFactory` — singleton, security, provider switching |

### fastapi/
| Level | File | Description |
|-------|------|-------------|
| Beginner | [app_factory_example.py](fastapi/beginner/app_factory_example.py) | `AppFactory`, `FastAPIConfig` presets, CORS, health routes, lifecycle events |
| Intermediate | [middleware_example.py](fastapi/intermediate/middleware_example.py) | `APIError`, `LoggingMiddleware`, exception handlers, error response format |

### deployment/
| Level | File | Description |
|-------|------|-------------|
| Intermediate | [pulumi_deployment_example.py](deployment/intermediate/pulumi_deployment_example.py) | Pulumi IaC — multi-environment deploy (dev, staging, production) |

### tests/
| Level | File | Description |
|-------|------|-------------|
| Unit | [test_itl_locations.py](tests/unit/test_itl_locations.py) | Location validation testing (27 regions) |
| Integration | [test_resource_group_big_3.py](tests/integration/test_resource_group_big_3.py) | Handler testing patterns for `ResourceGroupHandler` |

---

## Getting Started

### 1. Run Quickstart (5 minutes)
```bash
python core/quickstart.py
```
Learn basic SDK concepts: registry, resource requests, CRUD operations.

### 2. Explore Resource Types
Choose any resource type folder to see practical examples:

**For Compute:**
```bash
python compute/intermediate/big_3_examples.py
```
See VirtualMachineHandler with validation, state management, and timestamps.

**For Storage:**
```bash
python storage/intermediate/big_3_examples.py
```
See StorageAccountHandler with global uniqueness scoping.

**For Network:**
```bash
python network/intermediate/big_3_examples.py
```
See NetworkInterfaceHandler with resource group scoping.

**For Management:**
```bash
python management/intermediate/big_3_examples.py
```
See PolicyHandler, DatabaseHandler, and ManagementGroupHandler patterns.

### 3. Identity & FastAPI
```bash
python identity/beginner/tenant_example.py
python identity/beginner/organization_example.py
python fastapi/beginner/app_factory_example.py
```
Explore multi-tenant identity models and the FastAPI application factory.

### 4. Advanced Patterns
```bash
python compute/advanced/scoped_resource_examples.py
python providers/intermediate/custom_provider_example.py
python management/intermediate/resource_group_handler_example.py
```
Deep dive into resource scoping, custom providers, and the ResourceGroup reference handler.

### 5. Deploy with Pulumi
```bash
python deployment/intermediate/pulumi_deployment_example.py
```
Deploy infrastructure across dev, staging, and production environments.

### 6. Run Tests
```bash
python tests/unit/test_itl_locations.py
python tests/integration/test_resource_group_big_3.py
```
Learn testing patterns and location validation.

## Learning Paths

### Path 1: Learn Core SDK (20 min)
1. [core/quickstart.py](core/quickstart.py) — Registry basics
2. [core/intermediate/resource_id_example.py](core/intermediate/resource_id_example.py) — Resource ID generation & parsing
3. [core/intermediate/registry_example.py](core/intermediate/registry_example.py) — Provider registry patterns
4. [tests/unit/test_itl_locations.py](tests/unit/test_itl_locations.py) — Location validation

### Path 2: Learn Handler Patterns (1 hour)
1. [core/quickstart.py](core/quickstart.py) — Basics
2. [compute/intermediate/big_3_examples.py](compute/intermediate/big_3_examples.py) — Validation + State + Timestamps
3. [storage/intermediate/big_3_examples.py](storage/intermediate/big_3_examples.py) — Global scoping
4. [network/intermediate/big_3_examples.py](network/intermediate/big_3_examples.py) — RG scoping
5. [management/intermediate/resource_group_handler_example.py](management/intermediate/resource_group_handler_example.py) — Full Big 3 + scoping reference

### Path 3: Learn Resource Scoping (1.5 hours)
1. All big_3_examples.py files (see path 2)
2. [storage/intermediate/storage_account_example.py](storage/intermediate/storage_account_example.py) — Global vs RG scope comparison
3. [compute/advanced/scoped_resource_examples.py](compute/advanced/scoped_resource_examples.py) — Scoping patterns
4. [management/advanced/scoped_resource_examples.py](management/advanced/scoped_resource_examples.py) — MG scoping
5. [tests/integration/test_resource_group_big_3.py](tests/integration/test_resource_group_big_3.py) — Scope testing

### Path 4: Learn Identity (45 min)
1. [identity/beginner/tenant_example.py](identity/beginner/tenant_example.py) — Tenant lifecycle
2. [identity/beginner/organization_example.py](identity/beginner/organization_example.py) — Organizations & domains
3. [identity/intermediate/identity_provider_factory_example.py](identity/intermediate/identity_provider_factory_example.py) — Provider factory & singleton

### Path 5: Build APIs with FastAPI (30 min)
1. [fastapi/beginner/app_factory_example.py](fastapi/beginner/app_factory_example.py) — App factory & config
2. [fastapi/intermediate/middleware_example.py](fastapi/intermediate/middleware_example.py) — Logging & error handling
3. [providers/intermediate/custom_provider_example.py](providers/intermediate/custom_provider_example.py) — Wire providers into APIs

### Path 6: Deploy Infrastructure (1 hour)
1. [core/quickstart.py](core/quickstart.py) — Basics
2. [deployment/intermediate/pulumi_deployment_example.py](deployment/intermediate/pulumi_deployment_example.py) — Multi-env deployment

## Key Concepts

### The Big 3 Handler Patterns

**1. Validation (Pydantic)**
```python
class VirtualMachineSchema(BaseModel):
    vm_name: str = Field(..., description="Name")
    size: str = Field(..., description="Size")
    
    @validator('vm_name')
    def validate_vm_name(cls, v):
        # Custom validation logic
        return v

class VirtualMachineHandler(ValidatedResourceHandler, ...):
    SCHEMA_CLASS = VirtualMachineSchema
```

**2. Provisioning States**
```python
class VirtualMachineHandler(ProvisioningStateHandler, ...):
    # Automatically tracks: Creating → Succeeded → Deleting → Deleted
    # Check state: config['provisioning_state']
    # Check history: handler.get_state_history(resource_id)
```

**3. Timestamps**
```python
class VirtualMachineHandler(TimestampedResourceHandler, ...):
    # Automatically adds:
    # - createdTime: ISO 8601 UTC timestamp
    # - createdBy: User who created
    # - modifiedTime: Last modification timestamp
    # - modifiedBy: User who last modified
```

### Resource Scoping

Different resources have different uniqueness boundaries:

```python
# Subscription scope
UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
# → Unique within subscription

# Subscription + Resource Group scope (most common)
UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
# → Unique within RG, can reuse name in different RG

# Global scope (globally unique)
UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
# → Must be unique across entire system

# Management Group scope
UNIQUENESS_SCOPE = [UniquenessScope.MANAGEMENT_GROUP]
# → Unique within MG, can reuse in different MG
```

## File Organization

```
examples/
├── README.md                                          # This file
│
├── core/
│   ├── quickstart.py                                  # Basic registry + CRUD
│   └── intermediate/
│       ├── resource_id_example.py                     # ARM IDs, GUIDs, parsing
│       └── registry_example.py                        # Provider registry patterns
│
├── compute/
│   ├── intermediate/
│   │   └── big_3_examples.py                          # VirtualMachineHandler
│   └── advanced/
│       └── scoped_resource_examples.py                # VM scoping patterns
│
├── storage/
│   ├── intermediate/
│   │   ├── big_3_examples.py                          # StorageAccountHandler (global)
│   │   └── storage_account_example.py                 # Global scope deep dive
│   └── advanced/
│       └── scoped_resource_examples.py                # Global scoping patterns
│
├── network/
│   ├── intermediate/
│   │   └── big_3_examples.py                          # NetworkInterfaceHandler
│   └── advanced/
│       └── scoped_resource_examples.py                # Network scoping patterns
│
├── management/
│   ├── intermediate/
│   │   ├── big_3_examples.py                          # PolicyHandler, DatabaseHandler
│   │   └── resource_group_handler_example.py          # ResourceGroupHandler (Big 3 ref)
│   └── advanced/
│       └── scoped_resource_examples.py                # ManagementGroupHandler
│
├── providers/
│   └── intermediate/
│       └── custom_provider_example.py                 # Custom ResourceProvider
│
├── identity/
│   ├── beginner/
│   │   ├── tenant_example.py                          # Tenant lifecycle
│   │   └── organization_example.py                    # Orgs, domains, admin users
│   └── intermediate/
│       └── identity_provider_factory_example.py       # Factory, singleton, switching
│
├── fastapi/
│   ├── beginner/
│   │   └── app_factory_example.py                     # AppFactory, config presets
│   └── intermediate/
│       └── middleware_example.py                      # Logging, error handling
│
├── deployment/
│   └── intermediate/
│       └── pulumi_deployment_example.py               # Pulumi multi-env IaC
│
└── tests/
    ├── unit/
    │   └── test_itl_locations.py                      # Location validation
    └── integration/
        └── test_resource_group_big_3.py               # Handler testing patterns
```

**Total: 20 example files** across 10 categories and 3 difficulty levels.

## Running Examples

### Prerequisites
```bash
# Install SDK in editable mode
cd ..
pip install -e .
```

### Run specific example
```bash
# From examples folder
python core/quickstart.py
python core/intermediate/resource_id_example.py
python core/intermediate/registry_example.py
python compute/intermediate/big_3_examples.py
python storage/intermediate/storage_account_example.py
python identity/beginner/tenant_example.py
python fastapi/beginner/app_factory_example.py
python management/intermediate/resource_group_handler_example.py
python providers/intermediate/custom_provider_example.py
python deployment/intermediate/pulumi_deployment_example.py
```

### Run tests
```bash
python tests/unit/test_itl_locations.py
python tests/integration/test_resource_group_big_3.py
```

## Quick Reference

### Resource Handler Base Classes
```python
from itl_controlplane_sdk.providers import (
    ResourceProvider,              # Base class for all providers
    ValidatedResourceHandler,      # Pydantic validation
    ProvisioningStateHandler,      # State lifecycle management
    TimestampedResourceHandler,    # Audit timestamps
    ScopedResourceHandler,         # Uniqueness scoping
    UniquenessScope                # Scope enumeration
)
```

### SDK Classes
```python
from itl_controlplane_sdk import (
    ResourceProviderRegistry,      # Central registry
    ResourceProvider,              # Provider base
    ResourceRequest,               # Request object
    ProvisioningState              # State enum
)
```

### Identity Classes
```python
from itl_controlplane_sdk.identity.tenant import (
    TenantSpec, Tenant, TenantStatus, TenantResponse
)
from itl_controlplane_sdk.identity.organization import (
    OrganizationSpec, TenantAdminUser, CustomDomain
)
from itl_controlplane_sdk.identity.identity_provider_factory import (
    IdentityProviderFactory, get_factory, register_provider
)
```

### FastAPI Classes
```python
from itl_controlplane_sdk.fastapi.app_factory import AppFactory
from itl_controlplane_sdk.fastapi.config import FastAPIConfig
from itl_controlplane_sdk.fastapi.middleware.error_handling import (
    APIError, setup_exception_handlers
)
from itl_controlplane_sdk.fastapi.middleware.logging import LoggingMiddleware
```

### Resource IDs
```python
from itl_controlplane_sdk.providers.resource_ids import (
    generate_resource_id,          # Create ARM-style IDs
    parse_resource_id,             # Parse IDs into components
    ResourceIdentity               # Dual ID (ARM path + GUID)
)
```

### Location Validation
```python
from itl_controlplane_sdk.providers.itl_locations import (
    ITLLocationsHandler,           # Location validator (27 locations)
    ITLRegionMeta                  # Region classification
)
```

## Troubleshooting

**Import errors?**
Make sure SDK is installed in editable mode:
```bash
pip install -e ../..
```

**Can't run tests?**
Install pytest:
```bash
pip install pytest
```

**Looking for Pulumi examples?**
Install Pulumi:
```bash
pip install pulumi>=3.0.0
```

## Next Steps

1. **Choose a resource type** and read its README
2. **Run the examples** in that folder
3. **Study the code** to understand patterns
4. **Create your own handler** using the patterns
5. **Test it** using provided test patterns

## Contributing Examples

To add new examples:
1. Create files in the appropriate `category/level/` folder
2. Follow naming: `{feature}_example.py`
3. Add docstring explaining what it demonstrates
4. Update this README index with the new file
5. Include numbered examples with clear output
6. Add running instructions

## Additional Resources

- **SDK Documentation**: See `/docs/` folder
- **API Reference**: See `.project/platform/` documentation
- **Pulumi Documentation**: See `.project/pulumi/` planning documents
- **Architecture**: See `.project/platform/DOCUMENTATION_GAP_ANALYSIS.md`
