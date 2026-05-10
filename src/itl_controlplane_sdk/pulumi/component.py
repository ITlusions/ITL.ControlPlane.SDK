"""
ITL Pulumi Component Base — dual-target ComponentResource.

All ITL Pulumi components extend this class.  Each component can target
Azure (via ``pulumi-azure-native``) and/or the ITL ControlPlane API
simultaneously, controlled by the ``azure_enabled`` / ``itl_enabled`` flags.

Usage::

    from itl_controlplane_sdk.pulumi.component import ITLPulumiComponent

    class MyComponent(ITLPulumiComponent):
        def __init__(self, name, *, opts=None, **kwargs):
            super().__init__("itl:myns:MyComponent", name, opts=opts, **kwargs)
            # build child resources here
            self.register_outputs({})
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import pulumi
import pulumi.dynamic as dynamic


# ---------------------------------------------------------------------------
# Dynamic provider — ITL ControlPlane registration
# ---------------------------------------------------------------------------

class PulumiITLNativeProvider(dynamic.ResourceProvider):
    """Pulumi dynamic provider that registers a resource with the ITL
    ControlPlane REST API.  Performs a PUT on create/update and a DELETE on
    destroy against ``{endpoint}/api/v1/{resource_type}/{name}``.

    Pulumi provider type name: ``pulumi-itl-native``
    """

    def create(self, props: Dict[str, Any]) -> dynamic.CreateResult:
        self._put(props)
        return dynamic.CreateResult(id_=props["name"], outs=props)

    def update(
        self,
        _id: str,
        _old_inputs: Dict[str, Any],
        new_inputs: Dict[str, Any],
    ) -> dynamic.UpdateResult:
        self._put(new_inputs)
        return dynamic.UpdateResult(outs=new_inputs)

    def delete(self, _id: str, props: Dict[str, Any]) -> None:
        endpoint = props.get("endpoint", "")
        resource_type = props.get("resource_type", "resource")
        name = props.get("name", _id)
        if not endpoint:
            return
        try:
            import requests  # type: ignore[import-untyped]

            token = os.environ.get("ITL_CONTROLPLANE_TOKEN", "")
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            requests.delete(
                f"{endpoint}/api/v1/{resource_type}/{name}",
                headers=headers,
                timeout=30,
            )
        except Exception as exc:  # noqa: BLE001
            pulumi.log.warn(f"ITL ControlPlane deregister failed: {exc}")

    # ------------------------------------------------------------------
    def _put(self, props: Dict[str, Any]) -> None:
        endpoint = props.get("endpoint", "")
        if not endpoint:
            return
        try:
            import requests  # type: ignore[import-untyped]

            resource_type = props.get("resource_type", "resource")
            name = props.get("name")
            token = os.environ.get("ITL_CONTROLPLANE_TOKEN", "")
            headers = {
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            }
            payload = {k: v for k, v in props.items()
                       if k not in {"endpoint", "resource_type"}}
            requests.put(
                f"{endpoint}/api/v1/{resource_type}/{name}",
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
        except Exception as exc:  # noqa: BLE001
            pulumi.log.warn(f"ITL ControlPlane register failed: {exc}")


class _ITLRegistration(dynamic.Resource):
    """Child resource that persists an ITL ControlPlane registration."""

    def __init__(
        self,
        name: str,
        props: Dict[str, Any],
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(PulumiITLNativeProvider(), name, props, opts, provider_name="pulumi-itl-native")


# ---------------------------------------------------------------------------
# Base component
# ---------------------------------------------------------------------------

class ITLPulumiComponent(pulumi.ComponentResource):
    """Base class for all ITL dual-target Pulumi components.

    Sub-classes must call ``self.register_outputs({...})`` at the end of
    ``__init__`` after building all child resources.

    Args:
        resource_type:      Pulumi resource type string, e.g.
                            ``"itl:landingzone:ITLLandingZone"``.
        name:               Logical resource name (stack-unique).
        azure_enabled:      When ``True`` (default) the component provisions
                            native Azure resources via ``pulumi-azure-native``.
        itl_enabled:        When ``True`` (default) the component registers
                            the resource with the ITL ControlPlane API.
        itl_endpoint:       Base URL of the ITL ControlPlane API.  Falls back
                            to the ``ITL_CONTROLPLANE_ENDPOINT`` env var.
        subscription_id:    ITL subscription to scope the resource under.
                            Falls back to ``ITL_SUBSCRIPTION_ID`` env var.
        resource_group:     Default resource group for provider-scoped
                            resources.  Falls back to ``ITL_RESOURCE_GROUP``
                            env var, then ``"default"``.
        provider_namespace: ARM provider namespace used when building paths
                            for provider-scoped resources.
                            Defaults to ``"ITL.Resources"``.
        opts:               Standard Pulumi resource options.
    """

    def __init__(
        self,
        resource_type: str,
        name: str,
        *,
        azure_enabled: bool = True,
        itl_enabled: bool = True,
        itl_endpoint: Optional[str] = None,
        subscription_id: Optional[str] = None,
        resource_group: Optional[str] = None,
        provider_namespace: str = "ITL.Resources",
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(resource_type, name, {}, opts)
        self._azure_enabled = azure_enabled
        self._itl_enabled = itl_enabled
        self._itl_endpoint = itl_endpoint or os.environ.get(
            "ITL_CONTROLPLANE_ENDPOINT", ""
        )
        self._subscription_id = (
            subscription_id
            or os.environ.get("ITL_SUBSCRIPTION_ID", "")
        )
        self._resource_group = (
            resource_group
            or os.environ.get("ITL_RESOURCE_GROUP", "default")
        )
        self._provider_namespace = provider_namespace

    # ------------------------------------------------------------------
    # Protected helpers
    # ------------------------------------------------------------------

    def _register_with_itl(
        self,
        itl_resource_type: str,
        spec: Dict[str, Any],
        *,
        resource_name: Optional[str] = None,
        subscription_id: Optional[str] = None,
        resource_group: Optional[str] = None,
        provider_namespace: Optional[str] = None,
    ) -> Optional[_ITLRegistration]:
        """Register *spec* with the ITL ControlPlane API using an ARM-style path.

        The ARM path is built automatically from *itl_resource_type* and the
        subscription / resource-group context on this component (or the
        call-site overrides).

        Args:
            itl_resource_type:  Logical resource type, e.g. ``"ResourceGroup"``.
            spec:               Body sent to the API (tags, properties, …).
            resource_name:      Resource name in the ARM path.  Defaults to
                                this component's ``name``.
            subscription_id:    Override the component-level subscription.
            resource_group:     Override the component-level resource group.
            provider_namespace: Override the component-level provider namespace.

        Returns:
            The dynamic resource, or ``None`` when ITL is disabled or no
            endpoint is configured.
        """
        if not self._itl_enabled or not self._itl_endpoint:
            if self._itl_enabled and not self._itl_endpoint:
                pulumi.log.warn(
                    f"{self._name}: itl_enabled=True but no endpoint configured "
                    "(set ITL_CONTROLPLANE_ENDPOINT or pass itl_endpoint=)."
                )
            return None

        rname = resource_name or self._name
        sub = subscription_id or self._subscription_id
        rg = resource_group or self._resource_group
        ns = provider_namespace or self._provider_namespace

        arm_path = _build_arm_path(itl_resource_type, rname, sub, rg, ns)

        reg_name = f"{self._name}-itl-{itl_resource_type.lower()}"
        return _ITLRegistration(
            reg_name,
            {
                "endpoint": self._itl_endpoint,
                "arm_path": arm_path,
                "resource_type": itl_resource_type,
                "name": rname,
                **spec,
            },
            opts=pulumi.ResourceOptions(parent=self),
        )
