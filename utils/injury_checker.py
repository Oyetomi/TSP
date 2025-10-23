"""
Injury/Retirement Checker
Fetches recent injuries and retirements from TennisExplorer to filter out risky matches
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Set
import re

class InjuryChecker:
    """Check for recently injured or retired players"""
    
    INJURY_URL = "https://www.tennisexplorer.com/list-players/injured/"
    
    def __init__(self, days_back: int = 3):
        """
        Initialize injury checker
        
        Args:
            days_back: How many days back to check for injuries (default: 3)
        """
        self.days_back = days_back
        self.injured_players: Set[str] = set()
        self.injury_details: List[Dict] = []
        
    def fetch_injured_players(self) -> bool:
        """
        Fetch list of recently injured/retired players
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.get(self.INJURY_URL, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the injury table
            table = soup.find('table', class_='injured')
            if not table:
                print("⚠️  Could not find injury table")
                return False
            
            # Parse table rows
            rows = table.find('tbody').find_all('tr')
            cutoff_date = datetime.now() - timedelta(days=self.days_back)
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue
                
                # Extract date
                date_str = cells[0].text.strip()
                try:
                    injury_date = datetime.strptime(date_str, '%d.%m.%Y')
                    if injury_date < cutoff_date:
                        continue  # Skip old injuries
                except:
                    continue
                
                # Extract player name
                player_link = cells[1].find('a')
                if player_link:
                    player_name = player_link.text.strip()
                    
                    # Extract tournament
                    tournament_link = cells[2].find('a')
                    tournament = tournament_link.text.strip() if tournament_link else "Unknown"
                    
                    # Extract reason
                    reason = cells[3].text.strip()
                    
                    # Add to set (normalize name)
                    normalized_name = self._normalize_name(player_name)
                    self.injured_players.add(normalized_name)
                    
                    # Store details
                    self.injury_details.append({
                        'date': date_str,
                        'name': player_name,
                        'normalized_name': normalized_name,
                        'tournament': tournament,
                        'reason': reason
                    })
            
            print(f"✅ Found {len(self.injured_players)} recently injured/retired players")
            return True
            
        except Exception as e:
            print(f"❌ Error fetching injury data: {e}")
            return False
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize player name for comparison
        
        Args:
            name: Player name (e.g., "Shimabukuro S.")
        
        Returns:
            Normalized name (e.g., "shimabukuro")
        """
        # Remove initials and dots
        name = re.sub(r'\s+[A-Z]\.', '', name)
        # Remove extra spaces and convert to lowercase
        name = name.strip().lower()
        return name
    
    def is_player_injured(self, player_name: str) -> bool:
        """
        Check if a player is on the injury list
        
        Args:
            player_name: Full player name to check
        
        Returns:
            True if player is injured/retired recently
        """
        if not self.injured_players:
            return False
        
        normalized = self._normalize_name(player_name)
        
        # Check exact match
        if normalized in self.injured_players:
            return True
        
        # Check if last name matches (for different name formats)
        # Handle both "Shimabukuro S." and "Shimabukuro Sho" formats
        last_name = normalized.split()[0] if ' ' in normalized else normalized
        
        for injured in self.injured_players:
            injured_last = injured.split()[0] if ' ' in injured else injured
            
            # Match on last name if it's longer than 4 chars
            if last_name == injured_last and len(last_name) > 4:
                return True
        
        return False
    
    def get_injury_info(self, player_name: str) -> Dict:
        """
        Get injury details for a player
        
        Args:
            player_name: Player name to look up
        
        Returns:
            Dictionary with injury details or empty dict
        """
        normalized = self._normalize_name(player_name)
        
        for detail in self.injury_details:
            if detail['normalized_name'] == normalized:
                return detail
        
        return {}
    
    def print_injury_list(self):
        """Print all recently injured players"""
        if not self.injury_details:
            print("No injured players found")
            return
        
        print(f"\n🏥 Recently Injured/Retired Players (last {self.days_back} days):")
        print("=" * 80)
        for detail in self.injury_details:
            print(f"  🚑 {detail['name']:20s} | {detail['date']} | {detail['reason']:10s} | {detail['tournament']}")
        print("=" * 80)


def check_match_for_injuries(player1_name: str, player2_name: str, checker: InjuryChecker = None) -> tuple:
    """
    Check if either player in a match is injured
    
    Args:
        player1_name: First player's name
        player2_name: Second player's name
        checker: InjuryChecker instance (will create new if None)
    
    Returns:
        Tuple of (should_skip: bool, reason: str)
    """
    if checker is None:
        checker = InjuryChecker()
        checker.fetch_injured_players()
    
    p1_injured = checker.is_player_injured(player1_name)
    p2_injured = checker.is_player_injured(player2_name)
    
    if p1_injured:
        info = checker.get_injury_info(player1_name)
        reason = f"{player1_name} recently {info.get('reason', 'injured')} on {info.get('date', 'recently')}"
        return True, reason
    
    if p2_injured:
        info = checker.get_injury_info(player2_name)
        reason = f"{player2_name} recently {info.get('reason', 'injured')} on {info.get('date', 'recently')}"
        return True, reason
    
    return False, ""


if __name__ == "__main__":
    # Test the injury checker
    checker = InjuryChecker(days_back=3)
    
    if checker.fetch_injured_players():
        checker.print_injury_list()
        
        # Test some players
        test_players = [
            "Shimabukuro Sho",
            "Vondrousova Marketa", 
            "Kubler Jason",
            "Federer Roger",  # Should not be injured
        ]
        
        print("\n🔍 Testing player checks:")
        for player in test_players:
            is_injured = checker.is_player_injured(player)
            status = "🚑 INJURED" if is_injured else "✅ HEALTHY"
            print(f"  {status} - {player}")
            if is_injured:
                info = checker.get_injury_info(player)
                print(f"      Details: {info}")

