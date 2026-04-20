# ITL ControlPlane SDK — Documentation

> **Root docs:** [quick-start.md](./quick-start.md) · [quick-reference.md](./quick-reference.md)  
> **Onboarding:** [getting-started/](./getting-started/README.md)

---

## Structure

```
docs/
├── quick-start.md          ← Start here (new to the SDK)
├── quick-reference.md      ← Handler API cheat-sheet
├── getting-started/        ← Installation, 5-min example, key concepts
│
├── architecture/           ← System design & internals
├── features/               ← Feature-specific guides
├── guides/                 ← How-to guides, patterns, operations
├── ci-cd/                  ← CI/CD pipelines & versioning
├── roadmap/                ← Planned features & design docs
│
└── archive/                ← Superseded docs (historical reference)
```

---

## Architecture

| File | Description |
|------|-------------|
| [architecture/architecture.md](./architecture/architecture.md) | Complete system architecture, components, design principles |
| [architecture/core-concepts.md](./architecture/core-concepts.md) | Scoped handlers, resource ID strategy, modular architecture |

---

## Features

| File | Description |
|------|-------------|
| [features/resource-groups.md](./features/resource-groups.md) | Resource group creation, scoped uniqueness, extensibility |
| [features/handler-mixins.md](./features/handler-mixins.md) | Big 3: TimestampedResourceHandler, ProvisioningStateHandler, ValidatedResourceHandler |
| [features/location-validation.md](./features/location-validation.md) | LocationsHandler, 30+ Azure regions, 24 ITL custom locations |
| [features/api-endpoints.md](./features/api-endpoints.md) | FastAPI integration, AppFactory, middleware, HTTP routing |
| [features/async-patterns.md](./features/async-patterns.md) | Service Bus, async provider modes, message queuing |
| [features/worker-roles.md](./features/worker-roles.md) | Job queue, worker lifecycle, async offloading, scaling |

---

## How-To Guides

| File | Description |
|------|-------------|
| [guides/advanced-patterns.md](./guides/advanced-patterns.md) | Advanced handler patterns and composition |
| [guides/common-patterns.md](./guides/common-patterns.md) | Common development patterns |
| [guides/testing-guide.md](./guides/testing-guide.md) | Unit & integration testing strategies |
| [guides/deployment.md](./guides/deployment.md) | Kubernetes, Docker, environment configuration |
| [guides/monitoring.md](./guides/monitoring.md) | Observability, metrics, health checks |
| [guides/troubleshooting.md](./guides/troubleshooting.md) | Common issues and solutions |
| [guides/error-handling.md](./guides/error-handling.md) | Error handling patterns and best practices |
| [guides/rest-api-reference.md](./guides/rest-api-reference.md) | REST API conventions and reference |
| [guides/concurrency-and-async.md](./guides/concurrency-and-async.md) | Concurrency patterns and async usage |
| [guides/data-modeling-and-schemas.md](./guides/data-modeling-and-schemas.md) | Pydantic models, schemas, validation |
| [guides/migration-and-upgrades.md](./guides/migration-and-upgrades.md) | Version migration and upgrade procedures |
| [guides/seeding-guide.md](./guides/seeding-guide.md) | Database seeding and seed data management |
| [guides/tenant-realm-id-integration.md](./guides/tenant-realm-id-integration.md) | Tenant/realm ID integration guide |
| [guides/full-documentation-reference.md](./guides/full-documentation-reference.md) | Lifecycle hooks full reference |

---

## CI/CD & Versioning

| File | Description |
|------|-------------|
| [ci-cd/ci-cd-pipelines.md](./ci-cd/ci-cd-pipelines.md) | GitHub Actions workflows, automated versioning, PyPI publishing |

---

## Roadmap & Design

| File | Description |
|------|-------------|
| [roadmap/mixin-design-roadmap.md](./roadmap/mixin-design-roadmap.md) | Strategic plan for 11 advanced handler mixins (Tiers 1-3) |
| [roadmap/lifecycle-hooks-integration.md](./roadmap/lifecycle-hooks-integration.md) | Lifecycle hooks integration design |
| [roadmap/iam-implementation.md](./roadmap/iam-implementation.md) | IAM module: Keycloak wrapper, tokens, S2S auth, multi-tenant (#1–#6) |
| [roadmap/resource-id-scopes.md](./roadmap/resource-id-scopes.md) | UniquenessScope fixes and new scopes: SUBSCRIPTION_ONLY, PARENT_RESOURCE (#7–#10) |
| [roadmap/pulumi-integration.md](./roadmap/pulumi-integration.md) | Pulumi dual-target components and standalone package (#11–#12) |

---

## External Resources

- **[../README.md](../README.md)** — Project overview and quick start
- **[../examples/](../examples/README.md)** — Working code examples
- **[../.github/PYPI_SETUP.md](../.github/PYPI_SETUP.md)** — PyPI publishing setup
- **[archive/README.md](./archive/README.md)** — Legacy docs and consolidation history

---

**Last Updated**: April 20, 2026 · **SDK Version**: 1.x
