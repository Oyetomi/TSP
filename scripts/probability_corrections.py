#!/usr/bin/env python3

def analyze_correct_probabilities():
    """Analyze what the ACTUAL probabilities should have been"""
    
    print("🎯 CORRECT PROBABILITY ANALYSIS")
    print("="*60)
    print("Current system vs. what probabilities SHOULD have been")
    
    losses = [
        {
            "player": "Jazmin Ortenzi",
            "predicted": "76.3%",
            "clay_rate": "0% (0/1)",
            "tiebreak_rate": "0% (0/1)", 
            "sample_issues": "Extreme: 1 clay match, 1 tiebreak",
            "should_be": "~20-25%"
        },
        {
            "player": "Egor Gerasimov", 
            "predicted": "84.3%",
            "clay_rate": "42.1% (8/19)",
            "tiebreak_rate": "0% (0/4)",
            "sample_issues": "Mental fragility: 0% pressure performance",
            "should_be": "~35-40%"
        },
        {
            "player": "James Trotter",
            "predicted": "84.5%", 
            "clay_rate": "50% (2/4)",
            "tiebreak_rate": "50% (1/2)",
            "sample_issues": "Tiny samples: 4 clay, 2 tiebreaks",
            "should_be": "~50-55%"
        },
        {
            "player": "Mathys Erhard",
            "predicted": "84.7%",
            "clay_rate": "45.8% (11/24)", 
            "tiebreak_rate": "70% (7/10)",
            "sample_issues": "Good mental, but below-average surface",
            "should_be": "~60-65%"
        }
    ]
    
    print(f"\n📊 PROBABILITY CORRECTIONS NEEDED:")
    print("-" * 60)
    
    for loss in losses:
        print(f"\n🎾 {loss['player']}:")
        print(f"   ❌ Predicted: {loss['predicted']} (WRONG)")
        print(f"   🏟️ Clay: {loss['clay_rate']}")
        print(f"   🏆 Tiebreak: {loss['tiebreak_rate']}")
        print(f"   ⚠️ Issues: {loss['sample_issues']}")
        print(f"   ✅ Should be: {loss['should_be']} chance to win")
        
        # Calculate the error magnitude
        predicted_val = float(loss['predicted'].replace('%', ''))
        should_be_max = float(loss['should_be'].split('-')[1].replace('%', ''))
        error = predicted_val - should_be_max
        print(f"   🚨 ERROR: Overestimated by {error:.1f} percentage points!")
    
    print(f"\n💡 REQUIRED ALGORITHM CHANGES:")
    print("="*60)
    
    print(f"\n1. **SURFACE PERFORMANCE PENALTIES**")
    print(f"   • <30% surface rate → Max 30% win probability")
    print(f"   • 30-40% surface rate → Max 50% win probability") 
    print(f"   • 40-45% surface rate → Max 65% win probability")
    print(f"   • Only >50% surface rate can exceed 70% probability")
    
    print(f"\n2. **MENTAL TOUGHNESS PENALTIES**")
    print(f"   • 0% tiebreak rate → -30 percentage points penalty")
    print(f"   • <25% tiebreak rate → -20 percentage points penalty")
    print(f"   • 25-40% tiebreak rate → -10 percentage points penalty")
    
    print(f"\n3. **SAMPLE SIZE PENALTIES**") 
    print(f"   • <3 surface matches → Max 40% probability")
    print(f"   • <5 surface matches → Max 60% probability")
    print(f"   • <2 tiebreaks → Additional -15 percentage points")
    
    print(f"\n4. **COMPOUND PENALTIES**")
    print(f"   • Multiple red flags → Multiplicative penalties")
    print(f"   • Jazmin: Poor surface + Mental fragility + Tiny sample = ~20%")
    print(f"   • Egor: Poor surface + Mental fragility = ~35%")
    
    print(f"\n🎯 IMPLEMENTATION PRIORITY:")
    print(f"   1. Fix the PREDICTION ALGORITHM (not just confidence)")
    print(f"   2. Apply penalties to actual win probabilities")
    print(f"   3. Never exceed 75% for players with data quality issues")
    print(f"   4. Cap probabilities based on actual performance metrics")

if __name__ == "__main__":
    analyze_correct_probabilities()
