"""
Virtual Machine Resource Provider for ITL ControlPlane SDK

This provider manages virtual machine resources using the ITL ControlPlane SDK framework.
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ...src.controlplane_sdk.resource_provider import ResourceProvider
from ...src.controlplane_sdk.models import ResourceRequest, ResourceResponse, ResourceListResponse, ProvisioningState

logger = logging.getLogger(__name__)

@dataclass
class VirtualMachineProperties:
    """Virtual machine specific properties"""
    vm_size: str = "Standard_B1s"
    admin_username: str = "azureuser"
    disable_password_authentication: bool = True
    ssh_public_keys: List[str] = field(default_factory=list)
    os_disk_name: str = ""
    os_disk_caching: str = "ReadWrite"
    os_disk_create_option: str = "FromImage"
    image_publisher: str = "Canonical"
    image_offer: str = "0001-com-ubuntu-server-focal"
    image_sku: str = "20_04-lts-gen2"
    image_version: str = "latest"
    network_interface_ids: List[str] = field(default_factory=list)
    power_state: str = "running"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "hardwareProfile": {
                "vmSize": self.vm_size
            },
            "osProfile": {
                "computerName": "vm-computer",
                "adminUsername": self.admin_username,
                "disablePasswordAuthentication": self.disable_password_authentication,
                "linuxConfiguration": {
                    "ssh": {
                        "publicKeys": [
                            {"keyData": key} for key in self.ssh_public_keys
                        ]
                    }
                } if self.ssh_public_keys else None
            },
            "storageProfile": {
                "osDisk": {
                    "name": self.os_disk_name,
                    "caching": self.os_disk_caching,
                    "createOption": self.os_disk_create_option
                },
                "imageReference": {
                    "publisher": self.image_publisher,
                    "offer": self.image_offer,
                    "sku": self.image_sku,
                    "version": self.image_version
                }
            },
            "networkProfile": {
                "networkInterfaces": [
                    {"id": nic_id} for nic_id in self.network_interface_ids
                ]
            },
            "powerState": self.power_state,
            "provisioningState": ProvisioningState.SUCCEEDED.value
        }

class VirtualMachineProvider(ResourceProvider):
    """
    Virtual Machine Resource Provider implementation using the ITL ControlPlane SDK
    
    This demonstrates how to create a resource provider that manages
    virtual machine resources with standard REST APIs.
    """
    
    def __init__(self):
        super().__init__("ITL.Compute")
        self.supported_resource_types = ["virtualMachines"]
        
        # In-memory storage for demo (replace with actual backend)
        self._vms: Dict[str, VirtualMachineProperties] = {}
    
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Create or update a virtual machine"""
        vm_name = request.resource_name
        properties = request.body.get("properties", {})
        
        logger.info(f"Creating/updating VM: {vm_name}")
        
        # Validate VM-specific properties
        vm_errors = self._validate_vm_properties(properties)
        if vm_errors:
            raise ValueError(f"VM validation errors: {', '.join(vm_errors)}")
        
        # Parse VM properties
        vm_props = self._parse_vm_properties(properties, vm_name)
        
        # Simulate VM creation (replace with actual implementation)
        await self._simulate_vm_creation(vm_name)
        
        # Store in memory (replace with persistent storage)
        storage_key = f"{request.subscription_id}:{request.resource_group}:{vm_name}"
        self._vms[storage_key] = vm_props
        
        # Generate resource ID
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "virtualMachines", vm_name
        )
        
        # Create response
        response = ResourceResponse(
            id=resource_id,
            name=vm_name,
            type=f"{self.provider_namespace}/virtualMachines",
            location=request.location,
            properties=vm_props.to_dict(),
            tags=request.body.get("tags"),
            provisioning_state=ProvisioningState.SUCCEEDED
        )
        
        logger.info(f"VM created successfully: {resource_id}")
        return response
    
    async def get_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Get a virtual machine"""
        vm_name = request.resource_name
        storage_key = f"{request.subscription_id}:{request.resource_group}:{vm_name}"
        
        if storage_key not in self._vms:
            raise ValueError(f"Virtual machine '{vm_name}' not found")
        
        vm_props = self._vms[storage_key]
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "virtualMachines", vm_name
        )
        
        response = ResourceResponse(
            id=resource_id,
            name=vm_name,
            type=f"{self.provider_namespace}/virtualMachines",
            location=request.location,
            properties=vm_props.to_dict()
        )
        
        logger.info(f"Retrieved VM: {resource_id}")
        return response
    
    async def list_resources(self, request: ResourceRequest) -> ResourceListResponse:
        """List all virtual machines in a resource group"""
        prefix = f"{request.subscription_id}:{request.resource_group}:"
        vm_responses = []
        
        for key, vm_props in self._vms.items():
            if key.startswith(prefix):
                vm_name = key.split(':')[-1]
                resource_id = self.generate_resource_id(
                    request.subscription_id, request.resource_group, "virtualMachines", vm_name
                )
                
                vm_responses.append(ResourceResponse(
                    id=resource_id,
                    name=vm_name,
                    type=f"{self.provider_namespace}/virtualMachines",
                    location=request.location,
                    properties=vm_props.to_dict()
                ))
        
        logger.info(f"Listed {len(vm_responses)} VMs in resource group {request.resource_group}")
        return ResourceListResponse(value=vm_responses)
    
    async def delete_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Delete a virtual machine"""
        vm_name = request.resource_name
        storage_key = f"{request.subscription_id}:{request.resource_group}:{vm_name}"
        
        if storage_key not in self._vms:
            raise ValueError(f"Virtual machine '{vm_name}' not found")
        
        # Simulate VM deletion
        await self._simulate_vm_deletion(vm_name)
        del self._vms[storage_key]
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "virtualMachines", vm_name
        )
        
        response = ResourceResponse(
            id=resource_id,
            name=vm_name,
            type=f"{self.provider_namespace}/virtualMachines",
            location=request.location,
            properties={
                "provisioningState": "Deleted"
            }
        )
        
        logger.info(f"VM deleted: {resource_id}")
        return response
    
    async def execute_action(self, request: ResourceRequest) -> ResourceResponse:
        """Execute custom actions on virtual machine"""
        vm_name = request.resource_name
        action = request.action
        storage_key = f"{request.subscription_id}:{request.resource_group}:{vm_name}"
        
        if storage_key not in self._vms:
            raise ValueError(f"Virtual machine '{vm_name}' not found")
        
        vm_props = self._vms[storage_key]
        
        if action == "start":
            await self._simulate_vm_start(vm_name)
            vm_props.power_state = "running"
            result_data = {"status": "VM start initiated", "powerState": "running"}
        
        elif action == "stop":
            await self._simulate_vm_stop(vm_name)
            vm_props.power_state = "stopped"
            result_data = {"status": "VM stop initiated", "powerState": "stopped"}
        
        elif action == "restart":
            await self._simulate_vm_restart(vm_name)
            vm_props.power_state = "running"
            result_data = {"status": "VM restart initiated", "powerState": "running"}
        
        elif action == "deallocate":
            await self._simulate_vm_deallocate(vm_name)
            vm_props.power_state = "deallocated"
            result_data = {"status": "VM deallocated", "powerState": "deallocated"}
        
        else:
            raise NotImplementedError(f"Action '{action}' not supported for virtual machines")
        
        # Update stored VM
        self._vms[storage_key] = vm_props
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "virtualMachines", vm_name
        )
        
        response = ResourceResponse(
            id=resource_id,
            name=vm_name,
            type=f"{self.provider_namespace}/virtualMachines",
            location=request.location,
            properties={
                "action": action,
                "result": result_data,
                "powerState": vm_props.power_state,
                "provisioningState": ProvisioningState.SUCCEEDED.value
            }
        )
        
        logger.info(f"Executed action '{action}' on VM: {vm_name}")
        return response
    
    def _validate_vm_properties(self, properties: Dict[str, Any]) -> List[str]:
        """Validate virtual machine specific properties"""
        errors = []
        
        hardware_profile = properties.get("hardwareProfile", {})
        if not hardware_profile.get("vmSize"):
            errors.append("hardwareProfile.vmSize is required")
        
        os_profile = properties.get("osProfile", {})
        if not os_profile.get("adminUsername"):
            errors.append("osProfile.adminUsername is required")
        
        storage_profile = properties.get("storageProfile", {})
        if not storage_profile.get("imageReference"):
            errors.append("storageProfile.imageReference is required")
        
        return errors
    
    def _parse_vm_properties(self, properties: Dict[str, Any], vm_name: str) -> VirtualMachineProperties:
        """Parse and convert request properties to VM properties"""
        vm_props = VirtualMachineProperties()
        
        # Hardware profile
        hardware_profile = properties.get("hardwareProfile", {})
        vm_props.vm_size = hardware_profile.get("vmSize", vm_props.vm_size)
        
        # OS profile
        os_profile = properties.get("osProfile", {})
        vm_props.admin_username = os_profile.get("adminUsername", vm_props.admin_username)
        vm_props.disable_password_authentication = os_profile.get("disablePasswordAuthentication", True)
        
        # SSH keys
        linux_config = os_profile.get("linuxConfiguration", {})
        ssh_config = linux_config.get("ssh", {})
        public_keys = ssh_config.get("publicKeys", [])
        vm_props.ssh_public_keys = [key.get("keyData", "") for key in public_keys]
        
        # Storage profile
        storage_profile = properties.get("storageProfile", {})
        
        os_disk = storage_profile.get("osDisk", {})
        vm_props.os_disk_name = os_disk.get("name", f"{vm_name}-osdisk")
        vm_props.os_disk_caching = os_disk.get("caching", vm_props.os_disk_caching)
        vm_props.os_disk_create_option = os_disk.get("createOption", vm_props.os_disk_create_option)
        
        image_ref = storage_profile.get("imageReference", {})
        vm_props.image_publisher = image_ref.get("publisher", vm_props.image_publisher)
        vm_props.image_offer = image_ref.get("offer", vm_props.image_offer)
        vm_props.image_sku = image_ref.get("sku", vm_props.image_sku)
        vm_props.image_version = image_ref.get("version", vm_props.image_version)
        
        # Network profile
        network_profile = properties.get("networkProfile", {})
        network_interfaces = network_profile.get("networkInterfaces", [])
        vm_props.network_interface_ids = [nic.get("id", "") for nic in network_interfaces]
        
        return vm_props
    
    async def _simulate_vm_creation(self, vm_name: str):
        """Simulate VM creation delay"""
        logger.info(f"Simulating VM creation for {vm_name}")
        await asyncio.sleep(0.1)  # Simulate deployment time
    
    async def _simulate_vm_deletion(self, vm_name: str):
        """Simulate VM deletion delay"""
        logger.info(f"Simulating VM deletion for {vm_name}")
        await asyncio.sleep(0.1)
    
    async def _simulate_vm_start(self, vm_name: str):
        """Simulate VM start operation"""
        logger.info(f"Starting VM: {vm_name}")
        await asyncio.sleep(0.1)
    
    async def _simulate_vm_stop(self, vm_name: str):
        """Simulate VM stop operation"""
        logger.info(f"Stopping VM: {vm_name}")
        await asyncio.sleep(0.1)
    
    async def _simulate_vm_restart(self, vm_name: str):
        """Simulate VM restart operation"""
        logger.info(f"Restarting VM: {vm_name}")
        await asyncio.sleep(0.1)
    
    async def _simulate_vm_deallocate(self, vm_name: str):
        """Simulate VM deallocation"""
        logger.info(f"Deallocating VM: {vm_name}")
        await asyncio.sleep(0.1)