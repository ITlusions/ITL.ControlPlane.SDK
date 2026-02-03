"""
Metadata API endpoints for ITL ControlPlane SDK

Provides REST API endpoints for querying resource metadata, dependencies,
and hierarchical structures stored in the graph database.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Pydantic models for API responses
class ResourceMetadataResponse(BaseModel):
    """Resource metadata API response"""
    id: str
    name: str
    node_type: str
    properties: dict
    created_time: str
    modified_time: str

class DependencyResponse(BaseModel):
    """Resource dependency API response"""
    resource_id: str
    depends_on: List[str]
    dependents: List[str]
    dependency_type: str

class HierarchyResponse(BaseModel):
    """Resource hierarchy API response"""
    subscription_id: str
    resource_groups: List[str]
    resources: dict

class MetricsResponse(BaseModel):
    """Metadata metrics API response"""
    total_nodes: int
    total_relationships: int
    node_counts: dict
    relationship_counts: dict

class SearchRequest(BaseModel):
    """Search request model"""
    search_term: str
    subscription_id: Optional[str] = None

class DependencyRequest(BaseModel):
    """Dependency creation request"""
    source_resource_id: str
    target_resource_id: str
    dependency_type: str = "DEPENDS_ON"


def create_metadata_router(resource_registry) -> APIRouter:
    """
    Create metadata API router with the given resource registry
    
    Args:
        resource_registry: The resource registry instance to use
        
    Returns:
        FastAPI APIRouter with metadata endpoints
    """
    
    router = APIRouter(prefix="/metadata", tags=["metadata"])

    @router.get("/resources/{resource_id}", response_model=ResourceMetadataResponse)
    async def get_resource_metadata(
        resource_id: str = Path(..., description="The full resource ID")
    ):
        """Get metadata for a specific resource"""
        try:
            metadata = await resource_registry.get_resource_metadata(resource_id)
            
            if not metadata:
                raise HTTPException(status_code=404, detail=f"Resource metadata not found: {resource_id}")
            
            return ResourceMetadataResponse(
                id=metadata.id,
                name=metadata.name,
                node_type=metadata.node_type.value,
                properties=metadata.properties,
                created_time=metadata.created_time.isoformat(),
                modified_time=metadata.modified_time.isoformat()
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get resource metadata: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/resources/{resource_id}/dependencies", response_model=DependencyResponse)
    async def get_resource_dependencies(
        resource_id: str = Path(..., description="The full resource ID")
    ):
        """Get dependencies for a specific resource"""
        try:
            dependencies = await resource_registry.get_resource_dependencies(resource_id)
            
            if not dependencies:
                raise HTTPException(status_code=404, detail=f"Resource not found: {resource_id}")
            
            return DependencyResponse(
                resource_id=dependencies.resource_id,
                depends_on=dependencies.depends_on,
                dependents=dependencies.dependents,
                dependency_type=dependencies.dependency_type
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get resource dependencies: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/resources/dependencies")
    async def add_resource_dependency(dependency_request: DependencyRequest):
        """Add a dependency between two resources"""
        try:
            success = await resource_registry.add_resource_dependency(
                dependency_request.source_resource_id,
                dependency_request.target_resource_id,
                dependency_request.dependency_type
            )
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to create dependency")
            
            return {"message": "Dependency created successfully"}
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to add resource dependency: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/subscriptions/{subscription_id}/hierarchy", response_model=HierarchyResponse)
    async def get_subscription_hierarchy(
        subscription_id: str = Path(..., description="The subscription ID")
    ):
        """Get the complete resource hierarchy for a subscription"""
        try:
            hierarchy = await resource_registry.get_resource_hierarchy(subscription_id)
            
            if not hierarchy:
                raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")
            
            return HierarchyResponse(
                subscription_id=hierarchy.subscription_id,
                resource_groups=hierarchy.resource_groups,
                resources=hierarchy.resources
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get subscription hierarchy: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/resources/search", response_model=List[ResourceMetadataResponse])
    async def search_resources(search_request: SearchRequest):
        """Search for resources by name or properties"""
        try:
            resources = await resource_registry.search_resources(
                search_request.search_term,
                search_request.subscription_id
            )
            
            return [
                ResourceMetadataResponse(
                    id=resource.id,
                    name=resource.name,
                    node_type=resource.node_type.value,
                    properties=resource.properties,
                    created_time=resource.created_time.isoformat(),
                    modified_time=resource.modified_time.isoformat()
                )
                for resource in resources
            ]
        
        except Exception as e:
            logger.error(f"Failed to search resources: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/resources", response_model=List[ResourceMetadataResponse])
    async def list_resources_by_query(
        subscription_id: Optional[str] = Query(None, description="Filter by subscription ID"),
        resource_group: Optional[str] = Query(None, description="Filter by resource group"),
        resource_type: Optional[str] = Query(None, description="Filter by resource type"),
        location: Optional[str] = Query(None, description="Filter by location")
    ):
        """List resources with optional filters"""
        try:
            # Build search term from filters
            search_terms = []
            if resource_group:
                search_terms.append(resource_group)
            if resource_type:
                search_terms.append(resource_type)
            if location:
                search_terms.append(location)
            
            search_term = " ".join(search_terms) if search_terms else "*"
            
            resources = await resource_registry.search_resources(search_term, subscription_id)
            
            return [
                ResourceMetadataResponse(
                    id=resource.id,
                    name=resource.name,
                    node_type=resource.node_type.value,
                    properties=resource.properties,
                    created_time=resource.created_time.isoformat(),
                    modified_time=resource.modified_time.isoformat()
                )
                for resource in resources
            ]
        
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/metrics", response_model=MetricsResponse)
    async def get_metadata_metrics():
        """Get metadata service metrics"""
        try:
            metrics = await resource_registry.get_metadata_metrics()
            
            if not metrics:
                raise HTTPException(status_code=503, detail="Metadata service not available")
            
            return MetricsResponse(
                total_nodes=metrics.total_nodes,
                total_relationships=metrics.total_relationships,
                node_counts=metrics.node_counts,
                relationship_counts=metrics.relationship_counts
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get metadata metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/health")
    async def metadata_health_check():
        """Health check for metadata service"""
        try:
            metrics = await resource_registry.get_metadata_metrics()
            
            if metrics is not None:
                return {
                    "status": "healthy",
                    "total_nodes": metrics.total_nodes,
                    "total_relationships": metrics.total_relationships
                }
            else:
                return {"status": "metadata_disabled"}
        
        except Exception as e:
            logger.error(f"Metadata health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    return router
