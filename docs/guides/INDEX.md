# Development Guides Index

Complete reference for comprehensive guide collection on SDK usage, patterns, and operations.

---

## Quick Navigation

### Getting Started
- **[09-QUICK_START.md](../quick-start.md)** - 5-minute setup and your first resource

### Core Learning Path
1. **[01-GETTING_STARTED.md](../getting-started/README.md)** - SDK overview and first provider
2. **[09-QUICK_START.md](../quick-start.md)** - Fast hands-on start
3. **[03-CORE_CONCEPTS.md](../architecture/core-concepts.md)** - Fundamental concepts
4. **[06-HANDLER_MIXINS.md](../features/handler-mixins.md)** - Handler features and patterns

### Building Providers
- **[10-ADVANCED_PATTERNS.md](advanced-patterns.md)** - Complex implementation patterns
- **[11-COMMON_PATTERNS.md](common-patterns.md)** - Ready-to-use recipes (10 patterns)
- **[19-DATA_MODELING_AND_SCHEMAS.md](data-modeling-and-schemas.md)** - Schema design and databases
- **[17-REST_API_REFERENCE.md](rest-api-reference.md)** - HTTP API contract details

### Testing & Quality
- **[12-TESTING_GUIDE.md](testing-guide.md)** - Unit, integration, and E2E testing
- **[16-ERROR_HANDLING.md](error-handling.md)** - Error types and handling patterns
- **[18-CONCURRENCY_AND_ASYNC.md](concurrency-and-async.md)** - Async patterns and performance

### Operations
- **[13-DEPLOYMENT.md](deployment.md)** - Docker, Kubernetes, and production deployment
- **[14-MONITORING.md](monitoring.md)** - Logging, metrics, and observability
- **[15-TROUBLESHOOTING.md](troubleshooting.md)** - Common issues and solutions
- **[20-MIGRATION_AND_UPGRADES.md](migration-and-upgrades.md)** - Schema and SDK upgrades

---

## By Topic

### Architecture & Design
| Guide | Best For |
|-------|----------|
| [10-ADVANCED_PATTERNS.md](advanced-patterns.md) | Scope handlers, async patterns, event publishing |
| [11-COMMON_PATTERNS.md](common-patterns.md) | Delegating, caching, validating, rate-limiting, circuit breaker |
| [19-DATA_MODELING_AND_SCHEMAS.md](data-modeling-and-schemas.md) | Schema design, database choice, relationships, migrations |

### Development
| Guide | Best For |
|-------|----------|
| [09-QUICK_START.md](../quick-start.md) | First resource provider in 5 minutes |
| [16-ERROR_HANDLING.md](error-handling.md) | Error types, validation, custom responses |
| [17-REST_API_REFERENCE.md](rest-api-reference.md) | HTTP methods, status codes, request/response formats |
| [18-CONCURRENCY_AND_ASYNC.md](concurrency-and-async.md) | Async/await, concurrency control, performance tuning |

### Testing
| Guide | Best For |
|-------|----------|
| [12-TESTING_GUIDE.md](testing-guide.md) | Unit, integration, E2E tests, fixtures, coverage |

### Operations
| Guide | Best For |
|-------|----------|
| [13-DEPLOYMENT.md](deployment.md) | Docker, Kubernetes, Helm, production checklist |
| [14-MONITORING.md](monitoring.md) | Structured logging, Prometheus, health checks, tracing |
| [15-TROUBLESHOOTING.md](troubleshooting.md) | Common errors, diagnostic tools, recovery |
| [20-MIGRATION_AND_UPGRADES.md](migration-and-upgrades.md) | Schema versioning, data migrations, zero-downtime deploys |

---

## Learning Paths

### Path 1: Quick Start (30 minutes)
-> [09-QUICK_START.md](../quick-start.md)

Learn to create your first resource in 5 minutes, deploy locally, and test endpoints.

---

### Path 2: Full Getting Started (2 hours)
-> [01-GETTING_STARTED.md](../getting-started/README.md) ->  
-> [09-QUICK_START.md](../quick-start.md) ->  
-> [03-CORE_CONCEPTS.md](../architecture/core-concepts.md) ->  
-> [06-HANDLER_MIXINS.md](../features/handler-mixins.md)

Understand fundamentals, handler patterns, and mixins before diving into advanced patterns.

---

### Path 3: Complete Developer (Full week)
-> [This Index] ->  
-> [09-QUICK_START.md](../quick-start.md) ->  
-> [10-ADVANCED_PATTERNS.md](advanced-patterns.md) ->  
-> [11-COMMON_PATTERNS.md](common-patterns.md) ->  
-> [19-DATA_MODELING_AND_SCHEMAS.md](data-modeling-and-schemas.md) ->  
-> [12-TESTING_GUIDE.md](testing-guide.md) ->  
-> [18-CONCURRENCY_AND_ASYNC.md](concurrency-and-async.md) ->  
-> [13-DEPLOYMENT.md](deployment.md)

Complete comprehensive developer training covering architecture, patterns, testing, and deployment.

---

### Path 4: Operator Training (3 days)
-> [13-DEPLOYMENT.md](deployment.md) ->  
-> [14-MONITORING.md](monitoring.md) ->  
-> [20-MIGRATION_AND_UPGRADES.md](migration-and-upgrades.md) ->  
-> [15-TROUBLESHOOTING.md](troubleshooting.md)

Learn deployment, operations, monitoring, and troubleshooting for managing providers in production.

---

### Path 5: Architecture Review (4 hours)
-> [10-ADVANCED_PATTERNS.md](advanced-patterns.md) ->  
-> [11-COMMON_PATTERNS.md](common-patterns.md) ->  
-> [19-DATA_MODELING_AND_SCHEMAS.md](data-modeling-and-schemas.md) ->  
-> [16-ERROR_HANDLING.md](error-handling.md) ->  
-> [17-REST_API_REFERENCE.md](rest-api-reference.md)

Design and review resource provider architecture for correctness and best practices.

---

## Common Questions

### "I want to build my first provider"
-> [09-QUICK_START.md](../quick-start.md) (5 min)  
-> [01-GETTING_STARTED.md](../getting-started/README.md) (30 min)

### "How do I handle errors properly?"
-> [16-ERROR_HANDLING.md](error-handling.md)

### "What patterns should I use?"
-> [11-COMMON_PATTERNS.md](common-patterns.md) - choose what fits  
-> [10-ADVANCED_PATTERNS.md](advanced-patterns.md) - for complex scenarios

### "How do I test my provider?"
-> [12-TESTING_GUIDE.md](testing-guide.md)

### "How do I make it fast?"
-> [18-CONCURRENCY_AND_ASYNC.md](concurrency-and-async.md)

### "How do I deploy to Kubernetes?"
-> [13-DEPLOYMENT.md](deployment.md)

### "Things are broken, how do I fix it?"
-> [15-TROUBLESHOOTING.md](troubleshooting.md)

### "How do I upgrade the SDK?"
-> [20-MIGRATION_AND_UPGRADES.md](migration-and-upgrades.md)

### "How do I design my data model?"
-> [19-DATA_MODELING_AND_SCHEMAS.md](data-modeling-and-schemas.md)

### "What's the API contract?"
-> [17-REST_API_REFERENCE.md](rest-api-reference.md)

### "How do I monitor in production?"
-> [14-MONITORING.md](monitoring.md)

---

## All Guides at a Glance

| # | Guide | Topic | Duration | Level |
|---|-------|-------|----------|-------|
| 09 | [QUICK_START](../quick-start.md) | Getting started | 5 min | Beginner |
| 10 | [ADVANCED_PATTERNS](advanced-patterns.md) | Architecture | 30 min | Advanced |
| 11 | [COMMON_PATTERNS](common-patterns.md) | Design patterns | 20 min | Intermediate |
| 12 | [TESTING_GUIDE](testing-guide.md) | Quality assurance | 1 hour | Intermediate |
| 13 | [DEPLOYMENT](deployment.md) | Operations | 1 hour | Intermediate |
| 14 | [MONITORING](monitoring.md) | Observability | 45 min | Intermediate |
| 15 | [TROUBLESHOOTING](troubleshooting.md) | Debugging | 30 min | All levels |
| 16 | [ERROR_HANDLING](error-handling.md) | Error management | 20 min | Intermediate |
| 17 | [REST_API_REFERENCE](rest-api-reference.md) | API contract | Reference | Intermediate |
| 18 | [CONCURRENCY_AND_ASYNC](concurrency-and-async.md) | Performance | 45 min | Advanced |
| 19 | [DATA_MODELING_AND_SCHEMAS](data-modeling-and-schemas.md) | Design | 1 hour | Intermediate |
| 20 | [MIGRATION_AND_UPGRADES](migration-and-upgrades.md) | Operations | 1 hour | Intermediate |

**Total Guides:** 12 comprehensive guides  
**Total Content:** ~150KB (40,000+ words)  
**Estimated Reading:** 8-10 hours for all guides

---

## How to Use These Guides

### As a Developer
1. **First time?** Start with [QUICK_START](../quick-start.md)
2. **Building something?** Check [COMMON_PATTERNS](common-patterns.md)
3. **Complex scenario?** Read [ADVANCED_PATTERNS](advanced-patterns.md)
4. **Testing?** See [TESTING_GUIDE](testing-guide.md)
5. **Stuck?** Check [TROUBLESHOOTING](troubleshooting.md)

### As an Operator
1. **Deploying?** Start with [DEPLOYMENT](deployment.md)
2. **Monitoring?** Read [MONITORING](monitoring.md)
3. **Upgrading?** Check [MIGRATION_AND_UPGRADES](migration-and-upgrades.md)
4. **Issues?** Use [TROUBLESHOOTING](troubleshooting.md)

### As an Architect
1. **Designing system?** Start with [ADVANCED_PATTERNS](advanced-patterns.md)
2. **Data model?** Read [DATA_MODELING_AND_SCHEMAS](data-modeling-and-schemas.md)
3. **Error strategy?** Check [ERROR_HANDLING](error-handling.md)
4. **API contract?** See [REST_API_REFERENCE](rest-api-reference.md)

---

## Related Documentation

- **[SDK Overview](../README.md)** - SDK introduction and features
- **[Installation](../getting-started/README.md)** - Setup and dependencies
- **[Core Concepts](../architecture/core-concepts.md)** - Fundamental concepts
- **[Handler Mixins](../features/handler-mixins.md)** - Available handlers
- **[API Reference](rest-api-reference.md)** - Complete API documentation

---

## Contributing to Guides

Found an issue or want to add content?

1. **Report an issue** - Open GitHub issue with guide name
2. **Suggest improvement** - Create GitHub discussion
3. **Submit content** - Create pull request with additions

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-02 | Initial guide collection (12 guides) |

---

## Quick Links by Role

** Developer:**  
[QUICK_START](../quick-start.md) -> [COMMON_PATTERNS](common-patterns.md) -> [TESTING_GUIDE](testing-guide.md)

** Architect:**  
[ADVANCED_PATTERNS](advanced-patterns.md) -> [DATA_MODELING_AND_SCHEMAS](data-modeling-and-schemas.md) -> [ERROR_HANDLING](error-handling.md)

** Operator:**  
[DEPLOYMENT](deployment.md) -> [MONITORING](monitoring.md) -> [TROUBLESHOOTING](troubleshooting.md)

---

These comprehensive guides provide everything needed to build, test, deploy, and operate resource providers at production scale.

**Happy building! **
