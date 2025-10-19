"""
Compute Providers for ITL ControlPlane SDK

This package contains providers for compute resources including virtual machines.
"""

from .vm_provider import VirtualMachineProvider, VirtualMachineProperties

__all__ = [
    'VirtualMachineProvider',
    'VirtualMachineProperties'
]