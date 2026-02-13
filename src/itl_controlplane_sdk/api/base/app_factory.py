"""
FastAPI Application Factory

Provides a reusable factory for creating configured FastAPI applications
with common middleware, exception handlers, and health checks.
"""

import logging
from typing import List, Optional, Dict, Any, Callable
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from .config import FastAPIConfig
from ..middleware.logging import LoggingMiddleware
from ..middleware.error_handling import setup_exception_handlers
from ..routes.health import router as health_router

logger = logging.getLogger(__name__)


class AppFactory:
    """
    Factory for creating configured FastAPI applications
    
    Handles:
    - CORS middleware configuration
    - Logging middleware setup
    - Global exception handlers
    - Health check routes
    - Standard request/response patterns
    
    Usage:
        factory = AppFactory("My App", "1.0.0")
        app = factory.create_app(
            routers=[router1, router2],
            cors_origins=["https://example.com"]
        )
    """
    
    def __init__(self, title: str, version: str = "1.0.0", config: Optional[FastAPIConfig] = None):
        """
        Initialize the factory
        
        Args:
            title: Application title
            version: Application version
            config: Optional FastAPIConfig instance
        """
        self.title = title
        self.version = version
        self.config = config or FastAPIConfig()
    
    def create_app(
        self,
        routers: Optional[List[APIRouter]] = None,
        cors_origins: Optional[List[str]] = None,
        add_health_routes: bool = True,
        add_exception_handlers: bool = True,
        add_logging_middleware: bool = True,
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        openapi_url: str = "/openapi.json",
        custom_startup: Optional[Callable] = None,
        custom_shutdown: Optional[Callable] = None,
        lifespan: Optional[Callable] = None,
    ) -> FastAPI:
        """
        Create a configured FastAPI application
        
        Args:
            routers: List of APIRouter instances to include
            cors_origins: CORS allowed origins (default: ["*"])
            add_health_routes: Add standard health/readiness routes
            add_exception_handlers: Add global exception handlers
            add_logging_middleware: Add logging middleware
            docs_url: Swagger UI URL
            redoc_url: ReDoc URL
            openapi_url: OpenAPI schema URL
            custom_startup: Custom startup event handler (deprecated, use lifespan instead)
            custom_shutdown: Custom shutdown event handler (deprecated, use lifespan instead)
            lifespan: Async context manager for app lifecycle (FastAPI 0.93+)
        
        Returns:
            Configured FastAPI application
        """
        # Create FastAPI app
        app = FastAPI(
            title=self.title,
            version=self.version,
            docs_url=docs_url,
            redoc_url=redoc_url,
            openapi_url=openapi_url,
            lifespan=lifespan,
        )
        
        # Add middleware
        self._add_middleware(app, cors_origins, add_logging_middleware)
        
        # Add exception handlers
        if add_exception_handlers:
            setup_exception_handlers(app)
        
        # Add health routes
        if add_health_routes:
            app.include_router(health_router, tags=["System"])
        
        # Add custom routers
        if routers:
            for router in routers:
                app.include_router(router)
        
        # Add lifecycle events (deprecated, but still supported for backward compatibility)
        if custom_startup:
            app.add_event_handler("startup", custom_startup)
        if custom_shutdown:
            app.add_event_handler("shutdown", custom_shutdown)
        
        logger.info(f"Created FastAPI app: {self.title} v{self.version}")
        
        return app
        
        # Add health routes
        if add_health_routes:
            app.include_router(health_router, tags=["System"])
        
        # Add custom routers
        if routers:
            for router in routers:
                app.include_router(router)
        
        # Add lifecycle events
        if custom_startup:
            app.add_event_handler("startup", custom_startup)
        if custom_shutdown:
            app.add_event_handler("shutdown", custom_shutdown)
        
        logger.info(f"Created FastAPI app: {self.title} v{self.version}")
        
        return app
    
    def _add_middleware(
        self,
        app: FastAPI,
        cors_origins: Optional[List[str]] = None,
        add_logging: bool = True
    ) -> None:
        """
        Add middleware to the application
        
        Order matters: innermost middleware processes requests last
        1. LoggingMiddleware (runs first for requests, last for responses)
        2. CORSMiddleware (handles CORS)
        
        Args:
            app: FastAPI application
            cors_origins: CORS allowed origins
            add_logging: Whether to add logging middleware
        """
        # CORS middleware
        cors_config = cors_origins or self.config.cors_origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_config,
            allow_credentials=self.config.cors_credentials,
            allow_methods=self.config.cors_methods,
            allow_headers=self.config.cors_headers,
        )
        
        # Logging middleware
        if add_logging:
            app.add_middleware(LoggingMiddleware)
        
        logger.info(f"Configured middleware for {self.title}")
