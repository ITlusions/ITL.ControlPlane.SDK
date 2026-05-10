"""
Pulumi Infrastructure as Code Module

Provides Pulumi integration for managing cloud infrastructure
through the ITL ControlPlane SDK.

DSL components (recommended)
-----------------------------
Use these native ``pulumi.ComponentResource`` classes in your Pulumi programs:

* :class:`~.component.ITLPulumiComponent` — base class for all ITL components
* :class:`~.landing_zone.ITLLandingZone` — full landing zone
* :class:`~.aks.AKSCluster` — AKS with Flux, Defender, and logging
* :class:`~.defender.DefenderInitiative` — Defender for Cloud initiative

Each component accepts ``azure_enabled`` / ``itl_enabled`` flags for
dual-target deployment (Azure + ITL ControlPlane simultaneously).

Automation API wrapper (legacy)
--------------------------------
:class:`~.azure.ITLAzureStack` — code-generation wrapper around the
``PulumiRenderer`` + Pulumi Automation API.  Still available for scenarios
where you need to run Pulumi programmatically without writing a Pulumi program.
"""

__version__ = "1.1.0"
__author__ = "ITL Platform Engineering"

# DSL components
from .component import ITLPulumiComponent
from .resource_group import ResourceGroup
from .management_group import ManagementGroup
from .landing_zone import ITLLandingZone
from .aks import AKSCluster
from .defender import DefenderInitiative

# Infrastructure primitives
from .stack import PulumiStack, StackConfig
from .resource_mapper import ResourceMapper
from .deployment import PulumiDeployment

# ARM → ITL converter (generates Pulumi code)
from .arm_converter import ARMConverter

# ARM → ITL direct deployment (no Pulumi required)
from .arm_deployment import ITLARMDeployment, DeploymentResult

# Legacy Automation API wrapper
from .azure import ITLAzureStack

__all__ = [
    # DSL components
    "ITLPulumiComponent",
    "ResourceGroup",
    "ManagementGroup",
    "ITLLandingZone",
    "AKSCluster",
    "DefenderInitiative",
    # Infrastructure primitives
    "PulumiStack",
    "StackConfig",
    "ResourceMapper",
    "PulumiDeployment",
    # ARM tooling
    "ARMConverter",       # ARM template → Pulumi Python code
    "ITLARMDeployment",   # ARM template → ITL ControlPlane (direct)
    "DeploymentResult",
    # Legacy
    "ITLAzureStack",
]
