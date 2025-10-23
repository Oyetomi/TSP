#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from curl_cffi import requests
import json

def search_player_id_v2(player_name):
    """Search for player ID using the correct MatchDataProvider search endpoint"""
    try:
        # Use the working search endpoint format
        search_url = f"https://www.matchdata-api.example.com/api/v1/search/all?q={player_name.split()[1]}&page=0"  # Search by last name
        
        response = requests.get(
            search_url,
            headers={
                'accept': '*/*',
                'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
                'baggage': 'sentry-environment=production,sentry-release=t8wxr4GCNBzFQ4MgacIvM,sentry-public_key=d693747a6bb242d9bb9cf7069fb57988,sentry-trace_id=1340aab567165d43aa35d7bcc752e014',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'priority': 'u=1, i',
                'referer': 'https://www.matchdata-api.example.com/',
                'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'sec-gpc': '1',
                'sentry-trace': '1340aab567165d43aa35d7bcc752e014-a44c97ec763ed8d7',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                'x-requested-with': '9cf38a'
            },
            impersonate="chrome"
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"🔍 Search results for '{player_name}':")
            
            # Look for tennis players in results
            for result in data.get('results', []):
                if result.get('type') == 'team':
                    entity = result.get('entity', {})
                    sport = entity.get('sport', {})
                    
                    if sport.get('name') == 'Tennis':
                        full_name = entity.get('name', '')
                        player_id = entity.get('id')
                        country = entity.get('country', {}).get('name', 'Unknown')
                        
                        print(f"   • {full_name} (ID: {player_id}, {country})")
                        
                        # Check if this matches our target player
                        if player_name.lower() in full_name.lower() or full_name.lower() in player_name.lower():
                            print(f"   ✅ MATCH FOUND: {full_name} = {player_id}")
                            return player_id
            
            print(f"   ❌ No exact match found for '{player_name}'")
            return None
            
        else:
            print(f"❌ Search error {response.status_code} for {player_name}")
            return None
            
    except Exception as e:
        print(f"❌ Error searching for {player_name}: {e}")
        return None

def get_player_stats(player_id):
    """Fetch player statistics"""
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
            return response.json()
        else:
            print(f"❌ Error {response.status_code} fetching stats for player {player_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching stats for {player_id}: {e}")
        return None

def analyze_surface_performance(stats, surface="Red clay"):
    """Analyze surface-specific performance"""
    if not stats or 'statistics' not in stats:
        return "No data"
        
    statistics = stats['statistics']
    
    for stat_group in statistics:
        if not isinstance(stat_group, dict):
            continue
            
        ground_type = stat_group.get('groundType', '')
        if ground_type == surface:
            matches = stat_group.get('matches', 0)
            wins = stat_group.get('wins', 0)
            
            if matches > 0:
                win_rate = wins / matches
                return f"{wins}/{matches} = {win_rate:.1%} ({matches} matches)"
                
    return f"No {surface} data"

def analyze_tiebreak_performance(stats):
    """Analyze tiebreak performance"""
    if not stats or 'statistics' not in stats:
        return "No data"
        
    statistics = stats['statistics']
    
    for stat_group in statistics:
        if not isinstance(stat_group, dict):
            continue
            
        # Overall stats usually don't have groundType
        if 'groundType' not in stat_group or not stat_group.get('groundType'):
            tb_won = stat_group.get('tiebreaksWon', 0)
            tb_lost = stat_group.get('tiebreakLosses', 0)
            tb_total = tb_won + tb_lost
            
            if tb_total > 0:
                tb_rate = tb_won / tb_total
                return f"{tb_won}/{tb_total} = {tb_rate:.1%} ({tb_total} tiebreaks)"
                
    return "No tiebreak data"

def main():
    players_to_find = [
        "Jazmin Ortenzi",
        "Mathys Erhard", 
        "James Trotter"
    ]
    
    print("🔍 FINDING PLAYER IDs (V2 - Improved Search)")
    print("="*50)
    
    found_players = {}
    
    for player in players_to_find:
        print(f"\n{'='*50}")
        print(f"🔍 Searching for: {player}")
        player_id = search_player_id_v2(player)
        
        if player_id:
            print(f"\n📊 Getting statistics for {player} (ID: {player_id})...")
            stats = get_player_stats(player_id)
            
            if stats:
                surface_perf = analyze_surface_performance(stats, "Red clay")
                tiebreak_perf = analyze_tiebreak_performance(stats)
                
                print(f"   🏟️ Red Clay Performance: {surface_perf}")
                print(f"   🏆 Tiebreak Performance: {tiebreak_perf}")
                
                # Flag critical issues
                if "No tiebreak data" in tiebreak_perf:
                    print(f"   🚨 CRITICAL: No tiebreak data - system vulnerability!")
                    
                if "%" in surface_perf and "matches)" in surface_perf:
                    win_rate_str = surface_perf.split(" = ")[1].split("%")[0]
                    try:
                        win_rate = float(win_rate_str) / 100
                        if win_rate < 0.45:
                            print(f"   ⚠️ POOR SURFACE PERFORMANCE: {win_rate:.1%} < 45% threshold")
                    except:
                        pass
                
                found_players[player] = {
                    'id': player_id,
                    'surface_perf': surface_perf,
                    'tiebreak_perf': tiebreak_perf
                }
            else:
                print(f"   ❌ Could not fetch statistics")
        else:
            print(f"   ❌ Player ID not found")
    
    print(f"\n📋 COMPREHENSIVE RESULTS:")
    print("="*50)
    for player, data in found_players.items():
        print(f"\n{player}:")
        print(f"   ID: {data['id']}")
        print(f"   Surface: {data['surface_perf']}")
        print(f"   Tiebreak: {data['tiebreak_perf']}")
    
    return found_players

if __name__ == "__main__":
    main()
