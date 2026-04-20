# IAM Module: Implementation Roadmap

**Status**: In Progress (CP-IAM-001 partially complete)  
**Version**: 1.0  
**Created**: 2026-04-20  
**Issues**: [#1](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/1) · [#2](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/2) · [#3](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/3) · [#4](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/4) · [#5](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/5) · [#6](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/6)

---

## Overview

The IAM module adds identity and access management capabilities to the SDK. It wraps Keycloak 24.x as the identity provider and provides a complete authentication stack for multi-tenant resource providers.

**Module path**: `src/itl_sdk/iam/`

**Architecture**:

```
KeycloakClientWrapper        ← Keycloak Admin REST API client
TokenManager                 ← Token caching + automatic renewal
ServiceAuthClient            ← Authenticated HTTP client for S2S calls
TenantRegistry               ← Multi-tenant realm provisioning
```

---

## CP-IAM-001: Keycloak Client Wrapper — `#1`

**Status**: In Progress (SDK partially implemented — review current state)  
**File**: `src/itl_sdk/iam/keycloak_client.py`  
**Label**: enhancement · Project: IAM Implementation (In Progress)

### What it does

Typed Python wrapper for Keycloak Admin REST API. Foundation for all other IAM components.

**Scope**:
- `KeycloakConfig` dataclass — connection settings (base_url, realm, client_id, client_secret)
- `RealmRepresentation` dataclass — realm creation config
- `KeycloakClientWrapper` — async HTTP client with:
  - `authenticate()` — client credentials grant → admin token
  - `create_realm()` / `get_realm()` / `delete_realm()`
  - `create_client()` — OAuth2 client registration with service account support
  - `assign_realm_role()` — user role assignment
  - `close()` — clean HTTP connection teardown

**Keycloak version**: 24.x with OpenID Connect 1.0 / OAuth 2.0

### Acceptance Criteria

- [ ] `KeycloakConfig` contains all connection settings
- [ ] `authenticate()` obtains admin token via client credentials grant
- [ ] `create_realm()` creates realm with correct SSL and login settings
- [ ] `get_realm()`, `delete_realm()` implemented
- [ ] `create_client()` supports service accounts (for S2S auth)
- [ ] `assign_realm_role()` implemented
- [ ] `close()` closes HTTP connection cleanly

---

## CP-IAM-002: Token Lifecycle Management — `#2` / `#3`

**Status**: Open  
**File**: `src/itl_sdk/iam/token_manager.py`

### What it does

In-memory token cache with automatic refresh. Prevents redundant token requests across the service.

**Scope**:
- `TokenEntry` dataclass — `access_token`, `refresh_token`, `expires_at`, `realm`, `client_id`
- `TokenManager` — async cache with:
  - `get_token(realm, client_id, client_secret)` — returns cached or freshly acquired token
  - `_refresh_token()` — renews via Keycloak refresh_token grant
  - `invalidate(realm, client_id)` — removes entry (called on 401)
  - `close()` — HTTP teardown

**Cache key**: `"{realm}:{client_id}"`

**Token renewal trigger**: `expires_at - 60s` (60s safety buffer before expiry)

### Acceptance Criteria

- [ ] Cache hit returns token without Keycloak request
- [ ] Expired token triggers `_refresh_token()` automatically
- [ ] `invalidate()` removes cache entry
- [ ] 401 response from downstream triggers invalidate + 1 retry
- [ ] Thread-safe (asyncio lock on token refresh)

---

## CP-IAM-003: Service-to-Service Auth — `#4`

**Status**: Open  
**File**: `src/itl_sdk/iam/service_auth.py`  
**Note**: Build on ITLAuth PKCE flow and client credentials support

### What it does

Authenticated `httpx.AsyncClient` that transparently adds Bearer tokens to every outbound request. Used by resource providers calling other services.

**Scope**:
- `ServiceConfig` dataclass — `base_url`, `realm`, `client_id`, `client_secret`
- `ServiceAuthTransport` — custom httpx transport that injects `Authorization: Bearer {token}`
- `ServiceAuthClient` — context manager wrapping `ServiceAuthTransport` + `TokenManager`
  - `get()`, `post()`, `put()`, `delete()` — HTTP verbs
  - 401 → `TokenManager.invalidate()` + 1 retry

**Dependency**: Builds on `TokenManager` (#2) and ITLAuth PKCE patterns

### Acceptance Criteria

- [ ] `ServiceAuthTransport` adds Bearer token to every request
- [ ] Token automatically renewed via `TokenManager`
- [ ] `ServiceAuthClient` works as async context manager
- [ ] `get()`, `post()`, `put()`, `delete()` implemented
- [ ] 401 triggers token invalidation + retry (1x only)

---

## CP-IAM-004: Multi-Tenant Support — `#5`

**Status**: Open  
**File**: `src/itl_sdk/iam/multi_tenant.py`

### What it does

Tenant lifecycle management. Each tenant gets an isolated Keycloak realm. Realm names follow the convention `tenant-{tenant_id}`.

**Scope**:
- `TenantInfo` dataclass — `tenant_id`, `realm`, `status`, `created_at`, `display_name`
- `TenantRegistry` — async service:
  - `register_tenant(tenant_id, display_name)` → creates Keycloak realm
  - `get_tenant(tenant_id)` → fetch tenant info
  - `deactivate_tenant(tenant_id)` → disables realm (soft delete)
  - `validate_tenant_id(tenant_id)` → normalizes UUID, raises on invalid

**Tenant ID format**: lowercase UUID v4 (`a1b2c3d4-e5f6-7890-abcd-ef1234567890`)  
**Realm naming**: `tenant-{tenant_id}`

### Acceptance Criteria

- [ ] `register_tenant()` creates Keycloak realm named `tenant-{tenant_id}`
- [ ] `get_tenant()` returns `TenantInfo` or raises on not found
- [ ] `deactivate_tenant()` disables realm without deleting data
- [ ] `validate_tenant_id()` normalizes case, rejects non-UUID strings
- [ ] Duplicate registration is idempotent (returns existing)

---

## CP-IAM-005: Auth Integration & Testing — `#6`

**Status**: Open  
**Files**: `tests/iam/`  
**Note**: Validate full integration with ITLAuth authentication patterns and token flows

### What it does

End-to-end test suite for the IAM stack using `testcontainers` to spin up real Keycloak 24.x.

**Test files**:
```
tests/iam/
├── conftest.py              ← Keycloak container fixture (session-scoped)
├── test_integration.py      ← Full stack E2E tests
├── test_token_manager.py    ← TokenManager unit tests
└── test_multi_tenant.py     ← TenantRegistry integration tests
```

**Key test scenarios**:
- `TokenManager` — cache hit, cache miss, expired token renewal, `invalidate()`
- `TenantRegistry` — register creates realm, `validate_tenant_id()` rejects invalid / normalizes case
- E2E — authenticate → create realm → register client → assign role → validate token

**Test dependencies**:
```toml
[project.optional-dependencies]
test = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "testcontainers[keycloak]>=4.0",
]
```

### Acceptance Criteria

- [ ] `conftest.py` starts Keycloak 24.x via testcontainers
- [ ] TokenManager cache hit/miss/expired tests pass
- [ ] `invalidate()` test passes
- [ ] `TenantRegistry.validate_tenant_id()` tests: valid / invalid / case normalization
- [ ] Integration test for `register_tenant()` creates real Keycloak realm
- [ ] `pytest -x tests/iam/` passes completely
- [ ] ITLAuth PKCE integration validated in E2E flow

---

## Implementation Order

```
CP-IAM-001  KeycloakClientWrapper    ← Foundation (partially done)
    ↓
CP-IAM-002  TokenManager             ← Builds on nothing
    ↓
CP-IAM-003  ServiceAuthClient        ← Depends on TokenManager + ITLAuth
    ↓
CP-IAM-004  TenantRegistry           ← Depends on KeycloakClientWrapper
    ↓
CP-IAM-005  Integration Tests        ← Validates entire stack
```

---

## Module Layout

```
src/itl_sdk/iam/
├── __init__.py
├── keycloak_client.py     ← CP-IAM-001
├── token_manager.py       ← CP-IAM-002
├── service_auth.py        ← CP-IAM-003
└── multi_tenant.py        ← CP-IAM-004
```
