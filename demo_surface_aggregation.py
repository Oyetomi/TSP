#!/usr/bin/env python3
"""
Demo script showing how to configure indoor/outdoor hardcourt aggregation

This demonstrates the Python API for toggling surface aggregation.
You can also edit config.json directly for persistent changes.
"""

from prediction_config import (
    print_surface_aggregation_status,
    enable_hardcourt_aggregation,
    disable_hardcourt_aggregation
)

def main():
    print("🎾 SURFACE AGGREGATION CONFIGURATION DEMO")
    print("=" * 60)
    
    # Show current status
    print("\n1. Current configuration:")
    print_surface_aggregation_status()
    
    # Demo: Disable aggregation
    print("\n2. Testing: DISABLE aggregation (keep indoor/outdoor separate):")
    print("-" * 60)
    disable_hardcourt_aggregation()
    print_surface_aggregation_status()
    
    # Demo: Re-enable aggregation
    print("\n3. Testing: RE-ENABLE aggregation (combine indoor + outdoor):")
    print("-" * 60)
    enable_hardcourt_aggregation()
    print_surface_aggregation_status()
    
    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("\n📝 TWO WAYS TO CONFIGURE:")
    print("\n1️⃣  Edit config.json (RECOMMENDED - persistent):")
    print('   "aggregate_indoor_outdoor_hardcourt": true   # Aggregation ON')
    print('   "aggregate_indoor_outdoor_hardcourt": false  # Aggregation OFF')
    print("\n2️⃣  Python API (programmatic):")
    print("   from prediction_config import enable_hardcourt_aggregation")
    print("   enable_hardcourt_aggregation()   # Larger sample sizes")
    print("   disable_hardcourt_aggregation()  # Surface-specific data")
    print("\n💡 Default: ENABLED (recommended for better data quality)")

if __name__ == "__main__":
    main()

