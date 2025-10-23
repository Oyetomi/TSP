#!/usr/bin/env python3
"""
Verify if Tatjana Maria's "Sets Won vs Higher Ranked: 0" is correct
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.player_analysis_service import PlayerAnalysisService

def verify_tatjana_maria():
    """Verify Tatjana Maria's sets vs higher ranked calculation"""
    
    print("🎾 VERIFYING TATJANA MARIA'S SETS VS HIGHER RANKED")
    print("=" * 70)
    
    player_service = PlayerAnalysisService()
    
    # From the logs, we know Tatjana Maria is WTA #43
    # Her opponent Linda Noskova is WTA #23
    # So we need to check sets won vs players ranked 1-22 (higher than #23)
    
    # First, let's find Tatjana Maria's player ID by searching recent tournament data
    # Let's try to get her ID from MatchDataProvider by searching the match info
    
    print("🔍 Searching for Tatjana Maria in match data...")
    
    # From CSV, we can see the match ID is 14427814
    match_id = 14427814
    opponent_ranking = 23  # Linda Noskova's ranking
    
    # Let's search some common German player IDs or use a different approach
    # Let's try to get the match details first
    
    print(f"📊 Analyzing match {match_id}...")
    
    # We need to find Tatjana Maria's player ID
    # Let's try some educated guesses based on German WTA players
    potential_ids = [
        88998,   # Common pattern
        122345,  # Another pattern  
        89134,   # Try another
        104521,  # And another
    ]
    
    # Actually, let's use a more direct approach - search player names
    # Since we can't easily search by name, let's use the info from logs
    # Tatjana Maria: WTA #43, Age 38, Germany
    
    print(f"🏆 Opponent ranking: #{opponent_ranking} (Linda Noskova)")
    print(f"🎯 Looking for sets won vs players ranked 1-{opponent_ranking-1}")
    print()
    
    # Let's manually analyze with a known Tatjana Maria ID if we can find it
    # From WTA data, Tatjana Maria's common IDs...
    
    # Let's try to deduce from the MatchDataProvider match data
    try:
        print("🔍 Let's try to find Tatjana Maria's ID from recent matches...")
        
        # Since we know from logs she has 10 recent matches analyzed,
        # and she's ranked #43 WTA, let's try some common ID patterns
        
        # German WTA players often have IDs in certain ranges
        test_ids = [
            88998,  # Try this ID (common for German players)
            104521, # Another German pattern
            67890,  # Different range
            156789, # Another range
        ]
        
        for test_id in test_ids:
            try:
                print(f"\n📋 Testing ID {test_id}...")
                
                # Get player details to check name/country
                details = player_service.get_player_details(test_id)
                if details and 'team' in details:
                    name = details['team'].get('name', '')
                    country = details['team'].get('country', {}).get('name', '')
                    
                    print(f"   Name: {name}")
                    print(f"   Country: {country}")
                    
                    if 'Maria' in name and 'German' in country:
                        print(f"   🎯 FOUND POTENTIAL MATCH!")
                        
                        # Test the sets vs higher ranked calculation
                        form_result = player_service.analyze_recent_form(test_id, 10, opponent_ranking)
                        form_data = form_result.get('form_data', {})
                        sets_vs_higher = form_data.get('sets_vs_higher_ranked', 0)
                        
                        print(f"   📊 Sets vs higher ranked: {sets_vs_higher}")
                        
                        # Show some recent matches for verification
                        recent_matches = form_data.get('recent_matches', [])
                        print(f"\n   🔍 Recent matches analysis:")
                        manual_count = 0
                        
                        for i, match in enumerate(recent_matches[:10]):
                            opp_name = match.get('opponent_name', 'Unknown')
                            opp_rank = match.get('opponent_ranking', 'N/A')
                            player_sets = match.get('player_sets', 0)
                            
                            if isinstance(opp_rank, int) and opp_rank < opponent_ranking:
                                manual_count += player_sets
                                status = f"✅ +{player_sets} sets (HIGHER than #{opponent_ranking})"
                            elif isinstance(opp_rank, int):
                                status = f"❌ rank #{opp_rank} >= #{opponent_ranking}"
                            else:
                                status = f"⚠️ no rank data"
                                
                            print(f"   {i+1:2d}. vs {opp_name:<25} (#{opp_rank:<3}) - {player_sets} sets {status}")
                        
                        print(f"\n   🧮 Manual verification:")
                        print(f"      Expected count: {manual_count}")
                        print(f"      API result: {sets_vs_higher}")
                        
                        if manual_count == sets_vs_higher:
                            print(f"   ✅ CALCULATION IS CORRECT!")
                        else:
                            print(f"   ❌ MISMATCH DETECTED!")
                        
                        break
                        
            except Exception as e:
                print(f"   ❌ Error testing ID {test_id}: {e}")
                continue
        else:
            print(f"\n❌ Could not find Tatjana Maria's player ID")
            print(f"💡 Suggestion: Check the MatchDataProvider match page for player IDs")
            
    except Exception as e:
        print(f"❌ Error in verification: {e}")

if __name__ == "__main__":
    verify_tatjana_maria()
