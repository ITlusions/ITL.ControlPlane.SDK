"""
ResourceGroup — ITL Pulumi component for Azure Resource Groups.

Provisions an Azure Resource Group with ITL platform defaults (tags, lock)
and optionally registers it with the ITL ControlPlane API.

Usage::

    import pulumi
    from itl_controlplane_sdk.pulumi.resource_group import ResourceGroup

    rg = ResourceGroup(
        "payments-rg",
        location="westeurope",
        environment="production",
        owner="team@itlusions.com",
        lock=True,
        azure_enabled=True,
        itl_enabled=True,
    )

    pulumi.export("resource_group_name", rg.resource_group_name)
    pulumi.export("resource_group_id",   rg.resource_group_id)
"""

from __future__ import annotations

from typing import Dict, Optional

import pulumi
from pulumi import Input, Output

from .component import ITLPulumiComponent

try:
    import pulumi_azure_native.resources as az_resources  # type: ignore[import-untyped]
    _AZURE_NATIVE_AVAILABLE = True
except ImportError:
    _AZURE_NATIVE_AVAILABLE = False


class ResourceGroup(ITLPulumiComponent):
    """Azure Resource Group with ITL platform defaults.

    Azure side
    ----------
    - ``ResourceGroup`` with standard ITL tags.
    - Optional ``CanNotDelete`` management lock.

    ITL side
    --------
    - Registers the resource group in the ITL ControlPlane API so it
      appears in the platform inventory.

    Args:
        name:            Logical component name (also used as the Azure RG name
                         when *resource_group_name* is not supplied).
        location:        Azure region (default ``"westeurope"``).
        resource_group_name: Override the Azure resource group name.  Defaults
                         to *name*.
        environment:     Deployment environment tag.
        owner:           Team e-mail that owns this resource group.
        extra_tags:      Additional tags applied to the resource group.
        lock:            When ``True`` (default), adds a ``CanNotDelete``
                         management lock to the resource group.
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
        location: Input[str] = "westeurope",
        resource_group_name: Optional[Input[str]] = None,
        environment: str = "production",
        owner: str = "",
        extra_tags: Optional[Dict[str, str]] = None,
        lock: bool = True,
        subscription_id: Optional[str] = None,
        azure_enabled: bool = True,
        itl_enabled: bool = True,
        itl_endpoint: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(
            "itl:resources:ResourceGroup",
            name,
            azure_enabled=azure_enabled,
            itl_enabled=itl_enabled,
            itl_endpoint=itl_endpoint,
            subscription_id=subscription_id,
            opts=opts,
        )

        rg_name_input = resource_group_name or name

        tags: Dict[str, str] = {
            "environment": environment,
            "managed-by": "itl-controlplane",
            **({"owner": owner} if owner else {}),
            **(extra_tags or {}),
        }

        rg_id: Output[str] = Output.from_input("")
        rg_name: Output[str] = Output.from_input(rg_name_input if isinstance(rg_name_input, str) else name)

        if azure_enabled:
            if not _AZURE_NATIVE_AVAILABLE:
                raise ImportError(
                    "pulumi-azure-native is required for azure_enabled=True. "
                    "Install with: pip install pulumi-azure-native"
                )

            child_opts = pulumi.ResourceOptions(parent=self)

            rg = az_resources.ResourceGroup(
                name,
                resource_group_name=rg_name_input,
                location=location,
                tags=tags,
                opts=child_opts,
            )
            rg_id = rg.id
            rg_name = rg.name

            if lock:
                az_resources.ManagementLockByResourceGroup(
                    f"{name}-lock",
                    resource_group_name=rg.name,
                    level=az_resources.LockLevel.CAN_NOT_DELETE,
                    notes=f"ITL ControlPlane lock for resource group {name}",
                    opts=pulumi.ResourceOptions(parent=rg),
                )

        # ── ITL ControlPlane registration ─────────────────────────────────────
        self._register_with_itl(
            "ResourceGroup",
            {
                "name": name,
                "environment": environment,
                "owner": owner,
                "region": location if isinstance(location, str) else "__pulumi_output__",
            },
        )

        self.resource_group_name = rg_name
        self.resource_group_id = rg_id
        self.location = Output.from_input(location)

        self.register_outputs(
            {
                "resource_group_name": self.resource_group_name,
                "resource_group_id": self.resource_group_id,
                "location": self.location,
            }
        )
