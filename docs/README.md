# ITL ControlPlane SDK - Documentation Index

Complete documentation for the ITL ControlPlane SDK, organized by topic.

---

## 📚 Getting Started

Start here to understand the core concepts and architecture of the SDK.

### 1. [Scoped Resource Handler](./01-SCOPED_RESOURCE_HANDLER.md)
**What**: Complete guide to scope-aware resource management  
**Topics**: Uniqueness scopes, duplicate detection, storage keys, resource IDs  
**For**: Understanding how resources are managed across different scopes

### 2. [Resource ID Strategy](./02-RESOURCE_ID_STRATEGY.md)
**What**: Hybrid path + GUID resource identification  
**Topics**: Path-based IDs, GUIDs, hierarchical structure  
**For**: Understanding resource identification and addressing

### 3. [Modular Architecture](./03-MODULAR_ARCHITECTURE.md)
**What**: Module organization and design patterns  
**Topics**: Layer separation, dependency management, extensibility  
**For**: Understanding the SDK's modular structure

### 4. [Architecture Overview](./04-ARCHITECTURE.md)
**What**: Detailed SDK architecture and components  
**Topics**: Core layers, provider framework, identity integration  
**For**: Deep dive into SDK architecture and design decisions

---

## 🌐 FastAPI Integration

HTTP layer integration with FastAPI framework.

### 5. [FastAPI Module](./05-FASTAPI_MODULE.md)
**What**: Complete FastAPI integration guide  
**Topics**: App factory, middleware, routes, configuration  
**For**: Adding HTTP endpoints to your resource providers

### 6. [FastAPI Integration](./06-FASTAPI_INTEGRATION.md)
**What**: Integration patterns and examples  
**Topics**: Provider integration, error handling, custom routes  
**For**: Practical FastAPI integration patterns

### 7. [FastAPI Quick Reference](./07-FASTAPI_QUICK_REFERENCE.md)
**What**: FastAPI API quick reference  
**Topics**: Common tasks, middleware setup, route configuration  
**For**: Quick lookup of FastAPI integration patterns

---

## 🔧 CI/CD & Operations

Continuous integration, deployment, and version management.

### 8. [Pipeline Setup](./08-PIPELINE_SETUP.md)
**What**: Complete CI/CD pipeline documentation  
**Topics**: GitHub Actions, testing, publishing, security  
**For**: Setting up automated testing and publishing

### 9. [Automated Versioning](./09-AUTOMATED_VERSIONING.md)
**What**: Git tag-based version management  
**Topics**: Semantic versioning, tag creation, automated bumps  
**For**: Managing SDK versions with Git tags

### 10. [Version Update Guide](./10-VERSIONING_UPDATE.md)
**What**: Version update procedures  
**Topics**: Release process, changelog, breaking changes  
**For**: Updating versions and creating releases

---

## 🏗️ Resource Group & Handlers

Resource group implementation and handler patterns.

### 11. [Resource Group Creation Flow](./11-RESOURCE_GROUP_CREATION_FLOW.md)
**What**: Step-by-step RG creation process  
**Topics**: Validation, timestamps, provisioning states, storage  
**For**: Understanding what happens when creating a resource group

### 12. [Resource Group Big 3 Integration](./12-RESOURCE_GROUP_BIG_3_INTEGRATION.md)
**What**: Resource group with handler mixins  
**Topics**: Timestamps, provisioning states, validation integration  
**For**: See how Big 3 mixins work in production

### 13. [Scoped Resources Overview](./13-SCOPED_RESOURCES_OVERVIEW.md)
**What**: Comprehensive scoped resource guide  
**Topics**: Architecture, usage patterns, storage keys, examples  
**For**: Complete understanding of scoped resource system

---

## ⚡ Quick References

Fast lookup guides for common tasks.

### 14. [Quick Reference](./14-QUICK_REFERENCE.md)
**What**: SDK API quick reference  
**Topics**: Common tasks, scope configuration, API calls  
**For**: Quick lookup of SDK APIs and patterns

### 15. [Big 3 Quick Reference](./15-QUICK_REFERENCE_BIG_3.md)
**What**: Handler mixin quick reference  
**Topics**: Timestamps, provisioning states, validation usage  
**For**: Quick lookup of handler mixin features

---

## 📍 Location Management

Dynamic location validation and management.

### 16. [Locations Handler](./16-LOCATIONS_HANDLER.md)
**What**: Location handler implementation guide  
**Topics**: Azure regions, validation, region grouping  
**For**: Understanding dynamic location management

### 17. [Big 3 Implementation](./17-BIG_3_IMPLEMENTATION.md)
**What**: Complete handler mixin implementation  
**Topics**: Mixin pattern, MRO, integration testing  
**For**: Deep dive into handler mixin implementation

### 18. [ITL Locations Schema](./18-ITL_LOCATIONS_SCHEMA.md)
**What**: Custom ITL location validation  
**Topics**: ITL regions, custom locations, validation  
**For**: Using custom ITL location schema

### 19. [Dynamic Locations Summary](./19-DYNAMIC_LOCATIONS_SUMMARY.md)
**What**: Dynamic location management overview  
**Topics**: LocationsHandler, region metadata, validation  
**For**: Quick overview of dynamic location features

### 20. [Dynamic Locations Complete](./20-DYNAMIC_LOCATIONS_COMPLETE.md)
**What**: Complete location system documentation  
**Topics**: Implementation, usage, testing, migration  
**For**: Complete reference for location management

---

## 🎯 Advanced Topics

Deep dives into advanced features and patterns.

### 21. [Big 3 Summary](./21-BIG_3_SUMMARY.md)
**What**: Handler mixin feature summary  
**Topics**: TimestampedResourceHandler, ProvisioningStateHandler, ValidatedResourceHandler  
**For**: Understanding the three core handler mixins

### 22. [Big 3 Complete Summary](./22-BIG_3_COMPLETE_SUMMARY.md)
**What**: Detailed handler mixin documentation  
**Topics**: Implementation details, testing, performance, integration  
**For**: Complete reference for handler mixins

### 23. [Architecture Summary](./23-ARCHITECTURE_SUMMARY.md)
**What**: Quick architecture overview  
**Topics**: Core abstractions, scope configuration, storage format  
**For**: Quick architecture reference

---

## 📖 Documentation by Use Case

### I want to create a new resource provider
1. Start with [Architecture Overview](./04-ARCHITECTURE.md)
2. Read [Scoped Resource Handler](./01-SCOPED_RESOURCE_HANDLER.md)
3. Review [Big 3 Summary](./21-BIG_3_SUMMARY.md)
4. Use [Quick Reference](./14-QUICK_REFERENCE.md) for API calls

### I want to add HTTP endpoints
1. Read [FastAPI Module](./05-FASTAPI_MODULE.md)
2. Review [FastAPI Integration](./06-FASTAPI_INTEGRATION.md)
3. Use [FastAPI Quick Reference](./07-FASTAPI_QUICK_REFERENCE.md)

### I want to implement location validation
1. Start with [Locations Handler](./16-LOCATIONS_HANDLER.md)
2. Review [Dynamic Locations Complete](./20-DYNAMIC_LOCATIONS_COMPLETE.md)
3. Check [ITL Locations Schema](./18-ITL_LOCATIONS_SCHEMA.md) for custom locations

### I want to set up CI/CD
1. Read [Pipeline Setup](./08-PIPELINE_SETUP.md)
2. Review [Automated Versioning](./09-AUTOMATED_VERSIONING.md)
3. Follow [Version Update Guide](./10-VERSIONING_UPDATE.md)

### I want to understand resource groups
1. Read [Resource Group Creation Flow](./11-RESOURCE_GROUP_CREATION_FLOW.md)
2. Review [Resource Group Big 3 Integration](./12-RESOURCE_GROUP_BIG_3_INTEGRATION.md)
3. Check [Scoped Resources Overview](./13-SCOPED_RESOURCES_OVERVIEW.md)

---

## 🔗 External Resources

- **[Main README](../README.md)** - Project overview and quick start
- **[Examples Directory](../examples/)** - Working code examples
- **[PyPI Setup Guide](../.github/PYPI_SETUP.md)** - Package publishing
- **[Test Suite](../tests/)** - Comprehensive test examples

---

## 📝 Document Conventions

- **Numbered Docs (01-23)**: Core documentation in recommended reading order
- **Topics Section**: Quick overview of document contents
- **For Section**: Who should read this and why
- **Code Examples**: Inline examples throughout all documents
- **Cross-References**: Links to related documents

---

## 🆘 Need Help?

1. **Quick Task**: Check [Quick Reference](./14-QUICK_REFERENCE.md) or [Big 3 Quick Reference](./15-QUICK_REFERENCE_BIG_3.md)
2. **Understanding Concepts**: Start with [Getting Started](#-getting-started) section
3. **Implementation Details**: Check [Advanced Topics](#-advanced-topics) section
4. **Integration**: See [FastAPI Integration](#-fastapi-integration) or [Location Management](#-location-management)
5. **Operations**: Review [CI/CD & Operations](#-cicd--operations) section

---

**Last Updated**: February 3, 2026  
**SDK Version**: 1.0.0
