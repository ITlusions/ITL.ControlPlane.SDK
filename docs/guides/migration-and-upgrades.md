# Migration and Upgrade Guide

Managing schema evolution, SDK updates, and version transitions.

---

## SDK Version Management

### Check Your Version

```bash
# See installed SDK version
pip show itl-controlplane-sdk

# Check latest available
pip index versions itl-controlplane-sdk

# See what changed
https://github.com/ITL/controlplane-sdk/releases
```

---

## Upgrading the SDK

### Minor Version Upgrade (1.2.3 -> 1.3.0)

Backward compatible - safe to upgrade without code changes.

```bash
# Upgrade
pip install --upgrade itl-controlplane-sdk

# Restart provider
docker-compose restart provider

# Verify health
curl http://localhost:8000/health
```

**What might change:**
-  New methods added
-  New optional parameters
-  Bug fixes
-  Performance improvements

**What won't change:**
-  Method signatures
-  Error types
-  Required parameters

---

### Major Version Upgrade (1.0.0 -> 2.0.0)

May have breaking changes - review release notes carefully.

**Before upgrading:**

1. Read release notes
2. Check migration guide
3. Review deprecated APIs
4. Update code as needed
5. Test thoroughly

**Example breaking change:**

```python
# SDK 1.0 - old way
from itl_controlplane_sdk import ResourceProvider
provider = ResourceProvider("ITL.MyProvider")

# SDK 2.0 - new way
from itl_controlplane_sdk.v2 import ResourceProvider
provider = ResourceProvider(namespace="ITL.MyProvider")
```

**Migration steps:**

```bash
# 1. Update SDK
pip install itl-controlplane-sdk==2.0.0

# 2. Update imports in code
# See migration guide for changes

# 3. Run tests
pytest tests/

# 4. Deploy to staging
docker build -t my-provider:staging .
docker run -p 8000:8000 my-provider:staging

# 5. Test endpoints
curl http://localhost:8000/health

# 6. Deploy to production
docker tag my-provider:staging my-provider:2.0.0
# Push and deploy...
```

---

## Database Schema Migrations

### Setup Alembic

```bash
# Initialize Alembic in project
alembic init migrations

# Configure database
# Edit migrations/env.py
# Set sqlalchemy.url or use environment variable
```

### Create Migrations

```bash
# Auto-detect model changes
alembic revision --autogenerate -m "Add region field to resources"

# Review generated migration file
# migrations/versions/001_add_region_field.py
```

### Migration File Example

```python
# migrations/versions/001_add_region_field.py
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add new column
    op.add_column('resources', sa.Column('region', sa.String(), nullable=True))
    # Create index
    op.create_index('ix_resources_region', 'resources', ['region'])

def downgrade():
    # Drop index
    op.drop_index('ix_resources_region', table_name='resources')
    # Drop column
    op.drop_column('resources', 'region')
```

### Apply Migrations

```bash
# Apply latest migrations
alembic upgrade head

# Apply specific revision
alembic upgrade 0001

# Rollback one revision
alembic downgrade -1

# List migration history
alembic history

# Current version
alembic current
```

---

## Resource Schema Versioning

### Support Multiple Schema Versions

```python
from pydantic import BaseModel, validator
from typing import Optional

# Old schema
class ResourcePropertiesV1(BaseModel):
    name: str
    size: str

# New schema - all old fields + new ones
class ResourcePropertiesV2(BaseModel):
    name: str
    size: str
    region: str  # New required field

class MyProvider(ResourceProvider):
    async def create_or_update_resource(self, request):
        schema_version = self._detect_schema_version(request.properties)
        
        if schema_version == 1:
            # Convert V1 to V2
            properties = ResourcePropertiesV1(**request.properties)
            v2_properties = ResourcePropertiesV2(
                **properties.dict(),
                region="us-east-1"  # Default for old clients
            )
        else:
            v2_properties = ResourcePropertiesV2(**request.properties)
        
        return await self._create(v2_properties)
    
    def _detect_schema_version(self, properties) -> int:
        # If 'region' present, it's V2
        return 2 if 'region' in properties else 1
```

### Deprecation Timeline

```python
import warnings

class MyProvider(ResourceProvider):
    async def create_or_update_resource(self, request):
        schema_version = self._detect_schema_version(request.properties)
        
        if schema_version == 1:
            warnings.warn(
                "Resource schema V1 is deprecated. "
                "Please migrate to V2 by adding 'region' field. "
                "V1 will be removed in SDK 3.0 (Feb 2025)",
                DeprecationWarning,
                stacklevel=2
            )
            # ... convert V1 to V2 ...
```

**Deprecation steps:**

1. **Month 1-2**: Announce deprecation, allow both versions
2. **Month 3-4**: Log warnings for old schema use
3. **Month 5-6**: Encourage migration with documentation
4. **Month 7+**: Remove support for old schema

---

## Data Migrations

### Migrate Existing Resources

```python
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

async def migrate_data():
    """Migrate existing resources to new schema"""
    engine = create_async_engine("postgresql+asyncpg://...")
    
    async with AsyncSession(engine) as session:
        # Get all resources
        resources = await session.execute(
            "SELECT * FROM resources"
        )
        
        for resource in resources:
            # Update resource with new schema
            resource.region = "us-east-1"  # Default value
            
            await session.merge(resource)
        
        await session.commit()

# Run migration
asyncio.run(migrate_data())
```

### Create Migration Script

```python
# scripts/migrate_to_v2.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, update
from my_provider.models import ResourceModel

async def main():
    engine = create_async_engine("postgresql+asyncpg://...")
    
    async with AsyncSession(engine) as session:
        # Get all resources
        stmt = select(ResourceModel)
        resources = await session.scalars(stmt)
        
        migrated = 0
        for resource in resources:
            # Add default value for new field
            if resource.region is None:
                resource.region = "us-east-1"
                await session.merge(resource)
                migrated += 1
        
        await session.commit()
        print(f"Migrated {migrated} resources")

if __name__ == "__main__":
    asyncio.run(main())
```

### Run Safely

```bash
# 1. Backup database
pg_dump production_db > backup.sql

# 2. Test on staging
python scripts/migrate_to_v2.py --dry-run
python scripts/migrate_to_v2.py --database=staging_db

# 3. Verify
psql staging_db -c "SELECT COUNT(DISTINCT region) FROM resources;"

# 4. Run on production during maintenance window
python scripts/migrate_to_v2.py --database=production_db

# 5. Verify production
psql production_db -c "SELECT COUNT(DISTINCT region) FROM resources;"

# 6. Restore backup if needed
psql production_db < backup.sql
```

---

## Zero-Downtime Deployments

### Blue-Green Strategy

```bash
# Current production: "blue" (v1.2.3)
# New version: "green" (v1.3.0)

# Step 1: Deploy green alongside blue
docker run -d --name provider-green \
  -p 8001:8000 \
  my-provider:v1.3.0

# Step 2: Health check green
curl http://localhost:8001/health
curl -X PUT \
  http://localhost:8001/subscriptions/.../create \
  -H "Content-Type: application/json" \
  -d '{"properties": {}}'

# Step 3: Run smoke tests on green
pytest tests/e2e/ --provider-url=http://localhost:8001

# Step 4: Switch traffic to green
# Update API Gateway configuration
# Change provider URL from :8000 to :8001

# Step 5: Keep blue running for rollback
docker kill provider-blue  # Later, after monitoring

# Step 6: Monitor for issues
# If problems: switch back to blue immediately
```

### Canary Deployment

```yaml
# Route small % of traffic to new version
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: my-provider
spec:
  hosts:
  - my-provider
  http:
  - route:
    - destination:
        host: my-provider-v1
        subset: v1
      weight: 95
    - destination:
        host: my-provider-v2
        subset: v2
      weight: 5
```

**Steps:**

1. Deploy v2 to 5% traffic
2. Monitor metrics for 30 minutes
3. Increase to 25% if healthy
4. Increase to 50% if healthy
5. Roll out 100% if healthy
6. Rollback immediately if issues detected

---

## Breaking Changes

### What Constitutes Breaking Change

```python
# BREAKING: Method signature changed
# OLD: async def create(self, request)
# NEW: async def create(self, request, force=False)
# Problem: callers won't know about force parameter

# NOT BREAKING: New optional parameter with default
# OLD: async def create(self, request)
# NEW: async def create(self, request, force=False)
# OK: existing callers still work

# BREAKING: Return type changed
# OLD: returns ResourceResponse
# NEW: returns ResourceResponse | None
# Problem: callers might not handle None

# NOT BREAKING: Added exception type
# OLD: raises ValueError
# NEW: raises ValueError | ResourceNotFoundError
# OK: ValueError still raised, callers handle it
```

### Backward Compatibility Pattern

```python
class MyProvider(ResourceProvider):
    async def create_or_update_resource(
        self,
        request: ResourceRequest,
        force: bool = False
    ):
        """
        Create or update a resource.
        
        Args:
            request: Resource request
            force: Force creation even if validation fails (new in v1.2)
        """
        if not force:
            # Do validation (old behavior)
            await self._validate(request)
        else:
            # Skip validation (new behavior)
            logger.warning("Forcing creation without validation")
        
        return await self._create(request)
```

---

## Monitoring Migrations

### Health Checks During Migration

```bash
# Monitor while migration runs
watch -n 1 'curl http://localhost:8000/health'

# Check deployment rollout
kubectl rollout status deployment/my-provider -n itl-providers
```

### Verify Data Integrity

```python
async def verify_migration():
    """Verify data integrity after migration"""
    engine = create_async_engine("postgresql+asyncpg://...")
    
    async with AsyncSession(engine) as session:
        # Check all resources have new field
        stmt = select(func.count()).where(ResourceModel.region == None)
        null_count = await session.scalar(stmt)
        
        assert null_count == 0, f"{null_count} resources without region"
        
        # Check no resources were deleted
        stmt = select(func.count())
        total = await session.scalar(stmt)
        
        assert total >= EXPECTED_RESOURCE_COUNT, f"Missing resources"
        
        print(" Migration verified successfully")
```

---

## Common Pitfalls

### Don't

- Add required field without default
- Delete columns without migration
- Change field types without conversion
- Deploy without testing
- Skip backup before migration

### Do

- Always include default values
- Write migration scripts
- Test on staging first
- Backup before production changes
- Monitor during deployment
- Have rollback plan ready

---

## Rollback Procedures

### Application Rollback

```bash
# If new version has issues

# 1. Immediately revert deployment
docker kill my-provider-new
docker rename my-provider-blue my-provider
docker start my-provider

# 2. Switch traffic back
# Update API Gateway to point to old provider

# 3. Monitor
curl http://localhost:8000/health

# 4. Investigate issue
docker logs my-provider-new > debug.log
```

### Database Rollback

```bash
# If migration broke data

# 1. Stop application
docker stop my-provider

# 2. Restore from backup
pg_restore -d production_db backup.sql

# 3. Deploy old application version
docker run -d -p 8000:8000 my-provider:v1.2.3

# 4. Verify
curl http://localhost:8000/health
```

---

## Checklist for Releases

### Pre-Release

- [ ] All tests passing
- [ ] Breaking changes documented
- [ ] Migration scripts provided
- [ ] Upgrade guide written
- [ ] Staging deployment tested
- [ ] Performance tested

### Release

- [ ] Tag version in git
- [ ] Build and publish image
- [ ] Update documentation
- [ ] Announce in Slack/email
- [ ] Update changelog

### Post-Release

- [ ] Monitor metrics
- [ ] Check error rates
- [ ] Verify deployments
- [ ] Document any issues
- [ ] Plan rollback if needed

---

## Related Documentation

- [13-DEPLOYMENT.md](13-DEPLOYMENT.md) - Deployment strategies
- [14-MONITORING.md](14-MONITORING.md) - Monitoring deployments
- [19-DATA_MODELING_AND_SCHEMAS.md](19-DATA_MODELING_AND_SCHEMAS.md) - Schema design
- [02-INSTALLATION.md](../02-INSTALLATION.md) - SDK installation

---

Smooth migrations keep your provider healthy and users happy.
