# Pulumi Integration Roadmap

**Status**: In Progress  
**Version**: 1.2  
**Created**: 2026-04-20  
**Last Updated**: 2026-04-21  
**Issues**: [#11](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/11) · [#12](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/12)

---

## Overview

Two related issues extend the SDK's Pulumi footprint into a first-class integration layer that can deploy resources to both Azure and the ITL ControlPlane simultaneously. The goal is a `pip install`-able Pulumi component package — no SDK knowledge required from end-users.

**Dependency chain**:
```
itl-controlplane-pulumi   ← new standalone package (#12)
    |
    +-> itl-policy-builder          (templates + DSL)
    +-> itl-controlplane-sdk        (resource provider patterns)
    +-> pulumi-azure-native         (Azure deployment)
```

---

## Architecture Decision: SDK vs Resource Provider split

**Decision date**: 2026-04-21

The `pulumi/` module must be split across two responsibility layers.  The SDK owns the **contract**; resource providers own the **implementations**.

### SDK owns (`ITL.ControlPanel.SDK`)

| Module | Responsibility |
|--------|---------------|
| `pulumi/component.py` | `ITLPulumiComponent` ABC + `PulumiITLNativeProvider` dynamic provider |
| `pulumi/arm_deployment.py` | `ITLARMDeployment` — direct ARM→ITL deploy client |
| `pulumi/arm_converter.py` | `ARMConverter` — ARM/Bicep template → Pulumi Python codegen |
| `pulumi/stack.py` | `PulumiStack`, `StackConfig`, `StackEnvironment` |
| `pulumi/deployment.py` | `PulumiDeployment` — Automation API wrapper |
| `pulumi/resource_mapper.py` | `ResourceMapper` |

### Resource Providers own (per provider repo)

| Module | Repo | ITL namespace |
|--------|------|---------------|
| `pulumi/resource_group.py` | `ITL.ControlPlane.ResourceProvider.Core` | `ITL.Resources` |
| `pulumi/management_group.py` | `ITL.ControlPlane.ResourceProvider.Core` | `ITL.Management` |
| `pulumi/landing_zone.py` | `ITL.ControlPlane.ResourceProvider.Core` | composed |
| `pulumi/aks.py` | `ITL.ControlPlane.ResourceProvider.Compute` | `ITL.Compute` |
| `pulumi/virtual_machine.py` | `ITL.ControlPlane.ResourceProvider.Compute` | `ITL.Compute` |
| `pulumi/defender.py` | `ITL.ControlPlane.ResourceProvider.IAM` | `ITL.Security` |

**Import chain** (no circular deps):
```python
# Resource provider imports from SDK
from itl_controlplane_sdk.pulumi import ITLPulumiComponent

class AKSCluster(ITLPulumiComponent):   # lives in ResourceProvider.Compute
    ...

# End-user Pulumi program imports from provider packages
from itl_controlplane_sdk_compute.pulumi import AKSCluster
from itl_controlplane_sdk_core.pulumi import ResourceGroup, ITLLandingZone
```

**Rule**: Anything that references a specific `ITL.*` namespace belongs in the provider for that namespace, not the SDK.

---

## CP-SDK-011: Pulumi Dual-Target Module — `#11`

**Status**: ✅ Core complete — resource provider split pending  
**Location**: `pulumi/` module in `ITL.ControlPlane.SDK`  
**Related**: ITL.ControlPlane.PolicyBuilder #9 (Pulumi serializer, input format)

### Problem

Teams using Terraform or ARM must learn the PolicyBuilder Python SDK before they can use ITL policies. A Pulumi module that can target **both Azure Policy API and ITL ControlPlane API** simultaneously removes this barrier.

### What it does

Extends the existing `pulumi/` module in the SDK with dual-target deployment capability. Each component accepts `azure_enabled` and `itl_enabled` flags to route deployments independently.

**Base class**:
```python
class ITLPulumiComponent(pulumi.ComponentResource):
    """Base class for all ITL dual-target Pulumi components."""

    def __init__(self, name, azure_enabled=True, itl_enabled=True, opts=None):
        self._azure_enabled = azure_enabled
        self._itl_enabled   = itl_enabled

    def _deploy_to_azure(self, resource_dict: dict): ...
    def _deploy_to_itl(self, resource_dict: dict): ...
```

**Components implemented** (temporarily in SDK, to migrate per architecture decision above):

| Component | Location now | Target location | Status |
|-----------|-------------|-----------------|--------|
| `DefenderInitiative` | `pulumi/defender.py` | ResourceProvider.IAM | ✅ Done, pending move |
| `ITLLandingZone` | `pulumi/landing_zone.py` | ResourceProvider.Core | ✅ Done, pending move |
| `AKSCluster` | `pulumi/aks.py` | ResourceProvider.Compute | ✅ Done, pending move |
| `ResourceGroup` | `pulumi/resource_group.py` | ResourceProvider.Core | ✅ Done, pending move |
| `ManagementGroup` | `pulumi/management_group.py` | ResourceProvider.Core | ✅ Done, pending move |

**ARM tooling** (stays in SDK):

| Module | Status | Description |
|--------|--------|-------------|
| `arm_converter.py` | ✅ Done | ARM/Bicep → Pulumi Python codegen CLI (`itl-arm-convert`) |
| `arm_deployment.py` | ✅ Done | Direct ARM→ITL deployment client, no Pulumi needed (`itl-arm-deploy`) |

**ITL namespace support** — both `Microsoft.*` and `ITL.*` ARM types are accepted and normalised:

| ITL type | Microsoft equivalent |
|----------|---------------------|
| `ITL.Resources/resourceGroups` | `Microsoft.Resources/resourceGroups` |
| `ITL.Compute/managedClusters` | `Microsoft.ContainerService/managedClusters` |
| `ITL.Security/pricings` | `Microsoft.Security/pricings` |
| `ITL.Management/managementGroups` | `Microsoft.Management/managementGroups` |

**Usage**:
```python
landing_zone = ITLLandingZone("payments",
    subscription_id = "00000000-...",
    environment     = "production",
    owner           = "team@itlusions.com",
    budget          = 2000,
    region          = "westeurope",

    # Target selection
    azure_enabled   = True,   # → Azure Policy API
    itl_enabled     = True,   # → ITL ControlPlane API

    # Optional workloads
    aks_enabled     = True,
    flux_repo       = "https://github.com/ITlusions/itl-helm-charts",
)
```

**ARM deploy (no Pulumi required)**:
```bash
# Same UX as az deployment group create
itl-arm-deploy create \
    --name prod-deployment \
    --template-file template.json \
    --parameters @params.json \
    --subscription-id 00000000-...
```

**What ITL ControlPlane adds over Azure-only**:

| Capability | Azure | ITL ControlPlane |
|-----------|-------|-----------------|
| Resource governance | ✅ | ✅ |
| Subscription vending | ❌ | ✅ |
| Cross-tenant policies | ❌ | ✅ |
| Talos on-prem policies | ❌ | ✅ |
| Unified compliance report | ❌ | ✅ |

### Acceptance Criteria

- [x] `ITLPulumiComponent` base class implemented with `azure_enabled` / `itl_enabled` flags
- [x] `PulumiITLNativeProvider` dynamic provider renamed from `_ITLRegistrationProvider` (public API)
- [x] `ITLLandingZone` deploys to Azure when `azure_enabled=True`
- [x] `ITLLandingZone` calls ITL ControlPlane API when `itl_enabled=True`
- [x] Both targets can be active simultaneously without conflict
- [x] `DefenderInitiative` wraps `itl_policy_builder.templates.defender` — no logic duplication
- [x] `AKSCluster` accepts `flux_repo` and applies correct platform profile
- [x] `ARMConverter` — ARM templates → Pulumi Python code
- [x] `ITLARMDeployment` — ARM templates → ITL ControlPlane (direct, no Pulumi)
- [x] CLI entry-points: `itl-arm-deploy`, `itl-arm-convert`
- [x] Both `ITL.*` and `Microsoft.*` namespace types supported
- [x] 6 advanced example Pulumi programs created (`examples/pulumi/`)
- [ ] Resource-specific components moved to respective resource provider repos
- [ ] Unit tests mock both target APIs independently

---

## CP-SDK-012: ITL.ControlPlane.Pulumi Package — `#12`

**Status**: Open  
**New repo**: `ITlusions/ITL.ControlPlane.Pulumi`

### Problem

Even with the dual-target module in the SDK (#11), users still need to install the full SDK. A dedicated thin orchestration package (`itl-controlplane-pulumi`) published via pip removes the SDK as a required dependency for end-users. All logic stays in PolicyBuilder and the SDK — this package only wires them together for Pulumi consumers.

### Package structure

```
ITL.ControlPlane.Pulumi/
├── sdk/
│   └── python/
│       └── itl_controlplane_pulumi/
│           ├── __init__.py
│           ├── landing_zone.py       ← ITLLandingZone component
│           ├── defender.py           ← DefenderInitiative component
│           ├── aks.py                ← AKSCluster component
│           └── helm_charts.py        ← HelmChartDistribution component
├── examples/
│   ├── azure/                        ← Azure-only examples
│   ├── itl/                          ← ITL ControlPlane-only examples
│   └── both/                         ← Dual-target examples
├── tests/
├── pyproject.toml
└── README.md
```

### `pyproject.toml`

```toml
[project]
name = "itl-controlplane-pulumi"
version = "0.1.0"
dependencies = [
    "pulumi>=3.0.0",
    "pulumi-azure-native>=2.0.0",
    "itl-policy-builder>=1.0.0",
    "itl-controlplane-sdk>=1.0.0",
]
```

### Adoption path

```
Today:
  Team must learn Python SDK → call PolicyBuilder directly

With this package:
  pip install itl-controlplane-pulumi
  → Use familiar Pulumi patterns
  → ITL compliance guaranteed
  → No SDK internals knowledge required
```

### Acceptance Criteria

- [ ] Repo `ITlusions/ITL.ControlPlane.Pulumi` created with standard structure
- [ ] `ITLLandingZone` component instantiates without Azure credentials (dry-run mode)
- [ ] `DefenderInitiative` wraps PolicyBuilder defender templates — no logic duplication
- [ ] `AKSCluster` accepts `flux_repo` for itl-helm-charts integration
- [ ] Published to private PyPI or GitHub Packages as `itl-controlplane-pulumi`
- [ ] README includes quickstart and comparison with direct SDK usage
- [ ] Unit tests mock both target APIs independently

---

## Implementation Order

```
#11  Pulumi dual-target module (in SDK)              ← ✅ Core done
     └─ Resource provider split                      ← next step
          ├─ aks.py → ITL.ControlPlane.ResourceProvider.Compute
          ├─ defender.py → ITL.ControlPlane.ResourceProvider.IAM
          ├─ resource_group.py → ITL.ControlPlane.ResourceProvider.Core
          ├─ management_group.py → ITL.ControlPlane.ResourceProvider.Core
          └─ landing_zone.py → ITL.ControlPlane.ResourceProvider.Core

#12  ITL.ControlPlane.Pulumi package                 ← after split complete
     └─ thin wrapper that re-exports from provider packages
```

**Note**: #11 also depends on ITL.ControlPlane.PolicyBuilder #9 (Pulumi serializer) being available.
