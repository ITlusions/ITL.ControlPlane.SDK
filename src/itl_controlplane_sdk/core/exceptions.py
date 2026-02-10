"""
Production-grade exception hierarchy for the ITL ControlPlane SDK.

Provides two complementary exception families:

1. **Simple exceptions** — ``ResourceProviderError`` and subclasses.
   Compact, HTTP-status-aware, ideal for direct use in FastAPI route handlers.

2. **Structured exceptions** — ``ControlPlaneError`` and subclasses.
   Enterprise-grade with error categories, retry logic, structured context,
   and audit-trail support. Use these in provider business logic.

Both families are independent — providers can use either or both.

Simple exceptions (original)::

    raise ResourceNotFoundError("/subscriptions/sub-123")

Structured exceptions (new)::

    raise ConfigurationError(
        "Database connection failed",
        context={"host": "pg.example.com"},
        original_error=original_exception,
    )
"""

from enum import Enum
from typing import Any, Dict, Optional


# ===================================================================
# Simple exceptions (original SDK exceptions — kept for compatibility)
# ===================================================================


class ResourceProviderError(Exception):
    """Base exception for resource provider errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "InternalError",
        status_code: int = 500,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class ResourceNotFoundError(ResourceProviderError):
    """Exception for resource not found errors."""

    def __init__(self, resource_id: str):
        super().__init__(
            f"Resource not found: {resource_id}",
            error_code="ResourceNotFound",
            status_code=404,
        )


class ResourceConflictError(ResourceProviderError):
    """Exception for resource conflict errors."""

    def __init__(self, message: str):
        super().__init__(
            message,
            error_code="ResourceConflict",
            status_code=409,
        )


# ===================================================================
# Structured exceptions (enterprise-grade)
# ===================================================================


class ErrorCategory(str, Enum):
    """Exception categories for routing and retry logic."""

    CONFIGURATION = "configuration"   # Configuration/setup error (no retry)
    VALIDATION = "validation"         # Input validation error (no retry)
    TRANSIENT = "transient"           # Temporary error (retry possible)
    PERMANENT = "permanent"           # Permanent error (no retry)
    AUTHORIZATION = "authorization"   # Auth/authz error (no retry)
    EXTERNAL = "external"             # External service error (retry possible)


class ControlPlaneError(Exception):
    """
    Base exception for all control plane operations.

    Provides structured error information for logging, monitoring,
    and recovery.

    Example::

        try:
            await provider.create_resource(spec)
        except ControlPlaneError as e:
            logger.error(
                "Operation failed",
                extra={
                    "error_code": e.error_code,
                    "category": e.category,
                    "retryable": e.is_retryable(),
                    "context": e.context,
                }
            )
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.context = context or {}
        self.original_error = original_error

    def is_retryable(self) -> bool:
        """Check if operation can be retried."""
        return self.category in (ErrorCategory.TRANSIENT, ErrorCategory.EXTERNAL)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "context": self.context,
            "retryable": self.is_retryable(),
        }

    def to_log_dict(self) -> Dict[str, Any]:
        """
        Convert to structured logging format (JSON-serializable).

        Use with structured logging systems (JSON logs, CloudWatch, DataDog)
        to ensure consistent error information.

        Returns:
            Dictionary with error_code, category, message, is_retryable,
            context, and optionally original_error details.
        """
        result = {
            "error_code": self.error_code,
            "category": self.category.value,
            "message": self.message,
            "is_retryable": self.is_retryable(),
            "context": self.context,
        }
        if self.original_error:
            result["original_error"] = str(self.original_error)
            result["error_type"] = type(self.original_error).__name__
        return result


class ConfigurationError(ControlPlaneError):
    """Configuration or setup error (not retryable)."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            category=ErrorCategory.CONFIGURATION,
            context=context,
            original_error=original_error,
        )


class ValidationError(ResourceProviderError, ControlPlaneError):
    """
    Input validation error.

    Inherits from both families so it can be caught as either
    ``ResourceProviderError`` (status_code=400) or
    ``ControlPlaneError`` (category=VALIDATION).
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        context = context or {}
        if field:
            context["field"] = field

        # Initialize ResourceProviderError side
        ResourceProviderError.__init__(
            self,
            message=message,
            error_code="ValidationError",
            status_code=400,
        )
        # Initialize ControlPlaneError side
        self.category = ErrorCategory.VALIDATION
        self.context = context
        self.original_error = original_error


class AuthorizationError(ControlPlaneError):
    """Authorization/permission error (not retryable)."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            category=ErrorCategory.AUTHORIZATION,
            context=context,
            original_error=original_error,
        )


class ProviderError(ControlPlaneError):
    """
    Provider operation error (base for provider-specific errors).

    Adds ``provider`` and ``operation`` to the context automatically.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        provider: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        category: ErrorCategory = ErrorCategory.PERMANENT,
    ):
        context = context or {}
        context["provider"] = provider
        context["operation"] = operation
        super().__init__(
            message=message,
            error_code=error_code,
            category=category,
            context=context,
            original_error=original_error,
        )


class TransientError(ControlPlaneError):
    """
    Transient/retryable error.

    Includes optional ``retry_after`` and ``max_retries`` hints for
    callers implementing retry logic.
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        max_retries: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        context = context or {}
        if retry_after is not None:
            context["retry_after"] = retry_after
        if max_retries is not None:
            context["max_retries"] = max_retries
        super().__init__(
            message=message,
            error_code="TRANSIENT_ERROR",
            category=ErrorCategory.TRANSIENT,
            context=context,
            original_error=original_error,
        )


class ExternalServiceError(ControlPlaneError):
    """
    External service error (retryable).

    Use for failures communicating with external systems (databases,
    identity providers, message brokers, etc.).
    """

    def __init__(
        self,
        message: str,
        service: str,
        operation: str,
        status_code: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        context = context or {}
        context["service"] = service
        context["operation"] = operation
        if status_code:
            context["status_code"] = status_code
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL,
            context=context,
            original_error=original_error,
        )


class CascadeDeletionError(ControlPlaneError):
    """
    Cascade deletion encountered orphaned resources.

    Raised when deleting a parent resource succeeds but cascade cleanup
    of child resources in external systems fails or is incomplete.

    Resolution: log this error, add to a reconciliation queue, retry
    cascade cleanup, and alert operators after repeated failures.
    """

    def __init__(
        self,
        message: str,
        parent_resource_id: str,
        orphaned_resources: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        context = context or {}
        context["parent_resource_id"] = parent_resource_id
        if orphaned_resources:
            context["orphaned_resources"] = orphaned_resources
        super().__init__(
            message=message,
            error_code="CASCADE_DELETION_ERROR",
            category=ErrorCategory.PERMANENT,
            context=context,
            original_error=original_error,
        )


class TransactionError(ControlPlaneError):
    """Transaction/consistency error (transient, retryable)."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="TRANSACTION_ERROR",
            category=ErrorCategory.TRANSIENT,
            context=context,
            original_error=original_error,
        )
