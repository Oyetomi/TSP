#!/usr/bin/env python3
"""
Tiebreak Revalidation Script

Analyzes losing bets to see if incorporating tiebreak performance 
would have changed the predictions and improved accuracy.
"""

import asyncio
import csv
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from curl_cffi.requests import AsyncSession

# Define the losing bets with actual event IDs from our prediction data
LOSING_BETS = [
    {
        "match": "Victoria Rodriguez vs Haley Giavara",
        "bet_on": "Haley Giavara", 
        "confidence": 85.0,
        "result": "Won 0 sets",
        "event_id": 14628496  # From our CSV data
    },
    {
        "match": "Martina Okalova vs Martha Matoula",
        "bet_on": "Martha Matoula",
        "confidence": 85.0,
        "result": "Won 0 sets", 
        "event_id": 14628499
    },
    {
        "match": "Bernard Tomic vs Yasutaka Uchiyama",
        "bet_on": "Bernard Tomic",
        "confidence": 85.0,
        "result": "Won 0 sets",
        "event_id": 14552532
    },
    {
        "match": "Daniil Glinka vs Jurij Rodionov", 
        "bet_on": "Jurij Rodionov",
        "confidence": 85.0,
        "result": "Won 0 sets",
        "event_id": 14552910
    },
    {
        "match": "Nicolas Mejia vs Luca Potenza",
        "bet_on": "Luca Potenza", 
        "confidence": 0.0,  # Note: This was a SKIP_BET but validated anyway
        "result": "Won 0 sets",
        "event_id": 14552661
    },
    {
        "match": "Maria Timofeeva vs Veronika Erjavec",
        "bet_on": "Maria Timofeeva",
        "confidence": 85.0,
        "result": "Won 0 sets",
        "event_id": 14560138  # From validation results
    },
    {
        "match": "Nahia Berecoechea vs Tatiana Pieri", 
        "bet_on": "Tatiana Pieri",
        "confidence": 85.0,
        "result": "Won 0 sets",
        "event_id": 14627758  # From validation results
    },
    {
        "match": "Carson Branstine vs Noma Noha Akugue",
        "bet_on": "Noma Noha Akugue", 
        "confidence": 83.6,
        "result": "Won 0 sets",
        "event_id": 14627753  # From validation results
    },
    {
        "match": "Gabriela Lee vs Ekaterina Kazionova",
        "bet_on": "Gabriela Lee",
        "confidence": 67.5,
        "result": "Won 0 sets",
        "event_id": 14627751  # From validation results
    },
    {
        "match": "Jana Vanik vs Annika Kannan",
        "bet_on": "Jana Vanik", 
        "confidence": 85.0,
        "result": "Won 0 sets",
        "event_id": 14626471  # From validation results
    }
]

class TiebreakAnalyzer:
    """Analyzes tiebreak performance for tennis players."""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.matchdata-api.example.com/',
            'Origin': 'https://www.matchdata-api.example.com'
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = AsyncSession(impersonate="chrome120")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def search_player(self, player_name: str) -> Optional[Dict]:
        """Search for a player and get their ID."""
        try:
            # Clean player name for search
            search_name = player_name.replace(' ', '%20')
            url = f"https://www.matchdata-api.example.com/api/v1/search/tennis?q={search_name}"
            
            response = await self.session.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                for result in results:
                    if result.get('type') == 'team' and result.get('sport', {}).get('name') == 'Tennis':
                        entity = result.get('entity', {})
                        if self._is_name_match(player_name, entity.get('name', '')):
                            return {
                                'id': entity.get('id'),
                                'name': entity.get('name'),
                                'country': entity.get('country', {}).get('name', 'Unknown')
                            }
            
            print(f"   ❌ Player not found: {player_name}")
            return None
            
        except Exception as e:
            print(f"   ❌ Error searching for {player_name}: {e}")
            return None
    
    def _is_name_match(self, search_name: str, result_name: str) -> bool:
        """Check if names match (fuzzy matching)."""
        search_parts = search_name.lower().split()
        result_parts = result_name.lower().split()
        
        # Check if all search parts are found in result
        for search_part in search_parts:
            found = False
            for result_part in result_parts:
                if search_part in result_part or result_part in search_part:
                    found = True
                    break
            if not found:
                return False
        return True
    
    async def get_player_matches(self, player_id: int, limit: int = 20) -> List[Dict]:
        """Get recent matches for a player."""
        try:
            url = f"https://www.matchdata-api.example.com/api/v1/team/{player_id}/events/last/0"
            
            response = await self.session.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                
                matches = []
                for event in events[:limit]:
                    # Only include finished matches
                    status = event.get('status', {})
                    if status.get('type') == 'finished':
                        matches.append({
                            'id': event.get('id'),
                            'tournament': event.get('tournament', {}).get('name'),
                            'opponent': self._get_opponent_name(event, player_id),
                            'score': self._extract_score(event),
                            'date': event.get('startTimestamp')
                        })
                
                return matches[:limit]
            
            return []
            
        except Exception as e:
            print(f"   ❌ Error getting matches for player {player_id}: {e}")
            return []
    
    def _get_opponent_name(self, event: Dict, player_id: int) -> str:
        """Extract opponent name from event."""
        home = event.get('homeTeam', {})
        away = event.get('awayTeam', {})
        
        if home.get('id') == player_id:
            return away.get('name', 'Unknown')
        else:
            return home.get('name', 'Unknown')
    
    def _extract_score(self, event: Dict) -> Dict:
        """Extract match score details."""
        home_score = event.get('homeScore', {})
        away_score = event.get('awayScore', {})
        
        return {
            'home_sets': home_score.get('current', 0),
            'away_sets': away_score.get('current', 0),
            'periods': home_score.get('period1', 0)  # This might contain tiebreak info
        }
    
    async def analyze_tiebreak_performance(self, player_name: str) -> Dict:
        """Analyze a player's tiebreak performance from recent matches."""
        print(f"   🔍 Analyzing tiebreak performance for {player_name}...")
        
        # Search for player
        player_info = await self.search_player(player_name)
        if not player_info:
            return {
                'player_name': player_name,
                'tiebreak_record': '0-0',
                'tiebreak_win_rate': 0.0,
                'recent_form_tiebreaks': 'Unknown',
                'analysis': 'Player not found'
            }
        
        # Get recent matches
        matches = await self.get_player_matches(player_info['id'])
        
        if not matches:
            return {
                'player_name': player_name,
                'tiebreak_record': '0-0', 
                'tiebreak_win_rate': 0.0,
                'recent_form_tiebreaks': 'No recent matches',
                'analysis': 'No match data available'
            }
        
        # Analyze tiebreak performance (simplified - would need detailed match data)
        # For now, we'll simulate tiebreak analysis based on set scores
        tiebreak_wins = 0
        tiebreak_losses = 0
        close_set_performance = []
        
        for match in matches:
            score = match['score']
            home_sets = score['home_sets']
            away_sets = score['away_sets']
            
            # Identify close matches (could indicate tiebreaks)
            if abs(home_sets - away_sets) <= 1 and (home_sets + away_sets) >= 2:
                close_set_performance.append({
                    'opponent': match['opponent'],
                    'result': 'win' if home_sets > away_sets else 'loss',
                    'close_match': True
                })
                
                if home_sets > away_sets:
                    tiebreak_wins += 1
                else:
                    tiebreak_losses += 1
        
        total_tiebreaks = tiebreak_wins + tiebreak_losses
        tiebreak_win_rate = (tiebreak_wins / total_tiebreaks) if total_tiebreaks > 0 else 0.0
        
        return {
            'player_name': player_name,
            'player_id': player_info['id'],
            'country': player_info['country'],
            'recent_matches': len(matches),
            'tiebreak_record': f"{tiebreak_wins}-{tiebreak_losses}",
            'tiebreak_win_rate': tiebreak_win_rate,
            'close_matches': len(close_set_performance),
            'recent_form_tiebreaks': 'Strong' if tiebreak_win_rate > 0.6 else 'Weak' if tiebreak_win_rate < 0.4 else 'Average',
            'analysis': f"Won {tiebreak_wins}/{total_tiebreaks} close matches ({tiebreak_win_rate:.1%})"
        }
    
    async def revalidate_match(self, losing_bet: Dict) -> Dict:
        """Revalidate a losing bet incorporating tiebreak performance."""
        match = losing_bet['match']
        players = match.split(' vs ')
        
        if len(players) != 2:
            return {
                'original_bet': losing_bet,
                'tiebreak_analysis': 'Could not parse match',
                'recommendation': 'No change'
            }
        
        player1_name = players[0].strip()
        player2_name = players[1].strip()
        bet_on = losing_bet['bet_on']
        
        print(f"\n🔍 Revalidating: {match}")
        print(f"   💰 Original bet: {bet_on} (≥1 set) - {losing_bet['confidence']:.1f}% confidence")
        
        # Analyze both players
        player1_tb = await self.analyze_tiebreak_performance(player1_name)
        await asyncio.sleep(1)  # Rate limiting
        player2_tb = await self.analyze_tiebreak_performance(player2_name)
        
        # Determine if tiebreak data would change the prediction
        original_favorite = bet_on
        
        # Simple tiebreak-based prediction logic
        player1_tb_rate = player1_tb.get('tiebreak_win_rate', 0.0)
        player2_tb_rate = player2_tb.get('tiebreak_win_rate', 0.0)
        
        if player1_tb_rate > player2_tb_rate + 0.2:  # Significant tiebreak advantage
            tiebreak_favorite = player1_name
            confidence_modifier = "Higher"
        elif player2_tb_rate > player1_tb_rate + 0.2:
            tiebreak_favorite = player2_name 
            confidence_modifier = "Higher"
        else:
            tiebreak_favorite = original_favorite
            confidence_modifier = "Similar"
        
        recommendation = "No change"
        if tiebreak_favorite != original_favorite:
            recommendation = f"Switch bet to {tiebreak_favorite}"
        elif original_favorite == bet_on and confidence_modifier == "Higher":
            recommendation = f"Increase confidence in {original_favorite}"
        elif original_favorite == bet_on and confidence_modifier == "Lower":  
            recommendation = f"Decrease confidence in {original_favorite}"
        
        return {
            'match': match,
            'original_bet': losing_bet,
            'player1_tiebreak': player1_tb,
            'player2_tiebreak': player2_tb,
            'tiebreak_favorite': tiebreak_favorite,
            'confidence_modifier': confidence_modifier,
            'recommendation': recommendation
        }

async def main():
    """Main analysis function."""
    print("🎾 TIEBREAK REVALIDATION ANALYSIS")
    print("=" * 60)
    print(f"📊 Analyzing {len(LOSING_BETS)} losing bets for tiebreak performance impact...")
    
    results = []
    
    async with TiebreakAnalyzer() as analyzer:
        for i, bet in enumerate(LOSING_BETS):
            print(f"\n⏳ [{i+1}/{len(LOSING_BETS)}] Processing...")
            result = await analyzer.revalidate_match(bet)
            results.append(result)
            
            # Rate limiting
            await asyncio.sleep(2)
    
    # Summarize results
    print("\n" + "=" * 60)
    print("🎯 TIEBREAK REVALIDATION SUMMARY")
    print("=" * 60)
    
    changes_recommended = 0
    confidence_boosts = 0
    
    for result in results:
        print(f"\n📊 {result['match']}")
        print(f"   💰 Original: {result['original_bet']['bet_on']} ({result['original_bet']['confidence']:.1f}%)")
        print(f"   🎯 Tiebreak Analysis: {result['recommendation']}")
        
        if "Switch bet" in result['recommendation']:
            changes_recommended += 1
        elif "Increase confidence" in result['recommendation']:
            confidence_boosts += 1
    
    print(f"\n📈 POTENTIAL IMPROVEMENTS:")
    print(f"   🔄 Bet changes recommended: {changes_recommended}/{len(LOSING_BETS)}")
    print(f"   ⬆️  Confidence boosts: {confidence_boosts}/{len(LOSING_BETS)}")
    print(f"   📊 Potential improvement rate: {(changes_recommended + confidence_boosts)/len(LOSING_BETS):.1%}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"logs/tiebreak_revalidation_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
