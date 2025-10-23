#!/usr/bin/env python3
"""
Add Set Win Rate Heavy Configuration
Heavy weight on recent set win rate as the deciding factor
"""

from weight_config_manager import config_manager

def main():
    """Add Set Win Rate Heavy configuration"""
    
    print("🎯 ADDING SET WIN RATE HEAVY CONFIGURATION")
    print("📊 Making Recent Set Win Rate the deciding factor")
    print("=" * 50)
    
    # Configuration that heavily weights recent set win rate
    config_manager.add_config(
        "SET_WIN_RATE_HEAVY",
        "Set Win Rate Heavy",
        "Heavy weight on recent set win rate as deciding factor",
        {
            "recent_form": 0.60,        # 60% - MAIN DECIDING FACTOR
            "set_performance": 0.20,    # 20% - Secondary factor  
            "ranking_advantage": 0.10,   # 10% - Minimal ranking
            "surface_performance": 0.10, # 10% - Minimal surface
            "clutch_factor": 0.00,      # Remove clutch
            "momentum": 0.00,           # Remove momentum
            "physical_factors": 0.00    # Remove physical
        }
    )
    
    # Also create an even more extreme version
    config_manager.add_config(
        "SET_WIN_RATE_DOMINANT",
        "Set Win Rate Dominant", 
        "80% weight on recent set win rate - extreme version",
        {
            "recent_form": 0.80,        # 80% - DOMINANT FACTOR
            "set_performance": 0.15,    # 15% - Small secondary
            "ranking_advantage": 0.05,   # 5% - Tiny ranking influence
            "surface_performance": 0.00, # Remove surface
            "clutch_factor": 0.00,      # Remove clutch
            "momentum": 0.00,           # Remove momentum
            "physical_factors": 0.00    # Remove physical
        }
    )
    
    # Set the heavy one as active
    config_manager.set_active_config("SET_WIN_RATE_HEAVY")
    
    print("✅ Added SET_WIN_RATE_HEAVY (60% recent form)")
    print("✅ Added SET_WIN_RATE_DOMINANT (80% recent form)")
    print("🎯 Set SET_WIN_RATE_HEAVY as active")
    print("💡 Recent Set Win Rate is now the deciding factor!")

if __name__ == "__main__":
    main()
