#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from curl_cffi import requests
import json

def search_player_id(player_name):
    """Search for player ID using MatchDataProvider search"""
    try:
        # Use MatchDataProvider search API
        search_url = f"https://www.matchdata-api.example.com/api/v1/search?q={player_name.replace(' ', '%20')}"
        
        response = requests.get(
            search_url,
            headers={
                'accept': '*/*',
                'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
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
            
            # Look for tennis players in results
            for category in data.get('results', []):
                if category.get('type') == 'team' and category.get('sport', {}).get('name') == 'Tennis':
                    for result in category.get('results', []):
                        if result.get('entity', {}).get('name', '').lower() == player_name.lower():
                            return result.get('entity', {}).get('id')
            
            print(f"❌ Player '{player_name}' not found in search results")
            return None
            
        else:
            print(f"❌ Search error {response.status_code} for {player_name}")
            return None
            
    except Exception as e:
        print(f"❌ Error searching for {player_name}: {e}")
        return None

def main():
    players_to_find = [
        "Jazmin Ortenzi",
        "Mathys Erhard", 
        "James Trotter"
    ]
    
    print("🔍 FINDING PLAYER IDs")
    print("="*40)
    
    found_ids = {}
    
    for player in players_to_find:
        print(f"\n🔍 Searching for: {player}")
        player_id = search_player_id(player)
        
        if player_id:
            print(f"   ✅ Found: {player_id}")
            found_ids[player] = player_id
        else:
            print(f"   ❌ Not found")
    
    print(f"\n📋 RESULTS:")
    for player, player_id in found_ids.items():
        print(f"   {player}: {player_id}")
    
    return found_ids

if __name__ == "__main__":
    main()
