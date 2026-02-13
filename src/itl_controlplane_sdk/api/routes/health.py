"""
Health check routes for FastAPI applications.

Provides standard /health and /ready endpoints for monitoring
application status and readiness for requests.
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns 200 OK if the service is healthy and running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint.
    
    Returns 200 OK if the service is ready to handle requests.
    """
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
