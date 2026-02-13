"""
Observability routes for ITL ControlPlane providers.

Provides standard admin and observability endpoints for monitoring
resource storage, Neo4j sync status, and other system metrics.
"""

import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def setup_observability_routes(app: FastAPI, engine) -> None:
    """Setup standard observability and admin routes.
    
    Registers endpoints for:
    - Storage statistics (resource counts from PostgreSQL and Neo4j)
    - Neo4j sync triggers (manual full sync of data to Neo4j)
    
    Args:
        app: FastAPI application to register routes on
        engine: SQLAlchemyStorageEngine instance with stats and Neo4j methods
    
    Routes registered:
    - GET /admin/stats
    - POST /admin/neo4j-sync
    """
    
    @app.get("/admin/stats", summary="Storage Statistics", tags=["System"])
    async def storage_stats():
        """Get resource counts from PostgreSQL and Neo4j.
        
        Returns statistics about the number of resources stored in
        both the primary database and the graph database.
        """
        return await engine.get_stats()
    
    @app.post("/admin/neo4j-sync", summary="Trigger Neo4j full sync", tags=["System"])
    async def neo4j_full_sync():
        """Trigger a full sync of PostgreSQL data → Neo4j.
        
        Manually initiates a complete synchronization of all resources
        from the primary database to the Neo4j graph database.
        
        Returns status of the sync operation.
        """
        if not engine.neo4j_sync:
            return {"status": "skipped", "reason": "Neo4j not configured"}
        await engine.full_neo4j_sync()
        return {"status": "ok", "message": "Full Neo4j sync completed"}
