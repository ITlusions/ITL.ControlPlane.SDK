#!/usr/bin/env python3
"""Verify SDK build and imports."""

import sys

try:
    import itl_controlplane_sdk
    print("✓ SDK imported successfully")
    print(f"  Package: {itl_controlplane_sdk.__name__}")
    
    # Try importing key modules
    from itl_controlplane_sdk.core import exceptions
    print("✓ Core exceptions module loaded")
    
    from itl_controlplane_sdk.providers import ResourceProvider
    print("✓ ResourceProvider class accessible")
    
    from itl_controlplane_sdk.identity import IdentityProvider
    print("✓ Identity framework loaded")
    
    print("\n✅ SDK build successful - all core modules accessible")
    
except SyntaxError as e:
    print(f"❌ Syntax error in SDK: {e}")
    print(f"   File: {e.filename}, Line: {e.lineno}")
    sys.exit(1)
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
