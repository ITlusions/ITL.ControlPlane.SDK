"""
Logging Middleware

Logs all HTTP requests and responses with timing information.
"""

import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses
    
    Logs:
    - Request method, path, and query parameters
    - Response status code
    - Processing time
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request and log timing"""
        start_time = time.time()
        
        # Log incoming request
        logger.debug(
            f"→ {request.method} {request.url.path}",
            extra={"request_id": id(request)}
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"← {request.method} {request.url.path} "
            f"[{response.status_code}] ({process_time:.3f}s)",
            extra={"request_id": id(request)}
        )
        
        # Add processing time to response headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
