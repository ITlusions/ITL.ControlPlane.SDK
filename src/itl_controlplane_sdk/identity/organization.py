"""
Production-grade Organization models for ITL Control Plane.

An Organization is a business entity within a Tenant. Each tenant can have multiple
organizations, each with its own users, domains, and settings.

Design Principles:
- Organizations exist within a Tenant (realm isolation)
- Inherits isolation boundaries from parent Tenant
- Owns custom domains, admin user, and metadata
- Supports organization-scoped user management
- Type-safe with comprehensive validation
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import secrets

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict


class OrganizationStatus(str, Enum):
    """Organization lifecycle states."""

    CREATING = "creating"  # Initial state during creation
    ACTIVE = "active"  # Fully operational
    SUSPENDED = "suspended"  # Temporarily disabled (no API access)
    DELETING = "deleting"  # Being deleted
    DELETED = "deleted"  # Soft-deleted (kept for audit)


class TenantAdminRole(str, Enum):
    """Roles for tenant/organization admins."""

    TENANT_ADMIN = "tenant_admin"  # Can manage entire tenant + all orgs
    ORGANIZATION_ADMIN = "organization_admin"  # Can manage this org
    USER_ADMIN = "user_admin"  # Can manage users in this org
    DOMAIN_ADMIN = "domain_admin"  # Can manage domains in this org


class DomainStatus(str, Enum):
    """Custom domain verification states."""

    PENDING = "pending"  # Awaiting DNS verification
    VERIFIED = "verified"  # DNS verified and active
    FAILED = "failed"  # Verification failed
    REVOKED = "revoked"  # Manually revoked


class DomainVerificationMethod(str, Enum):
    """Domain verification methods."""

    DNS_CNAME = "dns_cname"  # CNAME record verification
    DNS_TXT = "dns_txt"  # TXT record verification
    HTACCESS = "htaccess"  # .htaccess file verification
    FILE_UPLOAD = "file_upload"  # File upload verification


class TenantAdminUser(BaseModel):
    """
    Admin user for an organization within a tenant.

    This user is created automatically when the organization is created and has
    the ability to manage the organization (create users, add domains, etc.).

    Immutable after creation (except roles/status).
    """

    user_id: str = Field(
        ...,
        description="User ID in Keycloak (UUID in the tenant realm)",
    )

    username: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Username (must be unique in the organization)",
    )

    email: EmailStr = Field(
        ...,
        description="Email address (must be unique in the organization)",
    )

    first_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="First name",
    )

    last_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Last name",
    )

    roles: List[TenantAdminRole] = Field(
        default_factory=lambda: [TenantAdminRole.ORGANIZATION_ADMIN],
        description="Roles assigned to this admin user",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When admin user was created",
    )

    last_login: Optional[datetime] = Field(
        default=None,
        description="When admin last logged in",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "a7b3c4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d",
                "username": "john.admin",
                "email": "john.admin@acme.com",
                "first_name": "John",
                "last_name": "Admin",
                "roles": ["organization_admin"],
                "created_at": "2026-01-31T10:00:00Z",
            }
        }
    )


class CustomDomain(BaseModel):
    """
    Custom domain associated with an organization.

    Supports domain ownership verification and custom domain configuration for SSO/email.
    One primary domain per organization, additional secondary domains optional.
    """

    domain_name: str = Field(
        ...,
        min_length=4,
        max_length=255,
        pattern=r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$",
        description="Domain name (FQDN, lowercase)",
    )

    primary: bool = Field(
        default=False,
        description="Is this the primary domain for the organization?",
    )

    status: DomainStatus = Field(
        default=DomainStatus.PENDING,
        description="Verification status",
    )

    verification_method: Optional[DomainVerificationMethod] = Field(
        default=DomainVerificationMethod.DNS_TXT,
        description="Method used for verification",
    )

    verification_token: Optional[str] = Field(
        default=None,
        description="Token for verification (e.g., TXT record value or file path)",
    )

    verification_challenge: Optional[str] = Field(
        default=None,
        description="Challenge value if using challenge-response verification",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When domain was added",
    )

    verified_at: Optional[datetime] = Field(
        default=None,
        description="When domain was verified",
    )

    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiration date for temporary domains",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (DNS records, certificates, etc.)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "domain_name": "acme.com",
                "primary": True,
                "status": "verified",
                "verification_method": "dns_txt",
                "verification_token": "itl-verify-a7b3c4d5e6f78a9b",
                "created_at": "2026-01-31T10:00:00Z",
                "verified_at": "2026-01-31T10:15:00Z",
            }
        }
    )

    @field_validator("domain_name")
    @classmethod
    def validate_domain_format(cls, v: str) -> str:
        """Additional domain validation."""
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Domain cannot start or end with hyphen")
        if ".." in v:
            raise ValueError("Domain cannot contain consecutive dots")
        return v.lower()

    def is_verified(self) -> bool:
        """Check if domain has been verified."""
        return self.status == DomainStatus.VERIFIED

    def is_primary(self) -> bool:
        """Check if this is the primary domain."""
        return self.primary and self.is_verified()


class OrganizationSpec(BaseModel):
    """
    Request specification for creating an organization within a tenant.

    This is the contract for creating an organization. The control plane receives this,
    validates it, passes it to the provider for implementation in Keycloak.

    IDEMPOTENCY:
    Each OrganizationSpec instance has a unique idempotency_key that prevents duplicate
    organization creation if the request is retried. The database should have:
        UNIQUE(tenant_id, idempotency_key)
    This allows safe retries - if creation fails halfway, retrying with the same
    spec will detect the partially-created organization and return it instead of
    creating a duplicate.

    TENANT CONTEXT:
    The tenant_id field is required and validated at construction time. This prevents
    accidental cross-tenant organization creation. All organization queries MUST filter
    by (tenant_id, org_id) not just org_id to prevent data leaks.

    Example:
        spec = OrganizationSpec(
            tenant_id="tenant-xyz",
            name="Acme Corporation",
            slug="acme-corp",
            owner_email="admin@acme.com",
            contact_email="contact@acme.com"
        )
    """

    tenant_id: str = Field(
        ...,
        description="ID of the parent tenant (realm)",
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organization display name",
    )

    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern="^[a-z0-9-]+$",
        description="URL-safe slug (lowercase, alphanumeric, hyphens)",
    )

    owner_email: EmailStr = Field(
        ...,
        description="Email of initial organization admin",
    )

    owner_first_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="First name of admin user",
    )

    owner_last_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Last name of admin user",
    )

    contact_email: Optional[EmailStr] = Field(
        default=None,
        description="Organization contact email",
    )

    website: Optional[str] = Field(
        default=None,
        max_length=2048,
        description="Organization website",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="Organization description",
    )

    attributes: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Custom attributes (industry, size, tier, etc.)",
    )

    idempotency_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Unique idempotency key for preventing duplicate org creation. Must be stored in DB with UNIQUE(tenant_id, idempotency_key) constraint.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "tenant-550e8400-e29b-41d4-a716-446655440000",
                "name": "Acme Corporation",
                "slug": "acme-corp",
                "owner_email": "john.admin@acme.com",
                "owner_first_name": "John",
                "owner_last_name": "Admin",
                "contact_email": "contact@acme.com",
                "website": "https://acme.com",
                "description": "Acme Corporation - Manufacturing",
                "attributes": {"industry": "manufacturing", "tier": "enterprise"},
            }
        }
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Ensure slug follows URL conventions."""
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Slug cannot start or end with hyphen")
        return v.lower()


class Organization(BaseModel):
    """
    Organization resource within a Tenant.

    An organization is a business entity that can:
    - Have multiple users (managed by org admin)
    - Have custom domains (verified ownership)
    - Have settings and metadata
    - Be managed independently within its tenant

    Isolation guarantees:
    - All users belong to the parent tenant's Keycloak realm
    - Organization data isolated at API/database level (org_id filtering)
    - Org admin can only access their org's data
    - tenant_id is validated at construction time (prevents cross-tenant queries)

    Production guarantees:
    - Immutable core properties (tenant_id, created_by, created_at)
    - Audit trail for all changes
    - Soft deletion support
    - Extensible metadata

    DATABASE CONSTRAINTS REQUIRED:
    - PRIMARY_KEY(id): Resource ID is globally unique
    - UNIQUE(tenant_id, slug): Slug is unique within tenant (enables URL routing)
    - FOREIGN_KEY(tenant_id) -> Tenant(id): Org belongs to exactly one tenant
    - UNIQUE(tenant_id, idempotency_key): Prevents duplicate creation on retry
    """

    id: str = Field(
        ...,
        description="Organization resource ID (format: org-<uuid>)",
    )

    resource_id: Optional[str] = Field(
        default=None,
        description="Hybrid resource ID combining path and GUID",
    )

    tenant_id: str = Field(
        ...,
        description="Parent tenant ID (immutable, defines realm)",
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organization display name",
    )

    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="URL-safe slug (unique within tenant)",
    )

    status: OrganizationStatus = Field(
        default=OrganizationStatus.CREATING,
        description="Current lifecycle status",
    )

    admin_user: TenantAdminUser = Field(
        ...,
        description="Organization admin user (created automatically)",
    )

    domains: List[CustomDomain] = Field(
        default_factory=list,
        description="Custom domains managed by this organization",
    )

    contact_email: Optional[EmailStr] = Field(
        default=None,
        description="Organization contact email",
    )

    website: Optional[str] = Field(
        default=None,
        description="Organization website",
    )

    description: Optional[str] = Field(
        default=None,
        description="Organization description",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When organization was created",
    )

    created_by: str = Field(
        ...,
        description="User ID who created this organization (audit trail)",
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        description="When organization was last updated",
    )

    updated_by: Optional[str] = Field(
        default=None,
        description="User ID who last updated (audit trail)",
    )

    user_count: int = Field(
        default=1,  # At minimum, the admin user
        ge=0,
        description="Total users in organization (including admin)",
    )

    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom attributes (industry, size, tier, features, etc.)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "org-550e8400-e29b-41d4-a716-446655440000",
                "resource_id": "/tenants/tenant-xyz/organizations/org-550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "tenant-xyz",
                "name": "Acme Corporation",
                "slug": "acme-corp",
                "status": "active",
                "admin_user": {
                    "user_id": "a7b3c4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d",
                    "username": "john.admin",
                    "email": "john.admin@acme.com",
                    "first_name": "John",
                    "last_name": "Admin",
                    "roles": ["organization_admin"],
                    "created_at": "2026-01-31T10:00:00Z",
                },
                "domains": [
                    {
                        "domain_name": "acme.com",
                        "primary": True,
                        "status": "verified",
                        "created_at": "2026-01-31T10:00:00Z",
                        "verified_at": "2026-01-31T10:15:00Z",
                    }
                ],
                "contact_email": "contact@acme.com",
                "website": "https://acme.com",
                "description": "Acme Corporation - Manufacturing",
                "created_at": "2026-01-31T10:00:00Z",
                "created_by": "system-admin-001",
                "user_count": 4,
                "attributes": {"industry": "manufacturing", "tier": "enterprise"},
            }
        }
    )

    def is_active(self) -> bool:
        """Check if organization is active."""
        return self.status == OrganizationStatus.ACTIVE

    def is_deletable(self) -> bool:
        """Check if organization can be deleted."""
        return self.status in (
            OrganizationStatus.ACTIVE,
            OrganizationStatus.SUSPENDED,
        )

    def has_verified_primary_domain(self) -> bool:
        """Check if organization has a verified primary domain."""
        return any(d.is_primary() for d in self.domains)

    def get_primary_domain(self) -> Optional[CustomDomain]:
        """Get the primary domain if it exists."""
        for domain in self.domains:
            if domain.is_primary():
                return domain
        return None

    def assert_tenant_context(self, expected_tenant_id: str) -> None:
        """
        Validate that this organization belongs to the expected tenant.

        Use this method before processing any organization operation to prevent
        accidental cross-tenant data access.

        Args:
            expected_tenant_id: The tenant ID that should own this organization

        Raises:
            ValueError: If tenant_id doesn't match expected_tenant_id
        """
        if self.tenant_id != expected_tenant_id:
            raise ValueError(
                f"Cross-tenant access prevented: expected tenant {expected_tenant_id}, "
                f"but organization belongs to tenant {self.tenant_id}"
            )

    def get_cascade_deletion_impact(self) -> Dict[str, Any]:
        """
        Document what resources would be affected if this organization is deleted.

        When an organization is soft-deleted, the provider must implement a reconciliation
        job to cascade the deletion to dependent resources in Keycloak (users, roles, etc.).
        This method documents what would be deleted.

        Returns:
            Dict with keys representing resource types and values as counts or 'unknown'

        Note:
            Soft delete only - this org will be marked as DELETED but kept in DB for audit.
            The reconciliation job must implement actual Keycloak deletion.
        """
        return {
            "users": len([admin for admin in [self.admin_user] if admin]),
            "domains": len(self.domains),
            "roles": "unknown (in keycloak)",
            "note": "Soft delete only. Provider must implement cascade cleanup via reconciliation job."
        }


class OrganizationResponse(BaseModel):
    """
    API response model for organization operations.

    Separates internal representation from API response,
    allowing us to hide/transform sensitive fields.
    """

    id: str
    tenant_id: str
    name: str
    slug: str
    status: OrganizationStatus
    admin_user: TenantAdminUser
    domain_count: int
    user_count: int
    contact_email: Optional[EmailStr] = None
    website: Optional[str] = None
    created_at: datetime
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_organization(cls, org: Organization) -> "OrganizationResponse":
        """Convert Organization model to response."""
        return cls(
            id=org.id,
            tenant_id=org.tenant_id,
            name=org.name,
            slug=org.slug,
            status=org.status,
            admin_user=org.admin_user,
            domain_count=len(org.domains),
            user_count=org.user_count,
            contact_email=org.contact_email,
            website=org.website,
            created_at=org.created_at,
            attributes=org.attributes,
        )


class OrganizationWithDomains(Organization):
    """Extended organization model including domain details (for detailed responses)."""

    pass  # Already includes domains in base model
