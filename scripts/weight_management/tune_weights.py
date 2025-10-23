#!/usr/bin/env python3
"""
Systematic Weight Tuning
Create and test different weight configurations to improve accuracy
"""

import sys
import os
from weight_config_manager import config_manager

def create_test_configurations():
    """Create different weight configurations to test"""
    
    # Configuration 1: Conservative (favor shorter matches)
    config_manager.add_config(
        "CONSERVATIVE_V1",
        "Conservative Configuration",
        "More conservative about predicting 3+ sets",
        {
            "ranking_advantage": 0.40,  # High ranking weight - rank difference often predicts dominance
            "recent_form": 0.30,        # Strong form advantage = dominance
            "surface_performance": 0.15, # Surface matters but less
            "set_performance": 0.10,    # Reduce set performance weight
            "clutch_factor": 0.05,      # Minimal clutch
            "momentum": 0.00,           # Remove momentum  
            "physical_factors": 0.00    # Remove physical
        }
    )
    
    # Configuration 2: Ranking Dominant 
    config_manager.add_config(
        "RANKING_DOMINANT_V1",
        "Ranking Dominant Configuration", 
        "Heavy weight on ranking differences",
        {
            "ranking_advantage": 0.50,  # Very high ranking weight
            "set_performance": 0.25,    # Moderate set performance
            "recent_form": 0.15,        # Lower form weight
            "surface_performance": 0.10, # Lower surface weight
            "clutch_factor": 0.00,      # Remove clutch
            "momentum": 0.00,           # Remove momentum
            "physical_factors": 0.00    # Remove physical
        }
    )
    
    # Configuration 3: Form + Surface Heavy
    config_manager.add_config(
        "FORM_SURFACE_V1",
        "Form + Surface Configuration",
        "Focus on recent form and surface performance",
        {
            "recent_form": 0.40,        # High form weight
            "surface_performance": 0.30, # High surface weight  
            "ranking_advantage": 0.20,   # Moderate ranking
            "set_performance": 0.10,    # Low set performance
            "clutch_factor": 0.00,      # Remove clutch
            "momentum": 0.00,           # Remove momentum
            "physical_factors": 0.00    # Remove physical
        }
    )
    
    # Configuration 4: Minimal Factors
    config_manager.add_config(
        "MINIMAL_V1", 
        "Minimal Factors Configuration",
        "Only ranking and form - simplest approach",
        {
            "ranking_advantage": 0.60,  # Very high ranking
            "recent_form": 0.40,        # High form
            "surface_performance": 0.00, # Remove everything else
            "set_performance": 0.00,
            "clutch_factor": 0.00,
            "momentum": 0.00,
            "physical_factors": 0.00
        }
    )
    
    # Configuration 5: Anti-Clutch (opposite of current)
    config_manager.add_config(
        "ANTI_CLUTCH_V1",
        "Anti-Clutch Configuration", 
        "Remove clutch factor completely - favor dominance",
        {
            "set_performance": 0.40,    # Higher set performance
            "ranking_advantage": 0.25,  # Moderate ranking
            "recent_form": 0.20,        # Moderate form
            "surface_performance": 0.15, # Moderate surface
            "clutch_factor": 0.00,      # REMOVE clutch completely
            "momentum": 0.00,           # Remove momentum
            "physical_factors": 0.00    # Remove physical
        }
    )
    
    print("✅ Created 5 new test configurations")
    print("💡 These focus on predicting shorter matches (2-0, 2-1)")

def main():
    """Create test configurations for systematic tuning"""
    
    print("🎯 SYSTEMATIC WEIGHT TUNING")
    print("📊 Creating configurations to fix over-prediction of 3+ sets")
    print("=" * 60)
    
    create_test_configurations()
    
    # Set one as active for testing
    config_manager.set_active_config("CONSERVATIVE_V1")
    
    print(f"\n🎯 Set CONSERVATIVE_V1 as active for testing")
    print(f"💡 Run simple_backtest.py to test all configurations")

if __name__ == "__main__":
    main()
