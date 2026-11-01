"""
Pydantic models for Analytics resources

Extends SDK GenericResourceBase
"""

from typing import Any, Dict, Optional
from datetime import datetime
from uuid import UUID
from pydantic import Field, BaseModel
from itl_controlplane_sdk.api.base.models import GenericResourceBase


# ============================================================================
# NOTEBOOK MODELS
# ============================================================================


class NotebookPropertiesRequest(BaseModel):
    """Notebook properties for request"""

    kernel: str = Field(default="python3.11", description="Kernel type")
    computeSku: str = Field(default="Standard_D4s_v3", description="Compute SKU")
    memory_gb: int = Field(default=16, description="Memory in GB")
    cpu_cores: int = Field(default=4, description="CPU cores")
    storage_gb: int = Field(default=100, description="Storage in GB")


class NotebookRequest(GenericResourceBase):
    """Request to create notebook"""

    name: str = Field(..., min_length=1, max_length=260, description="Notebook name")
    location: str = Field(..., description="Azure region (e.g., westeurope)")
    properties: NotebookPropertiesRequest = Field(default_factory=NotebookPropertiesRequest)


class NotebookProperties(BaseModel):
    """Notebook properties in response"""

    kernel: str
    computeSku: str
    memory_gb: int
    cpu_cores: int
    storage_gb: int
    pod_name: Optional[str] = None
    storage_bucket: Optional[str] = None
    notebook_url: Optional[str] = None


class NotebookResponse(GenericResourceBase):
    """Response for notebook resource"""

    id: UUID = Field(..., description="ARM resource ID")
    name: str = Field(..., description="Notebook name")
    type: str = Field(default="ITL.Analytics/notebooks", description="Resource type")
    location: str = Field(..., description="Azure region")
    status: str = Field(default="Running", description="Status: Creating, Running, Stopped, Error")
    properties: NotebookProperties = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    owner_id: str = Field(...)


# ============================================================================
# SPARK CLUSTER MODELS
# ============================================================================


class SparkClusterPropertiesRequest(BaseModel):
    """Spark cluster properties for request"""

    driver_cpu: int = Field(default=8, description="Driver CPU cores")
    driver_memory_gb: int = Field(default=32, description="Driver memory GB")
    worker_count: int = Field(default=3, description="Number of workers")
    worker_cpu: int = Field(default=16, description="Worker CPU cores")
    worker_memory_gb: int = Field(default=64, description="Worker memory GB")
    worker_gpus: int = Field(default=4, description="GPUs per worker")


class SparkClusterRequest(GenericResourceBase):
    """Request to create Spark cluster"""

    name: str = Field(..., min_length=1, max_length=260, description="Cluster name")
    location: str = Field(..., description="Azure region")
    properties: SparkClusterPropertiesRequest = Field(default_factory=SparkClusterPropertiesRequest)


class SparkClusterProperties(BaseModel):
    """Spark cluster properties in response"""

    driver_cpu: int
    driver_memory_gb: int
    worker_count: int
    worker_cpu: int
    worker_memory_gb: int
    worker_gpus: int
    master_url: Optional[str] = None
    driver_pod: Optional[str] = None


class SparkClusterResponse(GenericResourceBase):
    """Response for Spark cluster"""

    id: UUID = Field(..., description="ARM resource ID")
    name: str = Field(..., description="Cluster name")
    type: str = Field(default="ITL.Analytics/sparkClusters", description="Resource type")
    location: str = Field(..., description="Azure region")
    status: str = Field(default="Creating", description="Status")
    properties: SparkClusterProperties = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)


# ============================================================================
# ANALYTICS JOB MODELS
# ============================================================================


class AnalyticsJobPropertiesRequest(BaseModel):
    """Analytics job properties for request"""

    job_type: str = Field(..., description="Job type: etl, training, validation")
    compute_cluster_id: Optional[UUID] = Field(None, description="Cluster to run on")


class AnalyticsJobRequest(GenericResourceBase):
    """Request to create analytics job"""

    name: str = Field(..., description="Job name")
    location: str = Field(..., description="Azure region")
    properties: AnalyticsJobPropertiesRequest = Field(...)


class AnalyticsJobProperties(BaseModel):
    """Analytics job properties in response"""

    job_type: str
    compute_cluster_id: Optional[UUID] = None


class AnalyticsJobResponse(GenericResourceBase):
    """Response for analytics job"""

    id: UUID = Field(..., description="ARM resource ID")
    name: str = Field(..., description="Job name")
    type: str = Field(default="ITL.Analytics/analyticsJobs", description="Resource type")
    status: str = Field(default="Submitted", description="Job status")
    properties: AnalyticsJobProperties = Field(...)
    created_at: datetime = Field(...)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ============================================================================
# MODEL REGISTRY MODELS
# ============================================================================


class ModelPropertiesRequest(BaseModel):
    """Model properties for request"""

    framework: str = Field(..., description="Framework: sklearn, pytorch, tensorflow")
    version: str = Field(default="1.0.0", description="Model version")


class ModelRequest(GenericResourceBase):
    """Request to register model"""

    name: str = Field(..., description="Model name")
    location: str = Field(..., description="Azure region")
    properties: ModelPropertiesRequest = Field(...)


class ModelProperties(BaseModel):
    """Model properties in response"""

    framework: str
    version: str
    artifact_path: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ModelResponse(GenericResourceBase):
    """Response for model resource"""

    id: UUID = Field(..., description="ARM resource ID")
    name: str = Field(..., description="Model name")
    type: str = Field(default="ITL.Analytics/models", description="Resource type")
    properties: ModelProperties = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)


# ============================================================================
# DATASET MODELS
# ============================================================================


class DatasetPropertiesRequest(BaseModel):
    """Dataset properties for request"""

    location: str = Field(..., description="Data location (S3/MinIO path)")
    schema: Optional[Dict[str, Any]] = Field(None, description="Column definitions")


class DatasetRequest(GenericResourceBase):
    """Request to register dataset"""

    name: str = Field(..., description="Dataset name")
    location: str = Field(..., description="Azure region")
    properties: DatasetPropertiesRequest = Field(...)


class DatasetProperties(BaseModel):
    """Dataset properties in response"""

    location: str
    schema: Dict[str, Any] = Field(default_factory=dict)
    row_count: Optional[int] = None
    completeness: Optional[str] = None


class DatasetResponse(GenericResourceBase):
    """Response for dataset resource"""

    id: UUID = Field(..., description="ARM resource ID")
    name: str = Field(..., description="Dataset name")
    type: str = Field(default="ITL.Analytics/datasets", description="Resource type")
    location: str = Field(..., description="Data location")
    properties: DatasetProperties = Field(...)
    created_at: datetime = Field(...)


# ============================================================================
# INFERENCE ENDPOINT MODELS
# ============================================================================


class InferenceEndpointPropertiesRequest(BaseModel):
    """Inference endpoint properties for request"""

    model_id: UUID = Field(..., description="Model to serve")
    replica_count: int = Field(default=1, description="Number of replicas")
    cpu_per_replica: int = Field(default=4, description="CPUs per replica")
    memory_gb_per_replica: int = Field(default=8, description="Memory GB per replica")


class InferenceEndpointRequest(GenericResourceBase):
    """Request to create inference endpoint"""

    name: str = Field(..., description="Endpoint name")
    location: str = Field(..., description="Azure region")
    properties: InferenceEndpointPropertiesRequest = Field(...)


class InferenceEndpointProperties(BaseModel):
    """Inference endpoint properties in response"""

    model_id: UUID
    replica_count: int
    cpu_per_replica: int
    memory_gb_per_replica: int
    url: Optional[str] = None


class InferenceEndpointResponse(GenericResourceBase):
    """Response for inference endpoint resource"""

    id: UUID = Field(..., description="ARM resource ID")
    name: str = Field(..., description="Endpoint name")
    type: str = Field(default="ITL.Analytics/inferenceEndpoints", description="Resource type")
    status: str = Field(default="Creating", description="Endpoint status")
    properties: InferenceEndpointProperties = Field(...)
    created_at: datetime = Field(...)
    url: Optional[str] = Field(None, description="Endpoint URL")
