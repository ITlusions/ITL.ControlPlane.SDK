"""
Production-grade Tenant models for ITL Control Plane.

A Tenant represents an isolated Keycloak realm that can contain multiple organizations.
This provides the top-level isolation boundary for multi-tenancy.

Design Principles:
- Type-safe with Pydantic validation
- Idempotent operations (safe to retry)
- Audit-trail enabled (created_by, created_at)
- Extensible metadata for future requirements
- Clear error semantics
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID
import secrets

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict


class TenantStatus(str, Enum):
    """Tenant lifecycle states."""

    CREATING = "creating"  # Initial state during creation
    ACTIVE = "active"  # Fully operational
    SUSPENDED = "suspended"  # Temporarily disabled
    DELETING = "deleting"  # Being deleted
    DELETED = "deleted"  # Soft-deleted (kept for audit)


class TenantSpec(BaseModel):
    """
    Request specification for creating a new tenant.

    This is the contract for creating a tenant. The control plane receives this,
    validates it, and passes it to the TenantProvider for implementation.

    IDEMPOTENCY:
    Each TenantSpec instance has a unique idempotency_key that prevents duplicate
    realm creation if the request is retried. The database should have:
        UNIQUE(idempotency_key)
    This allows safe retries - if creation fails halfway, retrying with the same
    spec will detect the partially-created realm and return it instead of creating
    a duplicate orphaned realm.

    Example:
        spec = TenantSpec(
            name="Acme Corp Tenant",
            keycloak_realm_name="acme-tenant-prod",
            contact_email="admin@acme.com",
            description="Production tenant for Acme Corporation"
        )
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name of the tenant (human-readable)",
    )

    keycloak_realm_name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        pattern="^[a-z0-9-]+$",
        description="Keycloak realm name (lowercase, alphanumeric, hyphens only)",
    )

    contact_email: EmailStr = Field(
        ...,
        description="Contact email for tenant administration",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="Optional description of the tenant",
    )

    attributes: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Custom attributes (e.g., billing_id, region, features)",
    )

    idempotency_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Unique idempotency key for preventing duplicate realm creation. Must be stored in DB with UNIQUE constraint.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Corp",
                "keycloak_realm_name": "acme-tenant-prod",
                "contact_email": "admin@acme.com",
                "description": "Production tenant",
                "attributes": {"region": "eu-west-1", "tier": "enterprise"},
            }
        }
    )

    @field_validator("keycloak_realm_name")
    @classmethod
    def validate_realm_name(cls, v: str) -> str:
        """Ensure realm name follows Keycloak conventions."""
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Realm name cannot start or end with hyphen")
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("Realm name must contain only alphanumeric chars and hyphens")
        return v


class Tenant(BaseModel):
    """
    Tenant resource representing a Keycloak realm.

    A tenant is the top-level isolation boundary in the control plane. Each tenant:
    - Has its own Keycloak realm
    - Can contain multiple organizations
    - Is completely isolated from other tenants (users, roles, metadata)
    - Has a single lifecycle (CREATING → ACTIVE → SUSPENDED/DELETING → DELETED)

    Production guarantees:
    - Immutable once created (except status changes)
    - Audit trail for all changes (created_by, created_at)
    - Soft deletion support (never truly deleted, marked as DELETED)
    - Extensible metadata for future requirements

    DATABASE CONSTRAINTS REQUIRED:
    - UNIQUE(keycloak_realm_id): Each realm maps to exactly one tenant
    - UNIQUE(keycloak_realm_name): Realm names are globally unique in Keycloak
    - UNIQUE(idempotency_key): Prevents duplicate realm creation on retry
    """

    id: str = Field(
        ...,
        description="Tenant resource ID (format: tenant-<uuid>)",
    )

    resource_id: Optional[str] = Field(
        default=None,
        description="Hybrid resource ID combining path and GUID",
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name",
    )

    keycloak_realm: str = Field(
        ...,
        description="Keycloak realm name (primary identifier)",
    )

    keycloak_realm_id: Optional[str] = Field(
        default=None,
        description="Keycloak internal realm ID (UUID)",
    )

    status: TenantStatus = Field(
        default=TenantStatus.CREATING,
        description="Current lifecycle status",
    )

    contact_email: EmailStr = Field(
        ...,
        description="Contact email for tenant administration",
    )

    description: Optional[str] = Field(
        default=None,
        description="Tenant description",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When tenant was created",
    )

    created_by: str = Field(
        ...,
        description="User ID who created this tenant (for audit trail)",
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        description="When tenant was last updated",
    )

    updated_by: Optional[str] = Field(
        default=None,
        description="User ID who last updated this tenant (for audit trail)",
    )

    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom attributes (region, tier, features, etc.)",
    )

    organization_count: int = Field(
        default=0,
        ge=0,
        description="Number of organizations in this tenant",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "tenant-550e8400-e29b-41d4-a716-446655440000",
                "resource_id": "/tenants/acme-prod/tenant-550e8400-e29b-41d4-a716-446655440000",
                "name": "Acme Corp",
                "keycloak_realm": "acme-tenant-prod",
                "keycloak_realm_id": "a7b3c4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d",
                "status": "active",
                "contact_email": "admin@acme.com",
                "description": "Production tenant for Acme Corporation",
                "created_at": "2026-01-31T10:00:00Z",
                "created_by": "system-admin-001",
                "attributes": {"region": "eu-west-1", "tier": "enterprise"},
                "organization_count": 3,
            }
        }
    )

    def is_active(self) -> bool:
        """Check if tenant is in active state."""
        return self.status == TenantStatus.ACTIVE

    def is_deletable(self) -> bool:
        """Check if tenant can be deleted."""
        return self.status in (TenantStatus.ACTIVE, TenantStatus.SUSPENDED)


class TenantResponse(BaseModel):
    """
    API response model for tenant operations.

    Separates internal representation (Tenant) from API response,
    allowing us to hide sensitive fields if needed.
    """

    id: str
    name: str
    keycloak_realm: str
    status: TenantStatus
    contact_email: EmailStr
    description: Optional[str] = None
    created_at: datetime
    organization_count: int
    attributes: Dict[str, Any] = Field(default_factory=dict)


class TenantWithOrganizations(Tenant):
    """
    Extended tenant model including organization references.

    Used when returning detailed tenant information with its organizations.
    """

    organizations: list[str] = Field(
        default_factory=list,
        description="List of organization IDs in this tenant",
    )
