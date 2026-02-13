"""
FastAPI Configuration

Centralized configuration for FastAPI applications in ITL ControlPlane.
"""

from typing import List
from dataclasses import dataclass, field


@dataclass
class FastAPIConfig:
    """
    Configuration for FastAPI applications
    
    Attributes:
        cors_origins: CORS allowed origins
        cors_credentials: Allow credentials in CORS
        cors_methods: Allowed HTTP methods for CORS
        cors_headers: Allowed headers for CORS
        log_level: Logging level
        enable_metrics: Enable metrics collection
        enable_tracing: Enable request tracing
    """
    
    # CORS Configuration
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_credentials: bool = True
    cors_methods: List[str] = field(default_factory=lambda: ["*"])
    cors_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # Logging
    log_level: str = "INFO"
    
    # Features
    enable_metrics: bool = False
    enable_tracing: bool = False
    
    @classmethod
    def production(cls) -> "FastAPIConfig":
        """Create production configuration"""
        return cls(
            cors_origins=["https://example.com"],  # Update as needed
            cors_credentials=True,
            log_level="WARNING",
            enable_metrics=True,
            enable_tracing=True,
        )
    
    @classmethod
    def development(cls) -> "FastAPIConfig":
        """Create development configuration"""
        return cls(
            cors_origins=["*"],
            cors_credentials=True,
            log_level="DEBUG",
            enable_metrics=True,
            enable_tracing=False,
        )
