"""
Analytics models package for ITL Control Plane SDK
"""

# ORM Models
from .orm import (
    Notebook,
    NotebookStatus,
    SparkCluster,
    AnalyticsJob,
    Model,
    Dataset,
    InferenceEndpoint,
)

# Repository Base
from .base_repository import BaseAnalyticsRepository

# Pydantic Models
from .models import (
    NotebookPropertiesRequest,
    NotebookRequest,
    NotebookProperties,
    NotebookResponse,
    SparkClusterPropertiesRequest,
    SparkClusterRequest,
    SparkClusterProperties,
    SparkClusterResponse,
    AnalyticsJobPropertiesRequest,
    AnalyticsJobRequest,
    AnalyticsJobProperties,
    AnalyticsJobResponse,
    ModelPropertiesRequest,
    ModelRequest,
    ModelProperties,
    ModelResponse,
    DatasetPropertiesRequest,
    DatasetRequest,
    DatasetProperties,
    DatasetResponse,
    InferenceEndpointPropertiesRequest,
    InferenceEndpointRequest,
    InferenceEndpointProperties,
    InferenceEndpointResponse,
)

__all__ = [
    # Repository Base
    "BaseAnalyticsRepository",
    # ORM
    "Notebook",
    "NotebookStatus",
    "SparkCluster",
    "AnalyticsJob",
    "Model",
    "Dataset",
    "InferenceEndpoint",
    # Pydantic Models - Notebook
    "NotebookPropertiesRequest",
    "NotebookRequest",
    "NotebookProperties",
    "NotebookResponse",
    # Pydantic Models - Spark Cluster
    "SparkClusterPropertiesRequest",
    "SparkClusterRequest",
    "SparkClusterProperties",
    "SparkClusterResponse",
    # Pydantic Models - Analytics Job
    "AnalyticsJobPropertiesRequest",
    "AnalyticsJobRequest",
    "AnalyticsJobProperties",
    "AnalyticsJobResponse",
    # Pydantic Models - Model
    "ModelPropertiesRequest",
    "ModelRequest",
    "ModelProperties",
    "ModelResponse",
    # Pydantic Models - Dataset
    "DatasetPropertiesRequest",
    "DatasetRequest",
    "DatasetProperties",
    "DatasetResponse",
    # Pydantic Models - Inference Endpoint
    "InferenceEndpointPropertiesRequest",
    "InferenceEndpointRequest",
    "InferenceEndpointProperties",
    "InferenceEndpointResponse",
]
