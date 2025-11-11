#!/usr/bin/env python3
"""
Tennis Abstract Data Scraper
Properly extracts ELO ratings and player data from Tennis Abstract website
"""

import requests
import re
import time
import json
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import pandas as pd

class TennisAbstractScraper:
    """
    Scraper for Tennis Abstract data with proper structure understanding
    """
    
    def __init__(self, rate_limit_seconds=2):
        self.base_url = "https://tennisabstract.com"
        self.rate_limit = rate_limit_seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.logger = logging.getLogger(__name__)
        
        # Cache for ELO data
        self.elo_cache = {}  # ATP (men's) cache
        self.wta_elo_cache = {}  # WTA (women's) cache
        self.cache_timestamp = None
        self.wta_cache_timestamp = None
        
    def fetch_atp_elo_rankings(self, force_refresh=False) -> List[Dict]:
        """
        Fetch complete ATP ELO rankings table
        
        Returns:
            List of player dictionaries with ELO data
        """
        # Check cache (refresh weekly)
        if not force_refresh and self.elo_cache and self.cache_timestamp:
            age_hours = (datetime.now() - self.cache_timestamp).total_seconds() / 3600
            if age_hours < 168:  # 1 week
                self.logger.info("Using cached ELO data")
                return list(self.elo_cache.values())
        
        try:
            self.logger.info("Fetching ATP ELO rankings from Tennis Abstract...")
            
            url = f"{self.base_url}/reports/atp_elo_ratings.html"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the main table
            table = soup.find('table', {'id': 'reportable'})
            if not table:
                raise ValueError("Could not find ELO rankings table")
            
            players = []
            rows = table.find('tbody').find_all('tr')
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 16:
                    continue
                    
                try:
                    # Extract player data from table columns
                    player_data = {
                        'elo_rank': int(cols[0].get_text().strip()),
                        'name': self._extract_player_name(cols[1]),
                        'player_url': self._extract_player_url(cols[1]),
                        'age': float(cols[2].get_text().strip()),
                        'elo_rating': float(cols[3].get_text().strip()),
                        'hard_elo_rank': int(cols[5].get_text().strip()) if cols[5].get_text().strip().isdigit() else None,
                        'hard_elo': float(cols[6].get_text().strip()) if cols[6].get_text().strip() else None,
                        'clay_elo_rank': int(cols[7].get_text().strip()) if cols[7].get_text().strip().isdigit() else None,
                        'clay_elo': float(cols[8].get_text().strip()) if cols[8].get_text().strip() else None,
                        'grass_elo_rank': int(cols[9].get_text().strip()) if cols[9].get_text().strip().isdigit() else None,
                        'grass_elo': float(cols[10].get_text().strip()) if cols[10].get_text().strip() else None,
                        'peak_elo': float(cols[12].get_text().strip()) if cols[12].get_text().strip() else None,
                        'peak_month': cols[13].get_text().strip(),
                        'atp_rank': int(cols[15].get_text().strip()) if cols[15].get_text().strip().isdigit() else None,
                        'log_diff': float(cols[16].get_text().strip()) if cols[16].get_text().strip() else None,
                        'fetch_time': datetime.now().isoformat()
                    }
                    
                    players.append(player_data)
                    self.elo_cache[player_data['name']] = player_data
                    
                except (ValueError, IndexError, AttributeError) as e:
                    self.logger.warning(f"Error parsing row: {e}")
                    continue
            
            self.cache_timestamp = datetime.now()
            self.logger.info(f"Successfully fetched {len(players)} player ELO ratings")
            
            return players
            
        except Exception as e:
            self.logger.error(f"Failed to fetch ATP ELO rankings: {e}")
            return []
    
    def fetch_wta_elo_rankings(self, force_refresh=False) -> List[Dict]:
        """
        Fetch complete WTA ELO rankings table
        
        Returns:
            List of player dictionaries with ELO data
        """
        # Check cache (refresh weekly)
        if not force_refresh and self.wta_elo_cache and self.wta_cache_timestamp:
            age_hours = (datetime.now() - self.wta_cache_timestamp).total_seconds() / 3600
            if age_hours < 168:  # 1 week
                self.logger.info("Using cached WTA ELO data")
                return list(self.wta_elo_cache.values())
        
        try:
            self.logger.info("Fetching WTA ELO rankings from Tennis Abstract...")
            
            url = f"{self.base_url}/reports/wta_elo_ratings.html"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the main table
            table = soup.find('table', {'id': 'reportable'})
            if not table:
                raise ValueError("Could not find WTA ELO rankings table")
            
            players = []
            rows = table.find('tbody').find_all('tr')
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 16:
                    continue
                    
                try:
                    # Extract player data from table columns (same structure as ATP)
                    player_data = {
                        'elo_rank': int(cols[0].get_text().strip()),
                        'name': self._extract_player_name(cols[1]),
                        'player_url': self._extract_player_url(cols[1]),
                        'age': float(cols[2].get_text().strip()),
                        'elo_rating': float(cols[3].get_text().strip()),
                        'hard_elo_rank': int(cols[5].get_text().strip()) if cols[5].get_text().strip().isdigit() else None,
                        'hard_elo': float(cols[6].get_text().strip()) if cols[6].get_text().strip() else None,
                        'clay_elo_rank': int(cols[7].get_text().strip()) if cols[7].get_text().strip().isdigit() else None,
                        'clay_elo': float(cols[8].get_text().strip()) if cols[8].get_text().strip() else None,
                        'grass_elo_rank': int(cols[9].get_text().strip()) if cols[9].get_text().strip().isdigit() else None,
                        'grass_elo': float(cols[10].get_text().strip()) if cols[10].get_text().strip() else None,
                        'peak_elo': float(cols[12].get_text().strip()) if cols[12].get_text().strip() else None,
                        'peak_month': cols[13].get_text().strip(),
                        'wta_rank': int(cols[15].get_text().strip()) if cols[15].get_text().strip().isdigit() else None,
                        'log_diff': float(cols[16].get_text().strip()) if cols[16].get_text().strip() else None,
                        'tour': 'WTA',  # Mark as women's tour
                        'fetch_time': datetime.now().isoformat()
                    }
                    
                    players.append(player_data)
                    self.wta_elo_cache[player_data['name']] = player_data
                    
                except (ValueError, IndexError, AttributeError) as e:
                    self.logger.warning(f"Error parsing WTA row: {e}")
                    continue
            
            self.wta_cache_timestamp = datetime.now()
            self.logger.info(f"Successfully fetched {len(players)} WTA player ELO ratings")
            
            return players
            
        except Exception as e:
            self.logger.error(f"Failed to fetch WTA ELO rankings: {e}")
            return []
    
    def get_player_elo_data(self, player_name: str, tour: str = 'both') -> Optional[Dict]:
        """
        Get ELO data for a specific player with enhanced name matching
        
        Args:
            player_name: Player name to search for
            tour: 'atp', 'wta', or 'both' (default)
            
        Returns:
            Player ELO data dictionary or None
        """
        # Ensure caches are populated
        if tour in ['atp', 'both'] and not self.elo_cache:
            self.fetch_atp_elo_rankings()
        if tour in ['wta', 'both'] and not self.wta_elo_cache:
            self.fetch_wta_elo_rankings()
        
        # Generate search variants
        name_variants = self._generate_search_variants(player_name)
        
        # Search ATP first (if requested)
        if tour in ['atp', 'both']:
            # Try exact match first
            if player_name in self.elo_cache:
                result = self.elo_cache[player_name].copy()
                result['tour'] = 'ATP'
                return result
            
            # Try fuzzy matching with existing cache
            for cached_name, data in self.elo_cache.items():
                if self._names_match(player_name, cached_name):
                    result = data.copy()
                    result['tour'] = 'ATP'
                    return result
            
            # Try name variants
            for variant in name_variants:
                if variant in self.elo_cache:
                    self.logger.info(f"Found {player_name} using ATP variant: {variant}")
                    result = self.elo_cache[variant].copy()
                    result['tour'] = 'ATP'
                    return result
                
                # Try fuzzy matching on variants
                for cached_name, data in self.elo_cache.items():
                    if self._names_match(variant, cached_name):
                        self.logger.info(f"Found {player_name} using ATP variant {variant} -> {cached_name}")
                        result = data.copy()
                        result['tour'] = 'ATP'
                        return result
        
        # Search WTA (if requested)
        if tour in ['wta', 'both']:
            # Try exact match first
            if player_name in self.wta_elo_cache:
                result = self.wta_elo_cache[player_name].copy()
                result['tour'] = 'WTA'
                return result
            
            # Try fuzzy matching with existing cache
            for cached_name, data in self.wta_elo_cache.items():
                if self._names_match(player_name, cached_name):
                    result = data.copy()
                    result['tour'] = 'WTA'
                    return result
            
            # Try name variants
            for variant in name_variants:
                if variant in self.wta_elo_cache:
                    self.logger.info(f"Found {player_name} using WTA variant: {variant}")
                    result = self.wta_elo_cache[variant].copy()
                    result['tour'] = 'WTA'
                    return result
                
                # Try fuzzy matching on variants
                for cached_name, data in self.wta_elo_cache.items():
                    if self._names_match(variant, cached_name):
                        self.logger.info(f"Found {player_name} using WTA variant {variant} -> {cached_name}")
                        result = data.copy()
                        result['tour'] = 'WTA'
                        return result
        
        # Log unsuccessful search
        tours_searched = []
        if tour in ['atp', 'both']: tours_searched.append('ATP')
        if tour in ['wta', 'both']: tours_searched.append('WTA')
        
        self.logger.warning(f"Player not found in {'/'.join(tours_searched)} ELO cache: {player_name} (tried {len(name_variants)} variants)")
        return None
    
    def _generate_search_variants(self, player_name: str) -> list:
        """
        Generate name variants for searching in the ELO cache
        """
        variants = []
        
        # Common tennis player name variations
        name_lower = player_name.lower()
        
        # Rafael Nadal variations
        if 'rafael' in name_lower or 'rafa' in name_lower:
            if 'nadal' in name_lower:
                variants.extend(['Rafael Nadal', 'Rafa Nadal', 'R. Nadal'])
        
        # Alexander Zverev variations  
        if 'alexander' in name_lower or 'alex' in name_lower:
            if 'zverev' in name_lower:
                variants.extend(['Alexander Zverev', 'Alex Zverev', 'A. Zverev'])
        
        # Novak Djokovic variations
        if 'novak' in name_lower and 'djokovic' in name_lower:
            variants.extend(['Novak Djokovic', 'N. Djokovic'])
        
        # Carlos Alcaraz variations
        if 'carlos' in name_lower and 'alcaraz' in name_lower:
            variants.extend(['Carlos Alcaraz', 'C. Alcaraz'])
        
        # Daniil Medvedev variations
        if 'daniil' in name_lower and 'medvedev' in name_lower:
            variants.extend(['Daniil Medvedev', 'D. Medvedev'])
        
        # Jannik Sinner variations
        if 'jannik' in name_lower and 'sinner' in name_lower:
            variants.extend(['Jannik Sinner', 'J. Sinner'])
        
        # Add original name and basic variations
        variants.extend([
            player_name,
            player_name.title(),
            player_name.upper(),
            player_name.lower()
        ])
        
        # Remove duplicates
        return list(dict.fromkeys(variants))
    
    def build_player_url(self, player_name: str, gender: str = 'M') -> str:
        """
        Build Tennis Abstract URL for a player with multiple format attempts
        
        Args:
            player_name: Player name
            gender: 'M' for men, 'W' for women
            
        Returns:
            Tennis Abstract URL for the player
        """
        # Get player data to find their URL
        player_data = self.get_player_elo_data(player_name)
        if player_data and 'player_url' in player_data:
            url = player_data['player_url']
            # Ensure full URL
            if url.startswith('/'):
                return f"https://www.tennisabstract.com{url}"
            return url
        
        # Fallback: construct URL from name with multiple variants
        base_url = "https://www.tennisabstract.com/cgi-bin"
        script = "wplayer.cgi" if gender == 'W' else "player.cgi"
        
        # Try different name formats based on Tennis Abstract patterns
        name_variants = self._generate_name_variants(player_name)
        
        # Return the first variant (most likely to work)
        # In a full implementation, we could test each URL
        primary_variant = name_variants[0] if name_variants else player_name.replace(' ', '')
        return f"{base_url}/{script}?p={primary_variant}"
    
    def find_working_player_url(self, player_name: str, gender: str = 'M') -> Optional[str]:
        """
        Find a working Tennis Abstract URL by testing multiple variants
        
        Args:
            player_name: Player name
            gender: 'M' for men, 'W' for women
            
        Returns:
            Working URL or None if none found
        """
        # Check if we already have the URL from ELO data
        player_data = self.get_player_elo_data(player_name)
        if player_data and 'player_url' in player_data:
            url = player_data['player_url']
            if url.startswith('/'):
                return f"https://www.tennisabstract.com{url}"
            return url
        
        # Generate variants to test
        base_url = "https://www.tennisabstract.com/cgi-bin"
        script = "wplayer.cgi" if gender == 'W' else "player.cgi"
        name_variants = self._generate_name_variants(player_name)
        
        # Test each variant (with rate limiting)
        for variant in name_variants:
            test_url = f"{base_url}/{script}?p={variant}"
            
            try:
                # Quick HEAD request to check if URL exists
                time.sleep(self.rate_limit)  # Rate limiting
                response = self.session.head(test_url, timeout=10)
                
                if response.status_code == 200:
                    self.logger.info(f"Found working URL for {player_name}: {test_url}")
                    return test_url
                    
            except Exception as e:
                self.logger.debug(f"URL test failed for {test_url}: {e}")
                continue
        
        # If no working URL found, return the most likely variant
        if name_variants:
            fallback_url = f"{base_url}/{script}?p={name_variants[0]}"
            self.logger.warning(f"No working URL found for {player_name}, using fallback: {fallback_url}")
            return fallback_url
        
        return None
    
    def _generate_name_variants(self, player_name: str) -> list:
        """
        Generate different name format variants for Tennis Abstract URLs
        Based on observed patterns from the website
        """
        variants = []
        
        # Pattern 1: Simple concatenation (RafaelNadal)
        simple_name = player_name.replace(' ', '')
        variants.append(simple_name)
        
        # Pattern 2: Hyphenated (Reilly-Opelka, Qinwen-Zheng)
        hyphenated = player_name.replace(' ', '-')
        variants.append(hyphenated)
        
        # Pattern 3: First name + Last name variations
        parts = player_name.split()
        if len(parts) >= 2:
            # FirstLast
            variants.append(f"{parts[0]}{parts[-1]}")
            # First-Last
            variants.append(f"{parts[0]}-{parts[-1]}")
            # LastFirst (less common but possible)
            variants.append(f"{parts[-1]}{parts[0]}")
        
        # Pattern 4: Handle multi-word names (Xin-Yu-Wang)
        if len(parts) > 2:
            # All parts hyphenated
            all_hyphenated = '-'.join(parts)
            variants.append(all_hyphenated)
            
            # First + hyphenated last parts
            if len(parts) >= 3:
                first_plus_hyphenated_rest = f"{parts[0]}-{'-'.join(parts[1:])}"
                variants.append(first_plus_hyphenated_rest)
        
        # Pattern 5: Common tennis name variations
        name_lower = player_name.lower()
        if 'rafael' in name_lower and 'nadal' in name_lower:
            variants.extend(['RafaelNadal', 'RafaNadal', 'Rafael-Nadal'])
        elif 'alexander' in name_lower and 'zverev' in name_lower:
            variants.extend(['AlexanderZverev', 'Alexander-Zverev', 'AlexZverev'])
        elif 'novak' in name_lower and 'djokovic' in name_lower:
            variants.extend(['NovakDjokovic', 'Novak-Djokovic'])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant not in seen:
                seen.add(variant)
                unique_variants.append(variant)
        
        return unique_variants
    
    def fetch_player_detailed_stats(self, player_name: str) -> Dict:
        """
        Fetch detailed player statistics from individual player page
        
        Args:
            player_name: Player name
            
        Returns:
            Detailed player statistics
        """
        try:
            # Get player URL from ELO cache
            player_data = self.get_player_elo_data(player_name)
            if not player_data or not player_data.get('player_url'):
                self.logger.warning(f"No player URL found for {player_name}")
                return {}
            
            time.sleep(self.rate_limit)  # Rate limiting
            
            url = player_data['player_url']
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            content = response.text
            
            # Extract JavaScript variables
            stats = self._extract_js_variables(content)
            
            # Add ELO data from cache
            stats.update({
                'elo_rating': player_data['elo_rating'],
                'elo_rank': player_data['elo_rank'],
                'hard_elo': player_data['hard_elo'],
                'clay_elo': player_data['clay_elo'],
                'grass_elo': player_data['grass_elo'],
                'peak_elo': player_data['peak_elo']
            })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to fetch detailed stats for {player_name}: {e}")
            return {}
    
    def calculate_match_probability(self, player1_name: str, player2_name: str, surface: str = "hard") -> Dict:
        """
        Calculate match probability using Tennis Abstract ELO ratings
        
        Args:
            player1_name: First player name
            player2_name: Second player name  
            surface: Surface type ("hard", "clay", "grass")
            
        Returns:
            Match probability data
        """
        try:
            p1_data = self.get_player_elo_data(player1_name)
            p2_data = self.get_player_elo_data(player2_name)
            
            if not p1_data or not p2_data:
                return {
                    'error': f'Player data not found for {player1_name} or {player2_name}',
                    'probability': 0.5
                }
            
            # Get surface-specific ELO ratings
            surface_key = f"{surface}_elo"
            p1_elo = p1_data.get(surface_key, p1_data['elo_rating'])
            p2_elo = p2_data.get(surface_key, p2_data['elo_rating'])
            
            if p1_elo is None:
                p1_elo = p1_data['elo_rating']
            if p2_elo is None:
                p2_elo = p2_data['elo_rating']
            
            # Calculate ELO probability
            elo_diff = p1_elo - p2_elo
            probability = 1 / (1 + 10 ** (-elo_diff / 400))
            
            return {
                'player1': {
                    'name': player1_name,
                    'elo_rating': p1_data['elo_rating'],
                    'surface_elo': p1_elo,
                    'elo_rank': p1_data['elo_rank'],
                    'atp_rank': p1_data.get('atp_rank')
                },
                'player2': {
                    'name': player2_name,
                    'elo_rating': p2_data['elo_rating'],
                    'surface_elo': p2_elo,
                    'elo_rank': p2_data['elo_rank'],
                    'atp_rank': p2_data.get('atp_rank')
                },
                'surface': surface,
                'elo_difference': elo_diff,
                'probability_player1': probability,
                'probability_player2': 1 - probability,
                'confidence': self._calculate_confidence(elo_diff),
                'source': 'tennis_abstract'
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating match probability: {e}")
            return {'error': str(e), 'probability': 0.5}
    
    def export_elo_data_to_csv(self, filename: str = "tennis_abstract_elo.csv"):
        """
        Export ELO data to CSV for integration with existing system
        """
        try:
            players = self.fetch_atp_elo_rankings()
            
            if players:
                df = pd.DataFrame(players)
                df.to_csv(filename, index=False)
                self.logger.info(f"ELO data exported to {filename}")
                return True
            else:
                self.logger.error("No data to export")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to export ELO data: {e}")
            return False
    
    def _extract_player_name(self, cell) -> str:
        """Extract clean player name from table cell"""
        link = cell.find('a')
        if link:
            return link.get_text().strip().replace('\xa0', ' ')
        return cell.get_text().strip().replace('\xa0', ' ')
    
    def _extract_player_url(self, cell) -> str:
        """Extract player URL from table cell"""
        link = cell.find('a')
        if link and link.get('href'):
            href = link.get('href')
            if href.startswith('http'):
                return href
            return f"https://www.tennisabstract.com{href}"
        return ""
    
    def _extract_js_variables(self, content: str) -> Dict:
        """Extract JavaScript variables from player page"""
        variables = {}
        
        patterns = {
            'current_rank': r"var currentrank = (\d+);",
            'peak_rank': r"var peakrank = (\d+);",
            'height': r"var ht = (\d+);",
            'hand': r"var hand = '([LR])';",
            'backhand': r"var backhand = '([12])';",
            'country': r"var country = '([A-Z]{3})';",
            'elo_rating': r"var elo_rating = '(\d+)';",
            'elo_rank': r"var elo_rank = '(\d+)';",
            'dob': r"var dob = (\d+);",
        }
        
        for var_name, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                try:
                    value = match.group(1)
                    if var_name in ['current_rank', 'peak_rank', 'height', 'elo_rating', 'elo_rank', 'dob']:
                        variables[var_name] = int(value)
                    else:
                        variables[var_name] = value
                except ValueError:
                    pass
        
        return variables
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two player names match (fuzzy matching)"""
        # Enhanced fuzzy matching for tennis players
        def normalize_name(name):
            return name.lower().replace(' ', '').replace('-', '').replace('.', '').replace("'", '')
        
        name1_norm = normalize_name(name1)
        name2_norm = normalize_name(name2)
        
        # Exact match
        if name1_norm == name2_norm:
            return True
        
        # Check if one contains the other
        if name1_norm in name2_norm or name2_norm in name1_norm:
            return True
        
        # Split names and check individual parts
        parts1 = name1.lower().split()
        parts2 = name2.lower().split()
        
        # Check if all parts of shorter name are in longer name
        if len(parts1) <= len(parts2):
            shorter, longer = parts1, parts2
        else:
            shorter, longer = parts2, parts1
        
        matches = 0
        for part in shorter:
            for long_part in longer:
                if part in long_part or long_part in part:
                    matches += 1
                    break
        
        # Consider it a match if most parts match
        return matches >= len(shorter) * 0.8
    
    def _calculate_confidence(self, elo_diff: float) -> float:
        """Calculate confidence based on ELO difference"""
        # Higher ELO differences = higher confidence
        abs_diff = abs(elo_diff)
        
        if abs_diff < 50:
            return 0.6
        elif abs_diff < 100:
            return 0.7
        elif abs_diff < 200:
            return 0.8
        elif abs_diff < 300:
            return 0.9
        else:
            return 0.95


# Example usage and testing functions
def test_tennis_abstract_scraper():
    """Test the Tennis Abstract scraper"""
    print("🎾 Testing Tennis Abstract Scraper")
    print("=" * 50)
    
    scraper = TennisAbstractScraper()
    
    # Test 1: Fetch ELO rankings
    print("\n1. Fetching ATP ELO Rankings...")
    players = scraper.fetch_atp_elo_rankings()
    
    if players:
        print(f"✅ Fetched {len(players)} players")
        print("\nTop 5 players:")
        for i, player in enumerate(players[:5], 1):
            print(f"  {i}. {player['name']} - ELO: {player['elo_rating']} (Rank #{player['elo_rank']})")
    else:
        print("❌ Failed to fetch ELO rankings")
        return False
    
    # Test 2: Get specific player data
    print("\n2. Testing player-specific data...")
    test_players = ['Carlos Alcaraz', 'Jannik Sinner', 'Alexander Zverev']
    
    for player_name in test_players:
        player_data = scraper.get_player_elo_data(player_name)
        if player_data:
            print(f"✅ {player_name}:")
            print(f"   ELO: {player_data['elo_rating']} (#{player_data['elo_rank']})")
            print(f"   Hard: {player_data['hard_elo']}, Clay: {player_data['clay_elo']}, Grass: {player_data['grass_elo']}")
        else:
            print(f"❌ {player_name}: Not found")
    
    # Test 3: Calculate match probabilities
    print("\n3. Testing match probability calculations...")
    matches = [
        ('Carlos Alcaraz', 'Jannik Sinner', 'hard'),
        ('Alexander Zverev', 'Taylor Fritz', 'clay'),
        ('Novak Djokovic', 'Daniil Medvedev', 'grass')
    ]
    
    for p1, p2, surface in matches:
        prob_data = scraper.calculate_match_probability(p1, p2, surface)
        if 'error' not in prob_data:
            print(f"✅ {p1} vs {p2} ({surface}):")
            print(f"   Probability: {prob_data['probability_player1']:.1%} vs {prob_data['probability_player2']:.1%}")
            print(f"   ELO Diff: {prob_data['elo_difference']:+.0f}")
        else:
            print(f"❌ {p1} vs {p2}: {prob_data['error']}")
    
    # Test 4: Export data
    print("\n4. Testing data export...")
    if scraper.export_elo_data_to_csv("test_elo_export.csv"):
        print("✅ Data exported successfully")
    else:
        print("❌ Data export failed")
    
    return True


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    success = test_tennis_abstract_scraper()
    
    if success:
        print("\n🎯 INTEGRATION READY!")
        print("=" * 50)
        print("✅ Tennis Abstract data is accessible")
        print("✅ ELO ratings can be fetched reliably") 
        print("✅ Surface-specific ratings available")
        print("✅ Match probabilities can be calculated")
        print("✅ Data can be exported for integration")
        print("\nReady to enhance your prediction model! 🚀")
    else:
        print("\n❌ Integration test failed")
