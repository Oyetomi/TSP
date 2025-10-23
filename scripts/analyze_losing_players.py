#!/usr/bin/env python3

import requests
import json
import time
from curl_cffi import requests as cf_requests

# Player name to MatchDataProvider ID mapping from recent searches
PLAYER_IDS = {
    "Tommaso Compagnucci": 227447,
    "Filip Cristian Jianu": 230049,
    "Stefan Palosi": None,  # Need to find
    "Mathys Erhard": None,  # Need to find
    "Quinn Vandecasteele": None,  # Need to find
    "James Trotter": None,  # Need to find
    "Jazmin Ortenzi": None,  # Need to find
    "Berfu Cengiz": None,  # Need to find
    "Maxime Janvier": None,  # Need to find
    "Egor Gerasimov": None   # Need to find
}

def fetch_player_stats(player_id, player_name):
    """Fetch player statistics from MatchDataProvider"""
    if not player_id:
        print(f"❌ No ID found for {player_name}")
        return None
    
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
        # Use curl_cffi to mimic browser behavior
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching {player_name} ({player_id}): {e}")
        return None

def analyze_surface_performance(stats, player_name):
    """Analyze surface-specific performance"""
    if not stats:
        return
    
    print(f"\n🎾 {player_name.upper()} SURFACE ANALYSIS:")
    print("=" * 50)
    
    # Check if we have surface statistics
    statistics = stats.get('statistics', {})
    
    # Overall statistics
    print("📊 OVERALL STATS:")
    total_wins = statistics.get('wins', 0)
    total_losses = statistics.get('losses', 0)
    total_matches = total_wins + total_losses
    win_percentage = (total_wins / total_matches * 100) if total_matches > 0 else 0
    print(f"   Matches: {total_matches} (W: {total_wins}, L: {total_losses})")
    print(f"   Win %: {win_percentage:.1f}%")
    
    # Surface-specific stats
    surfaces = statistics.get('surfaceStatistics', {})
    if surfaces:
        print("\n🏟️ SURFACE BREAKDOWN:")
        for surface_key, surface_data in surfaces.items():
            if isinstance(surface_data, dict):
                wins = surface_data.get('wins', 0)
                losses = surface_data.get('losses', 0)
                matches = wins + losses
                win_pct = (wins / matches * 100) if matches > 0 else 0
                
                # Determine surface name
                surface_name = surface_key.replace('Statistics', '').upper()
                if 'clay' in surface_key.lower():
                    surface_name += " 🟫"
                elif 'hard' in surface_key.lower():
                    surface_name += " 🔵"
                elif 'grass' in surface_key.lower():
                    surface_name += " 🟢"
                
                print(f"   {surface_name}: {matches} matches ({wins}W-{losses}L) = {win_pct:.1f}%")
    else:
        print("   ❌ No surface statistics available")
    
    # Tiebreak performance for mental toughness
    tiebreaks = statistics.get('tieBreaksWon', 0)
    tiebreak_total = statistics.get('tieBreaksTotal', 0)
    if tiebreak_total > 0:
        tiebreak_pct = (tiebreaks / tiebreak_total * 100)
        print(f"\n🧠 MENTAL TOUGHNESS:")
        print(f"   Tiebreaks: {tiebreaks}/{tiebreak_total} = {tiebreak_pct:.1f}%")
    
    return {
        'total_matches': total_matches,
        'win_percentage': win_percentage,
        'surfaces': surfaces,
        'tiebreak_percentage': (tiebreaks / tiebreak_total * 100) if tiebreak_total > 0 else None
    }

def main():
    """Main analysis function"""
    print("🎾 LOSING PLAYERS SURFACE ANALYSIS")
    print("=" * 60)
    
    # Analyze the known players first
    known_players = ["Tommaso Compagnucci", "Filip Cristian Jianu"]
    
    for player_name in known_players:
        player_id = PLAYER_IDS.get(player_name)
        if player_id:
            print(f"\n🔍 Fetching stats for {player_name}...")
            stats = fetch_player_stats(player_id, player_name)
            analyze_surface_performance(stats, player_name)
            time.sleep(2)  # Rate limiting
    
    print("\n\n📋 SUMMARY OF ISSUES:")
    print("=" * 40)
    print("1. Check if players have sufficient clay court data")
    print("2. Compare actual surface performance vs our predictions")
    print("3. Look for mental toughness (tiebreak) red flags")
    print("4. Identify if our 'no_surface_data' default is causing issues")

if __name__ == "__main__":
    main()
