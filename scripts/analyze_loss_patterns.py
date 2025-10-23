#!/usr/bin/env python3
"""
Analyze the 4 recent losses by examining the prediction data itself
"""

import pandas as pd
import json

# The 4 recent losses to analyze
RECENT_LOSSES = [
    {
        "match": "Rebecca Marino vs Tatjana Maria",
        "bet_player": "Rebecca Marino", 
        "confidence": 66.2,
        "actual_sets": 0,
        "result": "0-2"
    },
    {
        "match": "Gauthier Onclin vs James McCabe",
        "bet_player": "James McCabe",
        "confidence": 82.8, 
        "actual_sets": 0,
        "result": "1-0 (James McCabe lost)"
    },
    {
        "match": "Carole Monnet vs Joanna Garland", 
        "bet_player": "Joanna Garland",
        "confidence": 85.0,
        "actual_sets": 0,
        "result": "2-0 (Joanna Garland lost)"
    },
    {
        "match": "Julia Grabher vs Carson Branstine",
        "bet_player": "Julia Grabher",
        "confidence": 67.1,
        "actual_sets": 0, 
        "result": "0-2"
    }
]

def analyze_prediction_data():
    """Analyze the prediction data for each loss"""
    try:
        # Skip comment lines that start with #
        df = pd.read_csv('tennis_predictions.csv', comment='#')
        
        print("🎾 ANALYZING PREDICTION DATA FOR 4 LOSSES")
        print("=" * 60)
        
        for i, loss in enumerate(RECENT_LOSSES, 1):
            print(f"🔥 LOSS #{i}: {loss['match']}")
            print("-" * 50)
            print(f"📋 Bet: {loss['bet_player']} ≥1 set ({loss['confidence']}% confidence)")
            print(f"📊 Result: {loss['result']} - Won {loss['actual_sets']} sets")
            print()
            
            bet_player = loss['bet_player']
            
            # Find this match in the CSV
            match_found = False
            for _, row in df.iterrows():
                if bet_player in row['player1_name'] or bet_player in row['player2_name']:
                    match_found = True
                    
                    print(f"🏟️  Tournament: {row['tournament']}")
                    print(f"🎾 Surface: {row['surface']}")
                    print()
                    
                    # Determine if bet player is P1 or P2
                    if bet_player == row['player1_name']:
                        bet_is_p1 = True
                        opponent = row['player2_name']
                    else:
                        bet_is_p1 = False
                        opponent = row['player1_name']
                    
                    print(f"👤 Bet Player ({bet_player}):")
                    if bet_is_p1:
                        print(f"   🏆 Ranking: #{row['player1_ranking']}")
                        print(f"   ⭐ UTR: {row['player1_utr_rating']}")
                        print(f"   📈 Form: {row['player1_form_score']:.1f}")
                        print(f"   🎯 Set Win Prob: {row['player1_set_probability'] * 100:.1f}%")
                    else:
                        print(f"   🏆 Ranking: #{row['player2_ranking']}")
                        print(f"   ⭐ UTR: {row['player2_utr_rating']}")
                        print(f"   📈 Form: {row['player2_form_score']:.1f}")
                        print(f"   🎯 Set Win Prob: {row['player2_set_probability'] * 100:.1f}%")
                    
                    print()
                    print(f"🆚 Opponent ({opponent}):")
                    if not bet_is_p1:
                        print(f"   🏆 Ranking: #{row['player1_ranking']}")
                        print(f"   ⭐ UTR: {row['player1_utr_rating']}")
                        print(f"   📈 Form: {row['player1_form_score']:.1f}")
                        print(f"   🎯 Set Win Prob: {row['player1_set_probability'] * 100:.1f}%")
                    else:
                        print(f"   🏆 Ranking: #{row['player2_ranking']}")
                        print(f"   ⭐ UTR: {row['player2_utr_rating']}")
                        print(f"   📈 Form: {row['player2_form_score']:.1f}")
                        print(f"   🎯 Set Win Prob: {row['player2_set_probability'] * 100:.1f}%")
                    
                    print()
                    
                    # Parse weight breakdown
                    try:
                        weight_data = eval(row['weight_breakdown'])
                        print("📊 PREDICTION BREAKDOWN:")
                        print("-" * 30)
                        
                        for key, value in weight_data.items():
                            if key == 'set_performance':
                                print(f"🎯 Set Performance: {value}")
                            elif key == 'utr':
                                print(f"⭐ UTR: {value}")
                            elif key == 'atp':
                                print(f"🏆 Ranking: {value}")
                            elif key == 'form':
                                print(f"📈 Form: {value}")
                            elif key == 'surface':
                                print(f"🎾 Surface: {value}")
                            elif key == 'mental_toughness':
                                print(f"🧠 Mental: {value}")
                            elif key == 'clutch':
                                print(f"🎯 Clutch: {value}")
                            elif key == 'return_serve':
                                print(f"🎾 Return: {value}")
                            elif key == 'resilience':
                                print(f"💪 Resilience: {value}")
                            elif key == 'momentum':
                                print(f"📈 Momentum: {value}")
                        
                    except Exception as e:
                        print(f"❌ Could not parse weight breakdown: {e}")
                    
                    print()
                    print("🔍 KEY FACTORS:")
                    print(f"   {row['key_factors']}")
                    print()
                    
                    # Analyze potential issues
                    print("⚠️ POTENTIAL ISSUES:")
                    issues = []
                    
                    # Check for low sample sizes in set performance
                    if 'quality:' in str(weight_data.get('set_performance', '')):
                        set_text = str(weight_data['set_performance'])
                        if 'quality: 33.3%' in set_text or 'quality: 25.0%' in set_text:
                            issues.append("🚨 LOW SAMPLE SIZE in set performance data")
                        if 'quality: 30.0%' in set_text:
                            issues.append("🚨 VERY LOW SAMPLE SIZE in set performance")
                    
                    # Check for surface issues
                    if 'surface' in weight_data:
                        surface_text = str(weight_data['surface'])
                        if 'confident_weak' in surface_text:
                            issues.append("🚨 WEAK SURFACE PERFORMANCE confidence")
                        if 'confident_minimal' in surface_text:
                            issues.append("🚨 MINIMAL SURFACE PERFORMANCE confidence")
                        if 'LOW_CONFIDENCE' in surface_text:
                            issues.append("🚨 LOW CONFIDENCE surface data")
                        if '(reduced weight)' in surface_text:
                            issues.append("⚠️ Surface data had reduced weight")
                    
                    # Check mental toughness disparity
                    if 'mental_toughness' in weight_data:
                        mental_text = str(weight_data['mental_toughness'])
                        if bet_is_p1:
                            # Extract P1 mental toughness percentage
                            try:
                                p1_mental = float(mental_text.split('P1: ')[1].split('%')[0])
                                p2_mental = float(mental_text.split('P2: ')[1].split('%')[0])
                                if p2_mental > p1_mental + 15:
                                    issues.append(f"🧠 MENTAL TOUGHNESS DISADVANTAGE: {p1_mental:.1f}% vs {p2_mental:.1f}%")
                            except:
                                pass
                        else:
                            try:
                                p1_mental = float(mental_text.split('P1: ')[1].split('%')[0])
                                p2_mental = float(mental_text.split('P2: ')[1].split('%')[0])
                                if p1_mental > p2_mental + 15:
                                    issues.append(f"🧠 MENTAL TOUGHNESS DISADVANTAGE: {p2_mental:.1f}% vs {p1_mental:.1f}%")
                            except:
                                pass
                    
                    # Check for red clay issues (based on known problems)
                    if row['surface'] == 'Red clay':
                        issues.append("🔴 RED CLAY MATCH - check for surface-specific data quality issues")
                    
                    if issues:
                        for issue in issues:
                            print(f"   {issue}")
                    else:
                        print("   ✅ No obvious data quality issues detected")
                    
                    break
            
            if not match_found:
                print(f"❌ Could not find prediction data for {bet_player}")
            
            print()
            print("=" * 60)
            print()
            
    except Exception as e:
        print(f"❌ Error analyzing prediction data: {e}")

if __name__ == "__main__":
    analyze_prediction_data()
