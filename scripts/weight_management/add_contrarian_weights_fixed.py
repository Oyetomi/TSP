#!/usr/bin/env python3
"""
Add Contrarian Crowd Weight Configuration - Fixed
Uses original balanced weights + contrarian crowd sentiment (sums to 1.0)
"""

from weight_config_manager import config_manager

def main():
    """Add contrarian crowd weight configuration"""
    
    print("🎯 ADDING CONTRARIAN CROWD WEIGHT CONFIGURATION")
    print("📊 Original balanced weights + 10% contrarian crowd sentiment")
    print("=" * 60)
    
    # Your specified weights adjusted to make room for 10% crowd factor
    contrarian_weights = {
        'set_performance': 0.31,      # Reduced from 35% to 31% 
        'recent_form': 0.22,          # Reduced from 25% to 22%
        'momentum': 0.12,             # Reduced from 13% to 12%
        'surface_performance': 0.11,  # Reduced from 12% to 11%
        'contrarian_crowd': 0.10,     # NEW: 10% for contrarian crowd sentiment
        'clutch_factor': 0.07,        # Reduced from 8% to 7%
        'physical_factors': 0.04,     # Keep same
        'ranking_advantage': 0.03     # Keep same
    }
    
    # Verify sum
    total = sum(contrarian_weights.values())
    print(f"📊 Weight sum verification: {total:.3f}")
    
    print("📊 NEW WEIGHT BREAKDOWN:")
    for factor, weight in contrarian_weights.items():
        print(f"   {factor}: {weight:.1%}")
    
    # Add the configuration
    config_manager.add_config(
        "CONTRARIAN_CROWD_V1",
        "Contrarian Crowd Configuration",
        "Original balanced weights + 10% contrarian crowd sentiment (bet opposite of public)",
        contrarian_weights
    )
    
    # Set it as active
    config_manager.set_active_config("CONTRARIAN_CROWD_V1")
    
    print(f"\n✅ Added CONTRARIAN_CROWD_V1 configuration")
    print(f"🎯 Set as active configuration")
    print(f"💡 System will now bet AGAINST crowd consensus!")
    print(f"📊 When crowd favors Player A by 70%+, we'll boost Player B's +1.5 sets odds")
    print(f"🔄 This is a contrarian strategy - betting against the public")

if __name__ == "__main__":
    main()
