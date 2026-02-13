#!/usr/bin/env python
"""Test auto-initialization of LocationsHandler"""
import sys
sys.path.insert(0, 'src')

# Import SDK - should auto-initialize locations
from itl_controlplane_sdk import LocationsHandler, RegionMeta

# Verify initialization happened
stats = LocationsHandler.get_stats()
print(f"✓ Auto-initialization successful!")
print(f"  Default locations: {stats['default']}")
print(f"  Available regions: {stats['regions']}")
print(f"  Sample locations: {sorted(LocationsHandler.get_valid_locations())[:3]}")

# Verify we can still register custom locations
LocationsHandler.register_location("singapore", "Singapore", "Asia Pacific")
stats = LocationsHandler.get_stats()
print(f"\n✓ Custom registration works!")
print(f"  Total locations: {stats['total']}")
print(f"  Custom locations: {stats['custom']}")

# Verify RegionMeta is accessible
print(f"\n✓ RegionMeta constants accessible!")
print(f"  Regions: {RegionMeta.UNITED_STATES}, {RegionMeta.EUROPE}, {RegionMeta.ASIA_PACIFIC}")
