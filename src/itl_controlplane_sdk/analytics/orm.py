"""
ORM Models for Analytics resources

Uses SQLAlchemy with async support
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Integer, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from itl_controlplane_sdk.persistence.data.models import Base
import uuid
import enum


class NotebookStatus(str, enum.Enum):
    """Notebook lifecycle states"""
    CREATING = "Creating"
    RUNNING = "Running"
    STOPPED = "Stopped"
    ERROR = "Error"
    TERMINATING = "Terminating"


class Notebook(Base):
    """Notebook ORM model"""
    __tablename__ = "notebooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ARM identifiers
    subscription_id = Column(String, nullable=False, index=True)
    resource_group = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    
    # Resource properties
    location = Column(String, nullable=False)
    status = Column(String, default=NotebookStatus.CREATING, nullable=False)
    
    # Notebook configuration
    kernel = Column(String, default="python3.11")
    compute_sku = Column(String, default="Standard_D4s_v3")
    memory_gb = Column(Integer, default=16)
    cpu_cores = Column(Integer, default=4)
    storage_gb = Column(Integer, default=100)
    
    # Infrastructure references
    pod_name = Column(String, nullable=True)  # Kubernetes pod name
    pod_namespace = Column(String, default="analytics")
    storage_bucket = Column(String, nullable=True)  # MinIO bucket
    storage_path = Column(String, nullable=True)
    
    # URLs & endpoints
    notebook_url = Column(String, nullable=True)  # https://notebooks.analytics.itl.com/...
    kernel_url = Column(String, nullable=True)   # Internal kernel URL
    
    # Metadata
    owner_id = Column(String, nullable=False)  # User ID from JWT
    tags = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Cost tracking
    hourly_cost = Column(String, default="0.00")  # From compute SKU pricing
    
    def __repr__(self):
        return f"<Notebook {self.subscription_id}/{self.resource_group}/{self.name}>"


class SparkCluster(Base):
    """Spark Cluster ORM model"""
    __tablename__ = "spark_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ARM identifiers
    subscription_id = Column(String, nullable=False, index=True)
    resource_group = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    
    # Status
    status = Column(String, default="Creating")
    master_url = Column(String, nullable=True)
    
    # Configuration
    driver_cpu = Column(Integer, default=8)
    driver_memory_gb = Column(Integer, default=32)
    worker_count = Column(Integer, default=3)
    worker_cpu = Column(Integer, default=16)
    worker_memory_gb = Column(Integer, default=64)
    worker_gpus = Column(Integer, default=4)
    
    # Infrastructure references
    driver_pod = Column(String, nullable=True)
    worker_pods = Column(JSON, default=[])  # List of pod names
    accelerator_allocation_ids = Column(JSON, default=[])  # GPU node allocation IDs
    
    # Metadata
    owner_id = Column(String, nullable=False)
    tags = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalyticsJob(Base):
    """Analytics Job ORM model"""
    __tablename__ = "analytics_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ARM identifiers
    subscription_id = Column(String, nullable=False, index=True)
    resource_group = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    
    # Job details
    status = Column(String, default="Submitted")
    job_type = Column(String)  # etl, training, validation, etc
    
    # Configuration
    compute_cluster_id = Column(UUID, nullable=True)  # Reference to SparkCluster
    
    # Metadata
    owner_id = Column(String, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class Model(Base):
    """ML Model ORM model"""
    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ARM identifiers
    subscription_id = Column(String, nullable=False, index=True)
    resource_group = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    
    # Model details
    version = Column(String, default="1.0.0")
    framework = Column(String)  # sklearn, pytorch, tensorflow, etc
    
    # Artifact storage
    artifact_path = Column(String)  # s3://bucket/path/model.pkl
    
    # Metadata
    owner_id = Column(String, nullable=False)
    metrics = Column(JSON, default={})  # accuracy, precision, recall, etc
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Dataset(Base):
    """Dataset ORM model"""
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ARM identifiers
    subscription_id = Column(String, nullable=False, index=True)
    resource_group = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    
    # Dataset details
    location = Column(String)  # s3://bucket/path
    schema = Column(JSON, default={})  # Column definitions
    
    # Quality metrics
    row_count = Column(Integer, nullable=True)
    completeness = Column(String, nullable=True)  # 99.8%
    
    # Metadata
    owner_id = Column(String, nullable=False)
    tags = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class InferenceEndpoint(Base):
    """Model Inference Endpoint ORM model"""
    __tablename__ = "inference_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ARM identifiers
    subscription_id = Column(String, nullable=False, index=True)
    resource_group = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    
    # Endpoint details
    status = Column(String, default="Creating")
    model_id = Column(UUID, nullable=False)
    url = Column(String, nullable=True)
    
    # Configuration
    replica_count = Column(Integer, default=1)
    cpu_per_replica = Column(Integer, default=4)
    memory_gb_per_replica = Column(Integer, default=8)
    
    # Metadata
    owner_id = Column(String, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
