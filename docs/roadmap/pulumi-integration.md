# Pulumi Integration Roadmap

**Status**: Open  
**Version**: 1.0  
**Created**: 2026-04-20  
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

## CP-SDK-011: Pulumi Dual-Target Module — `#11`

**Status**: Open  
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

**Components to implement**:

| Component | Purpose |
|-----------|---------|
| `DefenderInitiative` | Deploy Defender for Cloud initiative to Azure and/or ITL ControlPlane |
| `ITLLandingZone` | Full landing zone: governance, security, observability, networking |
| `AKSCluster` | AKS with Flux, Defender, logging pre-configured |

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

**What ITL ControlPlane adds over Azure-only**:

| Capability | Azure | ITL ControlPlane |
|-----------|-------|-----------------|
| Resource governance | ✅ | ✅ |
| Subscription vending | ❌ | ✅ |
| Cross-tenant policies | ❌ | ✅ |
| Talos on-prem policies | ❌ | ✅ |
| Unified compliance report | ❌ | ✅ |

### Acceptance Criteria

- [ ] `ITLLandingZone` deploys to Azure when `azure_enabled=True`
- [ ] `ITLLandingZone` calls ITL ControlPlane API when `itl_enabled=True`
- [ ] Both targets can be active simultaneously without conflict
- [ ] `DefenderInitiative` wraps `itl_policy_builder.templates.defender` — no logic duplication
- [ ] `AKSCluster` accepts `flux_repo` and applies correct platform profile
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
#11  Pulumi dual-target module (in SDK)    ← build first; #12 depends on it
#12  ITL.ControlPlane.Pulumi package       ← thin wrapper around #11
```

**Note**: #11 also depends on ITL.ControlPlane.PolicyBuilder #9 (Pulumi serializer) being available.
