#!/usr/bin/env python3
"""Simple SDK verification - just test imports work."""

import sys
import importlib

try:
    # Force reload
    if 'itl_controlplane_sdk' in sys.modules:
        del sys.modules['itl_controlplane_sdk']
    
    itl = importlib.import_module('itl_controlplane_sdk')
    print("✓ SDK module imported")
    
    # Try basic provider import
    providers = importlib.import_module('itl_controlplane_sdk.providers')
    print("✓ Providers module loaded")
    
    # Check what's available
    print(f"\nAvailable in providers: {[x for x in dir(providers) if not x.startswith('_')][:10]}")
    
    print("\n✅ SDK build successful!")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
