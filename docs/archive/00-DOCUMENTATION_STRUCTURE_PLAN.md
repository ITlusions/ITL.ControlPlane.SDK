# ITL ControlPlane SDK - Documentation Structure Plan

**Status**:  Strategic Plan  
**Date**: February 14, 2026  
**Purpose**: Consolidate, organize, and streamline 26 documentation files into a coherent hierarchy

---

## Current State Analysis

### Problems Identified

1. **Duplicate Content** (Consolidate These)
   - Big 3 Handlers: `17-BIG_3_IMPLEMENTATION.md`, `21-BIG_3_SUMMARY.md`, `22-BIG_3_COMPLETE_SUMMARY.md`
   - Locations: `16-LOCATIONS_HANDLER.md`, `18-ITL_LOCATIONS_SCHEMA.md`, `19-DYNAMIC_LOCATIONS_SUMMARY.md`, `20-DYNAMIC_LOCATIONS_COMPLETE.md`
   - Quick References: `07-FASTAPI_QUICK_REFERENCE.md`, `14-QUICK_REFERENCE.md`, `15-QUICK_REFERENCE_BIG_3.md`
   - Architecture: `04-ARCHITECTURE.md`, `23-ARCHITECTURE_SUMMARY.md`
   - Versioning: `09-AUTOMATED_VERSIONING.md`, `10-VERSIONING_UPDATE.md`

2. **Numbering Conflicts** (Fix These)
   - Files 20-23 have multiple documents with same number:
     - 20: `20-DYNAMIC_LOCATIONS_COMPLETE.md` + `20-WORKER_ROLE_INDEX.md`
     - 21: `21-BIG_3_SUMMARY.md` + `21-WORKER_ROLE_ARCHITECTURE.md`
     - 22: `22-BIG_3_COMPLETE_SUMMARY.md` + `22-WORKER_ROLE_QUICK_START.md`
     - 23: `23-ARCHITECTURE_SUMMARY.md` + `23-WORKER_ROLE_API_REFERENCE.md`

3. **Missing from README** (New Topics Added)
   - Worker Role System (multiple files)
   - Service Bus Provider Mode (25, 26)
   - Message Queue & Async Patterns

4. **Legacy Content** (Archive These)
   - 09-10: Versioning (outdated after automated versioning)
   - Some "summary" docs that duplicate detailed docs

---

## Current Document Inventory

### By Feature Area

**Core Architecture (4 docs)**
- `01-SCOPED_RESOURCE_HANDLER.md` 
- `02-RESOURCE_ID_STRATEGY.md` 
- `03-MODULAR_ARCHITECTURE.md` 
- `04-ARCHITECTURE.md` 

**HTTP/FastAPI (3 docs)**
- `05-FASTAPI_MODULE.md` 
- `06-FASTAPI_INTEGRATION.md` 
- `07-FASTAPI_QUICK_REFERENCE.md` 

**CI/CD & Versioning (3 docs)**
- `08-PIPELINE_SETUP.md` 
- `09-AUTOMATED_VERSIONING.md`  (duplicate with 10)
- `10-VERSIONING_UPDATE.md`  (duplicate with 09)

**Resource Groups & Handlers (5 docs)**
- `11-RESOURCE_GROUP_CREATION_FLOW.md` 
- `12-RESOURCE_GROUP_BIG_3_INTEGRATION.md` 
- `13-SCOPED_RESOURCES_OVERVIEW.md` 
- `14-QUICK_REFERENCE.md`  (overlaps with 15)
- `15-QUICK_REFERENCE_BIG_3.md`  (overlaps with 14)

**Locations & Validation (4 docs)**
- `16-LOCATIONS_HANDLER.md`  (overlaps with 19, 20)
- `17-BIG_3_IMPLEMENTATION.md`  (overlaps with 21, 22)
- `18-ITL_LOCATIONS_SCHEMA.md`  (overlaps with 16)
- `19-DYNAMIC_LOCATIONS_SUMMARY.md`  (overlaps with 20)
- `20-DYNAMIC_LOCATIONS_COMPLETE.md`  (overlaps with 16, 19)

**Big 3 Handler Mixins (3 docs)**
- `17-BIG_3_IMPLEMENTATION.md` (see above)
- `21-BIG_3_SUMMARY.md`  (overlaps with 17, 22)
- `22-BIG_3_COMPLETE_SUMMARY.md`  (overlaps with 17, 21)

**Worker Role System (5 docs - MISSING FROM README)**
- `20-WORKER_ROLE_INDEX.md`  (file conflict)
- `21-WORKER_ROLE_ARCHITECTURE.md`  (file conflict)
- `22-WORKER_ROLE_QUICK_START.md`  (file conflict)
- `23-WORKER_ROLE_API_REFERENCE.md`  (file conflict)
- `24-WORKER_RETRY_AND_DLQ.md`  (missing from README)

**Service Bus & Messaging (2 docs - MISSING FROM README)**
- `25-SERVICE_BUS_PROVIDER_MODE.md`  (missing from README)
- `26-GENERIC_SERVICEBUS_IMPLEMENTATION.md`  (missing from README)

**Architecture Summaries (1 doc)**
- `23-ARCHITECTURE_SUMMARY.md`  (overlaps with 04)

**Future Development & Planning (NEW)**
- `07-MIXIN_DESIGN_ROADMAP.md`  **NEW** (Strategic design for 11 advanced mixins)

---

## Proposed New Structure

### Strategy

1. **Consolidate** overlapping documents
2. **Renumber** to eliminate conflicts (use 01-40 range)
3. **Group by Feature** not by document type
4. **Create hierarchy**: Core → Intermediate → Advanced
5. **Remove archives** to `/99-Archive/`

---

### New Documentation Organization

#### **Section 1: Getting Started (01-05)**

```
01-SDK_OVERVIEW.md
   ├── Purpose, key features, quick start
   ├── Links to: Architecture, your use case
   └── New! Consolidates quick start from 00-GETTING-STARTED/README.md

02-ARCHITECTURE.md  
   ├── SDK layered architecture, module organization
   ├── Component relationships, design patterns
   ├── Consolidates: 04-ARCHITECTURE.md + 23-ARCHITECTURE_SUMMARY.md
   └── Links to: Core concepts, feature modules

03-CORE_CONCEPTS.md
   ├── Resource IDs, scopes, uniqueness
   ├── Request/response flow, providers
   ├── Consolidates: 01-SCOPED_RESOURCE_HANDLER.md + 02-RESOURCE_ID_STRATEGY.md + 03-MODULAR_ARCHITECTURE.md
   └── Links to: Handlers, location system

04-RESOURCE_GROUPS.md
   ├── Creating, managing, querying resource groups
   ├── Scope-aware uniqueness patterns
   ├── Consolidates: 11-RESOURCE_GROUP_CREATION_FLOW.md + 13-SCOPED_RESOURCES_OVERVIEW.md
   └── Links to: Handler mixins, examples
```

#### **Section 2: Core Features (05-10)**

```
05-RESOURCE_HANDLERS.md
   ├── Define, implement, extend resource handlers
   ├── Scope configuration, handler patterns
   ├── New consolidated document
   └── Links to: Handler mixins, examples

06-HANDLER_MIXINS.md
   ├── Big 3: Timestamps, Provisioning States, Validation
   ├── Usage patterns, integration, testing
   ├── Consolidates: 12-RESOURCE_GROUP_BIG_3_INTEGRATION.md + 15-QUICK_REFERENCE_BIG_3.md + 17-BIG_3_IMPLEMENTATION.md + 21-BIG_3_SUMMARY.md + 22-BIG_3_COMPLETE_SUMMARY.md
   └── Links to: Location validation, examples, testing

07-LOCATION_VALIDATION.md
   ├── Azure regions, custom locations, validation
   ├── LocationsHandler, dynamic validation
   ├── Consolidates: 16-LOCATIONS_HANDLER.md + 18-ITL_LOCATIONS_SCHEMA.md + 19-DYNAMIC_LOCATIONS_SUMMARY.md + 20-DYNAMIC_LOCATIONS_COMPLETE.md
   └── Links to: Handler mixins, schemas, examples

08-API_ENDPOINTS.md
   ├── FastAPI integration, middleware, routes
   ├── Error handling, OpenAPI, documentation
   ├── Consolidates: 05-FASTAPI_MODULE.md + 06-FASTAPI_INTEGRATION.md + 07-FASTAPI_QUICK_REFERENCE.md
   └── Links to: Provider servers, deployment

09-ASYNC_PATTERNS.md
   ├── Service bus, message queues, worker roles
   ├── Request/response correlation, DLQ handling
   ├── Consolidates: 25-SERVICE_BUS_PROVIDER_MODE.md + 26-GENERIC_SERVICEBUS_IMPLEMENTATION.md
   └── Links to: Worker roles, deployment patterns

10-QUICK_REFERENCE.md
   ├── API cheat sheets, common tasks
   ├── Configuration examples, troubleshooting
   ├── Consolidates: 14-QUICK_REFERENCE.md
   └── Links to: Core API docs, examples

11-PLANNING_AND_ROADMAP.md
   ├── Future development guides, architectural planning
   ├── Strategic decisions, design roadmaps
   ├── Currently includes: Mixin Design Roadmap
   └── Links to: Advanced features, planning docs
```

#### **Section 2.5: Future Development & Roadmaps**

```
ROADMAP-MIXINS.md (07-MIXIN_DESIGN_ROADMAP.md)
   ├── Strategic design for 11 advanced resource handler mixins
   ├── Mixin specifications: Tier 1 (6 mixins), Tier 2 (4 mixins), Tier 3 (1 mixin)
   ├── Problem statements, use cases, implementation complexity ratings
   ├── Expected rollout: Weeks 1-6+ across three phases
   └── Links to: Handler mixins, audit system, compliance frameworks
```

#### **Section 3: Advanced Features (11-20)**

```
11-WORKER_ROLES.md
   ├── Worker role system, configuration
   ├── Job processing, error handling, monitoring
   ├── Consolidates: 20-WORKER_ROLE_INDEX.md + 21-WORKER_ROLE_ARCHITECTURE.md + 22-WORKER_ROLE_QUICK_START.md + 23-WORKER_ROLE_API_REFERENCE.md
   └── Links to: Async patterns, deployment, DLQ

12-WORKER_DLQ_RETRY.md
   ├── Dead-letter queue handling, retry policies
   ├── Error classification, monitoring
   ├── Consolidates: 24-WORKER_RETRY_AND_DLQ.md
   └── Links to: Worker roles, async patterns

13-DEPLOYMENT.md
   ├── Kubernetes, Docker, environment configuration
   ├── Health checks, scaling, networking
   ├── New! Brings deployment patterns together
   └── Links to: CI/CD, worker roles, async patterns

14-CI_CD_PIPELINES.md
   ├── GitHub Actions, testing, publishing
   ├── PyPI deployment, versioning automation
   ├── Consolidates: 08-PIPELINE_SETUP.md + 09-AUTOMATED_VERSIONING.md + 10-VERSIONING_UPDATE.md
   └── Links to: Deployment, testing practices

15-TESTING_GUIDE.md
   ├── Unit testing, integration testing, e2e
   ├── Test patterns, mocking, fixtures
   ├── New! Comprehensive testing guide
   └── Links to: Examples, CI/CD
```

#### **Section 4: Examples & Reference (21-25)**

```
21-EXAMPLE_BASIC_PROVIDER.md
   ├── Minimal resource provider example
   ├── Step-by-step walkthrough
   ├── New! Restructured examples
   └── Links to: Core features, deployment

22-EXAMPLE_ADVANCED_PROVIDER.md
   ├── Full-featured provider with all mixins
   ├── Async patterns, validation, audit
   ├── New! Advanced example
   └── Links to: All features, best practices

23-BEST_PRACTICES.md
   ├── Design patterns, performance, security
   ├── Common pitfalls, optimization tips
   ├── New! Best practices guide
   └── Links to: All features, examples

24-TROUBLESHOOTING.md
   ├── Common issues, debugging, logs
   ├── Solution paths by symptom
   ├── New! Troubleshooting guide
   └── Links to: All features, support

25-API_REFERENCE.md
   ├── Complete SDK API documentation
   ├── Classes, methods, exceptions
   ├── Generated from docstrings
   └── Links to: Core features, examples
```

#### **Section 5: Operations & Maintenance (26-30)**

```
26-OPERATIONS.md
   ├── Production operations, monitoring
   ├── Log aggregation, metrics, alerting
   ├── New! Operations guide
   └── Links to: Deployment, troubleshooting

27-MIGRATION_GUIDE.md
   ├── Upgrading SDK versions
   ├── Breaking changes, deprecations
   ├── New! Migration path documentation
   └── Links to: CI/CD, changelog

28-CONTRIBUTING.md
   ├── Development setup, code standards
   ├── PR process, review guidelines
   ├── New! Contribution guidelines
   └── Links to: Testing, code style

29-CHANGELOG.md
   ├── Version history, features, fixes
   ├── Breaking changes, deprecations
   ├── Auto-generated from git tags
   └── Links to: Migration guide
```

---

## Action Plan

### Phase 1: Planning & Organization (Complete)
- [x] Analyze current structure
- [x] Identify duplicates and conflicts
- [x] Design new logical structure
- [ ] **Get stakeholder approval**

### Phase 2: Consolidation (Recommended Next)
- [ ] Merge Big 3 docs → `06-HANDLER_MIXINS.md`
- [ ] Merge Location docs → `07-LOCATION_VALIDATION.md`
- [ ] Merge FastAPI docs → `08-API_ENDPOINTS.md`
- [ ] Merge Worker Role docs → `11-WORKER_ROLES.md`
- [ ] Merge Service Bus docs → `09-ASYNC_PATTERNS.md`
- [ ] Merge Versioning docs → `14-CI_CD_PIPELINES.md`
- [ ] Archive obsolete docs → `99-Archive/`

### Phase 3: Creation (After Consolidation)
- [ ] Create missing guides (Deployment, Testing, Examples, etc.)
- [ ] Create new Quick Reference
- [ ] Create Best Practices guide
- [ ] Create Troubleshooting guide
- [x] **COMPLETED**: Create Mixin Design Roadmap (07-MIXIN_DESIGN_ROADMAP.md)
  - Documents 11 advanced mixins for future development
  - Includes 3 tiers: High Priority (6), Medium Priority (4), Low Priority (1)
  - Maps requirements to enterprise needs (audit, compliance, performance)
  - References: Handler mixins, audit system, policy frameworks

### Phase 4: Updates (After Creation)
- [ ] Update all cross-references
- [ ] Update README.md with new structure
- [ ] Create navigation sidebars/indices
- [ ] Add "see also" sections

### Phase 5: Validation (Final)
- [ ] Review for completeness
- [ ] Check all links work
- [ ] Update version numbers
- [ ] Publish updated docs

---

## Consolidation Mapping

### To Keep As-Is (No Changes)
```
01-SCOPED_RESOURCE_HANDLER.md → Merge into 03-CORE_CONCEPTS.md
02-RESOURCE_ID_STRATEGY.md    → Merge into 03-CORE_CONCEPTS.md
03-MODULAR_ARCHITECTURE.md    → Merge into 03-CORE_CONCEPTS.md
04-ARCHITECTURE.md            → Becomes 02-ARCHITECTURE.md
05-FASTAPI_MODULE.md          → Merge into 08-API_ENDPOINTS.md
06-FASTAPI_INTEGRATION.md     → Merge into 08-API_ENDPOINTS.md
07-FASTAPI_QUICK_REFERENCE.md → Merge into 08-API_ENDPOINTS.md
08-PIPELINE_SETUP.md          → Merge into 14-CI_CD_PIPELINES.md
11-RESOURCE_GROUP_CREATION_FLOW.md → Merge into 04-RESOURCE_GROUPS.md
13-SCOPED_RESOURCES_OVERVIEW.md    → Merge into 04-RESOURCE_GROUPS.md
```

### To Consolidate (Combine Similar Docs)
```
09-AUTOMATED_VERSIONING.md + 10-VERSIONING_UPDATE.md 
  → 14-CI_CD_PIPELINES.md (keep as primary, archive 09-10)

12-RESOURCE_GROUP_BIG_3_INTEGRATION.md + 15-QUICK_REFERENCE_BIG_3.md 
  + 17-BIG_3_IMPLEMENTATION.md + 21-BIG_3_SUMMARY.md 
  + 22-BIG_3_COMPLETE_SUMMARY.md
  → 06-HANDLER_MIXINS.md (consolidate, archive 12-15-17-21-22)

16-LOCATIONS_HANDLER.md + 18-ITL_LOCATIONS_SCHEMA.md 
  + 19-DYNAMIC_LOCATIONS_SUMMARY.md + 20-DYNAMIC_LOCATIONS_COMPLETE.md
  → 07-LOCATION_VALIDATION.md (consolidate, archive 16-18-19-20)

20-WORKER_ROLE_INDEX.md + 21-WORKER_ROLE_ARCHITECTURE.md 
  + 22-WORKER_ROLE_QUICK_START.md + 23-WORKER_ROLE_API_REFERENCE.md
  → 11-WORKER_ROLES.md (consolidate, archive 20-21-22-23 worker files)

25-SERVICE_BUS_PROVIDER_MODE.md + 26-GENERIC_SERVICEBUS_IMPLEMENTATION.md
  → 09-ASYNC_PATTERNS.md (consolidate, keep both numbered separately)

04-ARCHITECTURE.md + 23-ARCHITECTURE_SUMMARY.md
  → 02-ARCHITECTURE.md (consolidate, archive 23)

14-QUICK_REFERENCE.md (keep and expand)
  → 10-QUICK_REFERENCE.md
```

### To Create (Entirely New Docs)
```
- 01-SDK_OVERVIEW.md (new quick start index)
- 05-RESOURCE_HANDLERS.md (new guide)
- 13-DEPLOYMENT.md (new guide)
- 15-TESTING_GUIDE.md (new guide)
- 21-EXAMPLE_BASIC_PROVIDER.md (new examples)
- 22-EXAMPLE_ADVANCED_PROVIDER.md (new examples)
- 23-BEST_PRACTICES.md (new guide)
- 24-TROUBLESHOOTING.md (new guide)
- 25-API_REFERENCE.md (new reference)
- 26-OPERATIONS.md (new guide)
- 27-MIGRATION_GUIDE.md (new guide)
- 28-CONTRIBUTING.md (new guide)
- 29-CHANGELOG.md (auto-generated)
```

### To Archive (No Longer Needed)
```
99-Archive/
  ├── 09-AUTOMATED_VERSIONING.md
  ├── 10-VERSIONING_UPDATE.md
  ├── 12-RESOURCE_GROUP_BIG_3_INTEGRATION.md
  ├── 15-QUICK_REFERENCE_BIG_3.md
  ├── 16-LOCATIONS_HANDLER.md
  ├── 17-BIG_3_IMPLEMENTATION.md
  ├── 18-ITL_LOCATIONS_SCHEMA.md
  ├── 19-DYNAMIC_LOCATIONS_SUMMARY.md
  ├── 20-DYNAMIC_LOCATIONS_COMPLETE.md (old)
  ├── 20-WORKER_ROLE_INDEX.md
  ├── 21-BIG_3_SUMMARY.md
  ├── 21-WORKER_ROLE_ARCHITECTURE.md
  ├── 22-BIG_3_COMPLETE_SUMMARY.md
  ├── 22-WORKER_ROLE_QUICK_START.md
  ├── 23-ARCHITECTURE_SUMMARY.md
  ├── 23-WORKER_ROLE_API_REFERENCE.md
  └── README-ARCHIVE.md (index of archived docs)
```

---

## Benefits of New Structure

| Aspect | Before | After |
|--------|--------|-------|
| **Total Docs** | 26 files with overlaps | 29 focused files |
| **Duplicates** | ~8 docs duplicating content | 0 duplicates |
| **File Conflicts** | Multiple docs per number | Unique sequential numbers |
| **Organization** | Topic-scattered | Feature-grouped & hierarchical |
| **Navigation** | Cross-referenced chaos | Clear parent-child relationships |
| **Discoverability** | Hard to find related docs | Easy feature-based lookup |
| **Maintenance** | Update in 3+ places | Update once |
| **Onboarding** | 26 docs to browse | Clear learning path |

---

## New Navigation Hierarchy

```
README.md (master index)
├── 01-SDK_OVERVIEW.md (start here)
│   ├── 02-ARCHITECTURE.md (how it works)
│   ├── 03-CORE_CONCEPTS.md (key ideas)
│   └── [Use case pathways]
│
├── Section: Core Features (04-10)
│   ├── 04-RESOURCE_GROUPS.md
│   ├── 05-RESOURCE_HANDLERS.md
│   ├── 06-HANDLER_MIXINS.md
│   ├── 07-LOCATION_VALIDATION.md
│   ├── 08-API_ENDPOINTS.md
│   ├── 09-ASYNC_PATTERNS.md
│   └── 10-QUICK_REFERENCE.md
│
├── Section: Advanced Features (11-15)
│   ├── 11-WORKER_ROLES.md
│   ├── 12-WORKER_DLQ_RETRY.md
│   ├── 13-DEPLOYMENT.md
│   ├── 14-CI_CD_PIPELINES.md
│   └── 15-TESTING_GUIDE.md
│
├── Section: Learning (21-25)
│   ├── 21-EXAMPLE_BASIC_PROVIDER.md
│   ├── 22-EXAMPLE_ADVANCED_PROVIDER.md
│   ├── 23-BEST_PRACTICES.md
│   ├── 24-TROUBLESHOOTING.md
│   └── 25-API_REFERENCE.md
│
├── Section: Ops & Maintenance (26-29)
│   ├── 26-OPERATIONS.md
│   ├── 27-MIGRATION_GUIDE.md
│   ├── 28-CONTRIBUTING.md
│   └── 29-CHANGELOG.md
│
└── Archive (99-*)
    ├── README-ARCHIVE.md (what's archived and why)
    └── [All deprecated/superseded docs]
```

---

## Implementation Priority

### Critical (Start Here)
1. **Consolidate Big 3 documents** → Reduces 5→1 doc (biggest overlap)
2. **Consolidate Location documents** → Reduces 4→1 doc
3. **Consolidate Worker Role documents** → Reduces 4→1 doc
4. **Fix README.md** → Add missing sections

### High (Do Next)
5. **Consolidate FastAPI documents** → Reduces 3→1 doc
6. **Consolidate Versioning** → Reduces 2→1 doc (archive 1)
7. **Consolidate Architecture** → Reduces 2→1 doc (archive 1)

### Medium (Do After)
8. Create new guides (Deployment, Testing, Examples)
9. Create troubleshooting guide
10. Create best practices guide

### Low (Polish)
11. Create API reference
12. Create operations guide
13. Create migration guide
14. Create contribution guide

---

## Success Metrics

After restructuring, we should have:
-  0 duplicate content
-  0 numbering conflicts
-  100% cross-references working
-  Clear learning path for new users
-  Easy feature lookup by topic
-  Single source of truth per feature
-  All docs reflected in README
-  Archive clearly separated

---

## Next Steps

1. **Review** this plan with team
2. **Approve** structure and numbering
3. **Begin Phase 2** consolidation work
4. **Track progress** through phases
5. **Validate** against success metrics

---

**Created**: February 14, 2026  
**By**: Documentation Review  
**Status**:  Ready for Approval

