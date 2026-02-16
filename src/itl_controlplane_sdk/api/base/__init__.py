"""
Core FastAPI app infrastructure.

Provides app factory, configuration, and shared models.
"""

from .app_factory import AppFactory
from .config import FastAPIConfig
from .models import (
    GenericResourceBase,
    GenericResourceRequest,
    GenericResourceResponse,
)

__all__ = [
    "AppFactory",
    "FastAPIConfig",
    "GenericResourceBase",
    "GenericResourceRequest",
    "GenericResourceResponse",
]
