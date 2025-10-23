#!/usr/bin/env python3

import json
import time
from curl_cffi import requests

def fetch_player_clay_stats(player_id, player_name):
    """Fetch player statistics from MatchDataProvider using curl_cffi"""
    url = f"https://www.matchdata-api.example.com/api/v1/team/{player_id}/year-statistics/2025"
    
    headers = {
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
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'x-requested-with': '945e83'
    }
    
    try:
        response = requests.get(url, headers=headers, impersonate="chrome110")
        response.raise_for_status()
        data = response.json()
        
        print(f"\n🎾 {player_name.upper()} - CLAY COURT ANALYSIS")
        print("=" * 50)
        
        # Check the structure first
        if 'statistics' in data:
            stats = data['statistics']
            
            # Overall stats
            if isinstance(stats, list) and len(stats) > 0:
                overall = stats[0] if stats else {}
            else:
                overall = stats
            
            total_wins = overall.get('wins', 0)
            total_losses = overall.get('losses', 0)
            total_matches = total_wins + total_losses
            win_pct = (total_wins / total_matches * 100) if total_matches > 0 else 0
            
            print(f"📊 OVERALL 2025: {total_matches} matches ({total_wins}W-{total_losses}L) = {win_pct:.1f}%")
            
            # Look for surface-specific data
            surfaces_found = False
            for stat_group in (stats if isinstance(stats, list) else [stats]):
                if 'surfaceStatistics' in stat_group:
                    surfaces = stat_group['surfaceStatistics']
                    surfaces_found = True
                    
                    print("\n🏟️ SURFACE BREAKDOWN:")
                    for surface_name, surface_data in surfaces.items():
                        if isinstance(surface_data, dict):
                            s_wins = surface_data.get('wins', 0)
                            s_losses = surface_data.get('losses', 0)
                            s_matches = s_wins + s_losses
                            s_win_pct = (s_wins / s_matches * 100) if s_matches > 0 else 0
                            
                            surface_display = surface_name.replace('Statistics', '').upper()
                            if 'clay' in surface_name.lower():
                                surface_display += " 🟫 (RED CLAY)"
                                print(f"   ⚠️  {surface_display}: {s_matches} matches ({s_wins}W-{s_losses}L) = {s_win_pct:.1f}%")
                            elif 'hard' in surface_name.lower():
                                surface_display += " 🔵"
                                print(f"   {surface_display}: {s_matches} matches ({s_wins}W-{s_losses}L) = {s_win_pct:.1f}%")
                            else:
                                print(f"   {surface_display}: {s_matches} matches ({s_wins}W-{s_losses}L) = {s_win_pct:.1f}%")
            
            if not surfaces_found:
                print("   ❌ No surface statistics found in response")
            
            # Tiebreak stats
            tiebreaks_won = overall.get('tieBreaksWon', 0)
            tiebreaks_total = overall.get('tieBreaksTotal', 0)
            if tiebreaks_total > 0:
                tb_pct = (tiebreaks_won / tiebreaks_total * 100)
                print(f"\n🧠 MENTAL TOUGHNESS: {tiebreaks_won}/{tiebreaks_total} tiebreaks = {tb_pct:.1f}%")
            
        else:
            print("❌ No statistics field found")
            print("Raw response keys:", list(data.keys()))
        
        # Always dump raw JSON for debugging
        print(f"\n📄 RAW JSON for {player_name}:")
        print("=" * 30)
        print(json.dumps(data, indent=2))
        
        return data
        
    except Exception as e:
        print(f"❌ Error fetching {player_name} ({player_id}): {e}")
        return None

def main():
    """Analyze the losing players"""
    print("🎾 CLAY COURT ANALYSIS FOR LOSING BETS")
    print("=" * 60)
    
    # Players from the losing bets
    losing_players = [
        (227447, "Tommaso Compagnucci"),  # Lost on red clay
        (230049, "Filip Cristian Jianu"),  # Won on red clay but we bet against him
    ]
    
    for player_id, player_name in losing_players:
        print(f"\n🔍 Fetching {player_name}...")
        stats = fetch_player_clay_stats(player_id, player_name)
        time.sleep(2)  # Rate limiting
    
    print("\n\n📋 KEY FINDINGS:")
    print("=" * 40)
    print("1. Check if clay court win rates match our predictions")
    print("2. Look for red flags in surface-specific performance")
    print("3. Compare mental toughness (tiebreak rates)")
    print("4. Identify why our system marked them as 'no_surface_data'")

if __name__ == "__main__":
    main()
