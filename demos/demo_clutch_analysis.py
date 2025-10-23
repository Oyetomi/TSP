"""
Demo script showcasing clutch performance analysis.

This demonstrates how the system now properly evaluates:
1. Sets won even in losing matches (clutch performance)
2. Quality of opposition based on ranking comparisons
3. Context-aware form analysis
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def demonstrate_clutch_analysis():
    """Demonstrate the clutch performance and quality opposition analysis."""
    
    print("🎾 CLUTCH PERFORMANCE ANALYSIS DEMO")
    print("=" * 70)
    print("💪 Analyzing sets won in losses and quality of opposition")
    print("🎯 Context-aware form evaluation for set prediction\n")
    
    # Players to analyze
    players = [
        {"name": "Stefanos Tsitsipas", "id": 122366, "rank": 28},
        {"name": "Yunchaokete Bu", "id": 254227, "rank": 76}
    ]
    
    print("COMPREHENSIVE FORM ANALYSIS COMPARISON")
    print("-" * 70)
    
    for i, player in enumerate(players, 1):
        opponent = players[1] if i == 1 else players[0]
        
        print(f"\n🔍 Player {i}: {player['name']} (ATP #{player['rank']})")
        print(f"📊 Analysis context: vs ATP #{opponent['rank']} opponent")
        
        try:
            # Get enhanced form analysis with opponent context
            form_response = requests.get(
                f"{BASE_URL}/match-analysis/player/{player['id']}/recent-form"
                f"?num_matches=8&opponent_ranking={opponent['rank']}"
            )
            
            if form_response.status_code != 200:
                print(f"   ❌ Error fetching form data: {form_response.status_code}")
                continue
                
            form_data = form_response.json().get('form_data', {})
            
            print(f"   📈 Form Quality Score: {form_data.get('form_quality_score', 0):.1f}/100")
            print(f"   🏆 Match Record: {form_data.get('matches_won', 0)}W-{form_data.get('matches_lost', 0)}L")
            print(f"   🎾 Set Record: {form_data.get('total_sets_won', 0)}W-{form_data.get('total_sets_lost', 0)}L")
            print(f"   📊 Set Win Rate: {form_data.get('set_win_rate', 0):.1%}")
            
            # Quality indicators
            higher_sets = form_data.get('sets_vs_higher_ranked', 0)
            lower_sets = form_data.get('sets_vs_lower_ranked', 0)
            clutch_sets = form_data.get('clutch_sets', 0)
            clutch_rate = form_data.get('clutch_rate', 0)
            dominant_wins = form_data.get('dominant_wins', 0)
            
            print(f"\n   🎯 Quality Metrics:")
            print(f"      Sets vs higher-ranked: {higher_sets}")
            print(f"      Sets vs lower-ranked: {lower_sets}")
            print(f"      💪 Clutch sets (in losses): {clutch_sets}")
            print(f"      🎪 Clutch rate: {clutch_rate:.1%}")
            print(f"      🔥 Dominant wins: {dominant_wins}")
            
            # Show recent match analysis
            recent_matches = form_data.get('recent_matches', [])
            if recent_matches:
                print(f"\n   📋 Recent Match Details:")
                
                for j, match in enumerate(recent_matches[:3], 1):
                    opp_name = match.get('opponent_name', 'Unknown')[:20]
                    opp_rank = match.get('opponent_ranking')
                    match_result = "W" if match.get('match_won') else "L"
                    sets_score = f"{match.get('player_sets')}-{match.get('opponent_sets')}"
                    
                    print(f"      {j}. vs {opp_name} (#{opp_rank or 'NR'}): {match_result} {sets_score}")
                    
                    # Highlight clutch performance
                    if not match.get('match_won') and match.get('player_sets', 0) > 0:
                        print(f"         💪 CLUTCH: Won {match.get('player_sets')} set(s) in losing effort!")
                    
                    # Highlight quality opposition
                    if opp_rank and opponent['rank']:
                        if opp_rank < opponent['rank']:
                            diff = opponent['rank'] - opp_rank
                            print(f"         🎯 QUALITY: Faced opponent {diff} spots higher than current opponent")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("🧮 ENHANCED PREDICTION ANALYSIS")
    print("=" * 70)
    
    try:
        # Get the enhanced comparison
        comparison = requests.get(f"{BASE_URL}/match-analysis/compare/{players[0]['id']}/{players[1]['id']}")
        
        if comparison.status_code == 200:
            factors = comparison.json().get('prediction_factors', {})
            
            print("🎯 SOPHISTICATED PREDICTION FACTORS:")
            print(f"   🏆 Ranking advantage: {factors.get('ranking_advantage', 'N/A')}")
            print(f"   📈 Form advantage: {factors.get('form_advantage', 'N/A')}")
            print(f"   🎾 Set performance advantage: {factors.get('set_performance_advantage', 'N/A')}")
            print(f"   💪 Clutch performance advantage: {factors.get('clutch_advantage', 'N/A')}")
            print(f"   🎯 Quality opposition advantage: {factors.get('quality_opposition_advantage', 'N/A')}")
            
            print(f"\n📊 WEIGHTED SCORING:")
            print(f"   {players[0]['name']}: {factors.get('player1_total_score', 0)} points")
            print(f"   {players[1]['name']}: {factors.get('player2_total_score', 0)} points")
            
            print(f"\n🏅 FINAL ASSESSMENT:")
            recommendation = factors.get('overall_recommendation', 'N/A')
            confidence = factors.get('confidence_level', 'N/A')
            print(f"   Recommendation: {recommendation}")
            print(f"   Confidence: {confidence}")
            
            print(f"\n💡 KEY INSIGHTS:")
            for insight in factors.get('key_insights', []):
                print(f"   • {insight}")
                
        else:
            print("   ❌ Error fetching comparison data")
            
    except Exception as e:
        print(f"   ❌ Error in comparison: {e}")
    
    print("\n" + "=" * 70)
    print("✅ CLUTCH ANALYSIS DEMONSTRATION COMPLETE!")
    print("=" * 70)
    print("🎾 WHAT THIS ANALYSIS NOW CAPTURES:")
    print("   1. ✅ Sets won in losing matches (clutch performance)")
    print("   2. ✅ Opposition quality vs current opponent ranking")
    print("   3. ✅ Form quality scoring with weighted factors")
    print("   4. ✅ Individual match context and set breakdowns")
    print("   5. ✅ Multi-dimensional prediction with confidence")
    print("\n💪 CLUTCH FACTOR: A player who consistently wins sets")
    print("   against higher-ranked opponents (even in losses) shows")
    print("   much better form than simple win/loss records suggest!")
    print("\n🎯 QUALITY CONTEXT: Performance vs ATP #50 opponent is")
    print("   much more impressive than vs ATP #150 opponent!")

if __name__ == "__main__":
    try:
        demonstrate_clutch_analysis()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Ensure FastAPI server is running: python run_server.py")
