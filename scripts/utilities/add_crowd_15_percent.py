#!/usr/bin/env python3
"""
Add 15% Contrarian Crowd Weight Configuration
Your specified weights with 15% contrarian crowd sentiment
"""

from weight_config_manager import config_manager

def main():
    """Add 15% contrarian crowd weight configuration"""
    
    print("🎯 ADDING 15% CONTRARIAN CROWD WEIGHT CONFIGURATION")
    print("📊 Adjusting weights to give crowd 15% influence")
    print("=" * 60)
    
    # Your specified weights adjusted to make room for 15% crowd factor
    crowd_15_weights = {
        'set_performance': 0.30,      # Reduced from 35% to 30%
        'recent_form': 0.21,          # Reduced from 25% to 21%  
        'momentum': 0.11,             # Reduced from 13% to 11%
        'surface_performance': 0.10,  # Reduced from 12% to 10%
        'contrarian_crowd': 0.15,     # 15% for contrarian crowd sentiment
        'clutch_factor': 0.07,        # Reduced from 8% to 7%
        'physical_factors': 0.03,     # Reduced from 4% to 3%
        'ranking_advantage': 0.03     # Keep same
    }
    
    # Verify sum
    total = sum(crowd_15_weights.values())
    print(f"📊 Weight sum verification: {total:.3f}")
    
    print("📊 NEW WEIGHT BREAKDOWN:")
    for factor, weight in crowd_15_weights.items():
        print(f"   {factor}: {weight:.1%}")
    
    # Add the configuration
    config_manager.add_config(
        "CONTRARIAN_CROWD_15_V1",
        "15% Contrarian Crowd Configuration",
        "Balanced weights + 15% contrarian crowd sentiment (bet opposite of public)",
        crowd_15_weights
    )
    
    # Set it as active
    config_manager.set_active_config("CONTRARIAN_CROWD_15_V1")
    
    print(f"\n✅ Added CONTRARIAN_CROWD_15_V1 configuration")
    print(f"🎯 Set as active configuration")
    print(f"💡 System will now bet STRONGLY AGAINST crowd consensus!")
    print(f"📊 15% weight means crowd has MAJOR influence on predictions")
    print(f"🔄 When public heavily favors a player, we'll strongly boost their opponent")

if __name__ == "__main__":
    main()
