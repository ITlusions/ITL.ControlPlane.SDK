"""
Standard exceptions for the ITL ControlPlane SDK.

Provides a hierarchy of exception types for error handling across
all resource providers.
"""


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
