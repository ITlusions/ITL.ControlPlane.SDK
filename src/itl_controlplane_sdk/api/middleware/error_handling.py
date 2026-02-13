"""
Error Handling Middleware

Global exception handlers for consistent error responses.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class APIError(Exception):
    """
    Standard API error with consistent response format
    
    Attributes:
        status_code: HTTP status code
        code: Error code for client identification
        message: Human-readable error message
        details: Additional error details
    """
    
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup global exception handlers for the application
    
    Handles:
    - APIError: Structured API errors
    - ValueError: Validation errors (400)
    - KeyError: Not found errors (404)
    - Exception: Generic server errors (500)
    
    Args:
        app: FastAPI application
    """
    
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """Handle structured API errors"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "code": exc.code,
                "request_id": request.headers.get("x-request-id"),
                "timestamp": datetime.utcnow().isoformat(),
                "details": exc.details if exc.details else None,
            }
        )
    
    @app.exception_handler(ValueError)
    async def validation_error_handler(request: Request, exc: ValueError):
        """Handle validation errors"""
        return JSONResponse(
            status_code=400,
            content={
                "error": str(exc),
                "code": "VALIDATION_ERROR",
                "request_id": request.headers.get("x-request-id"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    @app.exception_handler(KeyError)
    async def not_found_handler(request: Request, exc: KeyError):
        """Handle not found errors"""
        return JSONResponse(
            status_code=404,
            content={
                "error": f"Resource not found: {str(exc)}",
                "code": "NOT_FOUND",
                "request_id": request.headers.get("x-request-id"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        """Handle generic unhandled exceptions"""
        logger.error(
            f"Unhandled exception: {exc}",
            exc_info=True,
            extra={"request_id": request.headers.get("x-request-id")}
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "request_id": request.headers.get("x-request-id"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
