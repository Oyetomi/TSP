#!/usr/bin/env python3
"""
Real Tiebreak Statistics Fetcher

Fetches actual tiebreak performance data from MatchDataProvider statistics endpoints
instead of using simulated data.
"""

import sys
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from curl_cffi.requests import AsyncSession

# Add project root to path
sys.path.append('/Users/abbey/Desktop/resources/prediction-projects/tennis/tennis-set-prediction')
from app.services.mental_toughness_service import mental_toughness_service

class RealTiebreakFetcher:
    """Fetches real tiebreak statistics from MatchDataProvider."""
    
    def __init__(self):
        self.session = None
        self.headers = {
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
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        self.cookies = {'perf_dv6Tr4n': '1'}
    
    async def __aenter__(self):
        self.session = AsyncSession(impersonate="chrome120")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_player(self, player_name: str) -> Optional[int]:
        """Search for a player and return their ID."""
        try:
            search_name = player_name.replace(' ', '%20')
            url = f"https://www.matchdata-api.example.com/api/v1/search/tennis?q={search_name}"
            
            response = await self.session.get(url, headers=self.headers, cookies=self.cookies, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                for result in results:
                    if result.get('type') == 'team' and result.get('sport', {}).get('name') == 'Tennis':
                        entity = result.get('entity', {})
                        if self._is_name_match(player_name, entity.get('name', '')):
                            return entity.get('id')
            
            return None
            
        except Exception as e:
            print(f"   ❌ Error searching for {player_name}: {e}")
            return None
    
    def _is_name_match(self, search_name: str, result_name: str) -> bool:
        """Check if names match with fuzzy matching."""
        search_parts = search_name.lower().split()
        result_parts = result_name.lower().split()
        
        matches = 0
        for search_part in search_parts:
            for result_part in result_parts:
                if search_part in result_part or result_part in search_part:
                    matches += 1
                    break
        
        return matches >= min(2, len(search_parts))
    
    async def get_player_tiebreak_stats(self, player_id: int, year: int = 2025) -> Dict:
        """Get real tiebreak statistics for a player."""
        try:
            url = f"https://www.matchdata-api.example.com/api/v1/team/{player_id}/year-statistics/{year}"
            
            response = await self.session.get(url, headers=self.headers, cookies=self.cookies, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                statistics = data.get('statistics', [])
                
                # Aggregate tiebreak stats across all surfaces
                total_tiebreak_wins = 0
                total_tiebreak_losses = 0
                total_matches = 0
                total_wins = 0
                total_break_points_won = 0
                total_break_points_faced = 0
                surface_breakdown = {}
                
                for stat in statistics:
                    surface = stat.get('groundType', 'Unknown')
                    wins = stat.get('tiebreaksWon', 0) 
                    losses = stat.get('tiebreakLosses', 0)
                    matches = stat.get('matches', 0)
                    match_wins = stat.get('wins', 0)
                    bp_won = stat.get('breakPointsScored', 0)
                    bp_total = stat.get('breakPointsTotal', 0)
                    
                    total_tiebreak_wins += wins
                    total_tiebreak_losses += losses
                    total_matches += matches
                    total_wins += match_wins
                    total_break_points_won += bp_won
                    total_break_points_faced += bp_total
                    
                    if wins + losses > 0:  # Only include surfaces with tiebreak data
                        surface_breakdown[surface] = {
                            'wins': wins,
                            'losses': losses,
                            'win_rate': wins / (wins + losses) if (wins + losses) > 0 else 0,
                            'matches': matches,
                            'match_wins': match_wins
                        }
                
                total_tiebreaks = total_tiebreak_wins + total_tiebreak_losses
                tiebreak_win_rate = total_tiebreak_wins / total_tiebreaks if total_tiebreaks > 0 else 0.5
                
                # Calculate break point conversion (pressure performance indicator)
                bp_conversion = total_break_points_won / total_break_points_faced if total_break_points_faced > 0 else 0.25
                
                # Calculate match win rate
                match_win_rate = total_wins / total_matches if total_matches > 0 else 0.5
                
                return {
                    'player_id': player_id,
                    'year': year,
                    'tiebreak_wins': total_tiebreak_wins,
                    'tiebreak_losses': total_tiebreak_losses,
                    'tiebreak_win_rate': tiebreak_win_rate,
                    'total_tiebreaks': total_tiebreaks,
                    'break_point_conversion': bp_conversion,
                    'break_points_won': total_break_points_won,
                    'break_points_faced': total_break_points_faced,
                    'match_win_rate': match_win_rate,
                    'total_matches': total_matches,
                    'total_wins': total_wins,
                    'surface_breakdown': surface_breakdown,
                    'has_sufficient_data': total_tiebreaks >= 3  # Minimum 3 tiebreaks for reliability
                }
            
            return None
            
        except Exception as e:
            print(f"   ❌ Error getting stats for player {player_id}: {e}")
            return None
    
    def calculate_mental_toughness_from_real_data(self, stats: Dict) -> float:
        """Calculate mental toughness score from real statistics."""
        if not stats or not stats.get('has_sufficient_data'):
            return 0.5  # Neutral if insufficient data
        
        # Weight factors for mental toughness calculation
        tiebreak_weight = 0.50      # Primary indicator
        bp_conversion_weight = 0.30 # Secondary pressure indicator  
        consistency_weight = 0.20   # Match win rate consistency
        
        # Tiebreak performance (0.0 to 1.0)
        tiebreak_score = stats['tiebreak_win_rate']
        
        # Break point conversion (normalized to 0.0-1.0, with 0.25 as baseline poor, 0.45 as excellent)
        bp_score = min(1.0, max(0.0, (stats['break_point_conversion'] - 0.15) / 0.35))
        
        # Match consistency (how well they convert skill to wins)
        match_consistency = stats['match_win_rate']
        
        # Calculate weighted mental toughness score
        mental_score = (
            tiebreak_score * tiebreak_weight +
            bp_score * bp_conversion_weight +
            match_consistency * consistency_weight
        )
        
        return max(0.0, min(1.0, mental_score))

async def test_real_tiebreak_data():
    """Test real tiebreak data fetching and analysis."""
    
    print("🎾 REAL TIEBREAK DATA ANALYSIS")
    print("=" * 60)
    
    # Test players from our losing bets + known players
    test_players = [
        "Billy Harris",           # From our analysis
        "Daniil Glinka", 
        "Bernard Tomic",
        "Jurij Rodionov",
        "Stefanos Tsitsipas"     # For comparison
    ]
    
    results = []
    
    async with RealTiebreakFetcher() as fetcher:
        for player_name in test_players:
            print(f"\n🔍 Analyzing: {player_name}")
            
            # Search for player
            player_id = await fetcher.search_player(player_name)
            
            if not player_id:
                print(f"   ❌ Player not found")
                continue
            
            print(f"   ✅ Found player ID: {player_id}")
            
            # Get tiebreak stats
            stats = await fetcher.get_player_tiebreak_stats(player_id)
            
            if not stats:
                print(f"   ❌ No statistics available")
                continue
            
            # Calculate mental toughness from real data
            mental_score = fetcher.calculate_mental_toughness_from_real_data(stats)
            
            print(f"   📊 Tiebreak record: {stats['tiebreak_wins']}-{stats['tiebreak_losses']} ({stats['tiebreak_win_rate']:.1%})")
            print(f"   🎯 Break points: {stats['break_points_won']}/{stats['break_points_faced']} ({stats['break_point_conversion']:.1%})")
            print(f"   🏆 Match record: {stats['total_wins']}/{stats['total_matches']} ({stats['match_win_rate']:.1%})")
            print(f"   🧠 Mental toughness score: {mental_score:.2f}")
            
            # Surface breakdown
            if stats['surface_breakdown']:
                print(f"   🏟️  Surface breakdown:")
                for surface, data in stats['surface_breakdown'].items():
                    print(f"      {surface}: {data['wins']}-{data['losses']} ({data['win_rate']:.1%})")
            
            # Generate confidence adjustment
            if mental_score <= 0.30:
                adjustment = -20
                severity = "High Risk"
            elif mental_score <= 0.40:
                adjustment = -12
                severity = "Moderate Risk"
            elif mental_score >= 0.70:
                adjustment = +5
                severity = "Mental Strength"
            else:
                adjustment = 0
                severity = "Average"
            
            print(f"   📈 Confidence adjustment: {adjustment:+.0f}% ({severity})")
            
            results.append({
                'player_name': player_name,
                'player_id': player_id,
                'mental_score': mental_score,
                'adjustment': adjustment,
                'severity': severity,
                'stats': stats
            })
            
            # Rate limiting
            await asyncio.sleep(1.5)
    
    # Summary
    print(f"\n" + "=" * 60)
    print("🎯 REAL DATA MENTAL TOUGHNESS SUMMARY")
    print("=" * 60)
    
    if results:
        weak_players = [r for r in results if r['mental_score'] < 0.4]
        strong_players = [r for r in results if r['mental_score'] > 0.6]
        
        print(f"📊 Analyzed {len(results)} players with real tiebreak data")
        print(f"💪 Mentally strong: {len(strong_players)} players")
        print(f"😰 Mentally weak: {len(weak_players)} players")
        
        if weak_players:
            print(f"\n🚨 Players with mental concerns:")
            for player in weak_players:
                stats = player['stats']
                print(f"   • {player['player_name']}: {player['mental_score']:.2f} score ({stats['tiebreak_wins']}-{stats['tiebreak_losses']} tiebreaks, {player['adjustment']:+.0f}% adjustment)")
        
        if strong_players:
            print(f"\n💪 Players with mental strength:")
            for player in strong_players:
                stats = player['stats']
                print(f"   • {player['player_name']}: {player['mental_score']:.2f} score ({stats['tiebreak_wins']}-{stats['tiebreak_losses']} tiebreaks, {player['adjustment']:+.0f}% adjustment)")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"logs/real_tiebreak_analysis_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_real_tiebreak_data())
