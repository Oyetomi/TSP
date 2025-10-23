#!/usr/bin/env python3
"""
Demo: Multi-Year Statistics Configuration

This script demonstrates how to configure and use the multi-year statistics feature.
You can switch between 2-year mode (2024-2025) and 3-year mode (2023-2024-2025).
"""

import prediction_config

def main():
    print("=" * 70)
    print("🎾 MULTI-YEAR STATISTICS DEMO")
    print("=" * 70)
    
    # Show current status
    print("\n1️⃣  CURRENT CONFIGURATION:")
    prediction_config.print_multi_year_stats_status()
    
    # Enable 3-year mode
    print("\n2️⃣  ENABLING 3-YEAR MODE:")
    print("-" * 70)
    prediction_config.enable_three_year_stats()
    
    # Show updated status
    print("\n3️⃣  UPDATED CONFIGURATION:")
    prediction_config.print_multi_year_stats_status()
    
    # Adjust minimum years required
    print("\n4️⃣  SETTING MINIMUM YEARS REQUIRED:")
    print("-" * 70)
    print("\nSetting to 2 (require at least 2 out of 3 years):")
    prediction_config.set_min_years_required(2)
    
    print("\n5️⃣  FINAL CONFIGURATION:")
    prediction_config.print_multi_year_stats_status()
    
    # Show how to disable
    print("\n6️⃣  DISABLING 3-YEAR MODE (back to default):")
    print("-" * 70)
    prediction_config.disable_three_year_stats()
    prediction_config.print_multi_year_stats_status()
    
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    
    print("\n📝 USAGE IN YOUR CODE:")
    print("-" * 70)
    print("""
# Enable 3-year stats mode
prediction_config.enable_three_year_stats()

# Set minimum years required (1, 2, or 3)
prediction_config.set_min_years_required(2)  # Recommended: 2 out of 3

# Check current status
prediction_config.print_multi_year_stats_status()

# Disable (back to 2-year mode)
prediction_config.disable_three_year_stats()

# Now run your betting analysis script as normal
# python3 betting_analysis_script.py
""")
    
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 70)
    print("""
1. START with 2-year mode (default) to compare performance
2. ENABLE 3-year mode if you want more historical depth
3. SET min_years_required=2 (balanced - requires 2 out of 3 years)
4. MONITOR results to see if 2023 data helps or hurts predictions
5. DISABLE if 2023 data is too outdated for current players

PROS of 3-year mode:
  ✅ Better sample sizes for players with limited recent matches
  ✅ More stable statistics across seasons
  ✅ Catches long-term trends

CONS of 3-year mode:
  ❌ 2023 data may be outdated (2 years old)
  ❌ Doesn't reflect recent improvements/declines as quickly
  ❌ Slightly slower (fetches 3 years instead of 2)
""")

if __name__ == "__main__":
    main()

