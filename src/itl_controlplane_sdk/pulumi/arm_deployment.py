"""
ITL ARM Deployment
==================
Deploy ARM templates directly to the ITL ControlPlane API — no Pulumi required.

The workflow mirrors ``az deployment group create``:

    itl deployment create \\
        --template-file template.json \\
        --parameters @params.json \\
        --subscription-id <sub-id>

Or from Python:

    from itl_controlplane_sdk.pulumi import ITLARMDeployment

    deployment = ITLARMDeployment(
        endpoint="https://controlplane.itlusions.com",
        subscription_id="<sub-id>",
    )
    result = deployment.create("my-deployment", template, parameters)
    print(result.outputs)

ITL uses the same ARM resource type format with an ``ITL.`` namespace prefix:

    ITL.Resources/resourceGroups      ↔  Microsoft.Resources/resourceGroups
    ITL.Compute/managedClusters       ↔  Microsoft.ContainerService/managedClusters
    ITL.Security/pricings             ↔  Microsoft.Security/pricings
    ITL.Management/managementGroups   ↔  Microsoft.Management/managementGroups

Both ``ITL.*`` and ``Microsoft.*`` types are accepted; Microsoft types are
automatically normalised to their ITL equivalents before deployment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = ["ITLARMDeployment", "DeploymentResult"]

# ---------------------------------------------------------------------------
# Microsoft → ITL namespace normalisation
# ---------------------------------------------------------------------------

_NAMESPACE_MAP: Dict[str, str] = {
    "microsoft.resources": "ITL.Resources",
    "microsoft.containerservice": "ITL.Compute",
    "microsoft.security": "ITL.Security",
    "microsoft.management": "ITL.Management",
    "microsoft.network": "ITL.Network",
    "microsoft.compute": "ITL.Compute",
    "microsoft.storage": "ITL.Storage",
    "microsoft.authorization": "ITL.Authorization",
    "microsoft.keyvault": "ITL.KeyVault",
}

# ARM resource type → ITL API path segment
_TYPE_TO_PATH: Dict[str, str] = {
    "itl.resources/resourcegroups": "resource-groups",
    "itl.compute/managedclusters": "managed-clusters",
    "itl.security/pricings": "security-pricings",
    "itl.management/managementgroups": "management-groups",
    "itl.network/virtualnetworks": "virtual-networks",
    "itl.compute/virtualmachines": "virtual-machines",
    "itl.storage/storageaccounts": "storage-accounts",
    "itl.authorization/roleassignments": "role-assignments",
    "itl.keyvault/vaults": "key-vaults",
}


def _normalise_type(arm_type: str) -> str:
    """Normalise a Microsoft.* ARM type to its ITL.* equivalent."""
    parts = arm_type.split("/", 1)
    ns = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    itl_ns = _NAMESPACE_MAP.get(ns, parts[0])
    return f"{itl_ns}/{rest}" if rest else itl_ns


def _api_path(itl_type: str) -> str:
    """Return the ITL API path segment for a normalised ITL.* resource type."""
    return _TYPE_TO_PATH.get(itl_type.lower(), itl_type.lower().replace("/", "-").replace(".", "-"))


# ---------------------------------------------------------------------------
# Parameter resolution
# ---------------------------------------------------------------------------

def _resolve_params(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten ARM parameter objects ``{"key": {"value": ...}}`` → ``{"key": ...}``."""
    resolved: Dict[str, Any] = {}
    for k, v in parameters.items():
        if isinstance(v, dict) and "value" in v:
            resolved[k] = v["value"]
        else:
            resolved[k] = v
    return resolved


def _resolve_value(value: Any, params: Dict[str, Any]) -> Any:
    """Resolve an ARM expression like ``[parameters('location')]``."""
    if not isinstance(value, str):
        return value
    m = re.fullmatch(r"\[parameters\('([^']+)'\)\]", value)
    if m:
        return params.get(m.group(1), value)
    return value


def _resolve_resource(resource: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively resolve all parameter references in a resource dict."""
    resolved: Dict[str, Any] = {}
    for k, v in resource.items():
        if isinstance(v, dict):
            resolved[k] = _resolve_resource(v, params)
        elif isinstance(v, list):
            resolved[k] = [
                _resolve_resource(item, params) if isinstance(item, dict)
                else _resolve_value(item, params)
                for item in v
            ]
        else:
            resolved[k] = _resolve_value(v, params)
    return resolved


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ResourceDeploymentResult:
    name: str
    itl_type: str
    status: str          # "created" | "updated" | "failed" | "skipped"
    status_code: int = 0
    error: str = ""


@dataclass
class DeploymentResult:
    deployment_name: str
    subscription_id: str
    resources: List[ResourceDeploymentResult] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0

    @property
    def succeeded(self) -> bool:
        return all(r.status != "failed" for r in self.resources)

    @property
    def failed_resources(self) -> List[ResourceDeploymentResult]:
        return [r for r in self.resources if r.status == "failed"]

    def summary(self) -> str:
        lines = [
            f"Deployment: {self.deployment_name}",
            f"Subscription: {self.subscription_id}",
            f"Duration: {self.finished_at - self.started_at:.1f}s",
            f"Resources: {len(self.resources)} total, "
            f"{sum(1 for r in self.resources if r.status == 'created')} created, "
            f"{sum(1 for r in self.resources if r.status == 'updated')} updated, "
            f"{len(self.failed_resources)} failed",
        ]
        if self.failed_resources:
            lines.append("Failed:")
            for r in self.failed_resources:
                lines.append(f"  - {r.itl_type}/{r.name}: {r.error}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deployment engine
# ---------------------------------------------------------------------------

class ITLARMDeployment:
    """Deploy ARM templates directly to the ITL ControlPlane.

    Parameters
    ----------
    endpoint:
        ITL ControlPlane base URL.  Falls back to the
        ``ITL_CONTROLPLANE_ENDPOINT`` environment variable.
    token:
        Bearer token.  Falls back to ``ITL_CONTROLPLANE_TOKEN``.
    subscription_id:
        Default Azure subscription ID.  Can be overridden per deployment.
    timeout:
        HTTP request timeout in seconds (default 30).
    dry_run:
        When ``True``, build the payload but do not send HTTP requests.
        Useful for validation and testing.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
        subscription_id: str = "",
        timeout: int = 30,
        dry_run: bool = False,
    ) -> None:
        self.endpoint = (endpoint or os.environ.get("ITL_CONTROLPLANE_ENDPOINT", "")).rstrip("/")
        self._token = token  # None → read from env at request time
        self.subscription_id = subscription_id
        self.timeout = timeout
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        deployment_name: str,
        template: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        subscription_id: str = "",
    ) -> DeploymentResult:
        """Deploy an ARM template to ITL.

        Parameters
        ----------
        deployment_name:
            Logical name for this deployment (used for tracking).
        template:
            Parsed ARM template dict.
        parameters:
            ARM parameters dict (``{"key": {"value": ...}}`` or flat).
        subscription_id:
            Override the instance-level ``subscription_id``.
        """
        sub_id = subscription_id or self.subscription_id
        params = _resolve_params(parameters or template.get("parameters", {}))

        result = DeploymentResult(
            deployment_name=deployment_name,
            subscription_id=sub_id,
        )

        for resource in template.get("resources", []):
            res_result = self._deploy_resource(resource, params, sub_id)
            result.resources.append(res_result)

        result.finished_at = time.time()
        return result

    def create_from_file(
        self,
        deployment_name: str,
        template_path: str | Path,
        parameters_path: Optional[str | Path] = None,
        subscription_id: str = "",
    ) -> DeploymentResult:
        """Load an ARM template (and optional parameters file) and deploy."""
        template = json.loads(Path(template_path).read_text(encoding="utf-8"))
        parameters: Dict[str, Any] = {}
        if parameters_path:
            raw = json.loads(Path(parameters_path).read_text(encoding="utf-8"))
            # Support both ARM params file format and flat dicts
            parameters = raw.get("parameters", raw)
        return self.create(deployment_name, template, parameters, subscription_id)

    def delete(
        self,
        deployment_name: str,
        template: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        subscription_id: str = "",
    ) -> DeploymentResult:
        """Delete all resources defined in an ARM template from ITL."""
        sub_id = subscription_id or self.subscription_id
        params = _resolve_params(parameters or template.get("parameters", {}))

        result = DeploymentResult(
            deployment_name=deployment_name,
            subscription_id=sub_id,
        )

        for resource in reversed(template.get("resources", [])):
            res_result = self._delete_resource(resource, params, sub_id)
            result.resources.append(res_result)

        result.finished_at = time.time()
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _deploy_resource(
        self,
        resource: Dict[str, Any],
        params: Dict[str, Any],
        subscription_id: str,
    ) -> ResourceDeploymentResult:
        resolved = _resolve_resource(resource, params)
        raw_type = str(resolved.get("type", ""))
        itl_type = _normalise_type(raw_type)
        name = str(resolved.get("name", ""))
        path_seg = _api_path(itl_type)

        payload = self._build_payload(resolved, itl_type, name, subscription_id)

        if self.dry_run:
            return ResourceDeploymentResult(
                name=name,
                itl_type=itl_type,
                status="skipped",
                status_code=0,
            )

        url = f"{self.endpoint}/api/v1/{path_seg}/{name}"
        try:
            import requests  # type: ignore[import-untyped]

            resp = requests.put(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            status = "created" if resp.status_code in (200, 201) else "updated" if resp.status_code == 204 else "failed"
            return ResourceDeploymentResult(
                name=name,
                itl_type=itl_type,
                status=status,
                status_code=resp.status_code,
                error="" if status != "failed" else resp.text[:200],
            )
        except Exception as exc:
            return ResourceDeploymentResult(
                name=name,
                itl_type=itl_type,
                status="failed",
                error=str(exc),
            )

    def _delete_resource(
        self,
        resource: Dict[str, Any],
        params: Dict[str, Any],
        subscription_id: str,
    ) -> ResourceDeploymentResult:
        resolved = _resolve_resource(resource, params)
        raw_type = str(resolved.get("type", ""))
        itl_type = _normalise_type(raw_type)
        name = str(resolved.get("name", ""))
        path_seg = _api_path(itl_type)

        if self.dry_run:
            return ResourceDeploymentResult(name=name, itl_type=itl_type, status="skipped")

        url = f"{self.endpoint}/api/v1/{path_seg}/{name}"
        try:
            import requests  # type: ignore[import-untyped]

            resp = requests.delete(url, headers=self._headers(), timeout=self.timeout)
            status = "created" if resp.status_code in (200, 204) else "failed"
            return ResourceDeploymentResult(
                name=name,
                itl_type=itl_type,
                status=status,
                status_code=resp.status_code,
                error="" if status != "failed" else resp.text[:200],
            )
        except Exception as exc:
            return ResourceDeploymentResult(
                name=name, itl_type=itl_type, status="failed", error=str(exc)
            )

    def _build_payload(
        self,
        resource: Dict[str, Any],
        itl_type: str,
        name: str,
        subscription_id: str,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "name": name,
            "type": itl_type,
            "location": resource.get("location", "westeurope"),
            "tags": resource.get("tags", {}),
            "properties": resource.get("properties", {}),
            "subscription_id": subscription_id,
        }
        if resource.get("resourceGroup"):
            payload["resource_group"] = resource["resourceGroup"]
        return payload

    def _headers(self) -> Dict[str, str]:
        token = self._token or os.environ.get("ITL_CONTROLPLANE_TOKEN", "")
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers


# ---------------------------------------------------------------------------
# CLI — mirrors az deployment group create
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        prog="itl-arm-deploy",
        description="Deploy an ARM template to the ITL ControlPlane",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    create_p = sub.add_parser("create", help="Deploy a template")
    create_p.add_argument("--name", "-n", required=True, help="Deployment name")
    create_p.add_argument("--template-file", "-f", required=True, help="ARM template JSON")
    create_p.add_argument("--parameters", "-p", help="Parameters file (@file.json or inline JSON)")
    create_p.add_argument("--subscription-id", default="", help="Subscription ID")
    create_p.add_argument("--endpoint", default="", help="ITL ControlPlane endpoint")
    create_p.add_argument("--dry-run", action="store_true", help="Validate without deploying")

    # delete
    delete_p = sub.add_parser("delete", help="Delete resources defined in a template")
    delete_p.add_argument("--name", "-n", required=True, help="Deployment name")
    delete_p.add_argument("--template-file", "-f", required=True, help="ARM template JSON")
    delete_p.add_argument("--subscription-id", default="", help="Subscription ID")
    delete_p.add_argument("--endpoint", default="", help="ITL ControlPlane endpoint")
    delete_p.add_argument("--dry-run", action="store_true", help="Validate without deleting")

    args = parser.parse_args()

    deployment = ITLARMDeployment(
        endpoint=args.endpoint or None,
        subscription_id=args.subscription_id,
        dry_run=args.dry_run,
    )

    template = json.loads(Path(args.template_file).read_text(encoding="utf-8"))

    parameters: Dict[str, Any] = {}
    if hasattr(args, "parameters") and args.parameters:
        p = args.parameters
        if p.startswith("@"):
            parameters = json.loads(Path(p[1:]).read_text(encoding="utf-8"))
        else:
            parameters = json.loads(p)

    if args.command == "create":
        result = deployment.create(args.name, template, parameters, args.subscription_id)
    else:
        result = deployment.delete(args.name, template, parameters, args.subscription_id)

    print(result.summary())
    sys.exit(0 if result.succeeded else 1)


if __name__ == "__main__":
    _main()
