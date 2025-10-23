#!/usr/bin/env python3
"""Create new UTR-focused configuration with 15% ranking weight"""

from weight_config_manager import config_manager

def create_utr_15_config():
    """Create UTR-focused configuration with 15% ranking weight"""
    
    # New weights with 15% UTR weight
    new_weights = {
        "set_performance": 0.25,        # Reduced from 30% to 25% (-5%)
        "recent_form": 0.20,            # Reduced from 22% to 20% (-2%)
        "ranking_advantage": 0.15,      # INCREASED from 8% to 15% (+7%)
        "momentum": 0.12,               # Same (12%)
        "surface_performance": 0.12,    # Same (12%)
        "clutch_factor": 0.09,          # Same (9%)
        "physical_factors": 0.05,       # Same (5%)
        "return_of_serve": 0.02         # Same (2%)
    }
    
    # Verify weights sum to 1.0
    total = sum(new_weights.values())
    print(f"📊 Total weights: {total:.3f}")
    
    if abs(total - 1.0) > 0.001:
        print(f"❌ Error: Weights don't sum to 1.0!")
        return False
    
    # Features to enable
    features = {
        "tiebreak_performance": False,
        "pressure_performance": False,
        "serve_dominance": False,
        "enhanced_year_blending": True,
        "crowd_sentiment": True,
        "dual_weighted_form": True
    }
    
    # Add the new configuration
    success = config_manager.add_config(
        code_name="UTR_FOCUSED_V1",
        name="UTR-Focused Configuration",
        description="15% weight on UTR/ranking advantage for better skill-based predictions. Prioritizes UTR over ATP/WTA when available.",
        weights=new_weights,
        features=features
    )
    
    if success:
        # Set as active configuration
        config_manager.set_active_config("UTR_FOCUSED_V1")
        print(f"\n✅ UTR-FOCUSED CONFIGURATION CREATED AND ACTIVATED!")
        print(f"\n📊 NEW WEIGHT BREAKDOWN:")
        for factor, weight in new_weights.items():
            print(f"   {factor}: {weight:.1%}")
        
        print(f"\n🎯 KEY CHANGES:")
        print(f"   • UTR/Ranking: 8% → 15% (+7%)")
        print(f"   • Set Performance: 30% → 25% (-5%)")
        print(f"   • Recent Form: 22% → 20% (-2%)")
        print(f"   • UTR priority: Skill level > tournament ranking")
        
        return True
    
    return False

if __name__ == "__main__":
    print("🎾 CREATING UTR-FOCUSED CONFIGURATION")
    print("="*50)
    success = create_utr_15_config()
    
    if success:
        print(f"\n🚀 SUCCESS! System now uses 15% UTR weight")
        print(f"🎯 UTR will be prioritized over ATP/WTA rankings")
        print(f"📈 Better predictions through skill-based analysis")
    else:
        print(f"\n❌ Failed to create configuration")
