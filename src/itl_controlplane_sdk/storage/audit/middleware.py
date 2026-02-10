"""
FastAPI Middleware for Audit Context.

Automatically sets audit context (actor_id, correlation_id, source_ip, etc.)
for each incoming request.

Usage::

    from fastapi import FastAPI
    from itl_controlplane_sdk.storage.audit import (
        AuditContextMiddleware,
        SQLAuditEventAdapter,
        AuditEventPublisher,
    )
    
    app = FastAPI()
    
    # Initialize adapter and publisher
    adapter = SQLAuditEventAdapter(engine.session_factory)
    publisher = AuditEventPublisher(adapter)
    
    # Add middleware - sets context for all requests
    app.add_middleware(
        AuditContextMiddleware,
        publisher=publisher,
        extract_actor_from_jwt=True,
    )
"""

import uuid
import logging
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .publisher import AuditContext, AuditEventPublisher
from .models import ActorType

logger = logging.getLogger(__name__)


class AuditContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that sets audit context for each request.
    
    Extracts:
    - actor_id: From JWT 'sub' claim or 'X-Actor-Id' header
    - actor_type: From JWT 'azp' claim (client_credentials) or header
    - actor_display_name: From JWT 'preferred_username' or 'name'
    - correlation_id: From 'X-Correlation-Id' header or generates UUID
    - request_id: Generates UUID for each request
    - source_ip: From 'X-Forwarded-For' or client IP
    - user_agent: From 'User-Agent' header
    
    Args:
        app: ASGI application
        publisher: AuditEventPublisher (optional, for request logging)
        extract_actor_from_jwt: Whether to extract actor from JWT (default: True)
        jwt_header: Header containing the JWT (default: Authorization)
        correlation_id_header: Header for correlation ID (default: X-Correlation-Id)
        actor_id_header: Header for explicit actor ID (default: X-Actor-Id)
        actor_type_header: Header for explicit actor type (default: X-Actor-Type)
    """
    
    def __init__(
        self,
        app,
        publisher: Optional[AuditEventPublisher] = None,
        extract_actor_from_jwt: bool = True,
        jwt_header: str = "Authorization",
        correlation_id_header: str = "X-Correlation-Id",
        actor_id_header: str = "X-Actor-Id",
        actor_type_header: str = "X-Actor-Type",
    ):
        super().__init__(app)
        self.publisher = publisher
        self.extract_actor_from_jwt = extract_actor_from_jwt
        self.jwt_header = jwt_header
        self.correlation_id_header = correlation_id_header
        self.actor_id_header = actor_id_header
        self.actor_type_header = actor_type_header
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and set audit context."""
        
        # Extract correlation ID (from header or generate)
        correlation_id = request.headers.get(self.correlation_id_header)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Extract source IP
        source_ip = self._extract_source_ip(request)
        
        # Extract user agent
        user_agent = request.headers.get("User-Agent", "")
        
        # Extract actor information
        actor_id, actor_type, actor_display_name = self._extract_actor(request)
        
        # Set audit context for this request
        async with AuditContext(
            actor_id=actor_id,
            actor_type=actor_type,
            actor_display_name=actor_display_name,
            correlation_id=correlation_id,
            request_id=request_id,
            source_ip=source_ip,
            user_agent=user_agent,
        ):
            # Add IDs to request state for downstream access
            request.state.correlation_id = correlation_id
            request.state.request_id = request_id
            request.state.actor_id = actor_id
            
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-Id"] = correlation_id
            response.headers["X-Request-Id"] = request_id
            
            return response
    
    def _extract_source_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxies."""
        # Check X-Forwarded-For first (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP (original client)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP (nginx proxy)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _extract_actor(self, request: Request) -> tuple[Optional[str], ActorType, Optional[str]]:
        """
        Extract actor information from request.
        
        Returns:
            Tuple of (actor_id, actor_type, actor_display_name)
        """
        actor_id: Optional[str] = None
        actor_type = ActorType.ANONYMOUS
        actor_display_name: Optional[str] = None
        
        # 1. Check explicit headers first
        explicit_actor = request.headers.get(self.actor_id_header)
        if explicit_actor:
            actor_id = explicit_actor
            actor_type_str = request.headers.get(self.actor_type_header, "USER")
            try:
                actor_type = ActorType(actor_type_str)
            except ValueError:
                actor_type = ActorType.USER
            return actor_id, actor_type, actor_display_name
        
        # 2. Try to extract from JWT
        if self.extract_actor_from_jwt:
            jwt_info = self._parse_jwt(request)
            if jwt_info:
                actor_id = jwt_info.get("sub")
                actor_display_name = jwt_info.get("preferred_username") or jwt_info.get("name")
                
                # Determine actor type from JWT
                azp = jwt_info.get("azp")  # authorized party (client)
                sub = jwt_info.get("sub")
                
                # If sub == azp, likely client_credentials (service principal)
                if azp and sub and azp == sub:
                    actor_type = ActorType.SERVICE_PRINCIPAL
                elif jwt_info.get("client_id"):
                    actor_type = ActorType.SERVICE_PRINCIPAL
                else:
                    actor_type = ActorType.USER
                
                return actor_id, actor_type, actor_display_name
        
        # 3. Check API key header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # Hash or identify the key
            actor_id = f"apikey:{api_key[:8]}..."
            actor_type = ActorType.SERVICE_PRINCIPAL
            return actor_id, actor_type, actor_display_name
        
        # 4. No authentication found
        return None, ActorType.ANONYMOUS, None
    
    def _parse_jwt(self, request: Request) -> Optional[dict]:
        """
        Parse JWT from Authorization header without verification.
        
        Note: This is for audit context only. Actual authentication
        should happen elsewhere with proper verification.
        """
        auth_header = request.headers.get(self.jwt_header)
        if not auth_header:
            return None
        
        # Extract token from "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        token = parts[1]
        
        try:
            import base64
            import json
            
            # JWT format: header.payload.signature
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            # Decode payload (middle part)
            # Add padding if needed
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        
        except Exception:
            return None


def get_audit_context_from_request(request: Request) -> dict:
    """
    Helper to get audit context values from request state.
    
    Use this in route handlers to access audit context.
    
    Example::
    
        @app.post("/resources")
        async def create_resource(request: Request):
            ctx = get_audit_context_from_request(request)
            print(f"Request from {ctx['actor_id']} ({ctx['correlation_id']})")
    """
    return {
        "correlation_id": getattr(request.state, "correlation_id", None),
        "request_id": getattr(request.state, "request_id", None),
        "actor_id": getattr(request.state, "actor_id", None),
    }
