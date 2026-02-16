"""
Re-export models for backward compatibility and Alembic/migration support.

This module provides a common import path for the Base SQLAlchemy metadata
used by migrations and model definitions.
"""

from .data.models import Base

__all__ = [
    "Base",
]
