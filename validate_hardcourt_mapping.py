#!/usr/bin/env python3
"""
Validate hardcourt surface mapping works correctly

Tests that "Hardcourt outdoor", "Hardcourt indoor" etc. map correctly to "Hard"
"""

from curl_cffi import requests as curl_requests
import json
from enhanced_statistics_handler import EnhancedStatisticsHandler
from app.services.player_analysis_service import PlayerAnalysisService

def test_hardcourt_surface_mapping():
    """Test hardcourt surface mapping for various players"""
    
    print("🧪 VALIDATING HARDCOURT SURFACE MAPPING")
    print("=" * 60)
    
    # Test with Simona Waltert (we know she has "Hardcourt outdoor" data)
    player_id = 215166
    
    print(f"\n1️⃣ TESTING WITH SIMONA WALTERT (ID: {player_id})")
    print("-" * 50)
    
    # Get raw API data first
    session = curl_requests.Session()
    url = f"https://www.matchdata-api.example.com/api/v1/team/{player_id}/year-statistics/2025"
    
    try:
        response = session.get(url, impersonate="chrome110")
        if response.status_code == 200:
            raw_data = response.json()
            
            print("📊 RAW MATCH_DATA HARDCOURT DATA:")
            hardcourt_surfaces = []
            for surface_stats in raw_data['statistics']:
                surface = surface_stats['groundType']
                if 'hard' in surface.lower():
                    matches = surface_stats['matches']
                    wins = surface_stats['wins']
                    win_rate = (wins / matches * 100) if matches > 0 else 0
                    hardcourt_surfaces.append(surface)
                    print(f"   🎾 {surface}: {wins}/{matches} ({win_rate:.1f}%)")
            
            if not hardcourt_surfaces:
                print("   ⚠️ No hardcourt data found for this player")
                return
            
        else:
            print(f"❌ API call failed: {response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ Error fetching raw data: {e}")
        return
    
    # Test enhanced statistics handler with different hardcourt requests
    player_service = PlayerAnalysisService()
    stats_handler = EnhancedStatisticsHandler(player_service)
    
    # Test various hardcourt surface requests
    test_surfaces = [
        "Hard",
        "Hardcourt",
        "Hardcourt outdoor", 
        "Hardcourt indoor"
    ]
    
    print(f"\n📈 ENHANCED STATISTICS HANDLER TESTS:")
    print("-" * 50)
    
    results = {}
    for test_surface in test_surfaces:
        print(f"\n🔍 Testing request for: '{test_surface}'")
        try:
            enhanced_stats = stats_handler.get_enhanced_player_statistics(player_id, test_surface)
            
            if enhanced_stats.get('statistics') and enhanced_stats['statistics'].get('matches', 0) > 0:
                stats = enhanced_stats['statistics']
                matches = stats.get('matches', 0)
                wins = stats.get('wins', 0)
                win_rate = (wins / matches * 100) if matches > 0 else 0
                ground_type = stats.get('groundType', 'Unknown')
                
                print(f"   ✅ SUCCESS: Found {matches:.1f} matches")
                print(f"   📊 Win Rate: {win_rate:.1f}%")
                print(f"   🎾 Mapped to: '{ground_type}'")
                
                results[test_surface] = {
                    'matches': matches,
                    'wins': wins,
                    'win_rate': win_rate,
                    'mapped_to': ground_type,
                    'success': True
                }
            else:
                print(f"   ❌ FAILED: No data found")
                results[test_surface] = {'success': False}
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results[test_surface] = {'success': False, 'error': str(e)}
    
    # Analyze results
    print(f"\n🎯 MAPPING ANALYSIS:")
    print("-" * 50)
    
    successful_requests = [surface for surface, result in results.items() if result.get('success')]
    failed_requests = [surface for surface, result in results.items() if not result.get('success')]
    
    if successful_requests:
        print("✅ SUCCESSFUL MAPPINGS:")
        for surface in successful_requests:
            result = results[surface]
            print(f"   '{surface}' → '{result['mapped_to']}' ({result['matches']:.1f} matches)")
        
        # Check consistency
        match_counts = [results[surface]['matches'] for surface in successful_requests]
        if len(set(match_counts)) == 1:
            print(f"\n✅ CONSISTENCY CHECK: All successful requests return same data ({match_counts[0]:.1f} matches)")
        else:
            print(f"\n⚠️ INCONSISTENCY: Different match counts returned: {match_counts}")
    
    if failed_requests:
        print(f"\n❌ FAILED MAPPINGS:")
        for surface in failed_requests:
            print(f"   '{surface}' → No data found")
    
    # Test normalization logic directly
    print(f"\n🧪 DIRECT NORMALIZATION TESTS:")
    print("-" * 50)
    
    test_inputs = [
        "Hard",
        "Hardcourt",
        "Hardcourt outdoor",
        "Hardcourt indoor", 
        "hard court",
        "Hard Court",
        "HARDCOURT OUTDOOR"
    ]
    
    for test_input in test_inputs:
        normalized = stats_handler._normalize_surface_name(test_input)
        print(f"   '{test_input}' → '{normalized}'")
    
    return results

def test_additional_players():
    """Test hardcourt mapping with additional players"""
    
    print(f"\n2️⃣ TESTING WITH ADDITIONAL PLAYERS")
    print("-" * 50)
    
    # Test with some other player IDs that likely have hardcourt data
    test_players = [
        {"id": 122366, "name": "Stefanos Tsitsipas"},  # From demo script
        {"id": 254227, "name": "Yunchaokete Bu"}       # From demo script
    ]
    
    player_service = PlayerAnalysisService()
    stats_handler = EnhancedStatisticsHandler(player_service)
    
    for player in test_players:
        print(f"\n🎾 Testing {player['name']} (ID: {player['id']}):")
        
        try:
            # Test with "Hard" request
            enhanced_stats = stats_handler.get_enhanced_player_statistics(player['id'], "Hard")
            
            if enhanced_stats.get('statistics') and enhanced_stats['statistics'].get('matches', 0) > 0:
                stats = enhanced_stats['statistics']
                matches = stats.get('matches', 0)
                wins = stats.get('wins', 0)
                win_rate = (wins / matches * 100) if matches > 0 else 0
                
                print(f"   ✅ Hard surface data: {wins:.1f}/{matches:.1f} ({win_rate:.1f}%)")
            else:
                print(f"   ⚠️ No hard surface data found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    # Test primary hardcourt mapping
    results = test_hardcourt_surface_mapping()
    
    # Test with additional players
    test_additional_players()
    
    print(f"\n🏆 HARDCOURT SURFACE MAPPING VALIDATION COMPLETE")
    print("=" * 60)
    
    if results:
        successful_count = len([r for r in results.values() if r.get('success')])
        total_count = len(results)
        
        print(f"📊 Results: {successful_count}/{total_count} surface requests successful")
        
        if successful_count == total_count:
            print("✅ ALL HARDCOURT MAPPINGS WORKING CORRECTLY!")
        elif successful_count > 0:
            print("⚠️ PARTIAL SUCCESS - Some mappings working")
        else:
            print("❌ HARDCOURT MAPPING ISSUES DETECTED")
    
    print("\n💡 The surface normalization fix should handle:")
    print("   • 'Hardcourt outdoor' → 'Hard'")
    print("   • 'Hardcourt indoor' → 'Hard'") 
    print("   • 'Hard' → 'Hard' (exact match)")
    print("   • Case insensitive matching")
