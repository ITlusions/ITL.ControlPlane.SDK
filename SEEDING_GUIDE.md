# Database Seeding Guide

This guide explains how to populate the ControlPlane database with default data (locations, tenants, policies, etc.).

## Overview

The SDK provides seed functions to initialize the database with commonly needed default data. All seed functions are **idempotent** - they safely check for existing data before creating new records, so they can be called multiple times without side effects.

## Available Seeds

### 1. **Locations** (`seed_locations`)
- **Purpose**: Populate available cloud regions and extended locations (edge zones)
- **Includes**: 18 standard Azure regions + 6 extended locations (CDN edge zones)
- **Source**: `DEFAULT_LOCATIONS` constant from `itl_controlplane_sdk.core.models.base.constants`
- **Tables**: `locations`, `extended_locations`

### 2. **Default Tenant** (`seed_default_tenant`)
- **Purpose**: Create the default "ITL" tenant for resource scoping
- **ID**: `ITL` (from `DEFAULT_TENANT`)
- **Table**: `tenants`
- **Required before**: Other seeds that need tenant_id

### 3. **Management Groups** (`seed_default_management_groups`)
- **Purpose**: Create standard management group hierarchy
- **Includes**:
  - Root
  - Infrastructure
  - Workloads
  - Platform
- **Table**: `management_groups`
- **Requires**: Default tenant to exist

### 4. **Policies** (`seed_default_policies`)
- **Purpose**: Create foundational governance policies
- **Includes**:
  - Enforce Encryption at Rest
  - Require RBAC
  - Enforce Resource Tagging
  - Audit Logging
- **Table**: `policies`
- **Requires**: Default tenant to exist

## Usage

### From Python Code

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from itl_controlplane_sdk.core.services.seed import SeedService

# Create async database session
database_url = "postgresql+asyncpg://user:pass@localhost/dbname"
engine = create_async_engine(database_url)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async with async_session() as session:
    # Seed all data
    results = await SeedService.seed_all(session)
    
    # Or seed individual components
    await SeedService.seed_default_tenant(session)
    await SeedService.seed_locations(session)
    await SeedService.seed_default_management_groups(session)
    await SeedService.seed_default_policies(session)
```

### From CLI

```bash
# Seed all data at once
python -m itl_controlplane_sdk.cli.seed all

# Seed individual components
python -m itl_controlplane_sdk.cli.seed tenants
python -m itl_controlplane_sdk.cli.seed locations
python -m itl_controlplane_sdk.cli.seed management-groups
python -m itl_controlplane_sdk.cli.seed policies

# With custom options
python -m itl_controlplane_sdk.cli.seed \
  --database-url postgresql+asyncpg://user:pass@localhost/dbname \
  --tenant-id MyTenant \
  all
```

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
  - Default: `postgresql+asyncpg://controlplane:controlplane@localhost:5432/controlplane`
- Tenant ID: Hard-coded to `ITL` (DEFAULT_TENANT_ID)

### Return Values

All seed functions return a dictionary with operation status:

```python
{
    "created": 18,          # Number of new records created
    "skipped": 6,           # Number of existing records (not duplicated)
    "total": 24             # Total records processed
}
```

## Execution Order

Seed functions should be called in this order (dependencies):

1. **Tenant** → Creates default tenant (other seeds depend on this)
2. **Locations** → Independent, can run anytime
3. **Management Groups** → Depends on tenant
4. **Policies** → Depends on tenant

The `seed_all()` function handles this ordering automatically.

## Integration Examples

### In Provider Initialization

```python
# In Core Provider startup
from itl_controlplane_sdk.core.services.seed import SeedService

async def startup():
    # Initialize database first
    await alembic_upgrade()
    
    # Then seed with defaults
    async with get_session() as session:
        results = await SeedService.seed_all(session)
        logger.info(f"Database seeded: {results}")
    
    # Then start provider services
    await start_services()
```

### In Migration Hooks

```python
# In alembic env.py after migrations
def run_migrations_online() -> None:
    # ... existing migration code ...
    
    with connectable.begin() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        
        with context.begin_transaction():
            context.run_migrations()
        
        # Seed defaults after migrations
        if environment == "development":
            asyncio.run(seed_defaults(connection))
```

### In Docker Entrypoint

```bash
#!/bin/bash
set -e

# Run migrations
alembic upgrade head

# Seed initial data
python -m itl_controlplane_sdk.cli.seed all

# Start services
python -m provider.main
```

## Data Consistency

All seed functions maintain data consistency:

- **Idempotency**: Check record existence before insert
- **Foreign Keys**: Respect all FK constraints
- **Transactions**: Commit atomically or rollback on error
- **Timestamps**: Set created_at and updated_at

## Example Output

```
INFO - Starting database seed process...
INFO - ✓ Created default tenant: ITL
INFO - ✓ Seeded 24 locations (0 already existed)
INFO - ✓ Seeded 4 management groups (0 already existed)
INFO - ✓ Seeded 4 policies (0 already existed)
INFO - ✓ Database seeding completed successfully

Database seed results:
  tenant: {'created': 1, 'skipped': 0}
  locations: {'created': 24, 'skipped': 0, 'total': 24}
  management_groups: {'created': 4, 'skipped': 0}
  policies: {'created': 4, 'skipped': 0}
```

## Troubleshooting

### Connection Issues

```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.CannotConnectNowError)
```

**Solution**: Ensure PostgreSQL is running and DATABASE_URL is correct:

```bash
# Test connection
python -c "import asyncpg; asyncio.run(asyncpg.connect('postgresql://...'))"
```

### Foreign Key Violations

```
sqlalchemy.exc.IntegrityError: (asyncpg.exceptions.IntegrityConstraintViolationError)
FOREIGN KEY violation
```

**Solution**: Ensure tenant exists before seeding other data. Use `seed_all()` which handles ordering.

### Already Exists Errors

Seed functions check for existing records and skip them. No error should occur on second run.

## Summary

| Seed Function | Records | Depends On | Purpose |
|---|---|---|---|
| `seed_default_tenant` | 1 tenant | - | Create default "ITL" tenant |
| `seed_locations` | 24 locations | - | Populate available regions/zones |
| `seed_management_groups` | 4 groups | Tenant | Create default MG hierarchy |
| `seed_default_policies` | 4 policies | Tenant | Create baseline governance policies |

Use `seed_all()` to run all seeds in correct order with proper dependency handling.
