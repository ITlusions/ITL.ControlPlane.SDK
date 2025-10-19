# Graph Database Configuration for ITL ControlPlane SDK

## Supported Graph Databases

The ITL ControlPlane SDK supports multiple graph database backends for storing resource metadata:

### 1. In-Memory Database (Development)
```python
from src.controlplane_sdk.metadata_service import MetadataService

# Simple in-memory database for development/testing
metadata_service = MetadataService(database_type="inmemory")
```

### 2. Neo4j Database (Production)

#### Installation:
```bash
# Install Neo4j driver
pip install neo4j

# Or add to requirements.txt
echo "neo4j>=5.0.0" >> requirements.txt
```

#### Configuration:
```python
from src.controlplane_sdk.metadata_service import MetadataService

# Neo4j configuration
metadata_service = MetadataService(
    database_type="neo4j",
    uri="bolt://localhost:7687",          # Neo4j server URI
    username="neo4j",                     # Username
    password="your-password",             # Password
    database="itl-metadata"               # Database name
)
```

#### Environment Variables:
```bash
# Set via environment variables
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
export NEO4J_DATABASE="itl-metadata"
```

```python
import os
from src.controlplane_sdk.metadata_service import MetadataService

# Use environment variables
metadata_service = MetadataService(
    database_type="neo4j",
    uri=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE", "neo4j")
)
```

## Registry Configuration

Enable or disable metadata tracking in the resource registry:

```python
from src.controlplane_sdk.registry import ResourceProviderRegistry

# Enable metadata tracking (default)
registry = ResourceProviderRegistry(enable_metadata=True)

# Disable metadata tracking
registry = ResourceProviderRegistry(enable_metadata=False)
```

## Docker Compose Setup for Neo4j

Create a `docker-compose.yml` file for local Neo4j development:

```yaml
version: '3.8'
services:
  neo4j:
    image: neo4j:5.12-community
    container_name: itl-neo4j
    restart: unless-stopped
    ports:
      - "7474:7474"   # HTTP
      - "7687:7687"   # Bolt
    environment:
      - NEO4J_AUTH=neo4j/itl-password
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_memory_heap_initial_size=512m
      - NEO4J_dbms_memory_heap_max_size=2G
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
      - neo4j-import:/var/lib/neo4j/import
      - neo4j-plugins:/plugins

volumes:
  neo4j-data:
  neo4j-logs:
  neo4j-import:
  neo4j-plugins:
```

Run with:
```bash
docker-compose up -d
```

Access Neo4j Browser at: http://localhost:7474

## Configuration Examples

### Development Configuration:
```python
# config/development.py
METADATA_CONFIG = {
    "database_type": "inmemory",
    "enable_metadata": True
}
```

### Production Configuration:
```python
# config/production.py
METADATA_CONFIG = {
    "database_type": "neo4j",
    "uri": "bolt://neo4j-cluster.internal:7687",
    "username": "itl_service",
    "password": "${NEO4J_PASSWORD}",  # From secret manager
    "database": "itl_production",
    "enable_metadata": True
}
```

### Testing Configuration:
```python
# config/testing.py
METADATA_CONFIG = {
    "database_type": "inmemory",
    "enable_metadata": True  # Enable for integration tests
}
```

## API Configuration

Add metadata endpoints to your FastAPI application:

```python
from src.api_layer.metadata_routes import metadata_router
from fastapi import FastAPI

app = FastAPI()
app.include_router(metadata_router, tags=["Metadata"])
```

Available endpoints:
- `GET /metadata/resources/{resource_id}` - Get resource metadata
- `GET /metadata/resources/{resource_id}/dependencies` - Get dependencies
- `POST /metadata/resources/dependencies` - Add dependency
- `GET /metadata/subscriptions/{subscription_id}/hierarchy` - Get hierarchy
- `POST /metadata/resources/search` - Search resources
- `GET /metadata/metrics` - Get database metrics
- `GET /metadata/health` - Health check

## Performance Tuning

### Neo4j Performance:
```python
# config/neo4j_performance.py
NEO4J_CONFIG = {
    "uri": "bolt://localhost:7687",
    "username": "neo4j",
    "password": "password",
    "max_connection_lifetime": 30 * 60,  # 30 minutes
    "max_connection_pool_size": 50,
    "connection_acquisition_timeout": 60,  # 60 seconds
    "encrypted": True  # For production
}
```

### Indexing for Performance:
```cypher
-- Create indexes for common queries
CREATE INDEX resource_subscription_idx FOR (r:resource) ON (r.subscriptionId);
CREATE INDEX resource_type_idx FOR (r:resource) ON (r.resourceType);
CREATE INDEX resource_group_location_idx FOR (rg:resourceGroup) ON (rg.location);
```

## Security Configuration

### Production Security:
```python
# config/security.py
SECURITY_CONFIG = {
    "neo4j": {
        "encrypted": True,
        "trust": "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES",
        "user_agent": "ITL-ControlPlane/1.0"
    },
    "api": {
        "require_auth": True,
        "allowed_origins": ["https://itl.company.com"],
        "rate_limit": "100/minute"
    }
}
```

## Monitoring and Logging

### Logging Configuration:
```python
import logging

# Configure metadata service logging
logging.getLogger('src.controlplane_sdk.metadata_service').setLevel(logging.INFO)
logging.getLogger('src.controlplane_sdk.graph_database').setLevel(logging.DEBUG)

# Neo4j driver logging
logging.getLogger('neo4j').setLevel(logging.WARNING)
```

### Metrics Collection:
```python
# Monitor metadata service health
async def check_metadata_health():
    try:
        metrics = await metadata_service.get_metrics()
        return {
            "status": "healthy",
            "nodes": metrics.total_nodes,
            "relationships": metrics.total_relationships
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Migration and Backup

### Data Migration:
```python
# Export metadata to JSON
async def export_metadata():
    all_nodes = await metadata_service.graph_db.find_nodes()
    return [node.dict() for node in all_nodes]

# Import metadata from JSON
async def import_metadata(exported_data):
    for node_data in exported_data:
        await metadata_service.graph_db.create_node(node_data)
```

### Neo4j Backup:
```bash
# Using Neo4j Admin tool
neo4j-admin dump --database=itl-metadata --to=/backups/metadata-backup.dump

# Restore
neo4j-admin load --from=/backups/metadata-backup.dump --database=itl-metadata
```