"""
ARM → ITL Pulumi DSL Converter
================================
Converts an Azure ARM template (JSON) into a ready-to-run Pulumi ``__main__.py``
that uses the ITL DSL components.

Known ARM resource types are mapped to ITL components:

    Microsoft.Resources/resourceGroups        → ResourceGroup
    Microsoft.ContainerService/managedClusters → AKSCluster
    Microsoft.Security/pricings               → DefenderInitiative
    Microsoft.Management/managementGroups     → ManagementGroup

All other resource types are emitted as ``pulumi_azure_native`` passthrough
calls so nothing is lost during conversion.

Usage
-----
**CLI:**

    python -m itl_controlplane_sdk.pulumi.arm_converter template.json \\
        --subscription-id <sub-id> \\
        --itl-enabled \\
        --output __main__.py

**Python API:**

    from itl_controlplane_sdk.pulumi import ARMConverter

    converter = ARMConverter(azure_enabled=True, itl_enabled=True)
    code = converter.convert_file("template.json", subscription_id="<sub-id>")
    print(code)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["ARMConverter"]

# ---------------------------------------------------------------------------
# Resource type → ITL component mapping
# ITL uses the same ARM structure with an "ITL." namespace prefix:
#   Microsoft.Resources  → ITL.Resources
#   Microsoft.ContainerService → ITL.Compute
#   Microsoft.Security   → ITL.Security
#   Microsoft.Management → ITL.Management
# ---------------------------------------------------------------------------

_ITL_COMPONENT_MAP: Dict[str, str] = {
    # Microsoft ARM types
    "microsoft.resources/resourcegroups": "ResourceGroup",
    "microsoft.containerservice/managedclusters": "AKSCluster",
    "microsoft.security/pricings": "DefenderInitiative",
    "microsoft.management/managementgroups": "ManagementGroup",
    # ITL-native ARM types (same structure, ITL. prefix)
    "itl.resources/resourcegroups": "ResourceGroup",
    "itl.compute/managedclusters": "AKSCluster",
    "itl.security/pricings": "DefenderInitiative",
    "itl.management/managementgroups": "ManagementGroup",
}

_DEFENDER_PLAN_TYPES = {
    "microsoft.security/pricings",
    "itl.security/pricings",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_name(arm_name: str) -> str:
    """Convert an ARM resource name to a valid Python identifier."""
    name = re.sub(r"[^a-zA-Z0-9_]", "_", arm_name)
    if name[0].isdigit():
        name = "r_" + name
    return name.lower()


def _arm_location(resource: Dict[str, Any], params: Dict[str, Any]) -> str:
    """Resolve the location value, substituting template parameters if needed."""
    loc = resource.get("location", "westeurope")
    if isinstance(loc, str) and loc.startswith("[parameters("):
        param_name = re.search(r"parameters\('([^']+)'\)", loc)
        if param_name:
            key = param_name.group(1)
            default = params.get(key, {}).get("defaultValue", "westeurope")
            return str(default)
    return str(loc)


def _arm_param(value: Any, params: Dict[str, Any], default: Any = None) -> Any:
    """Resolve an ARM parameter reference or return the literal value."""
    if isinstance(value, str):
        m = re.search(r"parameters\('([^']+)'\)", value)
        if m:
            key = m.group(1)
            return params.get(key, {}).get("defaultValue", default)
    return value if value is not None else default


# ---------------------------------------------------------------------------
# Per-type converters
# ---------------------------------------------------------------------------

class _ResourceConverter:
    """Base — emits a generic pulumi_azure_native passthrough."""

    def __init__(self, resource: Dict[str, Any], params: Dict[str, Any]) -> None:
        self.resource = resource
        self.params = params
        self.arm_name: str = str(resource.get("name", "unnamed"))
        self.py_name: str = _safe_name(self.arm_name)
        self.location: str = _arm_location(resource, params)
        self.rtype: str = str(resource.get("type", ""))

    def imports(self) -> List[str]:
        return ["import pulumi_azure_native as azure_native"]

    def code(self, azure_enabled: bool, itl_enabled: bool, subscription_id: str) -> str:
        ns, resource_class = self._split_type()
        indent = "    "
        lines = [
            f'{self.py_name} = azure_native.{ns}.{resource_class}(',
            f'{indent}"{self.arm_name}",',
            f'{indent}location="{self.location}",',
        ]
        props = self.resource.get("properties", {})
        for k, v in props.items():
            lines.append(f"{indent}{_safe_name(k)}={json.dumps(v)},")
        lines.append(")")
        return "\n".join(lines)

    def _split_type(self) -> Tuple[str, str]:
        parts = self.rtype.split("/")
        if len(parts) < 2:
            return "resources", "Resource"
        ns = parts[0].lower().replace("microsoft.", "")
        cls = parts[1][0].upper() + parts[1][1:]
        return ns, cls


class _ResourceGroupConverter(_ResourceConverter):
    def imports(self) -> List[str]:
        return ["from itl_controlplane_sdk.pulumi import ResourceGroup"]

    def code(self, azure_enabled: bool, itl_enabled: bool, subscription_id: str) -> str:
        props = self.resource.get("properties", {})
        tags = self.resource.get("tags", {})
        owner = tags.get("owner", "")
        environment = tags.get("environment", "production")
        lock = props.get("lock", True)
        lines = [
            f'{self.py_name} = ResourceGroup(',
            f'    "{self.arm_name}",',
            f'    location="{self.location}",',
            f'    environment="{environment}",',
        ]
        if owner:
            lines.append(f'    owner="{owner}",')
        if not lock:
            lines.append(f"    lock=False,")
        if subscription_id:
            lines.append(f'    subscription_id="{subscription_id}",')
        lines += [
            f"    azure_enabled={azure_enabled},",
            f"    itl_enabled={itl_enabled},",
            ")",
        ]
        return "\n".join(lines)


class _AKSConverter(_ResourceConverter):
    def imports(self) -> List[str]:
        return ["from itl_controlplane_sdk.pulumi import AKSCluster"]

    def code(self, azure_enabled: bool, itl_enabled: bool, subscription_id: str) -> str:
        props = self.resource.get("properties", {})
        agent_pool = (props.get("agentPoolProfiles") or [{}])[0]
        node_count = agent_pool.get("count", 3)
        vm_size = agent_pool.get("vmSize", "Standard_D4s_v5")
        k8s_version = props.get("kubernetesVersion", "1.30")
        rg_name = _arm_param(
            self.resource.get("resourceGroup", ""),
            self.params,
            "",
        )
        lines = [
            f'{self.py_name} = AKSCluster(',
            f'    "{self.arm_name}",',
            f'    location="{self.location}",',
            f'    resource_group_name="{rg_name or self.arm_name + "-rg"}",',
            f'    node_count={node_count},',
            f'    node_vm_size="{vm_size}",',
            f'    kubernetes_version="{k8s_version}",',
        ]
        if subscription_id:
            lines.append(f'    subscription_id="{subscription_id}",')
        lines += [
            f"    azure_enabled={azure_enabled},",
            f"    itl_enabled={itl_enabled},",
            ")",
        ]
        return "\n".join(lines)


class _DefenderConverter(_ResourceConverter):
    """Aggregates multiple Microsoft.Security/pricings into one DefenderInitiative."""

    # This is a sentinel — the actual aggregation happens in ARMConverter
    def imports(self) -> List[str]:
        return ["from itl_controlplane_sdk.pulumi import DefenderInitiative"]

    def code(self, azure_enabled: bool, itl_enabled: bool, subscription_id: str) -> str:
        return ""  # handled by ARMConverter._emit_defender_block


class _ManagementGroupConverter(_ResourceConverter):
    def imports(self) -> List[str]:
        return ["from itl_controlplane_sdk.pulumi import ManagementGroup"]

    def code(self, azure_enabled: bool, itl_enabled: bool, subscription_id: str) -> str:
        props = self.resource.get("properties", {})
        display_name = props.get("displayName", self.arm_name)
        parent_id = props.get("details", {}).get("parent", {}).get("id", "")
        lines = [
            f'{self.py_name} = ManagementGroup(',
            f'    "{self.arm_name}",',
            f'    display_name="{display_name}",',
            f'    group_id="{self.arm_name}",',
        ]
        if parent_id:
            lines.append(f'    parent_id="{parent_id}",')
        if subscription_id:
            lines.append(f'    subscription_ids=["{subscription_id}"],')
        lines += [
            f"    azure_enabled={azure_enabled},",
            f"    itl_enabled={itl_enabled},",
            ")",
        ]
        return "\n".join(lines)


_TYPE_TO_CONVERTER = {
    # Microsoft ARM types
    "microsoft.resources/resourcegroups": _ResourceGroupConverter,
    "microsoft.containerservice/managedclusters": _AKSConverter,
    "microsoft.security/pricings": _DefenderConverter,
    "microsoft.management/managementgroups": _ManagementGroupConverter,
    # ITL-native ARM types
    "itl.resources/resourcegroups": _ResourceGroupConverter,
    "itl.compute/managedclusters": _AKSConverter,
    "itl.security/pricings": _DefenderConverter,
    "itl.management/managementgroups": _ManagementGroupConverter,
}


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

class ARMConverter:
    """Convert an ARM template to a Pulumi ITL DSL ``__main__.py``.

    Parameters
    ----------
    azure_enabled:
        Emit ``azure_enabled=True`` on all ITL components (default ``True``).
    itl_enabled:
        Emit ``itl_enabled=True`` on all ITL components (default ``True``).
    """

    def __init__(
        self,
        azure_enabled: bool = True,
        itl_enabled: bool = True,
    ) -> None:
        self.azure_enabled = azure_enabled
        self.itl_enabled = itl_enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(
        self,
        template: Dict[str, Any],
        subscription_id: str = "",
    ) -> str:
        """Convert an ARM template dict to Pulumi Python source code."""
        params = template.get("parameters", {})
        resources: List[Dict[str, Any]] = template.get("resources", [])

        converters: List[_ResourceConverter] = []
        defender_resources: List[Dict[str, Any]] = []

        for res in resources:
            rtype = str(res.get("type", "")).lower()
            if rtype in _DEFENDER_PLAN_TYPES:
                defender_resources.append(res)
                continue
            cls = _TYPE_TO_CONVERTER.get(rtype, _ResourceConverter)
            converters.append(cls(res, params))  # type: ignore[arg-type]

        return self._render(converters, defender_resources, params, subscription_id)

    def convert_file(
        self,
        path: str | Path,
        subscription_id: str = "",
    ) -> str:
        """Load an ARM template from *path* and convert it."""
        template = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.convert(template, subscription_id=subscription_id)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(
        self,
        converters: List[_ResourceConverter],
        defender_resources: List[Dict[str, Any]],
        params: Dict[str, Any],
        subscription_id: str,
    ) -> str:
        imports: List[str] = ["import pulumi"]

        # Collect imports
        for conv in converters:
            for imp in conv.imports():
                if imp not in imports:
                    imports.append(imp)
        if defender_resources:
            imp = "from itl_controlplane_sdk.pulumi import DefenderInitiative"
            if imp not in imports:
                imports.append(imp)

        blocks: List[str] = ["\n".join(imports), ""]

        # Config block
        blocks.append("cfg = pulumi.Config()")
        if subscription_id:
            blocks.append(f'subscription_id = cfg.get("subscription_id") or "{subscription_id}"')
        else:
            blocks.append('subscription_id = cfg.require("subscription_id")')
        blocks.append("")

        # Resource blocks
        for conv in converters:
            code = conv.code(self.azure_enabled, self.itl_enabled, subscription_id)
            if code:
                blocks.append(code)
                blocks.append("")

        # Aggregate Defender plans into one DefenderInitiative
        if defender_resources:
            blocks.append(self._emit_defender_block(defender_resources, subscription_id))
            blocks.append("")

        # Exports
        output_lines = ["# Outputs"]
        for conv in converters:
            if isinstance(conv, _ResourceGroupConverter):
                output_lines.append(
                    f'pulumi.export("{conv.py_name}_id", {conv.py_name}.resource_group_id)'
                )
            elif isinstance(conv, _AKSConverter):
                output_lines.append(
                    f'pulumi.export("{conv.py_name}_name", {conv.py_name}.cluster_name)'
                )
            elif isinstance(conv, _ManagementGroupConverter):
                output_lines.append(
                    f'pulumi.export("{conv.py_name}_id", {conv.py_name}.management_group_id)'
                )
        if defender_resources:
            output_lines.append('pulumi.export("defender_initiative_id", defender.initiative_id)')

        blocks.append("\n".join(output_lines))

        return "\n".join(blocks)

    def _emit_defender_block(
        self,
        defender_resources: List[Dict[str, Any]],
        subscription_id: str,
    ) -> str:
        plans = [
            str(r.get("name", "")).lower().split("/")[-1]
            for r in defender_resources
        ]
        # Determine environment from tags
        env = "production"
        for r in defender_resources:
            env = r.get("tags", {}).get("environment", env)

        lines = [
            "defender = DefenderInitiative(",
            '    "defender-initiative",',
            f'    subscription_id="{subscription_id}",',
            f'    environment="{env}",',
            f"    plans={json.dumps(plans)},",
            f"    azure_enabled={self.azure_enabled},",
            f"    itl_enabled={self.itl_enabled},",
            ")",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an ARM template to a Pulumi ITL DSL __main__.py",
    )
    parser.add_argument("template", help="Path to ARM template JSON file")
    parser.add_argument(
        "--subscription-id",
        default="",
        help="Azure subscription ID to embed in the output",
    )
    parser.add_argument(
        "--itl-enabled",
        action="store_true",
        default=True,
        help="Enable ITL ControlPlane registration (default: on)",
    )
    parser.add_argument(
        "--no-itl",
        action="store_true",
        help="Disable ITL ControlPlane registration",
    )
    parser.add_argument(
        "--no-azure",
        action="store_true",
        help="Disable Azure provisioning (ITL-only)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="-",
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()

    itl_enabled = not args.no_itl
    azure_enabled = not args.no_azure

    converter = ARMConverter(azure_enabled=azure_enabled, itl_enabled=itl_enabled)
    code = converter.convert_file(args.template, subscription_id=args.subscription_id)

    if args.output == "-":
        print(code)
    else:
        Path(args.output).write_text(code, encoding="utf-8")
        print(f"Written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    _main()
