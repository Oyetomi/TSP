#!/usr/bin/env python3
"""
Add Contrarian Crowd Weight Configuration
Uses original balanced weights + contrarian crowd sentiment
"""

from weight_config_manager import config_manager

def main():
    """Add contrarian crowd weight configuration"""
    
    print("🎯 ADDING CONTRARIAN CROWD WEIGHT CONFIGURATION")
    print("📊 Original balanced weights + contrarian crowd sentiment")
    print("=" * 60)
    
    # Your specified weights + contrarian crowd factor
    contrarian_weights = {
        'set_performance': 0.32,      # Reduced from 35% to make room for crowd
        'recent_form': 0.23,          # Reduced from 25% to make room for crowd  
        'momentum': 0.12,             # Reduced from 13% to make room for crowd
        'surface_performance': 0.11,  # Reduced from 12% to make room for crowd
        'contrarian_crowd': 0.10,     # NEW: 10% for contrarian crowd sentiment
        'clutch_factor': 0.08,        # Keep same
        'physical_factors': 0.04,     # Keep same
        'ranking_advantage': 0.03     # Keep same
    }
    
    print("📊 NEW WEIGHT BREAKDOWN:")
    for factor, weight in contrarian_weights.items():
        print(f"   {factor}: {weight:.1%}")
    
    # Add the configuration
    config_manager.add_config(
        "CONTRARIAN_CROWD_V1",
        "Contrarian Crowd Configuration",
        "Original balanced weights + contrarian crowd sentiment (bet opposite of public)",
        contrarian_weights
    )
    
    # Set it as active
    config_manager.set_active_config("CONTRARIAN_CROWD_V1")
    
    print(f"\n✅ Added CONTRARIAN_CROWD_V1 configuration")
    print(f"🎯 Set as active configuration")
    print(f"💡 System will now bet AGAINST crowd consensus!")
    print(f"📊 When crowd favors Player A, we'll favor Player B for +1.5 sets")

if __name__ == "__main__":
    main()
