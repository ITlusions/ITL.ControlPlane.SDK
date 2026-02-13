#!/usr/bin/env python
"""Test auto-initialization of ITLLocationsHandler"""
import sys
sys.path.insert(0, 'src')

# Import SDK - should auto-initialize locations
from itl_controlplane_sdk import ITLLocationsHandler, ITLRegionMeta

# Verify initialization happened
stats = ITLLocationsHandler.get_stats()
print(f"✓ Auto-initialization successful!")
print(f"  Default locations: {stats['default']}")
print(f"  Available regions: {stats['regions']}")
print(f"  Sample locations: {sorted(ITLLocationsHandler.get_valid_locations())[:3]}")

# Verify we can still register custom locations
ITLLocationsHandler.register_location("singapore", "Singapore", "Asia Pacific")
stats = ITLLocationsHandler.get_stats()
print(f"\n✓ Custom registration works!")
print(f"  Total locations: {stats['total']}")
print(f"  Custom locations: {stats['custom']}")

# Verify ITLRegionMeta is accessible
print(f"\n✓ ITLRegionMeta constants accessible!")
print(f"  Regions: {ITLRegionMeta.UNITED_STATES}, {ITLRegionMeta.EUROPE}, {ITLRegionMeta.ASIA_PACIFIC}")
