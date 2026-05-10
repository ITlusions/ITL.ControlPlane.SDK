"""
ITLLandingZone — full Azure landing zone as a Pulumi ComponentResource.

Provisions resource governance, security, and optional workloads, and
simultaneously registers the landing zone with the ITL ControlPlane API.

Usage::

    import pulumi
    from itl_controlplane_sdk.pulumi.landing_zone import ITLLandingZone

    lz = ITLLandingZone(
        "payments",
        subscription_id="00000000-0000-0000-0000-000000000000",
        environment="production",
        owner="team@itlusions.com",
        budget=2000,
        region="westeurope",
        aks_enabled=True,
        flux_repo="https://github.com/ITlusions/itl-helm-charts",
        azure_enabled=True,
        itl_enabled=True,
    )

    pulumi.export("resource_group_name", lz.resource_group_name)
    pulumi.export("resource_group_id",   lz.resource_group_id)
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pulumi
from pulumi import Input, Output

from .component import ITLPulumiComponent
from .defender import DefenderInitiative
from .resource_group import ResourceGroup

try:
    import pulumi_azure_native.authorization as az_authz  # type: ignore[import-untyped]
    _AZURE_NATIVE_AVAILABLE = True
except ImportError:
    _AZURE_NATIVE_AVAILABLE = False


class ITLLandingZone(ITLPulumiComponent):
    """Full ITL landing zone: governance, security, observability, networking.

    Azure side
    ----------
    - Resource Group with standard ITL tags.
    - RBAC lock (``CanNotDelete``) on the resource group.
    - Defender for Cloud initiative via :class:`~.defender.DefenderInitiative`.
    - Optional AKS cluster via :class:`~.aks.AKSCluster` (lazy import).

    ITL side
    --------
    - Subscription registration in the ITL ControlPlane API.
    - Cross-tenant policy binding (if ``itl_enabled=True``).

    What ITL ControlPlane adds over Azure-only:

    =====================  =====  ================
    Capability             Azure  ITL ControlPlane
    =====================  =====  ================
    Resource governance    ✓      ✓
    Subscription vending   ✗      ✓
    Cross-tenant policies  ✗      ✓
    Talos on-prem policies ✗      ✓
    Unified compliance     ✗      ✓
    =====================  =====  ================

    Args:
        name:            Logical component name (also used as resource prefix).
        subscription_id: Azure subscription to configure.
        environment:     One of ``development``, ``staging``, ``production``.
        owner:           Team e-mail that owns this landing zone.
        budget:          Monthly budget in EUR/USD (stored as tag; cost alert
                         integration is a future roadmap item).
        region:          Azure region (default ``"westeurope"``).
        extra_tags:      Additional tags applied to all Azure resources.
        aks_enabled:     Provision an AKS cluster inside the landing zone.
        flux_repo:       GitOps source repository URL passed to the AKS
                         component (requires ``aks_enabled=True``).
        defender_enabled: Enable Defender for Cloud initiative (default ``True``).
        azure_enabled:   Provision Azure resources (default ``True``).
        itl_enabled:     Register with ITL ControlPlane (default ``True``).
        itl_endpoint:    ITL ControlPlane API base URL.
        opts:            Pulumi resource options.

    Outputs:
        resource_group_name:  Name of the provisioned resource group.
        resource_group_id:    ARM resource ID of the resource group.
        location:             Effective Azure region.
    """

    resource_group_name: Output[str]
    resource_group_id: Output[str]
    location: Output[str]

    def __init__(
        self,
        name: str,
        *,
        subscription_id: Input[str],
        environment: str,
        owner: str,
        budget: int,
        region: str = "westeurope",
        extra_tags: Optional[Dict[str, str]] = None,
        aks_enabled: bool = False,
        flux_repo: Optional[str] = None,
        defender_enabled: bool = True,
        azure_enabled: bool = True,
        itl_enabled: bool = True,
        itl_endpoint: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        sub_id_str = subscription_id if isinstance(subscription_id, str) else None
        super().__init__(
            "itl:landingzone:ITLLandingZone",
            name,
            azure_enabled=azure_enabled,
            itl_enabled=itl_enabled,
            itl_endpoint=itl_endpoint,
            subscription_id=sub_id_str,
            provider_namespace="ITL.Resources",
            opts=opts,
        )

        rg_id: Output[str] = Output.from_input("")
        rg_name: Output[str] = Output.from_input(f"{name}-rg")

        if azure_enabled:
            if not _AZURE_NATIVE_AVAILABLE:
                raise ImportError(
                    "pulumi-azure-native is required for azure_enabled=True. "
                    "Install with: pip install pulumi-azure-native"
                )

            child_opts = pulumi.ResourceOptions(parent=self)

            # ── Resource Group (via ITL component) ───────────────────────────
            rg_component = ResourceGroup(
                f"{name}-rg",
                location=region,
                environment=environment,
                owner=owner,
                extra_tags={"budget": str(budget), **(extra_tags or {})},
                lock=True,
                azure_enabled=True,
                itl_enabled=False,  # landing zone handles ITL registration
                opts=child_opts,
            )
            rg_id = rg_component.resource_group_id
            rg_name = rg_component.resource_group_name

            # ── Defender for Cloud ───────────────────────────────────────────
            if defender_enabled:
                DefenderInitiative(
                    f"{name}-defender",
                    subscription_id=subscription_id,
                    environment=environment,
                    azure_enabled=True,
                    itl_enabled=False,  # landing zone handles ITL registration
                    opts=pulumi.ResourceOptions(parent=self),
                )

            # ── AKS cluster (optional) ───────────────────────────────────────
            if aks_enabled:
                # Lazy import avoids circular dep and keeps AKS optional
                from .aks import AKSCluster  # noqa: PLC0415

                AKSCluster(
                    f"{name}-aks",
                    resource_group_name=rg_component.resource_group_name,
                    location=region,
                    environment=environment,
                    flux_repo=flux_repo,
                    azure_enabled=True,
                    itl_enabled=False,  # landing zone handles ITL registration
                    opts=pulumi.ResourceOptions(parent=self),
                )

        # ── ITL ControlPlane registration ─────────────────────────────────────
        self._register_with_itl(
            "Subscription",
            {
                "name": name,
                "subscription_id": subscription_id
                if isinstance(subscription_id, str)
                else "__pulumi_output__",
                "environment": environment,
                "owner": owner,
                "budget": str(budget),
                "region": region,
                "aks_enabled": str(aks_enabled),
                "defender_enabled": str(defender_enabled),
            },
        )

        self.resource_group_name = rg_name
        self.resource_group_id = rg_id
        self.location = Output.from_input(region)

        self.register_outputs(
            {
                "resource_group_name": self.resource_group_name,
                "resource_group_id": self.resource_group_id,
                "location": self.location,
            }
        )
