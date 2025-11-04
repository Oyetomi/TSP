"""
Script to check Sara Bejlek's recent match history and opponent rankings
to verify quality opposition data calculation
"""

import sys
import json
from datetime import datetime
from curl_cffi import requests

# Import API secrets
try:
    from api_secrets import MATCH_DATA_CONFIG
except ImportError:
    print("⚠️  WARNING: api_secrets.py not found!")
    sys.exit(1)

BASE_URL = MATCH_DATA_CONFIG.get('base_url', 'https://www.matchdata-api.example.com/api/v1')
HEADERS = MATCH_DATA_CONFIG.get('headers', {})
COOKIES = MATCH_DATA_CONFIG.get('cookies', {})

# Player IDs from CSV
BEJLEK_PLAYER_ID = 360184
UDVARDY_PLAYER_ID = 218347

def get_player_recent_matches(player_id: int, max_matches: int = 15):
    """Get recent matches for a player"""
    url = f"{BASE_URL}/team/{player_id}/events/last/0"
    
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            cookies=COOKIES,
            impersonate="chrome120",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        matches = data.get('events', [])[:max_matches]
        return matches
        
    except Exception as e:
        print(f"❌ Error fetching matches: {e}")
        return []

def get_opponent_info(match: dict, player_id: int):
    """Extract opponent information from match data"""
    try:
        # Debug: print match structure
        home_team = match.get('homeTeam', {})
        away_team = match.get('awayTeam', {})
        
        if home_team.get('id') == player_id:
            opponent = away_team
            player_was_home = True
        else:
            opponent = home_team
            player_was_home = False
        
        # Get score - try multiple structures
        score = match.get('score', {})
        sets = score.get('current', {})
        
        # Extract sets won
        if player_was_home:
            player_sets = sets.get('home', 0)
            opponent_sets = sets.get('away', 0)
        else:
            player_sets = sets.get('away', 0)
            opponent_sets = sets.get('home', 0)
        
        # Get opponent ranking - try multiple locations
        opponent_ranking = opponent.get('rank', None)
        if opponent_ranking is None:
            opponent_ranking = opponent.get('ranking', None)
        if opponent_ranking is None:
            # Try to get from statistics
            stats = match.get('statistics', {})
            if player_was_home:
                opponent_ranking = stats.get('awayTeam', {}).get('rank', None)
            else:
                opponent_ranking = stats.get('homeTeam', {}).get('rank', None)
        
        return {
            'opponent_name': opponent.get('name', 'Unknown'),
            'opponent_id': opponent.get('id'),
            'opponent_ranking': opponent_ranking,
            'player_sets': player_sets,
            'opponent_sets': opponent_sets,
            'result': 'W' if player_sets > opponent_sets else 'L',
            'date': match.get('startTimestamp'),
            'tournament': match.get('tournament', {}).get('name', 'Unknown'),
            'raw_match': match  # Keep raw data for debugging
        }
    except Exception as e:
        print(f"   ⚠️ Error extracting opponent info: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_matches(matches: list, player_id: int, quality_threshold: int = 108):
    """Analyze matches and categorize by opponent quality"""
    results = {
        'total_matches': len(matches),
        'quality_opponents': [],
        'non_quality_opponents': [],
        'no_ranking_data': [],
        'quality_sets': {'won': 0, 'total': 0},
        'non_quality_sets': {'won': 0, 'total': 0}
    }
    
    for match in matches:
        opponent_info = get_opponent_info(match, player_id)
        if not opponent_info:
            results['no_ranking_data'].append(match)
            continue
        
        opponent_ranking = opponent_info['opponent_ranking']
        
        if opponent_ranking is None:
            results['no_ranking_data'].append(opponent_info)
        elif opponent_ranking < quality_threshold:
            # Quality opponent (ranked better than threshold)
            results['quality_opponents'].append(opponent_info)
            results['quality_sets']['won'] += opponent_info['player_sets']
            results['quality_sets']['total'] += (opponent_info['player_sets'] + opponent_info['opponent_sets'])
        else:
            # Non-quality opponent (ranked worse than threshold)
            results['non_quality_opponents'].append(opponent_info)
            results['non_quality_sets']['won'] += opponent_info['player_sets']
            results['non_quality_sets']['total'] += (opponent_info['player_sets'] + opponent_info['opponent_sets'])
    
    return results

def format_date(timestamp):
    """Format timestamp to readable date"""
    if not timestamp:
        return "Unknown"
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d")
    except:
        return "Unknown"

def analyze_player(player_id: int, player_name: str, quality_threshold: int):
    """Analyze a single player's match history"""
    print("="*80)
    print(f"{player_name.upper()} RECENT MATCH ANALYSIS")
    print("="*80)
    print()
    print(f"Player ID: {player_id}")
    print(f"Quality Threshold: Top-{quality_threshold} (opponents ranked #1-{quality_threshold-1})")
    print()
    
    # Fetch recent matches
    print("📊 Fetching recent matches...")
    matches = get_player_recent_matches(player_id, max_matches=15)
    
    if not matches:
        print("❌ No matches found!")
        return None
    
    print(f"✅ Found {len(matches)} recent matches")
    print()
    
    # Analyze matches
    analysis = analyze_matches(matches, player_id, quality_threshold=quality_threshold)
    
    # Print summary
    print("="*80)
    print("MATCH ANALYSIS SUMMARY")
    print("="*80)
    print()
    print(f"Total Matches Analyzed: {analysis['total_matches']}")
    print(f"Quality Opponents (Top-{quality_threshold}): {len(analysis['quality_opponents'])}")
    print(f"Non-Quality Opponents (#{quality_threshold}+): {len(analysis['non_quality_opponents'])}")
    print(f"Matches Without Ranking Data: {len(analysis['no_ranking_data'])}")
    print()
    
    # Quality opposition sets
    print("="*80)
    print("QUALITY OPPOSITION SETS")
    print("="*80)
    print()
    if analysis['quality_sets']['total'] > 0:
        win_rate = analysis['quality_sets']['won'] / analysis['quality_sets']['total']
        print(f"Sets Won: {analysis['quality_sets']['won']}")
        print(f"Total Sets: {analysis['quality_sets']['total']}")
        print(f"Win Rate: {win_rate:.1%}")
    else:
        print("❌ ZERO quality opposition sets!")
        print("   This confirms the data quality issue")
    print()
    
    # Detailed match list - show first few matches
    print("="*80)
    print("RECENT MATCHES (showing opponent names)")
    print("="*80)
    print()
    for i, match in enumerate(matches[:10], 1):
        opponent_info = get_opponent_info(match, player_id)
        if opponent_info:
            date_str = format_date(opponent_info['date'])
            rank_str = f"Rank: #{opponent_info['opponent_ranking']}" if opponent_info['opponent_ranking'] else "Rank: Unknown"
            print(f"{i}. {date_str} - {opponent_info['opponent_name']} ({rank_str})")
            print(f"   Result: {opponent_info['result']} ({opponent_info['player_sets']}-{opponent_info['opponent_sets']})")
            print()
        else:
            print(f"{i}. Match data unavailable")
            print()
    
    print("="*80)
    print("QUALITY OPPONENTS (Top-108)")
    print("="*80)
    print()
    if analysis['quality_opponents']:
        for match in analysis['quality_opponents']:
            date_str = format_date(match['date'])
            print(f"{date_str} - {match['opponent_name']} (Rank: #{match['opponent_ranking']})")
            print(f"  Result: {match['result']} ({match['player_sets']}-{match['opponent_sets']})")
            print(f"  Tournament: {match['tournament']}")
            print()
    else:
        print("❌ NO quality opponents found!")
        print()
    
    print("="*80)
    print("NON-QUALITY OPPONENTS (#108+)")
    print("="*80)
    print()
    if analysis['non_quality_opponents']:
        for match in analysis['non_quality_opponents']:
            date_str = format_date(match['date'])
            print(f"{date_str} - {match['opponent_name']} (Rank: #{match['opponent_ranking']})")
            print(f"  Result: {match['result']} ({match['player_sets']}-{match['opponent_sets']})")
            print(f"  Tournament: {match['tournament']}")
            print()
    else:
        print("No non-quality opponents found")
        print()
    
    return analysis

def main():
    quality_threshold = 108  # Top-108 (opponents ranked #1-107)
    
    # Analyze Bejlek
    bejlek_analysis = analyze_player(BEJLEK_PLAYER_ID, "Sara Bejlek", quality_threshold)
    
    print("\n\n")
    
    # Analyze Udvardy
    udvardy_analysis = analyze_player(UDVARDY_PLAYER_ID, "Panna Udvardy", quality_threshold)
    
    # Final comparison
    print("\n\n")
    print("="*80)
    print("FINAL COMPARISON")
    print("="*80)
    print()
    if bejlek_analysis and udvardy_analysis:
        print("Sara Bejlek:")
        print(f"  Quality Sets: {bejlek_analysis['quality_sets']['total']}")
        print(f"  Quality Opponents: {len(bejlek_analysis['quality_opponents'])}")
        print()
        print("Panna Udvardy:")
        print(f"  Quality Sets: {udvardy_analysis['quality_sets']['total']}")
        print(f"  Quality Opponents: {len(udvardy_analysis['quality_opponents'])}")
        print()
        
        if bejlek_analysis['quality_sets']['total'] == 0:
            print("✅ CONFIRMED: Bejlek has 0 quality opposition sets")
            print("   Her 85.5% win rate is based on weak competition")
            print("   This match should have been skipped!")
        elif udvardy_analysis['quality_sets']['total'] == 0:
            print("⚠️  Both players have limited quality data")
            print("   Match reliability questionable")
        else:
            print(f"⚠️  Bejlek has {bejlek_analysis['quality_sets']['total']} quality sets")
            print("   Need to investigate why system shows 0")
            print("   Possible bug in quality opposition calculation")

if __name__ == "__main__":
    main()

