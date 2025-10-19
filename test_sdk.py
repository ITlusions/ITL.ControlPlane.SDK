#!/usr/bin/env python3
"""
Test script to validate the ITL ControlPlane SDK installation and functionality
"""

def test_imports():
    """Test that all core components can be imported"""
    try:
        from itl_controlplane_sdk import (
            ResourceProviderRegistry,
            ResourceProvider,
            ResourceRequest,
            ResourceResponse,
            ProvisioningState
        )
        print("✅ All core imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic SDK functionality"""
    try:
        from itl_controlplane_sdk import (
            ResourceProviderRegistry, 
            ResourceProvider, 
            ResourceRequest, 
            ResourceResponse, 
            ResourceListResponse,
            ProvisioningState
        )
        
        # Create a registry
        registry = ResourceProviderRegistry()
        
        # Create a simple test provider
        class TestProvider(ResourceProvider):
            def __init__(self):
                super().__init__("TestProvider")
            
            async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
                return ResourceResponse(
                    id=f"test-{request.resource_name}",
                    name=request.resource_name,
                    type=request.resource_type,
                    location=request.location,
                    properties=request.body,
                    tags={},
                    provisioning_state=ProvisioningState.SUCCEEDED
                )
            
            async def get_resource(self, resource_id: str) -> ResourceResponse:
                return ResourceResponse(
                    id=resource_id,
                    name="test-resource",
                    type="test",
                    location="eastus",
                    properties={},
                    tags={},
                    provisioning_state=ProvisioningState.SUCCEEDED
                )
            
            async def delete_resource(self, resource_id: str) -> bool:
                return True
            
            async def list_resources(self, resource_group: str) -> ResourceListResponse:
                return ResourceListResponse(value=[])
        
        # Register the provider
        provider = TestProvider()
        registry.register_provider("test", "testType", provider)
        
        # Verify registration
        providers = registry.list_providers()
        assert len(providers) > 0
        
        print("✅ Basic functionality test passed")
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_version():
    """Test that version information is accessible"""
    try:
        import itl_controlplane_sdk
        version = itl_controlplane_sdk.__version__
        print(f"✅ Version: {version}")
        return True
    except Exception as e:
        print(f"❌ Version test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 ITL ControlPlane SDK - Validation Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_basic_functionality,
        test_version
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("=" * 50)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! SDK is ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the installation.")
        return 1

if __name__ == "__main__":
    exit(main())