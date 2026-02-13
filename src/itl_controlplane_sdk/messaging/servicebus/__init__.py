"""
Service Bus Providers and Managers for ITL ControlPlane SDK.

Provider execution modes (API, ServiceBus, Hybrid) and service bus consumers.

Example:
    ```python
    from itl_controlplane_sdk.providers import ComputeProvider
    from itl_controlplane_sdk.messaging.servicebus import (
        ProviderModeManager,
        GenericServiceBusProvider,
        run_generic_servicebus_provider,
    )
    
    provider = ComputeProvider(engine=storage_engine)
    manager = ProviderModeManager(
        provider=provider,
        provider_namespace="ITL.Compute",
        app=fastapi_app,
        mode="hybrid"  # API + ServiceBus
    )
    await manager.run()
    ```
"""

from .generic import GenericServiceBusProvider
from .mode_manager import (
    ProviderModeManager,
    ProviderMode,
    run_generic_servicebus_provider,
)

__all__ = [
    # Providers
    "GenericServiceBusProvider",
    # Managers
    "ProviderModeManager",
    # Enums
    "ProviderMode",
    # Factory
    "run_generic_servicebus_provider",
]
