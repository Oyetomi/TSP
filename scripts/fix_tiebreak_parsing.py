#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from curl_cffi import requests
import json

def get_surface_specific_tiebreak_data(player_id, target_surface="Red clay"):
    """Get surface-specific tiebreak data using correct parsing"""
    try:
        url = f"https://www.matchdata-api.example.com/api/v1/team/{player_id}/year-statistics/2025"
        
        response = requests.get(
            url,
            headers={
                'accept': '*/*',
                'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'priority': 'u=1, i',
                'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'sec-gpc': '1',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
            },
            impersonate="chrome"
        )
        
        if response.status_code == 200:
            data = response.json()
            statistics = data.get('statistics', [])
            
            # Look for the specific surface
            for stat_group in statistics:
                if isinstance(stat_group, dict):
                    ground_type = stat_group.get('groundType', '')
                    
                    if ground_type == target_surface:
                        tb_won = stat_group.get('tiebreaksWon', 0)
                        tb_lost = stat_group.get('tiebreakLosses', 0)
                        tb_total = tb_won + tb_lost
                        matches = stat_group.get('matches', 0)
                        wins = stat_group.get('wins', 0)
                        
                        if tb_total > 0:
                            tb_rate = tb_won / tb_total
                            return {
                                'tiebreak_rate': tb_rate,
                                'tiebreaks_won': tb_won,
                                'tiebreaks_lost': tb_lost,
                                'total_tiebreaks': tb_total,
                                'surface_matches': matches,
                                'surface_wins': wins,
                                'surface_win_rate': wins / matches if matches > 0 else 0
                            }
                        else:
                            return {
                                'tiebreak_rate': None,
                                'tiebreaks_won': 0,
                                'tiebreaks_lost': 0,
                                'total_tiebreaks': 0,
                                'surface_matches': matches,
                                'surface_wins': wins,
                                'surface_win_rate': wins / matches if matches > 0 else 0,
                                'no_tiebreak_data': True
                            }
            
            # Surface not found
            return {'error': f'No data for {target_surface}'}
            
        else:
            return {'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        return {'error': str(e)}

def test_corrected_parsing():
    """Test the corrected tiebreak parsing on our losing players"""
    
    test_players = [
        (254281, "Jazmin Ortenzi"),
        (213076, "Mathys Erhard"), 
        (255993, "James Trotter"),
        (57021, "Egor Gerasimov")
    ]
    
    print("🔧 TESTING CORRECTED TIEBREAK PARSING")
    print("="*60)
    
    for player_id, player_name in test_players:
        print(f"\n🎾 {player_name} (ID: {player_id})")
        print("-" * 40)
        
        data = get_surface_specific_tiebreak_data(player_id, "Red clay")
        
        if 'error' in data:
            print(f"   ❌ Error: {data['error']}")
        else:
            print(f"   🏟️ Clay matches: {data['surface_matches']} ({data['surface_win_rate']:.1%} win rate)")
            
            if data.get('no_tiebreak_data'):
                print(f"   🏆 Tiebreaks: No tiebreak data (0 total)")
                print(f"   🚨 MENTAL TOUGHNESS: UNKNOWN - High uncertainty!")
            else:
                print(f"   🏆 Tiebreaks: {data['tiebreaks_won']}/{data['total_tiebreaks']} = {data['tiebreak_rate']:.1%}")
                
                # Analyze mental toughness
                if data['tiebreak_rate'] < 0.25:
                    print(f"   🚨 MENTAL TOUGHNESS: EXTREME FRAGILITY ({data['tiebreak_rate']:.1%})")
                elif data['tiebreak_rate'] < 0.40:
                    print(f"   ⚠️ MENTAL TOUGHNESS: FRAGILITY ({data['tiebreak_rate']:.1%})")
                elif data['tiebreak_rate'] > 0.75:
                    print(f"   💪 MENTAL TOUGHNESS: EXTREME STRENGTH ({data['tiebreak_rate']:.1%})")
                elif data['tiebreak_rate'] > 0.60:
                    print(f"   ✅ MENTAL TOUGHNESS: STRENGTH ({data['tiebreak_rate']:.1%})")
                else:
                    print(f"   😐 MENTAL TOUGHNESS: AVERAGE ({data['tiebreak_rate']:.1%})")

if __name__ == "__main__":
    test_corrected_parsing()
