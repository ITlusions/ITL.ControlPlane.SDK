"""
Core data models for the ITL ControlPlane SDK
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

class ProvisioningState(Enum):
    """Standard resource provisioning states"""
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELED = "Canceled"
    CREATING = "Creating"
    UPDATING = "Updating"
    DELETING = "Deleting"

@dataclass
class ResourceMetadata:
    """Standard resource metadata"""
    id: str
    name: str
    type: str
    location: str
    resource_group: str
    subscription_id: str
    tags: Optional[Dict[str, str]] = None
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None

@dataclass
class ResourceRequest:
    """Standard resource request structure"""
    subscription_id: str
    resource_group: str
    provider_namespace: str
    resource_type: str
    resource_name: str
    location: str
    body: Dict[str, Any]
    action: Optional[str] = None
    api_version: str = "2023-01-01"

@dataclass
class ResourceResponse:
    """Standard resource response structure"""
    id: str
    name: str
    type: str
    location: str
    properties: Dict[str, Any]
    tags: Optional[Dict[str, str]] = None
    provisioning_state: ProvisioningState = ProvisioningState.SUCCEEDED

@dataclass
class ResourceListResponse:
    """Response for resource list operations"""
    value: List[ResourceResponse]
    next_link: Optional[str] = None

@dataclass
class ErrorResponse:
    """Standard error response"""
    error: Dict[str, Any]
    
class ResourceProviderError(Exception):
    """Base exception for resource provider errors"""
    def __init__(self, message: str, error_code: str = "InternalError", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class ResourceNotFoundError(ResourceProviderError):
    """Exception for resource not found errors"""
    def __init__(self, resource_id: str):
        super().__init__(
            f"Resource not found: {resource_id}",
            error_code="ResourceNotFound",
            status_code=404
        )

class ResourceConflictError(ResourceProviderError):
    """Exception for resource conflict errors"""
    def __init__(self, message: str):
        super().__init__(
            message,
            error_code="ResourceConflict", 
            status_code=409
        )

class ValidationError(ResourceProviderError):
    """Exception for validation errors"""
    def __init__(self, message: str):
        super().__init__(
            message,
            error_code="ValidationError",
            status_code=400
        )