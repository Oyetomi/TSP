#!/usr/bin/env python3

import math

def calculate_sample_confidence(matches, wins):
    """Calculate statistical confidence for win rate based on sample size"""
    if matches == 0:
        return 0.0, 0.0, 0.0
    
    win_rate = wins / matches
    
    # Wilson Score Interval for confidence (more accurate than normal approximation)
    z = 1.96  # 95% confidence interval
    n = matches
    p = win_rate
    
    denominator = 1 + z**2/n
    centre_adjusted = p + z**2/(2*n)
    adjustment = z * math.sqrt((p*(1-p) + z**2/(4*n))/n)
    
    lower_bound = (centre_adjusted - adjustment) / denominator
    upper_bound = (centre_adjusted + adjustment) / denominator
    
    # Confidence score: How tight is the interval?
    confidence_width = upper_bound - lower_bound
    confidence_score = max(0, 1 - confidence_width)  # Tighter interval = higher confidence
    
    return win_rate, confidence_score, confidence_width

def suggest_surface_adjustments():
    """Suggest how to handle sample size mismatches"""
    
    print("🎾 SURFACE SAMPLE SIZE ANALYSIS")
    print("=" * 50)
    
    # Our examples
    tommaso_matches, tommaso_wins = 10, 5
    filip_matches, filip_wins = 35, 17
    
    print(f"\n📊 Tommaso: {tommaso_matches} matches, {tommaso_wins} wins")
    tom_rate, tom_conf, tom_width = calculate_sample_confidence(tommaso_matches, tommaso_wins)
    print(f"   Win Rate: {tom_rate:.1%}")
    print(f"   Confidence Score: {tom_conf:.3f}")
    print(f"   95% CI Width: ±{tom_width/2:.1%}")
    
    print(f"\n📊 Filip: {filip_matches} matches, {filip_wins} wins")
    filip_rate, filip_conf, filip_width = calculate_sample_confidence(filip_matches, filip_wins)
    print(f"   Win Rate: {filip_rate:.1%}")
    print(f"   Confidence Score: {filip_conf:.3f}")
    print(f"   95% CI Width: ±{filip_width/2:.1%}")
    
    print(f"\n🔍 RELIABILITY COMPARISON:")
    print(f"   Filip is {filip_conf/tom_conf:.1f}x more reliable")
    print(f"   Tommaso's range: {tom_rate-tom_width/2:.1%} to {tom_rate+tom_width/2:.1%}")
    print(f"   Filip's range: {filip_rate-filip_width/2:.1%} to {filip_rate+filip_width/2:.1%}")
    
    # Suggestions for improvement
    print(f"\n💡 SUGGESTED IMPROVEMENTS:")
    print(f"1. **Confidence-Weighted Surface Calculation**:")
    print(f"   - Use confidence score to adjust surface vs overall blending")
    print(f"   - Lower confidence = more regression to overall performance")
    
    print(f"\n2. **Tiered Confidence System**:")
    print(f"   - <5 matches: Heavy regression to overall (confidence penalty)")
    print(f"   - 5-15 matches: Moderate regression (current system)")
    print(f"   - 15-30 matches: Light regression")
    print(f"   - 30+ matches: Full surface rate (high confidence)")
    
    print(f"\n3. **Prediction Confidence Adjustment**:")
    print(f"   - Lower overall prediction confidence when key players have small samples")
    print(f"   - Flag matches where sample size mismatch is large")
    
    print(f"\n4. **Mental Toughness Integration**:")
    print(f"   - Tommaso: 0% tiebreak rate (0/1) = EXTREMELY unreliable")
    print(f"   - Should heavily penalize small tiebreak samples")

if __name__ == "__main__":
    suggest_surface_adjustments()
