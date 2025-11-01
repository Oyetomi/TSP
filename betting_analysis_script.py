"""
Comprehensive Tennis Betting Analysis Script

This script:
1. Fetches scheduled tennis events
2. Analyzes each match for set prediction
3. Filters matches available in bookmaker
4. Writes detailed CSV with predictions and reasoning
5. Uses weighted scoring system for set predictions
"""

import csv
import json
from curl_cffi import requests as curl_requests
from curl_cffi.requests import BrowserType
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from rapidfuzz import fuzz, process
import Levenshtein
import logging
import os
import concurrent.futures
import threading
import signal

# Import our services
from app.services.match_data_provider import MatchDataProvider as MatchDataProviderService
from app.services.player_analysis_service import PlayerAnalysisService
from app.services.mental_toughness_service import MentalToughnessService
from app.services.mental_toughness_logger import get_mental_logger
from enhanced_statistics_handler import EnhancedStatisticsHandler
from prediction_config import config as prediction_config
from weight_config_manager import config_manager, get_current_weights
from skip_logger import SkipLogger
from utils.injury_checker import InjuryChecker

@dataclass
class BookmakerMatch:
    """Bookmaker match information with both +1.5 and +2.5 sets markets"""
    event_id: str
    player1: str
    player2: str
    odds_player1_1_5: float  # Player 1 +1.5 sets odds
    odds_player2_1_5: float  # Player 2 +1.5 sets odds
    odds_player1_2_5: Optional[float] = None  # Player 1 +2.5 sets odds (for best-of-5)
    odds_player2_2_5: Optional[float] = None  # Player 2 +2.5 sets odds (for best-of-5)
    
    # Total Games Over/Under markets
    total_games_lines: Dict[str, Dict[str, float]] = None  # {'20.5': {'over': 1.85, 'under': 1.95}, '21.5': {...}}
    
    available: bool = True

@dataclass
class MatchFormat:
    """Match format information for set betting analysis"""
    is_best_of_five: bool
    tournament_name: str
    category: str  # ATP, WTA, etc.
    tournament_level: str  # Grand Slam, Masters 1000, etc.
    gender: str  # Male, Female, Mixed

@dataclass
class PlayerProfile:
    """Enhanced player profile for betting analysis"""
    id: int
    name: str
    age: Optional[int]
    gender: str
    country: str
    atp_ranking: Optional[int]
    wta_ranking: Optional[int]
    utr_rating: Optional[float]  # UTR rating (e.g., 14.6)
    utr_position: Optional[int]  # UTR ranking position
    utr_verified: Optional[bool] # Whether UTR is verified
    recent_form_score: float
    surface_win_rate: float
    head_to_head_record: Dict[str, int]
    clutch_performance: float
    injury_status: str
    momentum_score: float
    data_quality_issues: List[str] = None  # Track when player has insufficient data

@dataclass
class SetPrediction:
    """Comprehensive set prediction with reasoning and enhanced betting options"""
    predicted_winner: str
    confidence_level: str
    predicted_score: str
    win_probability: float
    key_factors: List[str]
    weight_breakdown: Dict[str, float]
    reasoning: str
    player1_probability: float = 0.0  # Individual probability for player1
    player2_probability: float = 0.0  # Individual probability for player2
    over_2_5_sets_probability: float = 0.0  # Probability match goes over 2.5 sets (to 3 sets)
    
    # Total Games prediction
    expected_total_games: float = 0.0  # Expected total games in match
    over_20_5_games_prob: float = 0.0  # Probability of Over 20.5 games
    over_21_5_games_prob: float = 0.0  # Probability of Over 21.5 games
    over_22_5_games_prob: float = 0.0  # Probability of Over 22.5 games (most common)
    over_23_5_games_prob: float = 0.0  # Probability of Over 23.5 games
    
    # Enhanced betting recommendations
    betting_type: str = "SETS"  # "SETS" or "GAMES" 
    game_handicap_recommendation: Optional[Dict[str, Any]] = None
    alternative_markets: List[Dict[str, Any]] = None
    market_selection_reason: str = ""
    
    # Skip signal (for low confidence/coin flip matches)
    should_skip: bool = False
    skip_reason: str = ""

# Import API secrets (keep endpoints and headers private)
try:
    from api_secrets import ODDS_PROVIDER_CONFIG, ODDS_PROVIDER_CONFIG  # ODDS_PROVIDER_CONFIG is alias
except ImportError:
    print("⚠️  WARNING: api_secrets.py not found! Using default odds provider configuration.")
    ODDS_PROVIDER_CONFIG = {
        'base_url': 'https://api.example.com/v1',
        'user_id': 'YOUR_USER_ID',
        'headers': {},
        'cookies': {}
    }
    ODDS_PROVIDER_CONFIG = ODDS_PROVIDER_CONFIG  # Fallback alias


class OddsProvider:
    """Betting odds provider API interface"""
    
    def __init__(self, user_id: str = None, access_token: str = None):
        # Use provided user_id or fall back to config
        self.user_id = user_id or ODDS_PROVIDER_CONFIG.get('user_id')
        self.access_token = access_token or ODDS_PROVIDER_CONFIG.get('access_token')
        self.base_url = ODDS_PROVIDER_CONFIG.get('base_url')
        
        # Get headers from config
        self.headers = ODDS_PROVIDER_CONFIG.get('headers', {}).copy()
        
        # Get cookies from config (merge with runtime values)
        self.cookies = ODDS_PROVIDER_CONFIG.get('cookies', {}).copy()
        self.cookies['userId'] = self.user_id
        
        if self.access_token:
            self.cookies['accessToken'] = self.access_token
    
    def get_tennis_markets(self, page_num: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Get tennis matches available for betting from odds provider
        Note: API returns ALL matches regardless of date - filtering happens client-side
        """
        url = f"{self.base_url}/wapConfigurableEventsByOrder"
        
        payload = {
            "productId": 3,
            "sportId": "sr:sport:5",  # Tennis sport ID
            "order": 0,
            "pageNum": page_num,
            "pageSize": page_size,
            "userId": self.user_id,
            "withTwoUpMarket": True,
            "withOneUpMarket": True
        }
        
        try:
            response = curl_requests.post(
                url, 
                json=payload, 
                headers=self.headers,
                cookies=self.cookies,
                impersonate=BrowserType.chrome120,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('bizCode') == 10000:  # Success code based on real response
                tournaments = data.get('data', {}).get('tournaments', [])
                total_events = sum(len(t.get('events', [])) for t in tournaments)
                print(f"📊 Found {total_events} tennis matches in {len(tournaments)} tournaments on Odds Provider")
                return data
            else:
                print(f"⚠️ Odds Provider API returned error: {data.get('message', 'Unknown error')}")
                return {}
            
        except Exception as e:
            print(f"Error fetching odds provider markets: {e}")
            return {}
    
    def get_available_matches(self, target_date: str = None) -> List[BookmakerMatch]:
        """
        Fetch ALL available matches from odds provider and filter client-side by target_date.
        API returns all matches regardless of date - we paginate through everything then filter.
        
        Args:
            target_date: Date string in YYYY-MM-DD format. If None, returns all matches.
        """
        matches = []
        page_num = 1
        page_size = 20
        
        # Parse target date for client-side filtering
        from datetime import datetime
        target_date_obj = None
        if target_date:
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
            print(f"📅 Fetching all matches, will filter for: {target_date}")
        else:
            print(f"📅 Fetching all available matches (no date filter)")
        
        while True:
            print(f"📖 Fetching odds provider page {page_num}...")
            tennis_data = self.get_tennis_markets(page_num=page_num, page_size=page_size)
            
            if not tennis_data:
                break
                
            # Check if there are tournaments on this page
            tournaments = tennis_data.get('data', {}).get('tournaments', [])
            page_matches_count = 0
            
            # Process tournaments on this page (even if empty - API might have more pages)
            for tournament in tournaments:
                tournament_events = tournament.get('events', [])
                
                for event in tournament_events:
                    try:
                        # Extract real match info from actual API structure
                        event_id = event.get('eventId', '')
                        home_team = event.get('homeTeamName', '')
                        away_team = event.get('awayTeamName', '')
                        event_time = event.get('eventTime', 0)  # Timestamp in milliseconds
                        
                        if not home_team or not away_team:
                            continue
                        
                        # Client-side date filtering (if target_date specified)
                        if target_date_obj and event_time:
                            event_datetime = datetime.fromtimestamp(event_time / 1000)
                            event_date = event_datetime.date()
                            if event_date != target_date_obj:
                                continue  # Skip matches not on target date
                        
                        # Skip doubles matches (check for "/" in team names)
                        if '/' in home_team or '/' in away_team:
                            continue
                        
                        # Skip SRL (Simulated Reality League) matches - virtual games
                        if '(Srl)' in home_team or '(Srl)' in away_team:
                            continue
                        
                        # Look for both +1.5 and +2.5 sets markets, AND Total Games markets
                        markets = event.get('markets', [])
                        home_plus_1_5_odds = None
                        away_plus_1_5_odds = None
                        home_plus_2_5_odds = None
                        away_plus_2_5_odds = None
                        total_games_lines = {}
                        
                        for market in markets:
                            market_desc = market.get('desc', '')
                            outcomes = market.get('outcomes', [])
                            
                            # SET HANDICAP MARKETS (+1.5, +2.5 sets)
                            if market_desc.startswith('Set handicap'):
                                for outcome in outcomes:
                                    outcome_desc = outcome.get('desc', '')
                                    odds = float(outcome.get('odds', 0))
                                    
                                    # Check for +1.5 sets markets
                                    if '(+1.5)' in outcome_desc:
                                        if outcome_desc.startswith('Home'):
                                            home_plus_1_5_odds = odds
                                        elif outcome_desc.startswith('Away'):
                                            away_plus_1_5_odds = odds
                                
                                    # Check for +2.5 sets markets (for best-of-5 matches)
                                    elif '(+2.5)' in outcome_desc:
                                        if outcome_desc.startswith('Home'):
                                            home_plus_2_5_odds = odds
                                        elif outcome_desc.startswith('Away'):
                                            away_plus_2_5_odds = odds
                            
                            # TOTAL GAMES O/U MARKETS
                            # Common formats: "Total Games Over/Under", "Games O/U", "Total - Games"
                            elif any(keyword in market_desc.lower() for keyword in ['total games', 'games o/u', 'total - games']):
                                # Parse line (e.g., "20.5", "21.5", "22.5")
                                # Outcomes typically: "Over 20.5" @ 1.85, "Under 20.5" @ 1.95
                                for outcome in outcomes:
                                    outcome_desc = outcome.get('desc', '').lower()
                                    odds = float(outcome.get('odds', 0))
                                    
                                    # Extract line number (e.g., "20.5" from "Over 20.5")
                                    import re
                                    line_match = re.search(r'(\d+\.5)', outcome_desc)
                                    if line_match:
                                        line = line_match.group(1)
                                        
                                        if line not in total_games_lines:
                                            total_games_lines[line] = {}
                                        
                                        if 'over' in outcome_desc:
                                            total_games_lines[line]['over'] = odds
                                        elif 'under' in outcome_desc:
                                            total_games_lines[line]['under'] = odds
                        
                        # ONLY include matches where we found BOTH +1.5 odds (minimum requirement)
                        if home_plus_1_5_odds is not None and away_plus_1_5_odds is not None:
                            match_info = f"✅ Found sets markets: {home_team} (+1.5) @ {home_plus_1_5_odds} / {away_team} (+1.5) @ {away_plus_1_5_odds}"
                            
                            # Add +2.5 info if available
                            if home_plus_2_5_odds is not None and away_plus_2_5_odds is not None:
                                match_info += f" | {home_team} (+2.5) @ {home_plus_2_5_odds} / {away_team} (+2.5) @ {away_plus_2_5_odds}"
                            
                            # Include Total Games info if available
                            if total_games_lines:
                                lines_str = ', '.join([f"{line} O/U: {data.get('over', 'N/A')}/{data.get('under', 'N/A')}" 
                                                       for line, data in sorted(total_games_lines.items())])
                                match_info += f" | Total Games: {lines_str}"
                            
                            matches.append(BookmakerMatch(
                                event_id=event_id,
                                player1=home_team,
                                player2=away_team,
                                odds_player1_1_5=home_plus_1_5_odds,
                                odds_player2_1_5=away_plus_1_5_odds,
                                odds_player1_2_5=home_plus_2_5_odds,
                                odds_player2_2_5=away_plus_2_5_odds,
                                total_games_lines=total_games_lines if total_games_lines else None,
                                available=True
                            ))
                            print(match_info)
                            page_matches_count += 1
                            
                    except Exception as e:
                        print(f"Error parsing event: {e}")
                        continue
            
            print(f"📖 Page {page_num}: Found {page_matches_count} matches")
            
            # Check if there are more events using the API's flag (like the old system)
            more_events = tennis_data.get('data', {}).get('moreEvents', False)
            if not more_events:
                print(f"📄 API indicates no more events after page {page_num}")
                break
                
            # Move to next page
            page_num += 1
            
            # Safety limit to prevent infinite loops
            if page_num > 50:
                print("⚠️ Reached page limit (50), stopping pagination")
                break
        
        # Summary
        if target_date_obj:
            print(f"📊 Fetched all pages, filtered to {len(matches)} matches for {target_date}")
        else:
            print(f"📊 Fetched {len(matches)} total matches across {page_num-1} pages")
        
        return matches
    
    def normalize_player_name(self, name: str) -> str:
        """Normalize player name for better matching"""
        # Remove common prefixes/suffixes and normalize
        name = name.strip()
        
        # Remove common tennis name variations
        removals = [' Jr.', ' Jr', ' Sr.', ' Sr', ' III', ' II', ' IV']
        for removal in removals:
            name = name.replace(removal, '')
        
        # Handle last name, first name format
        if ',' in name:
            parts = name.split(',')
            if len(parts) == 2:
                name = f"{parts[1].strip()} {parts[0].strip()}"
        
        # Remove extra spaces and convert to lowercase
        return ' '.join(name.lower().split())
    
    def fuzzy_match_player(self, target_name: str, candidate_names: List[str], threshold: int = 70) -> Optional[str]:
        """Find best fuzzy match for a player name using multiple algorithms"""
        if not target_name or not candidate_names:
            return None
            
        normalized_target = self.normalize_player_name(target_name)
        normalized_candidates = [self.normalize_player_name(name) for name in candidate_names]
        
        # Try different fuzzy matching algorithms
        best_match = None
        best_score = 0
        best_original = None
        
        for i, candidate in enumerate(normalized_candidates):
            # Test multiple similarity algorithms
            scores = [
                fuzz.ratio(normalized_target, candidate),           # Basic ratio
                fuzz.partial_ratio(normalized_target, candidate),   # Partial matching
                fuzz.token_sort_ratio(normalized_target, candidate), # Token sorting
                fuzz.token_set_ratio(normalized_target, candidate)   # Token set
            ]
            
            # Use the maximum score from all algorithms
            max_score = max(scores)
            
            if max_score > best_score and max_score >= threshold:
                best_score = max_score
                best_match = candidate
                best_original = candidate_names[i]
        
        return best_original if best_match else None
    
    def is_match_available(self, player1: str, player2: str) -> bool:
        """Check if a specific match is available for betting using fuzzy matching"""
        available_matches = self.get_available_matches()
        
        if not available_matches:
            return False
            
        # Create list of all player names from available matches
        all_players = []
        for match in available_matches:
            all_players.extend([match.player1, match.player2])
        
        # Try to fuzzy match both players
        match1 = self.fuzzy_match_player(player1, all_players, threshold=75)
        match2 = self.fuzzy_match_player(player2, all_players, threshold=75)
        
        if not match1 or not match2:
            return False
            
        # Check if both matched players are in the same match
        for match in available_matches:
            match_players = [match.player1, match.player2]
            
            if match1 in match_players and match2 in match_players:
                print(f"✅ Match found: '{player1}' → '{match1}', '{player2}' → '{match2}'")
                return True
                
        return False
    
    def get_match_odds(self, player1: str, player2: str) -> Optional[BookmakerMatch]:
        """Get odds for a specific match using fuzzy matching"""
        available_matches = self.get_available_matches()
        
        for match in available_matches:
            all_players = [match.player1, match.player2]
            
            match1 = self.fuzzy_match_player(player1, all_players, threshold=75)
            match2 = self.fuzzy_match_player(player2, all_players, threshold=75)
            
            if match1 in all_players and match2 in all_players:
                return match
                
        return None


# Backwards compatibility alias
OddsProviderAPI = OddsProvider


class TennisBettingAnalyzer:
    """Main betting analysis engine focused on +1.5 set betting"""
    
    def __init__(self, user_id: str = None, access_token: str = None, prediction_logger=None):
        self.match_data_service = MatchDataProviderService()
        self.player_service = PlayerAnalysisService()
        self.mental_toughness_service = MentalToughnessService()
        self.mental_logger = get_mental_logger()
        self.bookmaker = OddsProvider(user_id, access_token)
        self.prediction_logger = prediction_logger
        self._setup_surface_data_logging()
        
        # Data quality logging initialization
        self._setup_data_quality_logging()
        
        # Competitive resilience logging initialization
        self._setup_competitive_resilience_logging()
        
        # Initialize skip logger (clears log file on startup)
        self.skip_logger = SkipLogger()
        
        # Store config reference for feature checking (MUST be before stats_handler init)
        self.config = prediction_config
        
        # Initialize enhanced statistics handler with config
        self.stats_handler = EnhancedStatisticsHandler(self.player_service, self.config)
        
        # Initialize injury checker (configurable via prediction_config.py)
        injury_days = prediction_config.INJURY_CHECKER['days_back']
        self.injury_checker = InjuryChecker(days_back=injury_days)
        print(f"🏥 Initializing injury/retirement checker (last {injury_days} days)...")
        if self.injury_checker.fetch_injured_players():
            self.injury_checker.print_injury_list()
        
        # CONFIGURABLE prediction weights - loaded from weight configuration manager
        self.WEIGHTS = get_current_weights()
        
        # Crowd sentiment thresholds from config
        self.CROWD_CONFIDENCE_THRESHOLDS = prediction_config.CROWD_CONFIDENCE_THRESHOLDS
    
    def _convert_gender(self, gender_code: Optional[str]) -> str:
        """Convert gender code from API (M/F) to readable format (Male/Female)"""
        if not gender_code:
            return 'Unknown'
        elif gender_code == 'M':
            return 'Male'
        elif gender_code == 'F':
            return 'Female'
        else:
            return 'Unknown'
    
    def calculate_age(self, birth_timestamp: Optional[int]) -> Optional[int]:
        """Calculate player age from birth timestamp"""
        if not birth_timestamp:
            return None
        
        try:
            birth_date = datetime.fromtimestamp(birth_timestamp)
            today = datetime.now()
            age = today.year - birth_date.year
            if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                age -= 1
            return age
        except:
            return None
    
    def detect_match_format(self, tournament_name: str, category: str, player1_gender: str, player2_gender: str) -> MatchFormat:
        """Detect if match is best-of-3 or best-of-5 format based on tournament and player info"""
        
        # Normalize inputs
        tournament_lower = tournament_name.lower()
        category_lower = category.lower()
        
        # Determine gender context
        if player1_gender == 'M' and player2_gender == 'M':
            gender = 'Male'
        elif player1_gender == 'F' and player2_gender == 'F':
            gender = 'Female'
        else:
            gender = 'Mixed'
        
        # Grand Slam detection patterns
        grand_slam_patterns = [
            'us open', 'united states open', 'wimbledon', 'french open', 'roland garros',
            'australian open', 'grand slam'
        ]
        
        # Check if it's a Grand Slam tournament
        is_grand_slam = any(pattern in tournament_lower for pattern in grand_slam_patterns)
        
        # Determine tournament level
        if is_grand_slam:
            tournament_level = "Grand Slam"
        elif any(pattern in tournament_lower for pattern in ['masters 1000', 'masters', 'indian wells', 'miami open', 'monte carlo', 'madrid', 'rome', 'toronto', 'cincinnati', 'shanghai', 'paris']):
            tournament_level = "Masters 1000"
        elif '500' in tournament_lower or any(pattern in tournament_lower for pattern in ['atp 500', 'wta 500']):
            tournament_level = "ATP/WTA 500"
        elif '250' in tournament_lower or any(pattern in tournament_lower for pattern in ['atp 250', 'wta 250']):
            tournament_level = "ATP/WTA 250"
        elif 'challenger' in tournament_lower:
            tournament_level = "Challenger"
        elif 'itf' in tournament_lower:
            tournament_level = "ITF"
        else:
            tournament_level = "Other"
        
        # **CRITICAL RULE**: Best-of-5 ONLY for Grand Slam men's singles
        is_best_of_five = (is_grand_slam and gender == 'Male')
        
        return MatchFormat(
            is_best_of_five=is_best_of_five,
            tournament_name=tournament_name,
            category=category,
            tournament_level=tournament_level,
            gender=gender
        )
    
    def _extract_tournament_country(self, tournament_name: str) -> Optional[str]:
        """Extract country from tournament/city name - ENHANCED with missing cities"""
        if not tournament_name or tournament_name == "Unknown":
            return None
        
        tournament_lower = tournament_name.lower().strip()
        
        # City to country mapping - ENHANCED with additional Chinese cities and more
        city_to_country = {
            # Asia - ENHANCED
            'tokyo': 'Japan', 'osaka': 'Japan',
            'shanghai': 'China', 'beijing': 'China', 'wuhan': 'China', 'shenzhen': 'China',
            'guangzhou': 'China', 'zhuhai': 'China', 'tianjin': 'China',  # ✨ ADDED GUANGZHOU
            'hong kong': 'Hong Kong',
            'singapore': 'Singapore',
            'dubai': 'UAE', 'abu dhabi': 'UAE',
            'doha': 'Qatar',
            'bangkok': 'Thailand',
            'seoul': 'South Korea',
            'mumbai': 'India', 'bangalore': 'India', 'pune': 'India',
            
            # Europe
            'paris': 'France', 'lyon': 'France', 'metz': 'France',
            'rome': 'Italy', 'milan': 'Italy', 'palermo': 'Italy',
            'madrid': 'Spain', 'barcelona': 'Spain', 'valencia': 'Spain',
            'london': 'United Kingdom', 'birmingham': 'United Kingdom', 'eastbourne': 'United Kingdom',
            'berlin': 'Germany', 'munich': 'Germany', 'hamburg': 'Germany', 'stuttgart': 'Germany',
            'vienna': 'Austria',
            'basel': 'Switzerland', 'geneva': 'Switzerland',
            'amsterdam': 'Netherlands',
            'antwerp': 'Belgium',
            'stockholm': 'Sweden',
            'moscow': 'Russia', 'st petersburg': 'Russia',
            'prague': 'Czechia',
            'bucharest': 'Romania',
            'lisbon': 'Portugal',
            'athens': 'Greece',
            
            # Americas
            'new york': 'USA', 'miami': 'USA', 'indian wells': 'USA', 'cincinnati': 'USA',
            'atlanta': 'USA', 'washington': 'USA', 'san diego': 'USA', 'cleveland': 'USA',
            'houston': 'USA', 'dallas': 'USA', 'austin': 'USA', 'winston-salem': 'USA',
            'charleston': 'USA', 'san jose': 'USA',
            'montreal': 'Canada', 'toronto': 'Canada',
            'acapulco': 'Mexico',
            'buenos aires': 'Argentina',
            'santiago': 'Chile',
            'bogota': 'Colombia',
            'rio de janeiro': 'Brazil', 'sao paulo': 'Brazil',
            
            # Oceania
            'melbourne': 'Australia', 'sydney': 'Australia', 'brisbane': 'Australia',
            'adelaide': 'Australia', 'perth': 'Australia',
            'auckland': 'New Zealand',
        }
        
        # Check city mapping first
        for city, country in city_to_country.items():
            if city in tournament_lower:
                return country
        
        # Try to extract country from tournament name format: "City, Country, ..."
        parts = [part.strip() for part in tournament_name.split(',')]
        if len(parts) >= 2:
            potential_country = parts[1].strip()
            if potential_country and len(potential_country) > 2 and potential_country[0].isupper():
                return potential_country
        
        # Fallback: Check if country name appears anywhere in tournament name
        country_keywords = {
            'australia': 'Australia', 'australian': 'Australia',
            'france': 'France', 'french': 'France', 'roland garros': 'France',
            'spain': 'Spain', 'spanish': 'Spain',
            'italy': 'Italy', 'italian': 'Italy',
            'germany': 'Germany', 'german': 'Germany',
            'usa': 'USA', 'us': 'USA', 'united states': 'USA', 'american': 'USA',
            'uk': 'United Kingdom', 'britain': 'United Kingdom', 'british': 'United Kingdom',
            'china': 'China', 'chinese': 'China',
            'japan': 'Japan', 'japanese': 'Japan',
            'canada': 'Canada', 'canadian': 'Canada',
            'brazil': 'Brazil', 'brazilian': 'Brazil',
            'argentina': 'Argentina', 'argentine': 'Argentina',
            'russia': 'Russia', 'russian': 'Russia',
            'portugal': 'Portugal', 'portuguese': 'Portugal',
        }
        
        for keyword, country in country_keywords.items():
            if keyword in tournament_lower:
                return country
        
        return None
    
    def _countries_match(self, player_country: str, tournament_country: str) -> bool:
        """Check if player's country matches tournament country"""
        if not player_country or not tournament_country:
            return False
        
        pc_lower = player_country.lower().strip()
        tc_lower = tournament_country.lower().strip()
        
        # Direct match
        if pc_lower == tc_lower:
            return True
        
        # Contains match (e.g., "USA" in "United States")
        if pc_lower in tc_lower or tc_lower in pc_lower:
            return True
        
        # Common variations
        if (pc_lower in ['usa', 'united states', 'us'] and tc_lower in ['usa', 'united states', 'us']):
            return True
        if (pc_lower in ['uk', 'united kingdom', 'britain', 'great britain'] and
            tc_lower in ['uk', 'united kingdom', 'britain', 'great britain']):
            return True
        
        return False
    
    def _log_home_advantage(self, tournament: str, country: str, home_player: str,
                           home_country: str, away_player: str, away_country: str):
        """Log home advantage to file"""
        try:
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, "home_advantage.log")
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            bonus_pct = int(self.config.HOME_ADVANTAGE['bonus_percentage'] * 100)
            log_entry = (
                f"{timestamp} | Tournament: {tournament} ({country}) | "
                f"HOME: {home_player} ({home_country}) vs AWAY: {away_player} ({away_country}) | "
                f"Bonus: +{bonus_pct}%\n"
            )
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            # Don't fail the prediction if logging fails
            print(f"   ⚠️ Failed to log home advantage: {e}")
    
    def _player_won_match(self, match: Dict[str, Any], player_id: int) -> bool:
        """Helper method to determine if a player won a match"""
        try:
            home_team_id = match.get('homeTeam', {}).get('id')
            away_team_id = match.get('awayTeam', {}).get('id')
            winner_code = match.get('winnerCode', 0)
            
            if home_team_id == player_id:
                return winner_code == 1  # Home team won
            elif away_team_id == player_id:
                return winner_code == 2  # Away team won
            return False
        except:
            return False
    
    def _calculate_overall_win_rate(self, year_stats: Optional[Dict] = None) -> float:
        """Calculate player's overall win rate as intelligent fallback instead of arbitrary 0.5"""
        if not year_stats or not year_stats.get('statistics'):
            return 0.5  # Only use 0.5 when we have absolutely no data
        
        total_matches = 0
        total_wins = 0
        
        # Sum across all surfaces/conditions
        for stat in year_stats['statistics']:
            matches = stat.get('matches', 0)
            wins = stat.get('wins', 0)
            total_matches += matches
            total_wins += wins
        
        if total_matches == 0:
            return 0.5
        
        overall_rate = total_wins / total_matches
        
        # Apply confidence adjustment for small samples
        if total_matches < 10:
            # Blend toward neutral for very small samples
            confidence = total_matches / 10.0
            overall_rate = overall_rate * confidence + 0.5 * (1 - confidence)
        
        return overall_rate

    def _apply_data_quality_probability_caps(self, player1_match_prob: float, player2_match_prob: float,
                                           player1: PlayerProfile, player2: PlayerProfile, surface: str) -> tuple:
        """
        🚨 CRITICAL: Apply probability caps based on actual performance data
        Prevents overconfident predictions like our recent losses (82.8% and 85.0% confidence failures)
        ENHANCED VERSION based on 4-loss analysis findings
        """
        print(f"\n🚨 APPLYING ENHANCED DATA QUALITY PROBABILITY CAPS:")
        print(f"   Original: P1: {player1_match_prob:.1%}, P2: {player2_match_prob:.1%}")
        
        capped_probs = []
        players = [player1, player2]
        original_probs = [player1_match_prob, player2_match_prob]
        
        for i, (player, orig_prob) in enumerate(zip(players, original_probs)):
            capped_prob = orig_prob
            penalties = []
            
            # 🔴 RED CLAY ENHANCED VOLATILITY PENALTIES (higher upset rates)
            if surface.lower() in ['red clay', 'clay']:
                # Get surface data for clay experience requirements
                surface_matches, confidence_score = self._get_surface_match_data(player.id, surface)
                
                # ENHANCED CLAY PENALTIES based on data quality and experience
                if surface_matches < 20:  # Insufficient clay experience
                    capped_prob = min(capped_prob, 0.60)  # Harsh cap for inexperienced clay players
                    penalties.append(f"🔴 Clay inexperience penalty ({surface_matches} matches) → 60%")
                    print(f"   {player.name}: Insufficient clay experience ({surface_matches} matches)")
                elif confidence_score < 0.6:  # Low confidence clay data
                    capped_prob = min(capped_prob, 0.65)  # Moderate cap for questionable clay data
                    penalties.append(f"🔴 Clay data quality penalty (conf: {confidence_score:.2f}) → 65%")
                    print(f"   {player.name}: Poor clay data quality (conf: {confidence_score:.2f})")
                else:
                    capped_prob = min(capped_prob, 0.70)  # General clay volatility cap
                    penalties.append("🔴 Clay volatility factor → 70%")
                    print(f"   {player.name}: Clay court volatility penalty applied")
                    
                # Additional penalty for no surface data at all
                if surface_matches == 0:
                    capped_prob = min(capped_prob, 0.55)  # Very harsh for no clay data
                    penalties.append("🔴 NO CLAY DATA - extreme penalty → 55%")
                    print(f"   {player.name}: NO CLAY DATA - betting blind!")
            
            # 🎾 GENERAL SURFACE DATA REQUIREMENTS (for all surfaces)
            elif surface.lower() not in ['unknown', 'hard', 'hardcourt']:  # Apply to grass, other surfaces
                surface_matches, confidence_score = self._get_surface_match_data(player.id, surface)
                
                if surface_matches == 0:  # No surface experience at all
                    capped_prob = min(capped_prob, 0.60)  # Harsh penalty for no data
                    penalties.append(f"🎾 NO {surface.upper()} DATA - betting blind → 60%")
                    print(f"   {player.name}: NO {surface} experience - high risk bet")
                elif surface_matches < 10:  # Very limited experience
                    capped_prob = min(capped_prob, 0.70)  # Moderate penalty 
                    penalties.append(f"🎾 Limited {surface} experience ({surface_matches} matches) → 70%")
                    print(f"   {player.name}: Limited {surface} experience ({surface_matches} matches)")
                elif confidence_score < 0.5:  # Poor data quality
                    capped_prob = min(capped_prob, 0.75)  # Light penalty
                    penalties.append(f"🎾 Poor {surface} data quality (conf: {confidence_score:.2f}) → 75%")
                    print(f"   {player.name}: Poor {surface} data quality")
            
            # 1. ENHANCED SURFACE PERFORMANCE CAPS (more aggressive based on loss analysis)
            surface_confidence = 0.0
            try:
                surface_perf, confidence_data, data_quality = self.calculate_enhanced_surface_performance(player.id, surface)
                
                # Extract surface confidence from confidence_data if available
                if hasattr(confidence_data, 'confidence') or (isinstance(confidence_data, dict) and 'confidence' in confidence_data):
                    surface_confidence = confidence_data.confidence if hasattr(confidence_data, 'confidence') else confidence_data['confidence']
                elif "conf:" in str(data_quality):
                    # Extract confidence from data_quality string (e.g., "conf: 0.33")
                    try:
                        conf_str = str(data_quality).split("conf:")[1].split(")")[0].strip()
                        surface_confidence = float(conf_str)
                    except:
                        pass
                
                # AGGRESSIVE CONFIDENCE-BASED CAPS (from loss analysis)
                if surface_confidence < 0.20:  # Minimal confidence (like Loss #4: 0.19)
                    capped_prob = min(capped_prob, 0.35)
                    penalties.append(f"Surface conf <0.20 → cap 35%")
                elif surface_confidence < 0.35:  # Low confidence (like Loss #1,#3: 0.33,0.34)
                    capped_prob = min(capped_prob, 0.50)
                    penalties.append(f"Surface conf <0.35 → cap 50%")
                elif surface_confidence < 0.45:  # Weak confidence
                    capped_prob = min(capped_prob, 0.60)
                    penalties.append(f"Surface conf <0.45 → cap 60%")
                
                # PERFORMANCE-BASED CAPS (more aggressive)
                if surface_perf < 0.30:  # <30% surface rate
                    capped_prob = min(capped_prob, 0.25)
                    penalties.append(f"Surface <30% → cap 25%")
                elif surface_perf < 0.40:  # 30-40% surface rate  
                    capped_prob = min(capped_prob, 0.40)  # More aggressive
                    penalties.append(f"Surface <40% → cap 40%")
                elif surface_perf < 0.45:  # 40-45% surface rate
                    capped_prob = min(capped_prob, 0.55)  # More aggressive
                    penalties.append(f"Surface <45% → cap 55%")
                
                print(f"   {player.name}: Surface {surface_perf:.1%} (conf: {surface_confidence:.2f}) on {surface}")
                
            except Exception as e:
                # No surface data available - more aggressive uncertainty cap
                capped_prob = min(capped_prob, 0.45)  # Reduced from 0.60
                penalties.append("No surface data → cap 45%")
                print(f"   {player.name}: No surface data available")
            
            # 2. MENTAL TOUGHNESS PENALTIES (0% tiebreak = major penalty)
            try:
                tiebreak_performance = self.calculate_enhanced_tiebreak_performance(player.id, surface)
                
                if tiebreak_performance == 0.0:  # 0% tiebreak rate = extreme fragility
                    penalty = 0.30  # -30 percentage points
                    capped_prob = max(0.10, capped_prob - penalty)
                    penalties.append(f"0% tiebreak rate → -30pp penalty")
                elif tiebreak_performance < 0.25:  # <25% tiebreak rate
                    penalty = 0.20  # -20 percentage points  
                    capped_prob = max(0.10, capped_prob - penalty)
                    penalties.append(f"<25% tiebreak rate → -20pp penalty")
                elif tiebreak_performance < 0.40:  # 25-40% tiebreak rate
                    penalty = 0.10  # -10 percentage points
                    capped_prob = max(0.10, capped_prob - penalty)
                    penalties.append(f"<40% tiebreak rate → -10pp penalty")
                
                print(f"   {player.name}: Tiebreak {tiebreak_performance:.1%}")
                
            except Exception as e:
                # No tiebreak data - significant uncertainty penalty
                penalty = 0.15  # -15 percentage points for missing mental data
                capped_prob = max(0.10, capped_prob - penalty)
                penalties.append("No tiebreak data → -15pp penalty")
                print(f"   {player.name}: No tiebreak data (mental fragility unknown)")
            
            # 3. ENHANCED SAMPLE SIZE PENALTIES (based on actual surface data from API)
            try:
                # Get surface data directly instead of parsing data_quality string
                surface_matches, confidence_score = self._get_surface_match_data(player.id, surface)
                
                # Also log with player name for the surface data log
                try:
                    enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player.id, surface)
                    
                    # Log data quality assessment
                    issues = []
                    if enhanced_stats.get('has_404_error'):
                        issues.append("404 Error")
                    self._log_data_quality("Unknown Player", player.id, surface, 
                                         enhanced_stats=enhanced_stats, 
                                         context="Probability Caps Analysis")
                    
                    if not enhanced_stats.get('has_404_error'):
                        combined_stats = enhanced_stats.get('statistics', {})
                        matches = combined_stats.get('matches', 0)
                        wins = combined_stats.get('wins', 0)
                        tiebreaks_won = combined_stats.get('tiebreaksWon', 0)
                        tiebreaks_total = tiebreaks_won + combined_stats.get('tiebreakLosses', 0)
                        
                        # Log detailed surface data with player name
                        self._log_surface_data(player.name, player.id, surface, 
                                             matches, wins, tiebreaks_won, 
                                             tiebreaks_total, confidence_score, 
                                             f"Enhanced caps analysis - Orig prob: {original_prob:.1%}")
                except:
                    pass
                
                # AGGRESSIVE SAMPLE SIZE CAPS (from loss analysis findings)
                if surface_matches == 0:  # No surface data (like many losses)
                    capped_prob = min(capped_prob, 0.30)
                    penalties.append(f"0 surface matches → cap 30%")
                elif surface_matches < 3:  # Very small sample (more aggressive)
                    capped_prob = min(capped_prob, 0.35)
                    penalties.append(f"<3 surface matches → cap 35%")
                elif surface_matches < 5:  # Small sample (more aggressive)
                    capped_prob = min(capped_prob, 0.45)
                    penalties.append(f"<5 surface matches → cap 45%")
                elif surface_matches < 8:  # Limited sample
                    capped_prob = min(capped_prob, 0.60)
                    penalties.append(f"<8 surface matches → cap 60%")
                elif surface_matches < 15:  # Moderate sample
                    capped_prob = min(capped_prob, 0.70)
                    penalties.append(f"<15 surface matches → cap 70%")
                
                # CONFIDENCE-BASED CAPS (statistical reliability)
                if confidence_score < 0.20:  # Very low confidence
                    capped_prob = min(capped_prob, 0.35)
                    penalties.append(f"Confidence <0.20 → cap 35%")
                elif confidence_score < 0.35:  # Low confidence  
                    capped_prob = min(capped_prob, 0.50)
                    penalties.append(f"Confidence <0.35 → cap 50%")
                elif confidence_score < 0.50:  # Moderate confidence
                    capped_prob = min(capped_prob, 0.65)
                    penalties.append(f"Confidence <0.50 → cap 65%")
                        
                print(f"   {player.name}: {surface_matches} surface matches, {confidence_score:.2f} confidence")
                        
            except Exception as e:
                # No surface data available - apply default penalty
                capped_prob = min(capped_prob, 0.30)
                penalties.append("No surface data → cap 30%")
                print(f"   {player.name}: No surface data available: {e}")
                
                # Log the exception
                self._log_surface_data(player.name, player.id, surface, 0, 0, 
                                     extra_info=f"Enhanced caps exception: {str(e)}")
            
            # 4. ENHANCED MENTAL TOUGHNESS GAP PENALTIES (from Loss #4 analysis)
            try:
                # Calculate mental toughness for both players to identify gaps
                mental1 = self._calculate_mental_toughness_score(player1.id)
                mental2 = self._calculate_mental_toughness_score(player2.id)
                
                # Determine mental disadvantage for current player
                if i == 0:  # Player 1
                    mental_gap = mental2 - mental1  # Positive if P2 has advantage
                else:  # Player 2
                    mental_gap = mental1 - mental2  # Positive if P1 has advantage
                
                # Apply penalties for significant mental disadvantages
                if mental_gap > 0.20:  # >20% mental disadvantage (extreme)
                    capped_prob = min(capped_prob, 0.35)
                    penalties.append(f"Mental disadvantage >20% → cap 35%")
                elif mental_gap > 0.15:  # >15% mental disadvantage (like Loss #4: 15.6%)
                    capped_prob = min(capped_prob, 0.45)
                    penalties.append(f"Mental disadvantage >15% → cap 45%")
                elif mental_gap > 0.10:  # >10% mental disadvantage (significant)
                    capped_prob = min(capped_prob, 0.60)
                    penalties.append(f"Mental disadvantage >10% → cap 60%")
                
                current_mental = mental1 if i == 0 else mental2
                opponent_mental = mental2 if i == 0 else mental1
                print(f"   {player.name}: Mental {current_mental:.1%} vs opponent {opponent_mental:.1%} (gap: {mental_gap:+.1%})")
                
            except Exception as e:
                print(f"   {player.name}: Could not calculate mental gap: {e}")
            
            # 5. COMPOUND PENALTIES - Multiple red flags = even lower caps (more aggressive)
            if len(penalties) >= 3:  # More aggressive threshold
                # Multiple issues - apply additional compound penalty
                compound_penalty = (len(penalties) - 2) * 0.08  # 8% per additional issue beyond 2
                capped_prob = max(0.10, capped_prob - compound_penalty)
                penalties.append(f"Severe compound penalty: -{compound_penalty:.0%}")
            elif len(penalties) >= 2:
                # Multiple issues - apply compound penalty
                compound_penalty = len(penalties) * 0.05  # 5% per additional issue
                capped_prob = max(0.10, capped_prob - compound_penalty)
                penalties.append(f"Compound penalty: -{compound_penalty:.0%}")
            
            # Log the adjustments
            if penalties:
                print(f"   {player.name} PENALTIES: {'; '.join(penalties)}")
                print(f"   {player.name}: {orig_prob:.1%} → {capped_prob:.1%} (adjusted)")
            else:
                print(f"   {player.name}: No penalties applied")
                
            capped_probs.append(capped_prob)
        
        # Renormalize to ensure probabilities sum to 1.0
        total_capped = sum(capped_probs)
        if total_capped > 0:
            final_p1 = capped_probs[0] / total_capped
            final_p2 = capped_probs[1] / total_capped
        else:
            final_p1 = final_p2 = 0.5
        
        # 🚨 ULTIMATE OVERCONFIDENCE PROTECTION - Based on validation analysis
        # All our 75.8%-85.0% confidence losses were straight-set defeats
        # This suggests the system is systematically overconfident in this range
        max_confidence = 0.73  # Cap at 73% based on validation loss pattern
        
        if final_p1 > max_confidence:
            print(f"   🚨 OVERCONFIDENCE PROTECTION: P1 {final_p1:.1%} → {max_confidence:.1%}")
            # Adjust both probabilities proportionally
            excess = final_p1 - max_confidence
            final_p1 = max_confidence
            final_p2 = min(1.0, final_p2 + excess)
        elif final_p2 > max_confidence:
            print(f"   🚨 OVERCONFIDENCE PROTECTION: P2 {final_p2:.1%} → {max_confidence:.1%}")
            # Adjust both probabilities proportionally  
            excess = final_p2 - max_confidence
            final_p2 = max_confidence
            final_p1 = min(1.0, final_p1 + excess)
            
        print(f"   FINAL CAPPED: P1: {final_p1:.1%}, P2: {final_p2:.1%}")
        
        return final_p1, final_p2

    def _setup_surface_data_logging(self):
        """Setup surface data logging that clears on each run"""
        try:
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
            
            # Clear/create surface data log file
            self.surface_log_file = 'logs/surface_data.log'
            
            # Clear the log file (start fresh each run)
            with open(self.surface_log_file, 'w') as f:
                f.write(f"=== SURFACE DATA LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.write("Format: [TIMESTAMP] Player Name (ID) | Surface | Matches | Wins | Win% | Tiebreaks | TB% | Confidence\n")
                f.write("=" * 100 + "\n\n")
                
            print(f"✅ Surface data logging initialized: {self.surface_log_file}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not setup surface data logging: {e}")
            self.surface_log_file = None

    def _setup_data_quality_logging(self):
        """Setup data quality logging that clears on each run"""
        try:
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
            
            # Clear/create data quality log file
            self.data_quality_log_file = 'logs/data_quality.log'
            
            # Clear the log file (start fresh each run)
            with open(self.data_quality_log_file, 'w') as f:
                f.write(f"=== DATA QUALITY LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.write("Tracks player data quality assessments, sample sizes, and penalties\n")
                f.write("Format: [TIMESTAMP] Player Name (ID) | Assessment | Reliability | Sample Data | Issues | Context\n")
                f.write("=" * 120 + "\n\n")
                
            print(f"✅ Data quality logging initialized: {self.data_quality_log_file}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not setup data quality logging: {e}")
            self.data_quality_log_file = None

    def _setup_competitive_resilience_logging(self):
        """Setup competitive resilience logging that clears on each run"""
        try:
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
            
            # Clear/create competitive resilience log file
            self.competitive_resilience_log_file = 'logs/competitive_resilience.log'
            
            # Clear the log file (start fresh each run)
            with open(self.competitive_resilience_log_file, 'w') as f:
                f.write(f"=== COMPETITIVE RESILIENCE LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.write("Tracks sets taken in losses - measures competitive spirit when behind\n")
                f.write("Format: [TIMESTAMP] Player Name (ID) | Losses | Sets in Losses | Total Sets in Losses | Resilience % | Assessment\n")
                f.write("=" * 120 + "\n\n")
                
            print(f"✅ Competitive resilience logging initialized: {self.competitive_resilience_log_file}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not setup competitive resilience logging: {e}")
            self.competitive_resilience_log_file = None

    def _get_player_name(self, player_id: int) -> str:
        """Get player name from ID, with fallback to 'Player {ID}'"""
        try:
            # Try to get player name from the player service
            player_data = self.player_service.get_player_details(player_id)
            if player_data and 'team' in player_data:
                return player_data['team'].get('name', f'Player {player_id}')
            elif player_data and 'name' in player_data:
                return player_data.get('name', f'Player {player_id}')
            else:
                return f'Player {player_id}'
        except Exception as e:
            return f'Player {player_id}'

    def _log_data_quality(self, player_name: str, player_id: int, surface: str = None, 
                         data_quality: str = None, reliability_score: float = None, 
                         sample_data: dict = None, issues: list = None, 
                         context: str = None, enhanced_stats: dict = None):
        """Log detailed data quality information for a player"""
        if not hasattr(self, 'data_quality_log_file') or not self.data_quality_log_file:
            return
            
        try:
            # Resolve player name if needed
            if player_name == "Unknown Player":
                player_name = self._get_player_name(player_id)
            
            # Format timestamp
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Format sample data information
            sample_info = "No data"
            if sample_data:
                parts = []
                if 'matches' in sample_data:
                    parts.append(f"M:{sample_data['matches']}")
                if 'tiebreaks' in sample_data:
                    parts.append(f"TB:{sample_data['tiebreaks']}")
                if 'break_points' in sample_data:
                    parts.append(f"BP:{sample_data['break_points']}")
                if 'serve_points' in sample_data:
                    parts.append(f"SP:{sample_data['serve_points']}")
                sample_info = ", ".join(parts) if parts else "No data"
            
            # Extract additional info from enhanced stats
            if enhanced_stats:
                if not data_quality:
                    data_quality = enhanced_stats.get('data_quality', 'Unknown')
                if reliability_score is None:
                    reliability_score = enhanced_stats.get('reliability_score', 0.0)
                if not sample_data:
                    sample_data = enhanced_stats.get('sample_sizes', {})
                    sample_info = f"M:{sample_data.get('matches', 0)}, TB:{sample_data.get('tiebreaks', 0)}, BP:{sample_data.get('break_points', 0)}"
                if enhanced_stats.get('has_404_error'):
                    if not issues:
                        issues = []
                    issues.append("404 Error")
            
            # Format issues
            issues_str = "; ".join(issues) if issues else "None"
            
            # Format reliability score
            reliability_str = f"{reliability_score:.3f}" if reliability_score is not None else "N/A"
            
            # Format surface info
            surface_str = surface if surface else "General"
            
            # Format data quality
            quality_str = data_quality if data_quality else "Unknown"
            
            # Format context
            context_str = context if context else "Analysis"
            
            # Create log entry
            log_entry = (f"[{timestamp}] {player_name} ({player_id}) | "
                        f"{surface_str} | {quality_str} | Rel:{reliability_str} | "
                        f"{sample_info} | Issues: {issues_str} | {context_str}")
            
            # Write to log file
            with open(self.data_quality_log_file, 'a') as f:
                f.write(log_entry + "\n")
                
        except Exception as e:
            print(f"⚠️ Warning: Could not log data quality data: {e}")

    def _log_surface_data(self, player_name: str, player_id: int, surface: str, 
                         matches: int, wins: int, tiebreaks_won: int = 0, 
                         tiebreaks_total: int = 0, confidence: float = 0.0, extra_info: str = ""):
        """Log surface data for debugging and monitoring"""
        if not hasattr(self, 'surface_log_file') or not self.surface_log_file:
            return
            
        try:
            # If player name is "Unknown Player", try to get the real name
            if player_name == "Unknown Player":
                player_name = self._get_player_name(player_id)
                
            win_rate = (wins / matches * 100) if matches > 0 else 0
            tb_rate = (tiebreaks_won / tiebreaks_total * 100) if tiebreaks_total > 0 else 0
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_line = (f"[{timestamp}] {player_name} ({player_id}) | {surface} | "
                       f"{matches} matches | {wins} wins | {win_rate:.1f}% | "
                       f"{tiebreaks_won}/{tiebreaks_total} TB | {tb_rate:.1f}% | "
                       f"conf: {confidence:.3f}")
            
            if extra_info:
                log_line += f" | {extra_info}"
                
            log_line += "\n"
            
            with open(self.surface_log_file, 'a') as f:
                f.write(log_line)
                
        except Exception as e:
            # Don't let logging errors break the main functionality
            pass

    def calculate_sets_in_losses(self, player_id: int, surface: str = None) -> tuple:
        """
        Calculate competitive resilience - sets taken in losses from comprehensive 2-year data
        
        Args:
            player_id: Player ID to analyze
            surface: Surface to filter by (Clay/Hard/Grass) or None for all surfaces combined
                    If surface is unknown/None, uses ALL surfaces for comprehensive analysis
        
        Returns:
            (resilience_percentage, sets_in_losses, total_sets_in_losses, losses_count)
        """
        try:
            # Get comprehensive match data (2-year)
            comprehensive_matches = self.player_service.get_comprehensive_singles_matches(
                player_id, max_matches=200, max_pages=10
            )
            
            if not comprehensive_matches or not comprehensive_matches.get('events'):
                return 0.0, 0, 0, 0
            
            # Normalize surface name for filtering (if provided)
            target_surface = None
            if surface and surface.strip():  # Only process non-empty surfaces
                surface_mappings = {
                    'clay': ['clay', 'red clay'],
                    'hardcourt indoor': ['hardcourt indoor', 'indoor hardcourt'],
                    'hardcourt outdoor': ['hardcourt outdoor', 'outdoor hardcourt'], 
                    'hard': ['hard', 'hardcourt'],  # Generic hardcourt fallback
                    'grass': ['grass'],
                    'indoor': ['indoor'],  # Pure indoor (not hardcourt specific)
                    'outdoor': ['outdoor']  # Pure outdoor (not hardcourt specific)
                }
                
                surface_lower = surface.lower().strip()
                
                # Skip unknown/unrecognized surfaces - treat as fallback to all surfaces
                if surface_lower in ['unknown', 'n/a', 'not available', 'none']:
                    target_surface = None  # Fallback to all surfaces
                else:
                    for key, variations in surface_mappings.items():
                        if surface_lower in variations or any(var in surface_lower for var in variations):
                            target_surface = key
                            break
                    
                    # If no mapping found for a real surface string, treat as unknown (fallback to all)
                    if not target_surface:
                        target_surface = None
            
            losses_count = 0
            sets_won_in_losses = 0
            total_sets_in_losses = 0
            surface_filtered_matches = 0
            
            for match in comprehensive_matches.get('events', []):
                try:
                    # Surface filtering (if specified) - if surface is unknown/None, process ALL surfaces
                    if target_surface:
                        match_surface = match.get('groundType', '').lower()
                        if not match_surface:
                            continue  # Skip matches with no surface data
                        
                        # Check if match surface matches our target - ENHANCED SURFACE MATCHING
                        surface_match = False
                        if target_surface == 'clay' and ('clay' in match_surface or 'red' in match_surface):
                            surface_match = True
                        elif target_surface == 'hardcourt indoor' and ('hardcourt indoor' in match_surface or 'indoor' in match_surface):
                            surface_match = True
                        elif target_surface == 'hardcourt outdoor' and ('hardcourt outdoor' in match_surface or 'outdoor' in match_surface):
                            surface_match = True
                        elif target_surface == 'hard' and ('hard' in match_surface and 'indoor' not in match_surface and 'outdoor' not in match_surface):
                            surface_match = True  # Generic hardcourt only if not specifically indoor/outdoor
                        elif target_surface == 'grass' and ('grass' in match_surface):
                            surface_match = True
                        elif target_surface == 'indoor' and ('indoor' in match_surface):
                            surface_match = True
                        elif target_surface == 'outdoor' and ('outdoor' in match_surface):
                            surface_match = True
                        
                        if not surface_match:
                            continue  # Skip non-matching surface
                        
                        surface_filtered_matches += 1
                    
                    # Check if this player lost the match
                    if not self._player_won_match(match, player_id):
                        losses_count += 1
                        
                        # Get sets from homeScore and awayScore (correct MatchDataProvider structure)
                        home_score = match.get('homeScore', {})
                        away_score = match.get('awayScore', {})
                        
                        if home_score and away_score:
                            player_sets_won = 0
                            total_sets = 0
                            
                            # Determine which player is home vs away
                            home_team = match.get('homeTeam', {}).get('id')
                            away_team = match.get('awayTeam', {}).get('id')
                            
                            is_home_player = (player_id == home_team)
                            player_score_obj = home_score if is_home_player else away_score
                            opponent_score_obj = away_score if is_home_player else home_score
                            
                            # Count sets by examining period1, period2, period3, etc.
                            for period_key in ['period1', 'period2', 'period3', 'period4', 'period5']:
                                if period_key in player_score_obj and period_key in opponent_score_obj:
                                    player_set_score = player_score_obj.get(period_key, 0)
                                    opponent_set_score = opponent_score_obj.get(period_key, 0)
                                    
                                    # Only count if both scores are valid numbers > 0
                                    if isinstance(player_set_score, (int, float)) and isinstance(opponent_set_score, (int, float)):
                                        if player_set_score > 0 or opponent_set_score > 0:
                                            total_sets += 1
                                            if player_set_score > opponent_set_score:
                                                player_sets_won += 1
                            
                            sets_won_in_losses += player_sets_won
                            total_sets_in_losses += total_sets
                            
                except Exception as e:
                    # Skip problematic matches
                    continue
            
            # Calculate resilience percentage
            resilience_percentage = (sets_won_in_losses / total_sets_in_losses * 100) if total_sets_in_losses > 0 else 0.0
            
            return resilience_percentage, sets_won_in_losses, total_sets_in_losses, losses_count
            
        except Exception as e:
            print(f"⚠️ Error calculating sets in losses for player {player_id}: {e}")
            return 0.0, 0, 0, 0

    def _log_competitive_resilience(self, player_name: str, player_id: int, 
                                  resilience_percentage: float, sets_in_losses: int, 
                                  total_sets_in_losses: int, losses_count: int, surface: str = None):
        """Log competitive resilience data with optional surface context"""
        if not hasattr(self, 'competitive_resilience_log_file') or not self.competitive_resilience_log_file:
            return
            
        try:
            # If player name is "Unknown Player", try to get the real name
            if player_name == "Unknown Player":
                player_name = self._get_player_name(player_id)
            
            # Determine assessment based on resilience percentage
            if resilience_percentage >= 40:
                assessment = "High Resilience - Fighter"
            elif resilience_percentage >= 25:
                assessment = "Average Resilience"
            elif resilience_percentage >= 15:
                assessment = "Low Resilience"
            else:
                assessment = "Very Low Resilience"
            
            # Add surface context to assessment if provided
            surface_context = f" on {surface.title()}" if surface else " (All surfaces)"
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_line = (f"[{timestamp}] {player_name} ({player_id}) | "
                       f"{losses_count} losses{surface_context} | {sets_in_losses} sets won | "
                       f"{total_sets_in_losses} total sets | {resilience_percentage:.1f}% | {assessment}\n")
            
            # Write to log file
            with open(self.competitive_resilience_log_file, 'a') as f:
                f.write(log_line)
                
        except Exception as e:
            # Don't let logging errors break the main functionality
            pass

    def _get_surface_match_data(self, player_id: int, surface: str) -> tuple:
        """
        Get surface match count and confidence score directly from API data
        Used by enhanced probability caps for accurate sample size assessment
        """
        try:
            # Use the same data source as calculate_enhanced_surface_performance
            enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player_id, surface)
            
            if enhanced_stats.get('has_404_error'):
                # Log the 404 error
                self._log_surface_data("Unknown Player", player_id, surface, 0, 0, 
                                     extra_info="404 Error - No data available")
                return 0, 0.0  # No data available
            
            # Extract surface statistics from enhanced handler
            combined_stats = enhanced_stats.get('statistics', {})
            surface_matches = combined_stats.get('matches', 0)
            surface_wins = combined_stats.get('wins', 0)
            tiebreaks_won = combined_stats.get('tiebreaksWon', 0)
            tiebreaks_total = tiebreaks_won + combined_stats.get('tiebreakLosses', 0)
            
            if surface_matches > 0:
                # Calculate statistical confidence using the same method
                confidence_score = self._calculate_statistical_confidence(surface_matches, surface_wins)
                
                # Log the surface data found
                self._log_surface_data("Unknown Player", player_id, surface, 
                                     surface_matches, surface_wins, tiebreaks_won, 
                                     tiebreaks_total, confidence_score, "From enhanced stats")
                
                return surface_matches, confidence_score
            else:
                # Log zero matches found
                self._log_surface_data("Unknown Player", player_id, surface, 0, 0, 
                                     extra_info="No surface matches in enhanced stats")
                return 0, 0.0  # No surface matches
                
        except Exception as e:
            # Log the exception
            self._log_surface_data("Unknown Player", player_id, surface, 0, 0, 
                                 extra_info=f"Exception: {str(e)}")
            return 0, 0.0  # Default to no data on any error

    def _calculate_mental_toughness_score(self, player_id: int) -> float:
        """
        Calculate mental toughness score (tiebreak rate) for a player
        Used by enhanced probability caps for mental gap penalties
        """
        try:
            mental_analysis = self.analyze_player_mental_toughness("", player_id)
            tiebreak_rate = mental_analysis.get('tiebreak_rate', 0.5)
            
            # Handle cases where tiebreak_rate is not a number
            if isinstance(tiebreak_rate, str) or tiebreak_rate is None:
                return 0.5  # Default to average if no data
            
            return float(tiebreak_rate)
        except Exception:
            return 0.5  # Default to average mental toughness if calculation fails

    def _calculate_statistical_confidence(self, matches: float, wins: float) -> float:
        """Calculate statistical confidence score based on sample size using Wilson Score Interval"""
        if matches == 0:
            return 0.0
        
        import math
        win_rate = wins / matches
        z = 1.96  # 95% confidence interval
        n = matches
        p = win_rate
        
        # Wilson Score Interval width calculation
        denominator = 1 + z**2/n
        adjustment = z * math.sqrt((p*(1-p) + z**2/(4*n))/n)
        confidence_width = 2 * adjustment / denominator
        
        # Convert to confidence score (0-1, higher = more confident)
        confidence_score = max(0.0, min(1.0, 1 - confidence_width))
        return confidence_score
    
    def _apply_sample_size_weighting(self, raw_value: float, sample_size: float, 
                                     neutral_value: float = 0.5, full_confidence_threshold: float = 20.0) -> tuple:
        """
        Apply Bayesian shrinkage to regress small samples toward a neutral value.
        
        Args:
            raw_value: The calculated value (e.g., win rate, percentage)
            sample_size: Number of observations (matches, points, etc.)
            neutral_value: Value to regress toward (default 0.5 for rates)
            full_confidence_threshold: Sample size needed for 100% confidence (default 20)
            
        Returns:
            Tuple of (weighted_value, confidence_factor)
        """
        if sample_size == 0:
            return neutral_value, 0.0
        
        # Confidence scales linearly from 0 to 100% at threshold
        confidence = min(sample_size / full_confidence_threshold, 1.0)
        
        # Bayesian shrinkage: blend raw value with neutral based on confidence
        weighted_value = (raw_value * confidence) + (neutral_value * (1 - confidence))
        
        return weighted_value, confidence

    def calculate_enhanced_surface_performance(self, player_id: int, surface: str = 'Unknown') -> tuple:
        """Calculate surface-specific performance using TWO YEARS of data with intelligent fallbacks"""
        try:
            # 🚀 ENHANCED: Use 2-year data collection for better sample sizes
            current_year = datetime.now().year
            previous_year = current_year - 1
            
            # Fetch both years of data
            current_stats = self.player_service.get_player_year_statistics(player_id, current_year)
            previous_stats = self.player_service.get_player_year_statistics(player_id, previous_year)
            
            # Use enhanced statistics handler for intelligent multi-year combination
            enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player_id, surface)
            
            # Log comprehensive data quality assessment
            self._log_data_quality("Unknown Player", player_id, surface, 
                                 enhanced_stats=enhanced_stats, 
                                 context="Surface Performance Calculation")
            
            if enhanced_stats.get('has_404_error'):
                # Fallback to legacy single-year method if enhanced stats unavailable
                return self._calculate_single_year_surface_performance(player_id, surface)
            
            # Extract combined surface statistics from enhanced handler
            combined_stats = enhanced_stats.get('statistics', {})
            
            # Extract current-year-only stats for quality checking
            current_year_stats = enhanced_stats.get('current_year_only', {})
            self._current_year_surface_stats = {
                'matches': current_year_stats.get('matches', 0),
                'wins': current_year_stats.get('wins', 0),
                'win_rate': (current_year_stats.get('wins', 0) / current_year_stats.get('matches', 1)) if current_year_stats.get('matches', 0) > 0 else 0
            }
            
            # Calculate overall win rate from combined data
            overall_win_rate = self._calculate_overall_win_rate_from_enhanced(enhanced_stats)
            data_quality = "no_surface_data"
            
            # Look for surface-specific data in combined statistics
            surface_matches = combined_stats.get('matches', 0)
            surface_wins = combined_stats.get('wins', 0)
            
            # ENHANCED: Statistical confidence-weighted surface calculation
            if surface_matches > 0:
                surface_win_rate = surface_wins / surface_matches
                confidence_score = self._calculate_statistical_confidence(surface_matches, surface_wins)
                
                # Confidence-based blending: Higher confidence = more weight on surface data
                # Scale confidence score to reasonable range for surface weighting
                confidence_factor = min(confidence_score * 1.5, 1.0)  # Boost confidence slightly
                
                # Determine data quality and blending based on BOTH sample size AND confidence
                if surface_matches >= 30:  # Very strong sample
                    surface_weight = confidence_factor
                    data_quality = f"confident_strong (conf: {confidence_score:.2f})"
                elif surface_matches >= 15:  # Strong sample  
                    surface_weight = confidence_factor * 0.9
                    data_quality = f"confident_good (conf: {confidence_score:.2f})"
                elif surface_matches >= 8:  # Moderate sample
                    surface_weight = confidence_factor * 0.7
                    data_quality = f"confident_moderate (conf: {confidence_score:.2f})"
                elif surface_matches >= 3:  # Weak sample
                    surface_weight = confidence_factor * 0.4
                    data_quality = f"confident_weak (conf: {confidence_score:.2f})"
                else:  # Very weak sample
                    surface_weight = confidence_factor * 0.2
                    data_quality = f"confident_minimal (conf: {confidence_score:.2f})"
                
                # Apply confidence-weighted blending
                overall_weight = 1.0 - surface_weight
                performance = (surface_win_rate * surface_weight) + (overall_win_rate * overall_weight)
                
                # Flag when confidence is particularly low
                if confidence_score < 0.3:
                    data_quality += " [LOW_CONFIDENCE]"
                    
                # Log surface performance calculation
                tiebreaks_won = combined_stats.get('tiebreaksWon', 0)
                tiebreaks_total = tiebreaks_won + combined_stats.get('tiebreakLosses', 0)
                self._log_surface_data("Unknown Player", player_id, surface, 
                                     surface_matches, surface_wins, tiebreaks_won, 
                                     tiebreaks_total, confidence_score, 
                                     f"Surface calc - Final perf: {performance:.1%}, Data: {data_quality}")
            else:
                # No surface-specific data found
                performance = overall_win_rate
                data_quality = "no_surface_data"
                
                # Log no surface data
                self._log_surface_data("Unknown Player", player_id, surface, 0, 0, 
                                     extra_info=f"No surface data - Using overall: {overall_win_rate:.1%}")
            
            return (performance, surface, data_quality)
                
        except Exception as e:
            print(f"⚠️ Enhanced surface calculation failed for player {player_id}: {e}")
            # Fallback to single-year method
            return self._calculate_single_year_surface_performance(player_id, surface)
    
    def _calculate_single_year_surface_performance(self, player_id: int, surface: str = 'Unknown') -> tuple:
        """Fallback: Calculate surface-specific performance using single year (legacy method)"""
        try:
            # Get year statistics
            current_year = datetime.now().year
            year_stats = self.player_service.get_player_year_statistics(player_id, current_year)
            
            # Calculate overall win rate as intelligent fallback (not arbitrary 0.5)
            overall_win_rate = self._calculate_overall_win_rate(year_stats)
            data_quality = "no_surface_data"
            
            if not year_stats or not year_stats.get('statistics'):
                return (overall_win_rate, surface, data_quality)
            
            # Look for exact surface match first
            exact_surface_stats = None
            fallback_surface_stats = None
            # ALWAYS return tournament surface - historical surface names may differ
            actual_surface_found = surface
            
            for stat in year_stats['statistics']:
                stat_surface = stat.get('groundType', '')
                
                # Exact match (e.g., "Hardcourt outdoor" == "Hardcourt outdoor")
                if stat_surface.lower() == surface.lower():
                    exact_surface_stats = stat
                    # Keep tournament surface name, not historical surface name
                    data_quality = "exact_match"
                    break
                    
                # Fallback: partial match (e.g., "Hardcourt" in "Hardcourt outdoor")
                if 'hardcourt' in stat_surface.lower() and 'hardcourt' in surface.lower():
                    if not fallback_surface_stats:  # Take first match
                        fallback_surface_stats = stat
                        # Keep tournament surface name, not historical surface name
                        data_quality = "partial_match"
                elif 'clay' in stat_surface.lower() and 'clay' in surface.lower():
                    if not fallback_surface_stats:
                        fallback_surface_stats = stat
                        # Keep tournament surface name, not historical surface name
                        data_quality = "partial_match"
                elif 'grass' in stat_surface.lower() and 'grass' in surface.lower():
                    if not fallback_surface_stats:
                        fallback_surface_stats = stat
                        # Keep tournament surface name, not historical surface name
                        data_quality = "partial_match"
            
            # Use exact match if available, otherwise fallback
            surface_stats = exact_surface_stats or fallback_surface_stats
            
            if not surface_stats:
                # No surface-specific data - use overall win rate instead of 0.5
                return (overall_win_rate, surface, "no_surface_data")
            
            # Calculate win rate with intelligent confidence adjustment
            matches = surface_stats.get('matches', 0)
            wins = surface_stats.get('wins', 0)
            
            if matches >= 5:  # Strong sample size
                performance = wins / matches
                data_quality = f"{data_quality}_strong" if "match" in data_quality else "strong_sample"
            elif matches >= 2:  # Moderate sample size
                surface_win_rate = wins / matches
                # Blend surface data with overall performance for small samples
                # More matches = more weight to surface data
                surface_weight = matches / 5.0  # 0.4 to 1.0
                overall_weight = 1.0 - surface_weight
                performance = (surface_win_rate * surface_weight) + (overall_win_rate * overall_weight)
                data_quality = f"{data_quality}_moderate" if "match" in data_quality else "moderate_sample"
            else:
                # Very limited surface data - primarily use overall performance
                performance = overall_win_rate * 0.9 + (wins / max(matches, 1)) * 0.1
                data_quality = f"{data_quality}_weak" if "match" in data_quality else "weak_sample"
            
            return (performance, actual_surface_found, data_quality)
                
        except Exception as e:
            # Even in error cases, use overall win rate not 0.5
            overall_win_rate = self._calculate_overall_win_rate(year_stats if 'year_stats' in locals() else None)
            return (overall_win_rate, surface, "error_fallback")
    
    def _calculate_overall_win_rate_from_enhanced(self, enhanced_stats: dict) -> float:
        """Calculate overall win rate from enhanced statistics"""
        try:
            stats = enhanced_stats.get('statistics', {})
            total_matches = stats.get('matches', 0)
            total_wins = stats.get('wins', 0)
            
            if total_matches == 0:
                return 0.5  # Neutral fallback
            
            overall_rate = total_wins / total_matches
            
            # Apply confidence adjustment based on sample size
            if total_matches < 10:
                confidence = total_matches / 10.0
                overall_rate = overall_rate * confidence + 0.5 * (1 - confidence)
            
            return overall_rate
        except:
            return 0.5

    def calculate_enhanced_tiebreak_performance(self, player_id: int, surface: str = None) -> float:
        """Calculate tiebreak performance with year transition handling - NO FALLBACKS ALLOWED"""
        try:
            enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player_id, surface)
            
            # Log mental toughness data quality assessment
            mental_issues = []
            if enhanced_stats.get('has_404_error'):
                mental_issues.append("404 Error")
            
            # Check tiebreak sample size
            sample_sizes = enhanced_stats.get('sample_sizes', {})
            tiebreak_count = sample_sizes.get('tiebreaks', 0)
            if tiebreak_count < 3:
                mental_issues.append(f"Low TB sample ({tiebreak_count})")
                
            self._log_data_quality("Unknown Player", player_id, surface, 
                                 enhanced_stats=enhanced_stats, 
                                 issues=mental_issues,
                                 context="Mental Toughness Analysis")
            
            stats = enhanced_stats['statistics']
            reliability = enhanced_stats['reliability_score']
            
            # Check if we have any meaningful statistics at all
            if not stats or reliability == 0.0:
                raise ValueError(f"Player {player_id} has no reliable statistics available")
            
            # Check for tiebreak data FIRST - even if some years had 404s, we may have data from other years
            tb_won = stats.get('tiebreaksWon', 0)
            tb_lost = stats.get('tiebreakLosses', 0)
            tb_total = tb_won + tb_lost
            
            # CRITICAL: Only fail if we have NO tiebreak data AND a 404 error
            # If we have tiebreak data from at least one year, use it even if some years had 404s
            if tb_total == 0 and enhanced_stats.get('has_404_error'):
                raise ValueError(f"Player {player_id} has missing yearly statistics (404 errors) and no tiebreak data available")
            
            # If we have tiebreak data but some years had 404s, proceed anyway
            # (The enhanced_stats handler already combines data from available years)
            
            # Enhanced confidence-based tiebreak calculation
            if tb_total >= 3:  # Sufficient sample for base calculation
                tb_rate = tb_won / tb_total
                
                # Apply statistical confidence adjustment for sample size
                confidence_score = self._calculate_statistical_confidence(tb_total, tb_won)
                
                # For small tiebreak samples (3-10), add uncertainty penalty
                if tb_total < 10:
                    uncertainty_penalty = (1.0 - confidence_score) * 0.4  # Up to 40% regression
                    tb_rate = tb_rate * (1.0 - uncertainty_penalty) + 0.5 * uncertainty_penalty
                    
            elif tb_total > 0:  # VERY limited data (1-2 tiebreaks)
                # Calculate basic rate but heavily discount for extreme uncertainty
                raw_tb_rate = tb_won / tb_total
                confidence_score = self._calculate_statistical_confidence(tb_total, tb_won)
                
                # Extreme regression for tiny samples (especially single tiebreaks)
                # 1 tiebreak: heavy regression, 2 tiebreaks: moderate regression
                base_weight = min(0.3, tb_total * 0.15)  # 15% weight for 1, 30% for 2
                neutral_weight = 1.0 - base_weight
                
                # Additional confidence penalty
                final_weight = base_weight * confidence_score
                
                tb_rate = (raw_tb_rate * final_weight) + (0.5 * (1.0 - final_weight))
                
                # Flag extreme uncertainty for logging
                if tb_total == 1:
                    print(f"⚠️ Player {player_id}: Single tiebreak sample ({tb_won}/{tb_total}) - high uncertainty")
                    
            else:  # No tiebreak data at all
                raise ValueError(f"Player {player_id} has no tiebreak data in statistics")
            
            # Adjust confidence based on overall data reliability
            confidence_adjustment = 0.5 + (reliability * 0.5)  # 0.5 to 1.0 range
            return tb_rate * confidence_adjustment + 0.5 * (1 - confidence_adjustment)
        except Exception as e:
            print(f"❌ Cannot calculate tiebreak performance for player {player_id}: {e}")
            raise  # Re-raise to let caller handle the lack of data

    def calculate_enhanced_pressure_performance(self, player_id: int, surface: str = None) -> float:
        """Calculate pressure performance with year transition handling"""
        try:
            enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player_id, surface)
            stats = enhanced_stats['statistics']
            reliability = enhanced_stats['reliability_score']
            
            # Break point conversion
            bp_scored = stats.get('breakPointsScored', 0)
            bp_total = stats.get('breakPointsTotal', 0)
            conversion_rate = bp_scored / bp_total if bp_total >= 10 else 0.35  # Default for insufficient data
            
            # Break point save rate
            opp_bp_total = stats.get('opponentBreakPointsTotal', 0)
            opp_bp_scored = stats.get('opponentBreakPointsScored', 0)
            save_rate = (opp_bp_total - opp_bp_scored) / opp_bp_total if opp_bp_total >= 10 else 0.6
            
            # Combined pressure performance
            pressure_score = (conversion_rate * 0.6) + (save_rate * 0.4)
            
            # Adjust based on reliability
            confidence_adjustment = 0.5 + (reliability * 0.5)
            return pressure_score * confidence_adjustment + 0.5 * (1 - confidence_adjustment)
        except Exception as e:
            print(f"Error calculating pressure performance for player {player_id}: {e}")
            return 0.5

    def calculate_enhanced_serve_dominance(self, player_id: int, surface: str = None) -> float:
        """Calculate serve dominance with year transition handling"""
        try:
            enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player_id, surface)
            stats = enhanced_stats['statistics']
            reliability = enhanced_stats['reliability_score']
            
            matches = stats.get('matches', 1)
            
            # Aces per match
            aces_per_match = stats.get('aces', 0) / matches if matches > 0 else 0
            ace_score = min(aces_per_match / 15.0, 1.0)
            
            # First serve win rate
            first_serve_won = stats.get('firstServePointsScored', 0)
            first_serve_total = stats.get('firstServePointsTotal', 1)
            first_serve_rate = first_serve_won / first_serve_total if first_serve_total >= 20 else 0.65
            
            # Combined serve dominance
            raw_serve_score = (ace_score * 0.4) + (first_serve_rate * 0.6)
            
            # Apply sample-size weighting based on total serve points
            first_serve_points = stats.get('firstServePointsTotal', 0)
            
            # Apply Bayesian shrinkage: small samples regress toward 0.5 (neutral)
            serve_score, serve_confidence = self._apply_sample_size_weighting(
                raw_serve_score,
                first_serve_points / 10.0,  # Convert points to ~matches equivalent (10 points/match)
                neutral_value=0.5,
                full_confidence_threshold=20.0  # 200+ first serve points for full confidence
            )
            
            # Additional reliability adjustment from year blending
            reliability_adjustment = 0.5 + (reliability * 0.5)
            final_serve_score = serve_score * reliability_adjustment + 0.5 * (1 - reliability_adjustment)
            
            return final_serve_score
        except Exception as e:
            print(f"Error calculating serve dominance for player {player_id}: {e}")
            return 0.5
    
    def calculate_momentum(self, form_data: Dict[str, Any], player_id: int) -> float:
        """
        Calculate momentum score based on recent match results.
        
        Momentum considers:
        - Win/loss streak in last 5 matches
        - Quality of recent wins/losses
        - Recency weighting (more recent = higher impact)
        
        Returns: Score from -1.0 (terrible momentum) to +1.0 (great momentum)
        """
        try:
            # Get recent matches data
            matches_analyzed = form_data.get('matches_analyzed', 0)
            if matches_analyzed == 0:
                return 0.0
            
            # Get win rate from last 5 matches for momentum
            recent_win_rate = form_data.get('form_data', {}).get('match_win_rate', 0.5)
            
            # Simple momentum: recent win rate converted to -1 to +1 scale
            # 100% win rate = +1.0, 50% = 0.0, 0% = -1.0
            momentum = (recent_win_rate - 0.5) * 2.0
            
            # Cap at reasonable bounds
            return max(-1.0, min(1.0, momentum))
            
        except Exception as e:
            print(f"   ⚠️ Momentum calculation error for player {player_id}: {e}")
            return 0.0
    
    def get_enhanced_player_profile(self, player_id: int, opponent_ranking: Optional[int] = None, surface: str = 'Unknown') -> PlayerProfile:
        """Get comprehensive player profile for betting analysis"""
        
        # Track data quality for skip logic
        data_quality_issues = []
        
        try:
            # Get basic player info
            details = self.player_service.get_player_details(player_id)
            team_data = details.get('team', {})
            
            # Debug: Check if birthDateTimestamp exists
            birth_timestamp = team_data.get('playerTeamInfo', {}).get('birthDateTimestamp')
            if not birth_timestamp:
                print(f"⚠️ Missing birthDateTimestamp for player {player_id}: {team_data.get('name', 'Unknown')}")
                print(f"   playerTeamInfo keys: {list(team_data.get('playerTeamInfo', {}).keys())}")
            
            # Get rankings including UTR using updated MatchDataProvider service
            try:
                rankings = self.match_data_service.get_player_rankings(player_id)
                atp_rank = rankings.get('atp_ranking')
                wta_rank = rankings.get('wta_ranking')
                utr_rating = rankings.get('utr_rating')
                utr_position = rankings.get('utr_position')
                utr_verified = rankings.get('utr_verified', False)
            except Exception as e:
                if "404" in str(e) or "HTTP Error 404" in str(e):
                    data_quality_issues.append("Player rankings not found (404)")
                rankings = {}
                atp_rank = wta_rank = utr_rating = utr_position = None
                utr_verified = False
            
            # Get dual-weighted form analysis: recent + comprehensive
            # Recent form - HIGH WEIGHT (most predictive)
            recent_matches_count = self.config.FORM_ANALYSIS['recent_matches']
            recent_form_data = self.player_service.analyze_recent_form(player_id, recent_matches_count, opponent_ranking, surface)
            recent_form_score = recent_form_data.get('form_data', {}).get('form_quality_score', 0)
            
            # Comprehensive singles analysis - LOWER WEIGHT (context)
            comprehensive_matches_count = self.config.FORM_ANALYSIS['comprehensive_matches']
            comprehensive_matches = self.player_service.get_comprehensive_singles_matches(
                player_id, max_matches=comprehensive_matches_count, max_pages=5
            )
            comprehensive_form_score = 0
            if comprehensive_matches.get('events'):
                # Use the comprehensive matches data we already have instead of fetching again
                # Calculate form score from the comprehensive matches data
                total_matches = len(comprehensive_matches.get('events', []))
                if total_matches > 0:
                    # Simple form score based on match win rate from comprehensive data
                    wins = sum(1 for match in comprehensive_matches.get('events', []) 
                             if self._player_won_match(match, player_id))
                    comprehensive_form_score = (wins / total_matches) * 100
            
            # Calculate raw weighted combination: 70% recent + 30% comprehensive
            raw_form_score = (recent_form_score * 0.7) + (comprehensive_form_score * 0.3)
            
            # Apply sample-size weighting - account for matches analyzed
            recent_matches = recent_form_data.get('matches_analyzed', 0)
            comprehensive_matches_data = comprehensive_matches.get('events', [])
            comprehensive_count = len(comprehensive_matches_data)
            
            # Weight matches by their contribution to form score
            total_form_matches = (recent_matches * 0.7) + (comprehensive_count * 0.3)
            
            # Apply Bayesian shrinkage: small samples regress toward 50 (neutral)
            form_score, form_confidence = self._apply_sample_size_weighting(
                raw_form_score, 
                total_form_matches, 
                neutral_value=50.0,  # Neutral form score
                full_confidence_threshold=15.0  # 15 matches for full confidence (less than set wins)
            )
            
            print(f"\n   📊 FORM SCORE WEIGHTING:")
            print(f"      Raw score: {raw_form_score:.1f} from {total_form_matches:.1f} matches")
            print(f"      Confidence: {form_confidence:.1%} (100% at 15+ matches)")
            print(f"      Weighted score: {form_score:.1f} (regressed toward 50 by {(1-form_confidence)*100:.1f}%)")
            
            # Check for 404 errors in enhanced statistics (critical data)
            try:
                enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player_id, surface)
                
                # Log comprehensive player analysis data quality
                analysis_issues = []
                if enhanced_stats.get('has_404_error'):
                    data_quality_issues.append("Player statistics not found (404)")
                    analysis_issues.append("404 Error")
                
                # Check sample sizes for analysis
                sample_sizes = enhanced_stats.get('sample_sizes', {})
                if sample_sizes.get('matches', 0) < 10:
                    analysis_issues.append(f"Low match sample ({sample_sizes.get('matches', 0)})")
                if sample_sizes.get('tiebreaks', 0) < 5:
                    analysis_issues.append(f"Low TB sample ({sample_sizes.get('tiebreaks', 0)})")
                    
                self._log_data_quality("Unknown Player", player_id, surface,
                                     enhanced_stats=enhanced_stats,
                                     issues=analysis_issues,
                                     context="General Player Analysis")
                
            except Exception as e:
                if "404" in str(e) or "HTTP Error 404" in str(e):
                    data_quality_issues.append("Player statistics not found (404)")
            
            # Get enhanced surface-specific performance with year transition handling
            try:
                surface_result = self.calculate_enhanced_surface_performance(player_id, surface)
                if isinstance(surface_result, tuple):
                    if len(surface_result) == 3:
                        surface_win_rate, actual_surface, data_quality = surface_result
                        # Track data quality for potential weight adjustment
                        poor_data_quality = "weak" in data_quality or "no_surface" in data_quality
                    else:
                        surface_win_rate, _ = surface_result[:2]  # Legacy format support
                        poor_data_quality = False
                else:
                    # Fallback for unexpected return type - use overall performance
                    surface_win_rate = float(surface_result) if surface_result else 0.5
                    poor_data_quality = True
            except Exception as e:
                print(f"⚠️ Error in surface performance calculation for player {player_id}: {e}")
                surface_win_rate = 0.5
                poor_data_quality = True
            
            # Calculate momentum from recent matches (last 5 matches)
            momentum_score = self.calculate_momentum(recent_form_data, player_id)
            
            # Store surface data quality for weight adjustment later
            setattr(self, f'_surface_data_quality_{player_id}', poor_data_quality)
            
            return PlayerProfile(
                id=player_id,
                name=team_data.get('name', 'Unknown'),
                age=self.calculate_age(team_data.get('playerTeamInfo', {}).get('birthDateTimestamp')) or 'Unknown',
                gender=team_data.get('gender', 'Unknown'),
                country=team_data.get('country', {}).get('name', 'Unknown'),
                atp_ranking=atp_rank,
                wta_ranking=wta_rank,
                utr_rating=utr_rating,
                utr_position=utr_position,
                utr_verified=utr_verified,
                recent_form_score=form_score,
                surface_win_rate=surface_win_rate,
                head_to_head_record={'wins': 0, 'losses': 0},  # Would need H2H API
                # Weighted clutch performance: 70% recent + 30% comprehensive
                clutch_performance=(
                    (recent_form_data.get('form_data', {}).get('clutch_rate', 0) * 0.7) +
                    (comprehensive_form_score / 100 * 0.3)  # Use form score as clutch proxy for comprehensive
                ),
                injury_status='Unknown',  # Would need injury data
                momentum_score=momentum_score,
                data_quality_issues=data_quality_issues if data_quality_issues else None
            )
            
        except Exception as e:
            print(f"❌ CRITICAL: Unable to get player profile for {player_id}: {e}")
            print(f"   🚫 NO FALLBACK - Match will be skipped entirely")
            print(f"   ⚠️ Cannot make reliable predictions without real player data")
            return None  # Return None instead of fallback - match will be skipped
    
    def should_skip_match_due_to_data_quality(self, player1: PlayerProfile, player2: PlayerProfile) -> Tuple[bool, str]:
        """
        Check if match should be skipped due to insufficient player data (404 errors)
        
        Returns:
            Tuple[bool, str]: (should_skip, reason)
        """
        critical_issues = []
        
        # Check player 1 data quality
        if player1.data_quality_issues:
            for issue in player1.data_quality_issues:
                if "404" in issue or "not found" in issue or "unavailable" in issue:
                    critical_issues.append(f"{player1.name}: {issue}")
        
        # Check player 2 data quality  
        if player2.data_quality_issues:
            for issue in player2.data_quality_issues:
                if "404" in issue or "not found" in issue or "unavailable" in issue:
                    critical_issues.append(f"{player2.name}: {issue}")
        
        # Additional check: Analyze mental toughness to see if tiebreak data is missing
        try:
            player1_mental = self.analyze_player_mental_toughness(player1.name, player1.id)
            if player1_mental.get('data_quality_issue'):
                critical_issues.append(f"{player1.name}: {player1_mental['data_quality_issue']}")
                
            player2_mental = self.analyze_player_mental_toughness(player2.name, player2.id)
            if player2_mental.get('data_quality_issue'):
                critical_issues.append(f"{player2.name}: {player2_mental['data_quality_issue']}")
        except Exception:
            # If mental toughness analysis fails, that's also a data quality issue
            critical_issues.append("Mental toughness analysis failed")
        
        if critical_issues:
            reason = f"Insufficient player data: {'; '.join(critical_issues)}"
            return True, reason
            
        return False, ""
    
    def _log_skip_with_stats(
        self,
        reason: str,
        player1: PlayerProfile,
        player2: PlayerProfile,
        tournament: str,
        surface: str
    ):
        """Helper to log skip with detailed player stats"""
        current_year = datetime.now().year
        
        # Determine skip tier from reason
        reason_type = "OTHER"
        if "INSUFFICIENT DATA" in reason:
            reason_type = "TIER_0"
        elif "NO 2025 DATA" in reason or "NO 2024 DATA" in reason:
            reason_type = "TIER_1"
        elif "poor" in reason.lower() or "extremely poor" in reason.lower():
            reason_type = "TIER_2"
        elif "UNABLE TO VERIFY" in reason:
            reason_type = "TIER_3"
        
        # Extract player 1 stats
        try:
            p1_stats_data = self.stats_handler.get_enhanced_player_statistics(player1.id, surface)
            p1_curr = p1_stats_data.get('current_year_only', {})
            p1_stats = {
                'current_year': current_year,
                'current_year_matches': p1_curr.get('matches', 0),
                'current_year_wins': p1_curr.get('wins', 0),
                'current_year_win_rate': p1_curr.get('win_rate', 0.0),
                'blended_matches': p1_stats_data.get('matches', 0),
                'blended_wins': p1_stats_data.get('wins', 0),
                'blended_win_rate': p1_stats_data.get('win_rate', 0.0),
                'form_score': player1.recent_form_score,
                'ranking': player1.atp_ranking or player1.wta_ranking,
                'utr': player1.utr_rating,
                'aces_per_match': p1_stats_data.get('aces_per_match', 0),
            }
        except Exception:
            p1_stats = {
                'form_score': player1.recent_form_score,
                'ranking': player1.atp_ranking or player1.wta_ranking,
                'utr': player1.utr_rating
            }
        
        # Extract player 2 stats
        try:
            p2_stats_data = self.stats_handler.get_enhanced_player_statistics(player2.id, surface)
            p2_curr = p2_stats_data.get('current_year_only', {})
            p2_stats = {
                'current_year': current_year,
                'current_year_matches': p2_curr.get('matches', 0),
                'current_year_wins': p2_curr.get('wins', 0),
                'current_year_win_rate': p2_curr.get('win_rate', 0.0),
                'blended_matches': p2_stats_data.get('matches', 0),
                'blended_wins': p2_stats_data.get('wins', 0),
                'blended_win_rate': p2_stats_data.get('win_rate', 0.0),
                'form_score': player2.recent_form_score,
                'ranking': player2.atp_ranking or player2.wta_ranking,
                'utr': player2.utr_rating,
                'aces_per_match': p2_stats_data.get('aces_per_match', 0),
            }
        except Exception:
            p2_stats = {
                'form_score': player2.recent_form_score,
                'ranking': player2.atp_ranking or player2.wta_ranking,
                'utr': player2.utr_rating
            }
        
        # Log to skip logger
        self.skip_logger.log_skip(
            reason_type=reason_type,
            player1_name=player1.name,
            player2_name=player2.name,
            tournament=tournament,
            surface=surface,
            reason=reason,
            player1_stats=p1_stats,
            player2_stats=p2_stats
        )
    
    def should_skip_due_to_poor_current_year_performance(
        self, 
        player1: PlayerProfile, 
        player2: PlayerProfile, 
        surface: str,
        current_year: int
    ) -> Tuple[bool, str]:
        """
        Check if match should be skipped due to poor/missing performance on the surface.
        
        CRITICAL FIX: Year-blending was making poor 2025 performance (25% win rate) look better (~40-55%).
        This checks ACTUAL current year performance for TIER 1-3, not blended stats.
        
        MULTI-YEAR UPDATE: TIER 0 now adapts based on year mode:
        - 3-year mode: Uses blended match count (weighted across 2023-2024-2025)
        - 2-year mode: Uses current year matches only
        
        Skip conditions (Four-tier approach):
        TIER 0: If EITHER player has < 5 matches → SKIP (insufficient sample size)
                - 3-year mode: Check blended matches (e.g., 6.36 weighted matches)
                - 2-year mode: Check current-year matches only
        TIER 1: If EITHER player has 0 current-year matches → SKIP (pure extrapolation)
        TIER 2: If BOTH players have < 45% win rate (min 3 matches) → SKIP (both struggling)
                OR if ONE player has < 30% win rate (min 4 matches) → SKIP (extremely poor)
        TIER 3: If BOTH players have < 50% win rate (min 5 matches) → SKIP (both mediocre/coin flip)
        
        Returns:
            Tuple[bool, str]: (should_skip, reason)
        """
        MIN_MATCHES_THRESHOLD = 3  # Minimum matches to evaluate
        POOR_PERFORMANCE_THRESHOLD = 0.45  # 45% win rate threshold (INCREASED from 40%)
        
        # Get current-year-only stats for both players
        # These stats are stored temporarily during surface performance calculation
        player1_curr_year = getattr(self, '_current_year_surface_stats', None)
        
        # Need to calculate for both players
        # Temporarily fetch their current-year stats
        try:
            # Validate player IDs exist
            if not hasattr(player1, 'id') or not player1.id:
                raise AttributeError(f"{player1.name} has no valid player ID")
            if not hasattr(player2, 'id') or not player2.id:
                raise AttributeError(f"{player2.name} has no valid player ID")
            
            p1_stats = self.stats_handler.get_enhanced_player_statistics(player1.id, surface)
            if not p1_stats or 'current_year_only' not in p1_stats:
                raise ValueError(f"No current_year_only stats returned for {player1.name}")
            
            p1_curr = p1_stats.get('current_year_only', {})
            p1_matches = p1_curr.get('matches', 0)
            p1_wins = p1_curr.get('wins', 0)
            p1_win_rate = (p1_wins / p1_matches) if p1_matches > 0 else 0.0  # No matches = 0% win rate
            
            print(f"\n🔍 SKIP CHECK DEBUG - {player1.name}:")
            print(f"   Current year stats: {p1_matches} matches, {p1_wins} wins, {p1_win_rate:.1%}")
            
            p2_stats = self.stats_handler.get_enhanced_player_statistics(player2.id, surface)
            if not p2_stats or 'current_year_only' not in p2_stats:
                raise ValueError(f"No current_year_only stats returned for {player2.name}")
            
            p2_curr = p2_stats.get('current_year_only', {})
            p2_matches = p2_curr.get('matches', 0)
            p2_wins = p2_curr.get('wins', 0)
            p2_win_rate = (p2_wins / p2_matches) if p2_matches > 0 else 0.0  # No matches = 0% win rate
            
            print(f"🔍 SKIP CHECK DEBUG - {player2.name}:")
            print(f"   Current year stats: {p2_matches} matches, {p2_wins} wins, {p2_win_rate:.1%}")
            
            # TIER 0 CHECK: Skip if EITHER player has insufficient data (< 5 matches in 2-year mode, < 3 blended in 3-year mode)
            # When 3-year mode is enabled, use blended match count instead of just current year
            # Note: Lower threshold for 3-year mode because blended matches represent data from multiple years
            MIN_DATA_THRESHOLD_2_YEAR = 5
            MIN_DATA_THRESHOLD_3_YEAR = 3  # Lower threshold since blended = weighted sum across years
            
            # Check if 3-year mode is enabled
            use_three_year = False
            if self.config and hasattr(self.config, 'MULTI_YEAR_STATS'):
                use_three_year = self.config.MULTI_YEAR_STATS.get('enable_three_year_stats', False)
            
            if use_three_year:
                # Use blended match count from combined statistics
                p1_blended_matches = p1_stats.get('statistics', {}).get('matches', 0)
                p2_blended_matches = p2_stats.get('statistics', {}).get('matches', 0)
                
                print(f"   🔄 3-YEAR MODE: Blended matches: P1={p1_blended_matches:.1f}, P2={p2_blended_matches:.1f}")
                
                if p1_blended_matches < MIN_DATA_THRESHOLD_3_YEAR or p2_blended_matches < MIN_DATA_THRESHOLD_3_YEAR:
                    low_data_players = []
                    if p1_blended_matches < MIN_DATA_THRESHOLD_3_YEAR:
                        low_data_players.append(f"{player1.name} ({p1_blended_matches:.1f} blended matches)")
                    if p2_blended_matches < MIN_DATA_THRESHOLD_3_YEAR:
                        low_data_players.append(f"{player2.name} ({p2_blended_matches:.1f} blended matches)")
                    
                    reason = (f"⚠️  INSUFFICIENT DATA on {surface} for: {', '.join(low_data_players)}. "
                             f"Need minimum {MIN_DATA_THRESHOLD_3_YEAR} blended matches (3-year weighted) - predictions unreliable on small samples")
                    print(f"\n{reason}")
                    return True, reason
            else:
                # Use current year match count only (standard 2-year mode)
                if p1_matches < MIN_DATA_THRESHOLD_2_YEAR or p2_matches < MIN_DATA_THRESHOLD_2_YEAR:
                    low_data_players = []
                    if p1_matches < MIN_DATA_THRESHOLD_2_YEAR:
                        low_data_players.append(f"{player1.name} ({p1_matches} matches)")
                    if p2_matches < MIN_DATA_THRESHOLD_2_YEAR:
                        low_data_players.append(f"{player2.name} ({p2_matches} matches)")
                    
                    reason = (f"⚠️  INSUFFICIENT DATA on {surface} for: {', '.join(low_data_players)}. "
                             f"Need minimum {MIN_DATA_THRESHOLD_2_YEAR} {current_year} matches - predictions unreliable on small samples")
                    print(f"\n{reason}")
                    return True, reason
            
            # TIER 1 CHECK: Skip if EITHER player has ZERO current-year matches
            if p1_matches == 0 or p2_matches == 0:
                zero_data_players = []
                if p1_matches == 0:
                    zero_data_players.append(player1.name)
                if p2_matches == 0:
                    zero_data_players.append(player2.name)
                
                reason = (f"🚨 NO {current_year} DATA on {surface} for: {', '.join(zero_data_players)}. "
                         f"Predictions rely purely on {current_year-1} extrapolation - UNRELIABLE")
                print(f"\n{reason}")
                return True, reason
            
            # TIER 2 CHECK DISABLED FOR +1.5 SETS BETTING
            # "Both poor" doesn't matter for +1.5 sets - one will still win a set!
            # Only skip if performance is SO BAD it indicates data quality issues
            # 
            # OLD LOGIC (REMOVED):
            # p1_poor = (p1_matches >= MIN_MATCHES_THRESHOLD and p1_win_rate < POOR_PERFORMANCE_THRESHOLD)
            # p2_poor = (p1_matches >= MIN_MATCHES_THRESHOLD and p2_win_rate < POOR_PERFORMANCE_THRESHOLD)
            # if p1_poor and p2_poor: skip  ← Wrong for +1.5 sets!
            #
            # KEY INSIGHT: +1.5 sets is about RELATIVE performance, not absolute.
            # Even Kawa (33%) vs Bronzetti (39%) - Bronzetti is clearly better!
            
            # Also skip if one player is extremely poor (< 30% with 4+ matches)
            EXTREME_POOR_THRESHOLD = 0.30
            EXTREME_MATCHES_THRESHOLD = 4
            
            if p1_matches >= EXTREME_MATCHES_THRESHOLD and p1_win_rate < EXTREME_POOR_THRESHOLD:
                reason = (f"{player1.name} has extremely poor {current_year} {surface} form: "
                         f"{p1_win_rate:.1%} ({p1_wins}/{p1_matches} matches)")
                return True, reason
                
            if p2_matches >= EXTREME_MATCHES_THRESHOLD and p2_win_rate < EXTREME_POOR_THRESHOLD:
                reason = (f"{player2.name} has extremely poor {current_year} {surface} form: "
                         f"{p2_win_rate:.1%} ({p2_wins}/{p2_matches} matches)")
                return True, reason
            
            # TIER 3 CHECK DISABLED FOR +1.5 SETS BETTING
            # "Both mediocre" (<50%) doesn't matter - we predict based on RELATIVE performance!
            #
            # OLD LOGIC (REMOVED):
            # MEDIOCRE_THRESHOLD = 0.50
            # if p1_mediocre and p2_mediocre: skip ← Wrong for +1.5 sets!
            #
            # EXAMPLE: Player A (45%) vs Player B (48%) on surface
            # - Both < 50% (mediocre)
            # - But Player B is CLEARLY better (+3% edge)
            # - Player B should win at least one set!
            #
            # Only skip for data quality issues (TIER 0/1) or extreme cases (< 30%)
            
            return False, ""
            
        except Exception as e:
            # CRITICAL: If we can't verify current-year stats, SKIP the bet for safety
            reason = f"⚠️  UNABLE TO VERIFY CURRENT-YEAR PERFORMANCE: {type(e).__name__}: {e}"
            print(f"\n{reason}")
            print(f"   Defaulting to SKIP for safety - cannot confirm {current_year} reliability")
            return True, reason
    
    # REMOVED: Duplicate calculate_enhanced_tiebreak_performance method - using the no-fallback version above
    
    def calculate_enhanced_pressure_performance(self, player_id: int, surface: str = None) -> float:
        """Calculate pressure performance with year transition handling"""
        try:
            enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player_id, surface)
            stats = enhanced_stats['statistics']
            reliability = enhanced_stats['reliability_score']
            
            # Break point conversion
            bp_scored = stats.get('breakPointsScored', 0)
            bp_total = stats.get('breakPointsTotal', 1)
            conversion_rate = bp_scored / bp_total if bp_total >= 10 else 0.35  # Default for insufficient data
            
            # Break point save rate
            opp_bp_total = stats.get('opponentBreakPointsTotal', 1)
            opp_bp_scored = stats.get('opponentBreakPointsScored', 0)
            save_rate = (opp_bp_total - opp_bp_scored) / opp_bp_total if opp_bp_total >= 10 else 0.6
            
            # Combined pressure performance
            raw_pressure_score = (conversion_rate * 0.6) + (save_rate * 0.4)
            
            # Apply sample-size weighting based on total break points
            total_bp_sample = bp_total + opp_bp_total
            
            # Apply Bayesian shrinkage: small samples regress toward 0.5 (neutral)
            pressure_score, pressure_confidence = self._apply_sample_size_weighting(
                raw_pressure_score,
                total_bp_sample,
                neutral_value=0.5,
                full_confidence_threshold=30.0  # 30 total break points for full confidence
            )
            
            # Additional reliability adjustment from year blending
            reliability_adjustment = 0.5 + (reliability * 0.5)
            final_pressure_score = pressure_score * reliability_adjustment + 0.5 * (1 - reliability_adjustment)
            
            return final_pressure_score
            
        except Exception as e:
            print(f"   ⚠️ Pressure stats error for player {player_id}: {e}")
            return 0.5  # Neutral fallback
    
    def calculate_return_of_serve_performance(self, player_id: int, surface: str = None) -> float:
        """
        Calculate return-of-serve performance - Hannah Fry: "1% better at returning = amplified advantage"
        This is crucial for breaking the serve advantage
        """
        try:
            enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player_id, surface)
            stats = enhanced_stats['statistics']
            reliability = enhanced_stats['reliability_score']
            
            # Return game statistics
            return_games_won = stats.get('returnGamesWon', 0)
            return_games_played = stats.get('returnGamesPlayed', 1)
            
            # Break point conversion (key return metric)
            break_points_converted = stats.get('breakPointsScored', 0)
            break_points_faced = stats.get('breakPointsTotal', 1)
            
            # Calculate return performance metrics
            if return_games_played >= 20:  # Sufficient data
                return_game_win_rate = return_games_won / return_games_played
            else:
                return_game_win_rate = 0.25  # Tennis average for return games
                
            if break_points_faced >= 5:  # Some break point data
                break_point_conversion = break_points_converted / break_points_faced
            else:
                break_point_conversion = 0.35  # Tennis average
                
            # Weighted return performance: 60% return games + 40% break points
            # Break points are crucial moments where return skill shows
            raw_return_performance = (return_game_win_rate * 0.6) + (break_point_conversion * 0.4)
            
            # Apply sample-size weighting based on return games played
            # Apply Bayesian shrinkage: small samples regress toward 0.25 (tennis average for return)
            return_performance, return_confidence = self._apply_sample_size_weighting(
                raw_return_performance,
                return_games_played,
                neutral_value=0.25,  # Tennis average for return games
                full_confidence_threshold=30.0  # 30 return games for full confidence
            )
            
            # Apply Hannah Fry amplification for return performance
            if hasattr(self, 'config') and self.config.ENHANCED_FEATURES.get('hannah_fry_amplification', False):
                # Returns above 30% are excellent (tennis average ~25%)
                if return_performance > 0.30:
                    return_performance = self.config.apply_hannah_fry_amplification(
                        return_performance - 0.25, 'return'
                    ) + 0.25
            
            # Adjust based on data reliability
            confidence_adjustment = 0.5 + (reliability * 0.5)
            return return_performance * confidence_adjustment + 0.25 * (1 - confidence_adjustment)
            
        except Exception as e:
            print(f"   ⚠️ Return serve stats error for player {player_id}: {e}")
            return 0.25  # Tennis average fallback
    
    def calculate_enhanced_serve_dominance(self, player_id: int, surface: str = None) -> float:
        """Calculate serve dominance with year transition handling"""
        try:
            enhanced_stats = self.stats_handler.get_enhanced_player_statistics(player_id, surface)
            stats = enhanced_stats['statistics']
            reliability = enhanced_stats['reliability_score']
            
            matches = max(stats.get('matches', 1), 1)
            
            # Aces per match
            aces_per_match = stats.get('aces', 0) / matches
            ace_score = min(aces_per_match / 15.0, 1.0)  # 15+ aces/match = 1.0
            
            # First serve win rate
            first_serve_won = stats.get('firstServePointsScored', 0)
            first_serve_total = max(stats.get('firstServePointsTotal', 1), 1)
            first_serve_rate = first_serve_won / first_serve_total if first_serve_total >= 20 else 0.65
            
            # Combined serve dominance
            serve_score = (ace_score * 0.4) + (first_serve_rate * 0.6)
            
            # Adjust based on reliability
            confidence_adjustment = 0.5 + (reliability * 0.5)
            return serve_score * confidence_adjustment + 0.5 * (1 - confidence_adjustment)
            
        except Exception as e:
            print(f"   ⚠️ Serve stats error for player {player_id}: {e}")
            return 0.5  # Neutral fallback
    


    
    def analyze_crowd_sentiment_confidence(self, event_id: int, predicted_winner: str, 
                                         player1_name: str, player2_name: str, 
                                         base_confidence: float, tournament_level: str = "Unknown") -> Dict[str, Any]:
        """
        Analyze crowd sentiment as a confidence modifier using sophisticated framework
        
        Returns:
        - adjusted_confidence: Modified confidence level
        - crowd_analysis: Detailed breakdown of crowd impact
        """
        try:
            votes_data = self.player_service.get_match_votes(event_id)
            vote_info = votes_data.get('vote', {})
            vote1 = vote_info.get('vote1', 0)
            vote2 = vote_info.get('vote2', 0)
            total_votes = vote1 + vote2
            
            if total_votes == 0:
                return {
                    'adjusted_confidence': base_confidence,
                    'crowd_analysis': 'No crowd data available',
                    'confidence_adjustment': 0.0,
                    'crowd_favorite': 'Unknown',
                    'crowd_percentage': 0,
                    'vote_volume': 'None'
                }
            
            # Determine crowd favorite and percentage
            vote1_percentage = vote1 / total_votes
            vote2_percentage = vote2 / total_votes
            
            if vote1_percentage > vote2_percentage:
                crowd_favorite = player1_name
                crowd_percentage = vote1_percentage
            else:
                crowd_favorite = player2_name  
                crowd_percentage = vote2_percentage
            
            # Classify vote volume
            if total_votes < self.CROWD_CONFIDENCE_THRESHOLDS['ignore_threshold']:
                volume_category = 'Low'
                volume_impact = 'ignore'
            elif total_votes < self.CROWD_CONFIDENCE_THRESHOLDS['light_threshold']:
                volume_category = 'Medium'
                volume_impact = 'light'
            elif total_votes < self.CROWD_CONFIDENCE_THRESHOLDS['serious_threshold']:
                volume_category = 'High'
                volume_impact = 'serious'
            else:
                volume_category = 'Very High'
                volume_impact = 'major'
            
            # Determine if crowd agrees with our model
            crowd_agrees = (crowd_favorite == predicted_winner)
            
            # CRITICAL: Check for crowd sentiment circuit breaker before adjusting confidence
            if not crowd_agrees:
                crowd_disagreement_pct = crowd_percentage
                circuit_breaker_check = self.config.check_crowd_sentiment_circuit_breaker(
                    crowd_disagreement_pct, total_votes
                )
                
                if circuit_breaker_check['skip_bet']:
                    return {
                        'adjusted_confidence': -1.0,  # Special value to indicate skip
                        'crowd_analysis': circuit_breaker_check['reason'],
                        'confidence_adjustment': 0.0,
                        'crowd_favorite': crowd_favorite,
                        'crowd_percentage': crowd_percentage,
                        'vote_volume': volume_category,
                        'circuit_breaker_triggered': True,
                        'skip_reason': circuit_breaker_check['reason']
                    }
            
            # Calculate confidence adjustment based on framework
            confidence_adjustment = 0.0
            adjustment_reason = ""
            
            if volume_impact == 'ignore':
                # <100 votes: Ignore completely
                confidence_adjustment = 0.0
                adjustment_reason = f"Ignoring {total_votes} votes (insufficient volume)"
                
            elif crowd_agrees:
                # Crowd agrees with our model - confidence boost
                # CRITICAL FIX: Cap maximum crowd boost to +10% (lesson from Diallo failure)
                # Previous +20% boost turned marginal predictions into overconfident "guarantees"
                if volume_impact == 'light':
                    confidence_adjustment = 0.05  # +5%
                    adjustment_reason = f"Crowd validation (+5% confidence): {crowd_percentage:.1%} of {total_votes:,} votes"
                elif volume_impact == 'serious':
                    confidence_adjustment = 0.08  # +8%
                    adjustment_reason = f"Strong crowd validation (+8% confidence): {crowd_percentage:.1%} of {total_votes:,} votes"
                else:  # major
                    confidence_adjustment = 0.10  # +10% (capped, was +20%)
                    adjustment_reason = f"Massive crowd validation (+10% confidence - capped): {crowd_percentage:.1%} of {total_votes:,} votes"
                    
            else:
                # Crowd disagrees with our model - confidence reduction
                disagreement_strength = crowd_percentage  # How strongly they disagree
                
                if volume_impact == 'light':
                    confidence_adjustment = -0.15  # -15%
                    adjustment_reason = f"Crowd disagreement (-15% confidence): {crowd_percentage:.1%} of {total_votes:,} favor {crowd_favorite}"
                elif volume_impact == 'serious':
                    confidence_adjustment = -0.30  # -30%
                    adjustment_reason = f"Strong crowd disagreement (-30% confidence): {crowd_percentage:.1%} of {total_votes:,} favor {crowd_favorite}"
                else:  # major
                    confidence_adjustment = -0.50  # -50%
                    adjustment_reason = f"Massive crowd disagreement (-50% confidence): {crowd_percentage:.1%} of {total_votes:,} favor {crowd_favorite}"
            
            # Apply high-profile match considerations
            high_profile_tournaments = ['Grand Slam', 'Masters', 'WTA 1000']
            if any(level in tournament_level for level in high_profile_tournaments):
                if not crowd_agrees and volume_impact in ['serious', 'major']:
                    # Reduce penalty slightly for high-profile matches (emotional betting)
                    confidence_adjustment *= 0.8
                    adjustment_reason += " (adjusted for high-profile emotional betting)"
            
            # Calculate final adjusted confidence (ensure bounds)
            adjusted_confidence = max(0.0, min(1.0, base_confidence + confidence_adjustment))
            
            return {
                'adjusted_confidence': adjusted_confidence,
                'crowd_analysis': adjustment_reason,
                'confidence_adjustment': confidence_adjustment,
                'crowd_favorite': crowd_favorite,
                'crowd_percentage': crowd_percentage,
                'vote_volume': volume_category,
                'total_votes': total_votes,
                'crowd_agrees': crowd_agrees,
                'tournament_profile': tournament_level
            }
            
        except Exception as e:
            return {
                'adjusted_confidence': base_confidence,
                'crowd_analysis': f'Error analyzing crowd sentiment: {str(e)}',
                'confidence_adjustment': 0.0,
                'crowd_favorite': 'Unknown',
                'crowd_percentage': 0,
                'vote_volume': 'Error'
            }
    
    def analyze_player_mental_toughness(self, player_name: str, player_id: int) -> Dict[str, Any]:
        """
        Analyze mental toughness for any individual player
        
        Returns:
        - tiebreak_rate: Player's tiebreak win rate (0.0-1.0)
        - category: Mental toughness category (Extreme Fragility, Fragility, Average, Strength, Extreme Strength)
        - analysis: Detailed text analysis
        - confidence_adjustment: What adjustment this would apply if they were predicted winner
        """
        try:
            if not player_id:
                return {
                    'tiebreak_rate': 'N/A',
                    'category': 'Unknown',
                    'analysis': 'No player ID provided',
                    'confidence_adjustment': 0.0
                }
            
            # Get real tiebreak performance data - no fallbacks allowed
            try:
                tiebreak_performance = self.calculate_enhanced_tiebreak_performance(player_id)
            except Exception as e:
                # Cannot get reliable tiebreak data - this should trigger match skip
                return {
                    'tiebreak_rate': 'No Data',
                    'category': 'Insufficient Data',
                    'analysis': f'Tiebreak data unavailable: {str(e)}',
                    'confidence_adjustment': 0.0,
                    'data_quality_issue': 'Tiebreak statistics not available'
                }
            
            # Define thresholds
            MENTAL_FRAGILITY_THRESHOLD = 0.40
            MENTAL_STRENGTH_THRESHOLD = 0.60
            EXTREME_FRAGILITY_THRESHOLD = 0.25
            EXTREME_STRENGTH_THRESHOLD = 0.75
            
            # Categorize mental toughness
            if tiebreak_performance < EXTREME_FRAGILITY_THRESHOLD:
                category = "Extreme Fragility"
                confidence_adjustment = -0.25
                analysis = f'EXTREME mental fragility: {tiebreak_performance:.1%} tiebreak win rate'
                
            elif tiebreak_performance < MENTAL_FRAGILITY_THRESHOLD:
                category = "Mental Fragility"
                confidence_adjustment = -0.15
                analysis = f'Mental fragility detected: {tiebreak_performance:.1%} tiebreak win rate'
                
            elif tiebreak_performance > EXTREME_STRENGTH_THRESHOLD:
                category = "Extreme Strength"
                confidence_adjustment = 0.15
                analysis = f'EXTREME mental strength: {tiebreak_performance:.1%} tiebreak win rate'
                
            elif tiebreak_performance > MENTAL_STRENGTH_THRESHOLD:
                category = "Mental Strength"
                confidence_adjustment = 0.10
                analysis = f'Mental strength detected: {tiebreak_performance:.1%} tiebreak win rate'
                
            else:
                category = "Average"
                confidence_adjustment = 0.0
                analysis = f'Average mental toughness: {tiebreak_performance:.1%} tiebreak win rate'
            
            return {
                'tiebreak_rate': f'{tiebreak_performance:.1%}',
                'category': category,
                'analysis': analysis,
                'confidence_adjustment': confidence_adjustment
            }
            
        except Exception as e:
            return {
                'tiebreak_rate': 'Error',
                'category': 'Unknown',
                'analysis': f'Mental analysis failed: {str(e)}',
                'confidence_adjustment': 0.0
            }

    def analyze_mental_toughness_differential(self, event_id: int, predicted_winner: str,
                                           player1_name: str, player2_name: str,
                                           base_confidence: float, tournament_level: str,
                                           player1_id: int, player2_id: int,
                                           player1_mental: Dict[str, Any], 
                                           player2_mental: Dict[str, Any]) -> Dict[str, Any]:
        """
        IMPROVED: Analyze mental toughness differential between BOTH players
        
        This addresses the key issue: mental toughness should affect predictions regardless 
        of who is initially predicted to win.
        
        Returns confidence adjustments based on mental toughness advantages/disadvantages
        """
        try:
            # Extract tiebreak rates (remove % symbol and convert to float)
            p1_rate_str = player1_mental.get('tiebreak_rate', '50.0%')
            p2_rate_str = player2_mental.get('tiebreak_rate', '50.0%')
            
            try:
                p1_tiebreak = float(p1_rate_str.replace('%', '')) / 100.0
                p2_tiebreak = float(p2_rate_str.replace('%', '')) / 100.0
            except:
                # Fallback to equal if parsing fails
                p1_tiebreak = 0.5
                p2_tiebreak = 0.5
            
            # Calculate mental toughness differential
            mental_differential = p1_tiebreak - p2_tiebreak
            
            # Determine who has mental advantage
            if abs(mental_differential) < 0.05:  # Less than 5% difference
                mental_advantage = "Equal"
                confidence_adjustment = 0.0
                analysis = f"Similar mental toughness: {p1_rate_str} vs {p2_rate_str}"
                
            elif mental_differential > 0:  # Player 1 has advantage
                mental_advantage = player1_name
                
                # Scale adjustment based on differential size - ENHANCED PENALTIES
                if mental_differential >= 0.40:  # 40%+ difference = EXTREME
                    confidence_adjustment = 0.20 if predicted_winner == player1_name else -0.25
                    analysis = f"EXTREME mental advantage: {player1_name} ({p1_rate_str}) vs {player2_name} ({p2_rate_str})"
                elif mental_differential >= 0.25:  # 25-40% difference = MAJOR
                    confidence_adjustment = 0.15 if predicted_winner == player1_name else -0.20
                    analysis = f"MAJOR mental advantage: {player1_name} ({p1_rate_str}) vs {player2_name} ({p2_rate_str})"
                elif mental_differential >= 0.15:  # 15-25% difference = SIGNIFICANT
                    confidence_adjustment = 0.12 if predicted_winner == player1_name else -0.15
                    analysis = f"SIGNIFICANT mental advantage: {player1_name} ({p1_rate_str}) vs {player2_name} ({p2_rate_str})"
                elif mental_differential >= 0.10:  # 10-15% difference = MODERATE
                    confidence_adjustment = 0.10 if predicted_winner == player1_name else -0.10
                    analysis = f"Moderate mental advantage: {player1_name} ({p1_rate_str}) vs {player2_name} ({p2_rate_str})"
                else:  # 5-10% difference = SLIGHT
                    confidence_adjustment = 0.05 if predicted_winner == player1_name else -0.05
                    analysis = f"Slight mental edge: {player1_name} ({p1_rate_str}) vs {player2_name} ({p2_rate_str})"
                    
            else:  # Player 2 has advantage
                mental_advantage = player2_name
                mental_differential = abs(mental_differential)
                
                # Scale adjustment based on differential size - ENHANCED PENALTIES
                if mental_differential >= 0.40:  # 40%+ difference = EXTREME
                    confidence_adjustment = 0.20 if predicted_winner == player2_name else -0.25
                    analysis = f"EXTREME mental advantage: {player2_name} ({p2_rate_str}) vs {player1_name} ({p1_rate_str})"
                elif mental_differential >= 0.25:  # 25-40% difference = MAJOR
                    confidence_adjustment = 0.15 if predicted_winner == player2_name else -0.20
                    analysis = f"MAJOR mental advantage: {player2_name} ({p2_rate_str}) vs {player1_name} ({p1_rate_str})"
                elif mental_differential >= 0.15:  # 15-25% difference = SIGNIFICANT
                    confidence_adjustment = 0.12 if predicted_winner == player2_name else -0.15
                    analysis = f"SIGNIFICANT mental advantage: {player2_name} ({p2_rate_str}) vs {player1_name} ({p1_rate_str})"
                elif mental_differential >= 0.10:  # 10-15% difference = MODERATE
                    confidence_adjustment = 0.10 if predicted_winner == player2_name else -0.10
                    analysis = f"Moderate mental advantage: {player2_name} ({p2_rate_str}) vs {player1_name} ({p1_rate_str})"
                else:  # 5-10% difference = SLIGHT
                    confidence_adjustment = 0.05 if predicted_winner == player2_name else -0.05
                    analysis = f"Slight mental edge: {player2_name} ({p2_rate_str}) vs {player1_name} ({p1_rate_str})"
            
            # Apply adjustment
            adjusted_confidence = max(0.0, min(1.0, base_confidence + confidence_adjustment))
            apply_adjustment = abs(confidence_adjustment) >= 0.05
            
            # Add upset warning if mentally weaker player is predicted to win
            if confidence_adjustment <= -0.05:
                analysis += f" ⚠️ UPSET RISK: Predicted winner has weaker mental game"
            
            return {
                'apply_adjustment': apply_adjustment,
                'adjusted_confidence': adjusted_confidence,
                'analysis': analysis,
                'confidence_adjustment': confidence_adjustment,
                'mental_advantage': mental_advantage,
                'differential': abs(p1_tiebreak - p2_tiebreak)
            }
            
        except Exception as e:
            return {
                'apply_adjustment': False,
                'adjusted_confidence': base_confidence,
                'analysis': f'Mental differential analysis failed: {str(e)}',
                'confidence_adjustment': 0.0,
                'mental_advantage': 'Unknown',
                'differential': 0.0
            }

    def analyze_mental_toughness_confidence(self, event_id: int, predicted_winner: str, 
                                         player1_name: str, player2_name: str, 
                                         base_confidence: float, tournament_level: str = "Unknown",
                                         predicted_winner_id: int = None) -> Dict[str, Any]:
        """
        Analyze mental toughness as a confidence modifier using real tiebreak and pressure data
        
        Returns:
        - apply_adjustment: Whether to apply mental toughness adjustment
        - adjusted_confidence: Modified confidence level
        - analysis: Detailed breakdown of mental toughness impact
        - confidence_adjustment: Percentage adjustment applied
        """
        try:
            # Apply mental toughness analysis for all tournaments initially (for testing)
            # Later can be restricted to ATP/WTA events
            # print(f"🧠 Mental toughness check: Tournament={tournament_level}, Confidence={base_confidence:.1%}")
            
            # REMOVED: No longer skip low confidence predictions
            # Mental toughness is valuable for ALL prediction confidence levels
            # Can boost Low → Medium or penalize Medium → Low
            
            
            # DATA-DRIVEN approach: Use real tiebreak performance analysis
            if not predicted_winner_id:
                return {
                    'apply_adjustment': False,
                    'adjusted_confidence': base_confidence,
                    'analysis': f'Mental toughness analysis skipped (no player ID provided)',
                    'confidence_adjustment': 0.0
                }
            
            try:
                # Use existing enhanced tiebreak performance calculation
                tiebreak_performance = self.calculate_enhanced_tiebreak_performance(predicted_winner_id)
                
                # Define thresholds based on real data analysis - IMPROVED
                MENTAL_FRAGILITY_THRESHOLD = 0.40   # Below 40% tiebreak win rate = fragile
                MENTAL_STRENGTH_THRESHOLD = 0.60    # Above 60% tiebreak win rate = strong
                EXTREME_FRAGILITY_THRESHOLD = 0.25  # Below 25% = extreme fragility
                EXTREME_STRENGTH_THRESHOLD = 0.75   # Above 75% = extreme strength
                
                confidence_adjustment = 0.0
                analysis_text = ""
                
                if tiebreak_performance < EXTREME_FRAGILITY_THRESHOLD:
                    # Extreme mental fragility
                    confidence_adjustment = -0.25  # -25% penalty
                    analysis_text = f'EXTREME mental fragility: {tiebreak_performance:.1%} tiebreak win rate (below {EXTREME_FRAGILITY_THRESHOLD:.0%} threshold)'
                    
                elif tiebreak_performance < MENTAL_FRAGILITY_THRESHOLD:
                    # Mental fragility
                    confidence_adjustment = -0.15  # -15% penalty
                    analysis_text = f'Mental fragility detected: {tiebreak_performance:.1%} tiebreak win rate (below {MENTAL_FRAGILITY_THRESHOLD:.0%} threshold)'
                    
                elif tiebreak_performance > EXTREME_STRENGTH_THRESHOLD:
                    # Extreme mental strength
                    confidence_adjustment = 0.15   # +15% bonus
                    analysis_text = f'EXTREME mental strength: {tiebreak_performance:.1%} tiebreak win rate (above {EXTREME_STRENGTH_THRESHOLD:.0%} threshold)'
                    
                elif tiebreak_performance > MENTAL_STRENGTH_THRESHOLD:
                    # Mental strength
                    confidence_adjustment = 0.10   # +10% bonus (doubled from +5%)
                    analysis_text = f'Mental strength detected: {tiebreak_performance:.1%} tiebreak win rate (above {MENTAL_STRENGTH_THRESHOLD:.0%} threshold)'
                    
                else:
                    # Average mental toughness
                    analysis_text = f'Average mental toughness: {tiebreak_performance:.1%} tiebreak win rate'
                
                # Apply adjustment
                adjusted_confidence = max(0.0, min(1.0, base_confidence + confidence_adjustment))
                apply_adjustment = abs(confidence_adjustment) >= 0.05  # Only apply if 5%+ adjustment
                
                return {
                    'apply_adjustment': apply_adjustment,
                    'adjusted_confidence': adjusted_confidence,
                    'analysis': analysis_text,
                    'confidence_adjustment': confidence_adjustment
                }
                
            except Exception as analysis_error:
                # If tiebreak analysis fails, continue without adjustment
                return {
                    'apply_adjustment': False,
                    'adjusted_confidence': base_confidence,
                    'analysis': f'Mental toughness analysis failed: {str(analysis_error)}',
                    'confidence_adjustment': 0.0
                }
            
        except Exception as e:
            print(f"⚠️ Mental toughness analysis error: {e}")
            return {
                'apply_adjustment': False,
                'adjusted_confidence': base_confidence,
                'analysis': f'Mental toughness analysis error: {str(e)}',
                'confidence_adjustment': 0.0
            }
    
    def _calculate_quality_opposition_performance(self, recent_form_data: Dict, ranking_threshold: int) -> Dict[str, float]:
        """Calculate win rate against opponents ranked better than threshold for accurate performance comparison."""
        try:
            # Handle both old and new data structures
            matches = recent_form_data.get('matches', [])
            if not matches and 'form_data' in recent_form_data:
                # New structure: recent_form_data['form_data']['recent_matches']
                matches = recent_form_data['form_data'].get('recent_matches', [])
            
            sets_won_vs_quality = 0
            total_sets_vs_quality = 0
            matches_vs_quality = 0
            
            for match in matches:
                # Handle both old structure (match_analysis nested) and new structure (direct)
                if 'match_analysis' in match:
                    # Old structure
                    match_analysis = match.get('match_analysis', {})
                    opponent_ranking = match_analysis.get('opponent_ranking')
                    player_sets_won = match_analysis.get('player_sets', 0)
                    opponent_sets_won = match_analysis.get('opponent_sets', 0)
                else:
                    # New structure (direct fields)
                    opponent_ranking = match.get('opponent_ranking')
                    player_sets_won = match.get('player_sets', 0)
                    opponent_sets_won = match.get('opponent_sets', 0)
                
                # Count sets if opponent was ranked better than our threshold
                if opponent_ranking and isinstance(opponent_ranking, int) and opponent_ranking < ranking_threshold:
                    sets_won_vs_quality += player_sets_won
                    total_sets_vs_quality += (player_sets_won + opponent_sets_won)
                    matches_vs_quality += 1
            
            # Calculate win rates
            set_win_rate_vs_quality = (sets_won_vs_quality / total_sets_vs_quality) if total_sets_vs_quality > 0 else 0
            
            return {
                'sets_won': sets_won_vs_quality,
                'total_sets': total_sets_vs_quality,
                'set_win_rate': set_win_rate_vs_quality,
                'matches_played': matches_vs_quality,
                'has_sufficient_data': total_sets_vs_quality >= 4  # Minimum 4 sets for meaningful sample
            }
        except Exception as e:
            print(f"   ⚠️ Error calculating quality opposition performance: {e}")
            return {
                'sets_won': 0, 'total_sets': 0, 'set_win_rate': 0, 
                'matches_played': 0, 'has_sufficient_data': False
            }

    def _calculate_set_probability(self, match_probability: float, is_best_of_five: bool = False) -> float:
        """
        Convert match win probability to "+1.5 sets" probability (winning at least 1 set).
        
        In tennis, even if you're unlikely to win the match, you can still win sets.
        This uses a realistic model based on tennis scoring dynamics and match format.
        
        Args:
            match_probability: Probability of winning the match (0.0 to 1.0)
            is_best_of_five: True for Grand Slam men's singles, False for best-of-3
        """
        # Ensure probability is in valid range
        match_prob = max(0.0, min(1.0, match_probability))
        
        # REALISTIC tennis-specific conversion - prevent extreme probabilities
        # First, cap match probabilities to avoid 100%/0% scenarios
        match_prob = max(0.05, min(0.90, match_prob))  # Cap between 5% and 90%
        
        if is_best_of_five:
            # **BEST-OF-5 FORMAT** (Grand Slam men's singles)
            # Higher probability of winning at least 1 set due to more opportunities
            # Even a heavy underdog has a good chance to steal at least one set
            
            if match_prob >= 0.75:
                # Strong favorite - very high set probability (need 3 of 5)
                set_prob = 0.92 + (match_prob - 0.75) * 0.32  # 92-100%
            elif match_prob >= 0.60:
                # Moderate favorite - excellent set probability  
                set_prob = 0.82 + (match_prob - 0.60) * 0.67  # 82-92%
            elif match_prob >= 0.40:
                # Competitive range - very good set probability
                set_prob = 0.72 + (match_prob - 0.40) * 0.5   # 72-82%
            elif match_prob >= 0.25:
                # Underdog - still good set probability (more sets to win)
                set_prob = 0.60 + (match_prob - 0.25) * 0.8   # 60-72%
            else:
                # Heavy underdog - decent set probability in best-of-5
                set_prob = 0.45 + match_prob * 0.6            # 45-60%
                
            # Final bounds for best-of-5 - slightly reduced max from 99% to 98% for realism
            return max(0.45, min(0.98, set_prob))
            
        else:
            # **BEST-OF-3 FORMAT** (all other matches)
            # Original logic - lower probabilities due to fewer opportunities
            
            if match_prob >= 0.75:
                # Strong favorite - high but not extreme set probability
                set_prob = 0.80 + (match_prob - 0.75) * 0.33  # 80-85%
            elif match_prob >= 0.60:
                # Moderate favorite - good set probability  
                set_prob = 0.70 + (match_prob - 0.60) * 0.67  # 70-80%
            elif match_prob >= 0.40:
                # Competitive range - balanced set probability
                set_prob = 0.60 + (match_prob - 0.40) * 0.5   # 60-70%
            elif match_prob >= 0.25:
                # Underdog - still reasonable set probability
                set_prob = 0.50 + (match_prob - 0.25) * 0.67  # 50-60%
            else:
                # Heavy underdog - minimum but realistic set probability
                set_prob = 0.35 + match_prob * 0.75           # 35-50%
                
            # Final bounds for best-of-3 - increased max from 85% to 95% for better granularity
            return max(0.35, min(0.95, set_prob))
    
    def _get_historical_match_patterns(self, player_id: int, surface: str = None, max_matches: int = 50) -> Dict[str, Any]:
        """
        Analyze historical match patterns to get actual game counts per set and 3-set match rates.
        
        Returns:
            Dict with:
            - avg_games_per_set_2_0: Average games per set in 2-0 matches
            - avg_games_per_set_2_1: Average games per set in 2-1 matches  
            - avg_total_games_2_0: Average total games in 2-0 matches
            - avg_total_games_2_1: Average total games in 2-1 matches
            - three_set_rate: Percentage of matches that went 3 sets
            - sample_size: Number of matches analyzed
        """
        try:
            comprehensive_matches = self.player_service.get_comprehensive_singles_matches(
                player_id, max_matches=max_matches, max_pages=5
            )
            
            if not comprehensive_matches or not comprehensive_matches.get('events'):
                return None
            
            games_2_0 = []  # Total games in 2-0 matches
            games_2_1 = []  # Total games in 2-1 matches
            games_3_plus = []  # Total games in 3+ set matches (best-of-5)
            three_set_count = 0
            total_finished_matches = 0
            games_3_plus_samples = 0  # Count of 3+ set matches
            
            for match in comprehensive_matches.get('events', []):
                try:
                    if match.get('status', {}).get('type') != 'finished':
                        continue
                    
                    # Surface filtering
                    if surface and surface.lower() not in ['unknown', 'n/a', 'none']:
                        match_surface = match.get('groundType', '').lower()
                        if surface.lower() not in match_surface and match_surface not in surface.lower():
                            continue
                    
                    home_score = match.get('homeScore', {})
                    away_score = match.get('awayScore', {})
                    
                    if not home_score or not away_score:
                        continue
                    
                    # Count sets and games
                    sets_played = 0
                    total_games = 0
                    
                    for period_key in ['period1', 'period2', 'period3', 'period4', 'period5']:
                        p1_games = home_score.get(period_key)
                        p2_games = away_score.get(period_key)
                        
                        if p1_games is None or p2_games is None:
                            break
                        
                        if isinstance(p1_games, (int, float)) and isinstance(p2_games, (int, float)):
                            sets_played += 1
                            total_games += int(p1_games) + int(p2_games)
                    
                    if sets_played < 2:
                        continue
                    
                    total_finished_matches += 1
                    
                    if sets_played == 2:
                        games_2_0.append(total_games)
                    elif sets_played == 3:
                        games_2_1.append(total_games)
                        three_set_count += 1
                    elif sets_played >= 4:  # Best-of-5: 3+ sets
                        games_3_plus.append(total_games)
                        three_set_count += 1
                        games_3_plus_samples += 1
                        
                except Exception:
                    continue
            
            if total_finished_matches == 0:
                return None
            
            # Calculate averages
            result = {
                'avg_total_games_2_0': sum(games_2_0) / len(games_2_0) if games_2_0 else None,
                'avg_total_games_2_1': sum(games_2_1) / len(games_2_1) if games_2_1 else None,
                'avg_total_games_3_plus': sum(games_3_plus) / len(games_3_plus) if games_3_plus else None,
                'three_set_rate': three_set_count / total_finished_matches if total_finished_matches > 0 else 0.0,
                'sample_size': total_finished_matches,
                'games_2_0_samples': len(games_2_0),
                'games_2_1_samples': len(games_2_1),
                'games_3_plus_samples': games_3_plus_samples
            }
            
            return result
            
        except Exception as e:
            return None
    
    def _get_h2h_three_set_rate(self, player1_id: int, player2_id: int, event_id: str = None, surface: str = None) -> Optional[float]:
        """
        Get head-to-head 3-set match rate between two players.
        
        Returns:
            Rate (0.0-1.0) of matches that went 3 sets, or None if not available
        """
        if not event_id:
            return None
        
        try:
            import asyncio
            
            # Use the async H2H analysis
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            h2h_data = loop.run_until_complete(
                self.player_service.analyze_head_to_head(event_id, player1_id, player2_id, surface)
            )
            
            if not h2h_data or not h2h_data.get('total_matches') or h2h_data['total_matches'] < 2:
                return None
            
            # Try to get match details from H2H data structure
            # The H2H data might already have match details
            matches = h2h_data.get('matches', [])
            if not matches:
                # Fallback: extract from comprehensive matches
                comprehensive_matches = self.player_service.get_comprehensive_singles_matches(
                    player1_id, max_matches=100
                ).get('events', [])
                
                # Filter for H2H matches
                matches = []
                for match in comprehensive_matches:
                    home_id = match.get('homeTeam', {}).get('id')
                    away_id = match.get('awayTeam', {}).get('id')
                    if (home_id == player1_id and away_id == player2_id) or (home_id == player2_id and away_id == player1_id):
                        if match.get('status', {}).get('type') == 'finished':
                            matches.append(match)
            
            if len(matches) < 2:
                return None
            
            # Count 3-set matches
            three_set_count = 0
            for match in matches:
                home_score = match.get('homeScore', {})
                away_score = match.get('awayScore', {})
                
                if not home_score or not away_score:
                    continue
                
                sets_played = 0
                for period_key in ['period1', 'period2', 'period3']:
                    if home_score.get(period_key) is not None and away_score.get(period_key) is not None:
                        sets_played += 1
                
                if sets_played == 3:
                    three_set_count += 1
            
            return three_set_count / len(matches) if matches else None
            
        except Exception as e:
            # Silently fail - H2H data is optional
            return None
    
    def _get_recent_three_set_rate(self, player_id: int, surface: str = None, max_matches: int = 10) -> Optional[float]:
        """
        Get recent 3-set match rate for a player.
        
        Returns:
            Rate (0.0-1.0) of recent matches that went 3 sets, or None if not available
        """
        patterns = self._get_historical_match_patterns(player_id, surface, max_matches=max_matches)
        if patterns and patterns.get('sample_size', 0) >= 5:
            return patterns.get('three_set_rate')
        return None
    
    def _calculate_over_2_5_sets_probability(
        self, 
        player1_set_prob: float, 
        player2_set_prob: float,
        player1: PlayerProfile,
        player2: PlayerProfile,
        surface: str = 'Unknown',
        match_format: MatchFormat = None,
        event_id: str = None
    ) -> float:
        """
        Calculate probability that match goes over 2.5 sets using proper probability theory and historical data.
        
        For best-of-3: Over 2.5 sets = match goes 2-1 or 1-2 (both players win at least 1 set)
        For best-of-5: Over 2.5 sets = match goes 3+ sets
        
        Uses historical match patterns when available, falls back to probability theory.
        
        Args:
            player1_set_prob: Player 1's probability of winning ≥1 set
            player2_set_prob: Player 2's probability of winning ≥1 set
            player1: Player 1 profile
            player2: Player 2 profile
            surface: Match surface
            match_format: Match format info
            
        Returns:
            Probability (0.0 to 1.0) that match goes over 2.5 sets
        """
        is_best_of_five = match_format.is_best_of_five if match_format else False
        
        # BEST-OF-5 LOGIC
        if is_best_of_five:
            # For best-of-5, over 2.5 sets means 3+ sets
            # Get historical 3-set rate for both players
            p1_patterns = self._get_historical_match_patterns(player1.id, surface, max_matches=30)
            p2_patterns = self._get_historical_match_patterns(player2.id, surface, max_matches=30)
            
            historical_3_set_rate = None
            if p1_patterns and p2_patterns:
                # Blend both players' historical rates
                p1_rate = p1_patterns.get('three_set_rate', 0.0)
                p2_rate = p2_patterns.get('three_set_rate', 0.0)
                p1_weight = p1_patterns.get('sample_size', 0) / max(p1_patterns.get('sample_size', 0) + p2_patterns.get('sample_size', 0), 1)
                historical_3_set_rate = (p1_rate * p1_weight) + (p2_rate * (1 - p1_weight))
            
            # Base probability: Both players need to win sets
            # In best-of-5, if both have high set probabilities, match is more likely to go 3+ sets
            base_prob = (player1_set_prob * player2_set_prob) * 1.1  # Adjust for correlation
            
            # Use historical rate if available and reliable
            if historical_3_set_rate and historical_3_set_rate > 0.1:  # At least 10% to be meaningful
                # Blend historical (60%) with calculated (40%)
                final_prob = (historical_3_set_rate * 0.6) + (base_prob * 0.4)
            else:
                final_prob = base_prob
            
            return max(0.25, min(0.90, final_prob))
        
        # BEST-OF-3 LOGIC
        # Get multiple data sources for 3-set likelihood
        
        # 1. Historical 3-set rates for both players (general pattern)
        p1_patterns = self._get_historical_match_patterns(player1.id, surface, max_matches=30)
        p2_patterns = self._get_historical_match_patterns(player2.id, surface, max_matches=30)
        
        historical_3_set_rate = None
        if p1_patterns and p2_patterns and p1_patterns.get('sample_size', 0) >= 5 and p2_patterns.get('sample_size', 0) >= 5:
            # Blend both players' historical rates
            p1_rate = p1_patterns.get('three_set_rate', 0.0)
            p2_rate = p2_patterns.get('three_set_rate', 0.0)
            p1_weight = p1_patterns.get('sample_size', 0) / max(p1_patterns.get('sample_size', 0) + p2_patterns.get('sample_size', 0), 1)
            historical_3_set_rate = (p1_rate * p1_weight) + (p2_rate * (1 - p1_weight))
        
        # 2. Recent form: Are players going 3 sets recently? (more predictive)
        p1_recent_rate = self._get_recent_three_set_rate(player1.id, surface, max_matches=10)
        p2_recent_rate = self._get_recent_three_set_rate(player2.id, surface, max_matches=10)
        
        recent_form_rate = None
        if p1_recent_rate is not None and p2_recent_rate is not None:
            # Average recent rates (both players going 3 sets recently = strong signal)
            recent_form_rate = (p1_recent_rate + p2_recent_rate) / 2.0
        
        # 3. Head-to-head: Do these players usually go 3 sets? (most predictive)
        h2h_rate = self._get_h2h_three_set_rate(player1.id, player2.id, event_id, surface) if event_id else None
        
        # Combine all signals with weights
        # H2H is most predictive (50%), recent form next (30%), historical pattern last (20%)
        combined_rate = None
        if h2h_rate is not None and h2h_rate > 0:
            # H2H available - use it heavily
            if recent_form_rate is not None:
                combined_rate = (h2h_rate * 0.5) + (recent_form_rate * 0.3) + (historical_3_set_rate * 0.2 if historical_3_set_rate else h2h_rate * 0.2)
            elif historical_3_set_rate is not None:
                combined_rate = (h2h_rate * 0.6) + (historical_3_set_rate * 0.4)
            else:
                combined_rate = h2h_rate
        elif recent_form_rate is not None:
            # Recent form available
            if historical_3_set_rate is not None:
                combined_rate = (recent_form_rate * 0.6) + (historical_3_set_rate * 0.4)
            else:
                combined_rate = recent_form_rate
        else:
            # Fall back to historical only
            combined_rate = historical_3_set_rate
        
        # PROBABILITY THEORY CALCULATION
        # Calculate competitiveness FIRST (needed for match win probability estimation)
        match_competitiveness = 1.0 - abs(player1_set_prob - player2_set_prob)
        
        # Estimate match win probabilities from set probabilities
        # If both players have decent set probabilities, the match is competitive
        # Competitive matches: winning ≥1 set → higher chance to win match
        # Formula: More competitive → higher conversion rate
        
        # Base conversion: P(win match) ≈ P(win ≥1 set) * conversion_factor
        # For competitive matches (competitiveness > 0.7): use higher conversion (0.80-0.85)
        # For one-sided matches (competitiveness < 0.5): use lower conversion (0.70-0.75)
        if match_competitiveness > 0.70:
            # Very competitive: both players likely to win sets → higher match win probability
            conversion_factor = 0.70 + (match_competitiveness - 0.70) * 0.5  # 0.70 to 0.85
        elif match_competitiveness > 0.50:
            # Moderately competitive
            conversion_factor = 0.65 + (match_competitiveness - 0.50) * 0.25  # 0.65 to 0.70
        else:
            # One-sided: use conservative estimate
            conversion_factor = 0.60 + (match_competitiveness / 0.50) * 0.10  # 0.60 to 0.70
        
        p1_match_win_prob = player1_set_prob * conversion_factor
        p2_match_win_prob = player2_set_prob * conversion_factor
        
        # Normalize to sum to 1
        total_match_prob = p1_match_win_prob + p2_match_win_prob
        if total_match_prob > 0:
            p1_match_win_prob /= total_match_prob
            p2_match_win_prob /= total_match_prob
        
        # Estimate probability of 2-1 vs 2-0 scorelines
        # More competitive matches → more 2-1 finishes
        # Typical rates: competitive (0.8-1.0) → 45-60% of wins are 2-1
        #                one-sided (0.0-0.5) → 25-35% of wins are 2-1
        p1_2_1_given_win = 0.25 + (match_competitiveness * 0.35)  # 0.25 to 0.60
        p2_2_1_given_win = 0.25 + (match_competitiveness * 0.35)
        
        # Calculate probability of 2-1 finishes
        p_2_1_p1_wins = p1_match_win_prob * p1_2_1_given_win
        p_2_1_p2_wins = p2_match_win_prob * p2_2_1_given_win
        
        # P(Over 2.5) = P(2-1)
        base_prob = p_2_1_p1_wins + p_2_1_p2_wins
        
        # ADDITIONAL BOOST: If both players have good set probabilities (>50%),
        # the match is inherently competitive and more likely to go 3 sets
        competitive_boost = 1.0
        if player1_set_prob > 0.50 and player2_set_prob > 0.50:
            # Both players likely to win sets → boost the probability
            # The boost increases with how strong both players' set probabilities are
            avg_set_prob = (player1_set_prob + player2_set_prob) / 2.0
            competitive_boost = 1.0 + (avg_set_prob - 0.50) * 0.4  # Up to +20% boost (if avg = 1.0)
            base_prob *= competitive_boost
        
        # Apply adjustments (multiplicative, not additive to prevent >100%)
        # Resilience: Players who fight → more 2-1 finishes
        resilience_multiplier = 1.0
        try:
            p1_resilience = self.calculate_sets_in_losses(player1.id, surface)[0] / 100.0
            p2_resilience = self.calculate_sets_in_losses(player2.id, surface)[0] / 100.0
            avg_resilience = (p1_resilience + p2_resilience) / 2.0
            
            # High resilience (>30%) → up to +20% boost
            if avg_resilience > 0.30:
                resilience_multiplier = 1.0 + (avg_resilience - 0.30) * 0.4
            elif avg_resilience > 0.20:
                resilience_multiplier = 1.0 + (avg_resilience - 0.20) * 0.2
        except Exception:
            pass
        
        # Mental toughness: Tiebreaks → tight sets → more 2-1 finishes
        mental_multiplier = 1.0
        try:
            p1_mental = self.analyze_player_mental_toughness(player1.name, player1.id)
            p2_mental = self.analyze_player_mental_toughness(player2.name, player2.id)
            
            p1_tiebreak_rate = float(p1_mental.get('tiebreak_rate', '50.0%').replace('%', '')) / 100.0
            p2_tiebreak_rate = float(p2_mental.get('tiebreak_rate', '50.0%').replace('%', '')) / 100.0
            avg_tiebreak = (p1_tiebreak_rate + p2_tiebreak_rate) / 2.0
            
            # High tiebreak rates (>55%) → up to +15% boost
            if avg_tiebreak > 0.55:
                mental_multiplier = 1.0 + (avg_tiebreak - 0.55) * 0.3
        except Exception:
            pass
        
        # Apply multipliers
        calculated_prob = base_prob * resilience_multiplier * mental_multiplier
        
        # Blend with combined historical/H2H/recent data if available
        if combined_rate and combined_rate > 0.05:  # At least 5% to be meaningful
            # Blend data-driven (50%) with calculated (50%)
            # Data-driven includes H2H, recent form, and historical patterns
            final_prob = (combined_rate * 0.5) + (calculated_prob * 0.5)
            
            # Log which factors were used
            factors_used = []
            if h2h_rate is not None:
                factors_used.append(f"H2H: {h2h_rate:.1%}")
            if recent_form_rate is not None:
                factors_used.append(f"Recent Form: {recent_form_rate:.1%}")
            if historical_3_set_rate is not None:
                factors_used.append(f"Historical: {historical_3_set_rate:.1%}")
            
            print(f"\n📊 OVER 2.5 SETS ANALYSIS:")
            if factors_used:
                print(f"   Data Sources: {', '.join(factors_used)}")
            print(f"   Combined Data Rate: {combined_rate:.1%}")
            print(f"   Calculated Probability: {calculated_prob:.1%}")
            print(f"   Blended Final: {final_prob:.1%}")
        elif historical_3_set_rate and historical_3_set_rate > 0.05:
            # Fallback to historical only
            final_prob = (historical_3_set_rate * 0.4) + (calculated_prob * 0.6)
            print(f"\n📊 OVER 2.5 SETS ANALYSIS:")
            print(f"   Historical Rate: {historical_3_set_rate:.1%}")
            print(f"   Calculated Probability: {calculated_prob:.1%}")
            print(f"   Blended Final: {final_prob:.1%}")
        else:
            final_prob = calculated_prob
            print(f"\n📊 OVER 2.5 SETS ANALYSIS:")
            print(f"   Using Calculated Probability Only: {calculated_prob:.1%}")
            print(f"   (No historical data available)")
        
        # Tournament level adjustment
        # Grand Slams and Masters: slightly more 3-set matches (mental/physical factors)
        tournament_multiplier = 1.0
        if match_format:
            tournament_level = match_format.tournament_level.lower()
            if 'grand slam' in tournament_level:
                tournament_multiplier = 1.05  # +5% boost
                print(f"   Tournament Boost: Grand Slam (+5%)")
            elif 'masters' in tournament_level:
                tournament_multiplier = 1.03  # +3% boost
                print(f"   Tournament Boost: Masters 1000 (+3%)")
        
        final_prob *= tournament_multiplier
        
        # Cap at realistic bounds
        # ATP/WTA average: ~35-40% of matches go 3 sets
        # Competitive matches: up to 55-60%
        # With H2H showing high rate: can go up to 70%
        max_cap = 0.75 if (h2h_rate and h2h_rate > 0.6) else 0.70
        if final_prob > max_cap:
            print(f"   ⚠️ Capped at {max_cap:.1%} (realistic maximum)")
        
        return max(0.20, min(max_cap, final_prob))
    
    def _calculate_total_games_prediction(
        self,
        player1: PlayerProfile,
        player2: PlayerProfile,
        over_2_5_sets_prob: float,
        player1_set_prob: float,
        player2_set_prob: float,
        surface: str = 'Unknown',
        match_format: MatchFormat = None
    ) -> Dict[str, Any]:
        """
        Predict total games in the match using actual historical game counts and dynamic adjustments.
        
        Uses:
        - Historical game averages from actual match data
        - Serve dominance (break point conversion, hold %)
        - Tiebreak likelihood (historical tiebreak rates)
        - Surface-specific adjustments
        - Match format (best-of-3 vs best-of-5)
        
        Args:
            player1: Player 1 profile
            player2: Player 2 profile
            over_2_5_sets_prob: Probability match goes to 3 sets
            player1_set_prob: Player 1's set probability
            player2_set_prob: Player 2's set probability
            surface: Match surface
            match_format: Match format info
            
        Returns:
            Dictionary with expected total and probabilities for common lines
        """
        is_best_of_five = match_format.is_best_of_five if match_format else False
        
        # Get historical match patterns for both players
        p1_patterns = self._get_historical_match_patterns(player1.id, surface, max_matches=40)
        p2_patterns = self._get_historical_match_patterns(player2.id, surface, max_matches=40)
        
        # STEP 1: Base expectation from historical data
        if is_best_of_five:
            # Best-of-5: Use 3+ set averages
            if p1_patterns and p2_patterns:
                p1_games_3plus = p1_patterns.get('avg_total_games_3_plus')
                p2_games_3plus = p2_patterns.get('avg_total_games_3_plus')
                
                if p1_games_3plus and p2_games_3plus:
                    # Blend both players' historical averages
                    p1_weight = p1_patterns.get('games_3_plus_samples', 0) / max(
                        p1_patterns.get('games_3_plus_samples', 0) + p2_patterns.get('games_3_plus_samples', 0), 1
                    )
                    base_games_3_plus = (p1_games_3plus * p1_weight) + (p2_games_3plus * (1 - p1_weight))
                else:
                    base_games_3_plus = 35.0  # Fallback: typical best-of-5 match
            else:
                base_games_3_plus = 35.0
            
            # For best-of-5, over 2.5 sets means 3+ sets
            base_expected_games = base_games_3_plus
            
        else:
            # Best-of-3: Blend 2-0 and 2-1 averages based on probability
            if p1_patterns and p2_patterns:
                p1_games_2_0 = p1_patterns.get('avg_total_games_2_0')
                p1_games_2_1 = p1_patterns.get('avg_total_games_2_1')
                p2_games_2_0 = p2_patterns.get('avg_total_games_2_0')
                p2_games_2_1 = p2_patterns.get('avg_total_games_2_1')
                
                # Blend both players' historical averages
                if p1_games_2_0 and p2_games_2_0:
                    p1_weight_2_0 = p1_patterns.get('games_2_0_samples', 0) / max(
                        p1_patterns.get('games_2_0_samples', 0) + p2_patterns.get('games_2_0_samples', 0), 1
                    )
                    blended_games_2_0 = (p1_games_2_0 * p1_weight_2_0) + (p2_games_2_0 * (1 - p1_weight_2_0))
                else:
                    blended_games_2_0 = 18.5  # Fallback
                
                if p1_games_2_1 and p2_games_2_1:
                    p1_weight_2_1 = p1_patterns.get('games_2_1_samples', 0) / max(
                        p1_patterns.get('games_2_1_samples', 0) + p2_patterns.get('games_2_1_samples', 0), 1
                    )
                    blended_games_2_1 = (p1_games_2_1 * p1_weight_2_1) + (p2_games_2_1 * (1 - p1_weight_2_1))
                else:
                    blended_games_2_1 = 24.5  # Fallback
                
                # Use historical averages if available
                base_games_2_0 = blended_games_2_0
                base_games_2_1 = blended_games_2_1
            else:
                # Fallback to conservative defaults
                base_games_2_0 = 18.5  # Reduced from 19.0
                base_games_2_1 = 24.5  # Reduced from 27.0
            
            # Weighted average based on probability
            base_expected_games = (
                over_2_5_sets_prob * base_games_2_1 +
                (1 - over_2_5_sets_prob) * base_games_2_0
            )
        
        # STEP 2: Serve Dominance Adjustment (using actual stats)
        serve_adjustment = 0.0
        avg_serve_strength = 0.5
        try:
            p1_serve = self.calculate_enhanced_serve_dominance(player1.id, surface)
            p2_serve = self.calculate_enhanced_serve_dominance(player2.id, surface)
            avg_serve_strength = (p1_serve + p2_serve) / 2.0
            
            # Strong servers → fewer breaks → more games
            # Weak servers → more breaks → fewer games
            if avg_serve_strength > 0.65:  # Both strong servers
                serve_adjustment = 2.0  # Reduced from 3.0
            elif avg_serve_strength > 0.55:
                serve_adjustment = 1.0  # Reduced from 1.5
            elif avg_serve_strength < 0.45:  # Both weak servers
                serve_adjustment = -1.5  # Reduced from -2.0
        except Exception:
            pass
        
        # STEP 3: Tiebreak Likelihood Adjustment (using actual tiebreak rates)
        match_competitiveness = 1.0 - abs(player1_set_prob - player2_set_prob)
        
        tiebreak_adjustment = 0.0
        avg_tiebreak_rate = 0.5
        tiebreak_likelihood = 0.0
        
        try:
            p1_mental = self.analyze_player_mental_toughness(player1.name, player1.id)
            p2_mental = self.analyze_player_mental_toughness(player2.name, player2.id)
            
            p1_tiebreak_rate = float(p1_mental.get('tiebreak_rate', '50.0%').replace('%', '')) / 100.0
            p2_tiebreak_rate = float(p2_mental.get('tiebreak_rate', '50.0%').replace('%', '')) / 100.0
            avg_tiebreak_rate = (p1_tiebreak_rate + p2_tiebreak_rate) / 2.0
            
            # Estimate tiebreak likelihood
            # Competitive match + high tiebreak players + strong servers → more tiebreaks
            tiebreak_likelihood = match_competitiveness * avg_tiebreak_rate * avg_serve_strength
            
            # Each tiebreak adds ~1 game (7-6 instead of 6-4)
            # Expected additional games = expected number of tiebreaks × 1
            # In best-of-3: max 2 tiebreaks possible, in best-of-5: max 4
            max_tiebreaks = 4 if is_best_of_five else 2
            tiebreak_adjustment = tiebreak_likelihood * max_tiebreaks * 1.0  # Reduced from 4.0
        except Exception:
            pass
        
        # STEP 4: Surface Adjustment (dynamic based on serve dominance)
        surface_adjustment = 0.0
        surface_lower = surface.lower()
        
        # Surface effect is stronger when serve dominance is high
        surface_multiplier = 0.5 + (avg_serve_strength * 0.5)  # 0.5 to 1.0
        
        if 'grass' in surface_lower or 'indoor' in surface_lower:
            surface_adjustment = 0.5 * surface_multiplier  # Reduced from 1.0
        elif 'clay' in surface_lower:
            surface_adjustment = -0.5 * (1 - surface_multiplier)  # Less effect on clay
        
        # STEP 5: Calculate expected total
        expected_total = (
            base_expected_games +
            serve_adjustment +
            tiebreak_adjustment +
            surface_adjustment
        )
        
        # Cap at realistic bounds
        if is_best_of_five:
            expected_total = max(25.0, min(45.0, expected_total))
        else:
            expected_total = max(16.0, min(28.0, expected_total))
        
        # STEP 6: Calculate probabilities for common lines
        # Use normal distribution with variance based on match uncertainty
        # Higher uncertainty for competitive matches
        std_dev = 2.5 + (match_competitiveness * 1.5)  # Reduced from 3.0 + 2.0
        
        def calculate_over_prob(line: float) -> float:
            """Calculate probability of going over a specific line using normal distribution"""
            from math import erf, sqrt
            z_score = (line - expected_total) / std_dev
            # Cumulative normal distribution
            prob_under = 0.5 * (1 + erf(z_score / sqrt(2)))
            return max(0.05, min(0.95, 1.0 - prob_under))
        
        # Calculate most common lines
        result = {
            'expected_total_games': round(expected_total, 1),
            'over_19_5_prob': min(0.95, max(0.05, calculate_over_prob(19.5))),
            'over_20_5_prob': min(0.95, max(0.05, calculate_over_prob(20.5))),
            'over_21_5_prob': min(0.95, max(0.05, calculate_over_prob(21.5))),
            'over_22_5_prob': min(0.95, max(0.05, calculate_over_prob(22.5))),
            'over_23_5_prob': min(0.95, max(0.05, calculate_over_prob(23.5))),
            'over_24_5_prob': min(0.95, max(0.05, calculate_over_prob(24.5))),
            'over_25_5_prob': min(0.95, max(0.05, calculate_over_prob(25.5))),
            'std_dev': round(std_dev, 2),
            'serve_strength': round(avg_serve_strength, 3),
            'tiebreak_likelihood': round(tiebreak_likelihood, 3),
            'match_competitiveness': round(match_competitiveness, 3)
        }
        
        # Add best-of-5 lines if applicable
        if is_best_of_five:
            result.update({
                'over_30_5_prob': min(0.95, max(0.05, calculate_over_prob(30.5))),
                'over_32_5_prob': min(0.95, max(0.05, calculate_over_prob(32.5))),
                'over_35_5_prob': min(0.95, max(0.05, calculate_over_prob(35.5))),
            })
        
        return result
    
    def _calculate_total_games_edge_and_recommendation(
        self,
        expected_total_games: float,
        match_competitiveness: float,
        bookmaker_lines: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Calculate edges for all bookmaker Total Games lines and recommend the best bet.
        
        Args:
            expected_total_games: Our predicted expected total games
            match_competitiveness: How close the match is expected to be (0-1)
            bookmaker_lines: Dict of lines like {"20.5": {"over": 1.85, "under": 1.95}}
            
        Returns:
            Dictionary with recommended line, bet type, odds, and edge
        """
        if not bookmaker_lines:
            return {
                'recommended_line': None,
                'recommended_bet': None,
                'recommended_odds': None,
                'edge': None
            }
        
        # Calculate standard deviation (same logic as in _calculate_total_games_prediction)
        std_dev = 3.0 + (match_competitiveness * 2.0)
        
        def calculate_over_prob(line: float) -> float:
            """Calculate probability of going over a specific line using normal distribution"""
            from math import erf, sqrt
            z_score = (line - expected_total_games) / std_dev
            # Cumulative normal distribution
            prob_under = 0.5 * (1 + erf(z_score / sqrt(2)))
            return max(0.05, min(0.95, 1.0 - prob_under))
        
        def calculate_edge(our_prob: float, bookmaker_odds: float) -> float:
            """Calculate edge percentage"""
            if not bookmaker_odds or bookmaker_odds <= 1.0:
                return 0.0
            implied_prob = 1.0 / bookmaker_odds
            edge = our_prob - implied_prob
            return edge
        
        # Evaluate all available lines
        best_edge = 0.0
        best_line = None
        best_bet_type = None
        best_odds = None
        
        for line_str, odds_dict in bookmaker_lines.items():
            try:
                line = float(line_str)
                our_over_prob = calculate_over_prob(line)
                our_under_prob = 1.0 - our_over_prob
                
                # Check "Over" bet
                if 'over' in odds_dict and odds_dict['over']:
                    over_odds = odds_dict['over']
                    over_edge = calculate_edge(our_over_prob, over_odds)
                    
                    if over_edge > best_edge and over_edge >= 0.05:  # Minimum 5% edge
                        best_edge = over_edge
                        best_line = line
                        best_bet_type = 'Over'
                        best_odds = over_odds
                
                # Check "Under" bet
                if 'under' in odds_dict and odds_dict['under']:
                    under_odds = odds_dict['under']
                    under_edge = calculate_edge(our_under_prob, under_odds)
                    
                    if under_edge > best_edge and under_edge >= 0.05:  # Minimum 5% edge
                        best_edge = under_edge
                        best_line = line
                        best_bet_type = 'Under'
                        best_odds = under_odds
            except (ValueError, KeyError) as e:
                continue
        
        return {
            'recommended_line': best_line,
            'recommended_bet': best_bet_type,
            'recommended_odds': best_odds,
            'edge': best_edge if best_edge > 0 else None
        }
    
    def calculate_weighted_prediction(self, player1: PlayerProfile, player2: PlayerProfile, 
                                    surface: str = 'Unknown', event_id: int = None, 
                                    match_format: MatchFormat = None) -> SetPrediction:
        """Calculate weighted set prediction for +1.5 sets betting using comprehensive factors"""
        
        player1_score = 0.0
        player2_score = 0.0
        weight_breakdown = {}
        key_factors = []
        
        # Extract tournament name early for confidence penalties
        tournament_name = "Unknown"
        if match_format:
            tournament_name = match_format.tournament_name
        
        # Initialize data quality discount factors (may be modified later)
        set_performance_discount = 1.0
        form_discount = 1.0
        
        # Log weight calculations start
        if self.prediction_logger:
            self.prediction_logger.log_weight_calculations(self.WEIGHTS, {})
        
        # HOME COUNTRY ADVANTAGE - Playing in home country (configurable)
        if self.config.HOME_ADVANTAGE['enable_home_advantage']:
            home_advantage_weight = self.config.HOME_ADVANTAGE['bonus_percentage']
            bonus_display = int(home_advantage_weight * 100)  # Convert to percentage for display
            tournament_country = self._extract_tournament_country(tournament_name)
            
            if tournament_country:
                p1_home = player1.country and self._countries_match(player1.country, tournament_country)
                p2_home = player2.country and self._countries_match(player2.country, tournament_country)
                
                if p1_home or p2_home:
                    print(f"\n\033[92m{'='*70}\033[0m")
                    print(f"\033[92m🏠 HOME COUNTRY ADVANTAGE DETECTED!\033[0m")
                    print(f"\033[92m   🌍 Tournament: {tournament_name}\033[0m")
                    print(f"\033[92m   📍 Country: {tournament_country}\033[0m")
                    
                    if p1_home and not p2_home:
                        player1_score += home_advantage_weight
                        key_factors.append(f"{player1.name} playing in home country ({player1.country})")
                        print(f"\033[92m   ✅ {player1.name} ({player1.country}) - HOME ADVANTAGE +{bonus_display}%\033[0m")
                        print(f"\033[92m   📈 Bonus applied: +{home_advantage_weight:.3f} to score\033[0m")
                        weight_breakdown['home_advantage'] = f"{player1.name} home advantage (+{bonus_display}%)"
                        
                        # Log to file (if enabled in config)
                        if self.config.HOME_ADVANTAGE['log_to_file']:
                            self._log_home_advantage(tournament_name, tournament_country, player1.name, player1.country, player2.name, player2.country)
                        
                    elif p2_home and not p1_home:
                        player2_score += home_advantage_weight
                        key_factors.append(f"{player2.name} playing in home country ({player2.country})")
                        print(f"\033[92m   ✅ {player2.name} ({player2.country}) - HOME ADVANTAGE +{bonus_display}%\033[0m")
                        print(f"\033[92m   📈 Bonus applied: +{home_advantage_weight:.3f} to score\033[0m")
                        weight_breakdown['home_advantage'] = f"{player2.name} home advantage (+{bonus_display}%)"
                        
                        # Log to file (if enabled in config)
                        if self.config.HOME_ADVANTAGE['log_to_file']:
                            self._log_home_advantage(tournament_name, tournament_country, player2.name, player2.country, player1.name, player1.country)
                        
                    elif p1_home and p2_home:
                        print(f"\033[92m   ⚖️  Both players from {tournament_country} - No advantage applied\033[0m")
                        weight_breakdown['home_advantage'] = "Both players from home country (neutral)"
                    
                    print(f"\033[92m{'='*70}\033[0m")
        else:
            # Home advantage is disabled in config
            weight_breakdown['home_advantage'] = "Disabled in config"
        
        # 1. Set Performance (35%) - Most important for +1.5 betting
        # Get recent form data to analyze set performance with opponent context
        try:
            # Get opponent rankings for context
            opponent_ranking_for_p1 = player2.atp_ranking or player2.wta_ranking
            opponent_ranking_for_p2 = player1.atp_ranking or player1.wta_ranking
            
            # Dual-weighted set performance analysis: recent + comprehensive
            
            # RECENT FORM (10 matches) - HIGH WEIGHT for set performance
            print(f"🔍 DETAILED FORM ANALYSIS:")
            print(f"{'='*60}")
            
            recent_matches_count = self.config.FORM_ANALYSIS['recent_matches']
            print(f"📊 Fetching recent form ({recent_matches_count} matches) for both players on {surface}...")
            recent_form1 = self.player_service.analyze_recent_form(
                player1.id, recent_matches_count, opponent_ranking_for_p1, surface
            )
            recent_form2 = self.player_service.analyze_recent_form(
                player2.id, recent_matches_count, opponent_ranking_for_p2, surface
            )
            
            # Display detailed recent matches for Player 1
            print(f"\n🎾 {player1.name} - RECENT MATCHES (Last {recent_matches_count}):")
            print(f"{'-'*60}")
            recent_matches1 = recent_form1.get('form_data', {}).get('recent_matches', [])
            for i, match in enumerate(recent_matches1[:recent_matches_count]):
                opponent = match.get('opponent_name', 'Unknown')
                player_sets = match.get('player_sets', 0)
                opponent_sets = match.get('opponent_sets', 0)
                match_date = match.get('match_date', 'Unknown')
                tournament = match.get('tournament', 'Unknown')
                surface = match.get('surface', 'Unknown')
                opponent_rank = match.get('opponent_ranking', 'Unranked')
                
                # Fix date display - if it's still "Unknown", try to get from timestamp
                if match_date == 'Unknown' and 'timestamp' in match:
                    try:
                        from datetime import datetime
                        match_date = datetime.fromtimestamp(match['timestamp']).strftime('%Y-%m-%d')
                    except:
                        match_date = 'Unknown'
                
                result_emoji = "✅" if player_sets > opponent_sets else "❌"
                print(f"   {i+1:2d}. {result_emoji} {match_date} vs {opponent}")
                print(f"       📍 {tournament} ({surface})")
                print(f"       🎾 Sets: {player_sets}-{opponent_sets}")
                print(f"       🏆 Opponent Rank: #{opponent_rank if opponent_rank != 'Unranked' else 'Unranked'}")
                
            # Display detailed recent matches for Player 2  
            print(f"\n🎾 {player2.name} - RECENT MATCHES (Last {recent_matches_count}):")
            print(f"{'-'*60}")
            recent_matches2 = recent_form2.get('form_data', {}).get('recent_matches', [])
            for i, match in enumerate(recent_matches2[:recent_matches_count]):
                opponent = match.get('opponent_name', 'Unknown')
                player_sets = match.get('player_sets', 0)
                opponent_sets = match.get('opponent_sets', 0)
                match_date = match.get('match_date', 'Unknown')
                tournament = match.get('tournament', 'Unknown')
                surface = match.get('surface', 'Unknown')
                opponent_rank = match.get('opponent_ranking', 'Unranked')
                
                # Fix date display - if it's still "Unknown", try to get from timestamp
                if match_date == 'Unknown' and 'timestamp' in match:
                    try:
                        from datetime import datetime
                        match_date = datetime.fromtimestamp(match['timestamp']).strftime('%Y-%m-%d')
                    except:
                        match_date = 'Unknown'
                
                result_emoji = "✅" if player_sets > opponent_sets else "❌"
                print(f"   {i+1:2d}. {result_emoji} {match_date} vs {opponent}")
                print(f"       📍 {tournament} ({surface})")
                print(f"       🎾 Sets: {player_sets}-{opponent_sets}")
                print(f"       🏆 Opponent Rank: #{opponent_rank if opponent_rank != 'Unranked' else 'Unranked'}")
            
            # COMPREHENSIVE FORM - LOWER WEIGHT for context
            # Use SAME opponent ranking context AND surface for consistency with recent form
            comprehensive_matches_count = self.config.FORM_ANALYSIS['comprehensive_matches']
            comprehensive_form1 = self.player_service.analyze_recent_form(
                player1.id, comprehensive_matches_count, opponent_ranking_for_p1, surface  # Same context as recent form
            )
            comprehensive_form2 = self.player_service.analyze_recent_form(
                player2.id, comprehensive_matches_count, opponent_ranking_for_p2, surface  # Same context as recent form
            )
            
            # Extract metrics from both recent and comprehensive analysis
            print(f"\n📈 FORM ANALYSIS SUMMARY:")
            print(f"{'='*60}")
            
            recent_set_rate1 = recent_form1.get('form_data', {}).get('set_win_rate', 0.5)
            recent_set_rate2 = recent_form2.get('form_data', {}).get('set_win_rate', 0.5)
            comprehensive_set_rate1 = comprehensive_form1.get('form_data', {}).get('set_win_rate', 0.5)
            comprehensive_set_rate2 = comprehensive_form2.get('form_data', {}).get('set_win_rate', 0.5)
            
            # Display form statistics
            print(f"🏆 {player1.name} Form Stats:")
            print(f"   📊 Recent Set Win Rate ({self.config.FORM_ANALYSIS['recent_matches']} matches): {recent_set_rate1:.1%}")
            print(f"   📊 Comprehensive Set Win Rate ({self.config.FORM_ANALYSIS['comprehensive_matches']} matches): {comprehensive_set_rate1:.1%}")
            print(f"   📊 Matches Analyzed (Recent): {recent_form1.get('matches_analyzed', 0)}")
            print(f"   📊 Matches Analyzed (Comprehensive): {comprehensive_form1.get('matches_analyzed', 0)}")
            
            print(f"\n🏆 {player2.name} Form Stats:")
            print(f"   📊 Recent Set Win Rate ({self.config.FORM_ANALYSIS['recent_matches']} matches): {recent_set_rate2:.1%}")
            print(f"   📊 Comprehensive Set Win Rate ({self.config.FORM_ANALYSIS['comprehensive_matches']} matches): {comprehensive_set_rate2:.1%}")
            print(f"   📊 Matches Analyzed (Recent): {recent_form2.get('matches_analyzed', 0)}")
            print(f"   📊 Matches Analyzed (Comprehensive): {comprehensive_form2.get('matches_analyzed', 0)}")
            
            # SAMPLE SIZE WEIGHTED set win rates: Apply confidence adjustment based on matches analyzed
            # More matches = higher confidence = less regression to mean
            recent_match_count1 = recent_form1.get('matches_analyzed', 0)
            recent_match_count2 = recent_form2.get('matches_analyzed', 0)
            comprehensive_matches1 = comprehensive_form1.get('matches_analyzed', 0)
            comprehensive_matches2 = comprehensive_form2.get('matches_analyzed', 0)
            
            # Calculate raw weighted rates (75% recent + 25% comprehensive)
            raw_rate1 = (recent_set_rate1 * 0.75) + (comprehensive_set_rate1 * 0.25)
            raw_rate2 = (recent_set_rate2 * 0.75) + (comprehensive_set_rate2 * 0.25)
            
            # Apply confidence adjustment based on total matches analyzed
            # More matches = more weight to actual rate, fewer matches = regress toward 50%
            total_matches1 = (recent_match_count1 * 0.75) + (comprehensive_matches1 * 0.25)
            total_matches2 = (recent_match_count2 * 0.75) + (comprehensive_matches2 * 0.25)
            
            # STRICTER THRESHOLD: reaches 100% confidence at 35 matches (was 20)
            # This addresses the "hot streak illusion" from small samples
            SAMPLE_CONFIDENCE_THRESHOLD = 35.0
            confidence1 = min(total_matches1 / SAMPLE_CONFIDENCE_THRESHOLD, 1.0)
            confidence2 = min(total_matches2 / SAMPLE_CONFIDENCE_THRESHOLD, 1.0)
            
            # Apply confidence weighting: (actual_rate * confidence) + (50% * (1 - confidence))
            set_win_rate1 = (raw_rate1 * confidence1) + (0.50 * (1 - confidence1))
            set_win_rate2 = (raw_rate2 * confidence2) + (0.50 * (1 - confidence2))
            
            print(f"\n⚖️ SAMPLE-SIZE WEIGHTED SET WIN RATES:")
            print(f"   📊 {player1.name}:")
            print(f"      Raw rate: {raw_rate1:.1%} from {total_matches1:.1f} matches")
            print(f"      Confidence: {confidence1:.1%} (100% at {SAMPLE_CONFIDENCE_THRESHOLD:.0f}+ matches)")
            print(f"      Adjusted rate: {set_win_rate1:.1%} (regressed toward 50% by {(1-confidence1)*100:.1f}%)")
            print(f"   📊 {player2.name}:")
            print(f"      Raw rate: {raw_rate2:.1%} from {total_matches2:.1f} matches")
            print(f"      Confidence: {confidence2:.1%} (100% at {SAMPLE_CONFIDENCE_THRESHOLD:.0f}+ matches)")
            print(f"      Adjusted rate: {set_win_rate2:.1%} (regressed toward 50% by {(1-confidence2)*100:.1f}%)")
            
            # IMPROVED: Use fair ranking threshold for quality opposition analysis
            # Use the WORSE ranking (higher number) between the two opponents as the threshold
            # This ensures both players have realistic chances of playing "quality" opposition
            standardized_ranking_threshold = max(opponent_ranking_for_p1 or 100, opponent_ranking_for_p2 or 100)
            # Use dynamic threshold based on actual player rankings (no artificial minimum)
            
            # Calculate quality opposition performance with proper win rates for fair comparison
            quality_perf1 = self._calculate_quality_opposition_performance(recent_form1, standardized_ranking_threshold)
            quality_perf2 = self._calculate_quality_opposition_performance(recent_form2, standardized_ranking_threshold)
            
            # CRITICAL: Apply data quality gates based on failed prediction analysis
            total_sets_analyzed = quality_perf1['total_sets'] + quality_perf2['total_sets']
            matches_analyzed = recent_form1.get('matches_analyzed', 0) + recent_form2.get('matches_analyzed', 0)
            avg_matches_analyzed = matches_analyzed / 2 if matches_analyzed > 0 else 0
            
            # Get individual player data for hard minimum checks
            # CRITICAL: Use TOTAL sets from ALL matches, not just quality opposition!
            # quality_perf only counts sets vs ranked opponents - could be 0 even if player played 2 sets
            player1_sets = recent_form1.get('form_data', {}).get('total_sets_won', 0) + recent_form1.get('form_data', {}).get('total_sets_lost', 0)
            player2_sets = recent_form2.get('form_data', {}).get('total_sets_won', 0) + recent_form2.get('form_data', {}).get('total_sets_lost', 0)
            player1_matches = recent_form1.get('matches_analyzed', 0)
            player2_matches = recent_form2.get('matches_analyzed', 0)
            min_sets = min(player1_sets, player2_sets)
            min_matches = min(player1_matches, player2_matches)
            
            data_quality_check = self.config.check_data_quality_gates(
                set_sample_size=min_sets,  # Use MINIMUM, not total!
                match_sample_size=min_matches,  # Use MINIMUM, not average!
                surface_quality="strong"  # Placeholder - could be enhanced
            )
            
            # CRITICAL: Check if match should be skipped due to insufficient data
            if data_quality_check.get('should_skip', False):
                print(f"\n🚫 CRITICAL DATA INSUFFICIENCY - SKIPPING MATCH!")
                print(f"   Risk Level: {data_quality_check['risk_level']}")
                print(f"   Reason: {data_quality_check['skip_reason']}")
                print(f"   📊 {player1.name}: {player1_sets} sets, {player1_matches} matches")
                print(f"   📊 {player2.name}: {player2_sets} sets, {player2_matches} matches")
                print(f"   ⚠️  Making predictions with {min_sets} min sets / {min_matches} min matches would be random noise")
                
                # Log the skip
                self.skip_logger.log_skip(
                    reason_type="INSUFFICIENT_DATA",
                    player1_name=player1.name,
                    player2_name=player2.name,
                    tournament=tournament_name,
                    surface=surface,
                    reason=data_quality_check['skip_reason']
                )
                return None  # Skip this match
            
            if data_quality_check['apply_discounts']:
                print(f"\n⚠️ DATA QUALITY GATES TRIGGERED!")
                print(f"   Risk Level: {data_quality_check['risk_level']}")
                for warning in data_quality_check['warnings']:
                    print(f"   • {warning}")
                    
                # Apply discounts to set performance calculations
                set_performance_discount = data_quality_check['set_performance_discount']
                form_discount = data_quality_check['form_discount']
                
                print(f"   📊 Set Performance Discount: {set_performance_discount:.2f}")
                print(f"   📊 Form Discount: {form_discount:.2f}")
            else:
                set_performance_discount = 1.0
                form_discount = 1.0
            
            print(f"\n🎯 QUALITY OPPOSITION PERFORMANCE (Standardized Threshold: Top-{standardized_ranking_threshold}):")
            print(f"   🏆 {player1.name}: {quality_perf1['sets_won']}/{quality_perf1['total_sets']} sets ({quality_perf1['set_win_rate']:.1%}) vs top-{standardized_ranking_threshold}")
            print(f"   🏆 {player2.name}: {quality_perf2['sets_won']}/{quality_perf2['total_sets']} sets ({quality_perf2['set_win_rate']:.1%}) vs top-{standardized_ranking_threshold}")
            
            # Check if ranking data is available in match history
            total_ranking_data_available = quality_perf1['total_sets'] + quality_perf2['total_sets']
            if total_ranking_data_available == 0:
                print(f"   📊 Note: No opponent ranking data available in match history - quality opposition analysis disabled")
            
            # IMPROVED: Use win rates instead of raw totals for accurate performance comparison
            # Apply quality opposition bonus only if player has sufficient data (4+ sets)
            quality_bonus1 = quality_perf1['set_win_rate'] if quality_perf1['has_sufficient_data'] else 0
            quality_bonus2 = quality_perf2['set_win_rate'] if quality_perf2['has_sufficient_data'] else 0
            
            # NEW: OPPONENT QUALITY PENALTY - Penalize players who haven't faced quality opposition
            # This addresses the failure pattern where players with inflated set win rates (from weak opponents) mislead the model
            opponent_quality_penalty1 = 1.0
            opponent_quality_penalty2 = 1.0
            
            if self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('enable_opponent_quality_penalty', False):
                quality_threshold = self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('opponent_quality_threshold', 0.30)
                penalty_amount = self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('opponent_quality_penalty', 0.30)
                
                # Calculate % of matches against quality opponents
                total_matches1 = recent_form1.get('matches_analyzed', 0)
                total_matches2 = recent_form2.get('matches_analyzed', 0)
                
                if total_matches1 > 0:
                    quality_match_pct1 = quality_perf1.get('matches_played', quality_perf1.get('matches_vs_quality', 0)) / total_matches1 if total_matches1 > 0 else 0
                    if quality_match_pct1 < quality_threshold:
                        opponent_quality_penalty1 = 1.0 - penalty_amount
                        print(f"\n⚠️ OPPONENT QUALITY PENALTY - {player1.name}:")
                        print(f"   📊 Only {quality_match_pct1:.1%} of matches vs quality opponents (threshold: {quality_threshold:.1%})")
                        print(f"   📉 Applying {penalty_amount:.1%} penalty to set performance (likely inflated by weak competition)")
                
                if total_matches2 > 0:
                    quality_match_pct2 = quality_perf2.get('matches_played', quality_perf2.get('matches_vs_quality', 0)) / total_matches2 if total_matches2 > 0 else 0
                    if quality_match_pct2 < quality_threshold:
                        opponent_quality_penalty2 = 1.0 - penalty_amount
                        print(f"\n⚠️ OPPONENT QUALITY PENALTY - {player2.name}:")
                        print(f"   📊 Only {quality_match_pct2:.1%} of matches vs quality opponents (threshold: {quality_threshold:.1%})")
                        print(f"   📉 Applying {penalty_amount:.1%} penalty to set performance (likely inflated by weak competition)")
            
            # Combined set performance score (IMPROVED: 75% raw set rate, 25% quality opposition WIN RATE)
            # Apply data quality discount AND opponent quality penalty if triggered
            set_performance1 = ((set_win_rate1 * 0.75) + (quality_bonus1 * 0.25)) * set_performance_discount * opponent_quality_penalty1
            set_performance2 = ((set_win_rate2 * 0.75) + (quality_bonus2 * 0.25)) * set_performance_discount * opponent_quality_penalty2
            
            print(f"\n🧮 COMBINED SET PERFORMANCE CALCULATION:")
            print(f"   Formula: (Overall Set Win Rate × 75%) + (Quality Opposition Win Rate × 25%)")
            print(f"   🎾 {player1.name}: ({set_win_rate1:.1%} × 75%) + ({quality_bonus1:.1%} × 25%) = {set_performance1:.3f}")
            print(f"   🎾 {player2.name}: ({set_win_rate2:.1%} × 75%) + ({quality_bonus2:.1%} × 25%) = {set_performance2:.3f}")
            if not quality_perf1['has_sufficient_data']:
                print(f"   ⚠️ {player1.name}: Insufficient quality opposition data ({quality_perf1['total_sets']} sets), using 0% bonus")
            if not quality_perf2['has_sufficient_data']:
                print(f"   ⚠️ {player2.name}: Insufficient quality opposition data ({quality_perf2['total_sets']} sets), using 0% bonus")
            
            # CRITICAL: HARD SKIP FOR POOR QUALITY OPPOSITION DATA
            # Skip matches where both players have unreliable data or predicted winner has inflated win rate
            quality_sets_won_p1 = quality_perf1.get('sets_won', 0)
            quality_sets_won_p2 = quality_perf2.get('sets_won', 0)
            quality_matches_faced_p1 = quality_perf1.get('matches_played', 0)
            quality_matches_faced_p2 = quality_perf2.get('matches_played', 0)
            
            # Rule 1: Skip if BOTH players have 0 quality sets won (both unreliable)
            if quality_sets_won_p1 == 0 and quality_sets_won_p2 == 0:
                skip_reason = (
                    f"Both players have 0 quality opposition sets won - data unreliable. "
                    f"{player1.name}: {quality_sets_won_p1} sets won ({quality_matches_faced_p1} matches faced), "
                    f"{player2.name}: {quality_sets_won_p2} sets won ({quality_matches_faced_p2} matches faced). "
                    f"Match outcome unpredictable when both players' win rates are based on weak competition."
                )
                print(f"\n🚫 HARD SKIP: POOR QUALITY OPPOSITION DATA")
                print(f"   Reason: {skip_reason}")
                self.skip_logger.log_skip(
                    reason_type="INSUFFICIENT_QUALITY_DATA",
                    player1_name=player1.name,
                    player2_name=player2.name,
                    tournament=tournament_name,
                    surface=surface,
                    reason=skip_reason
                )
                return None  # Skip this match
            
            # Rule 2: Skip if predicted winner has 0 quality sets won + high win rate + faced quality opponents
            # Determine predicted winner based on set win rates
            predicted_winner_is_p1 = set_win_rate1 > set_win_rate2
            
            if predicted_winner_is_p1:
                pred_quality_sets_won = quality_sets_won_p1
                pred_quality_matches_faced = quality_matches_faced_p1
                pred_win_rate = set_win_rate1
                pred_name = player1.name
            else:
                pred_quality_sets_won = quality_sets_won_p2
                pred_quality_matches_faced = quality_matches_faced_p2
                pred_win_rate = set_win_rate2
                pred_name = player2.name
            
            # Check if predicted winner has problematic quality data
            if (pred_quality_sets_won == 0 and 
                pred_win_rate > 0.75 and 
                pred_quality_matches_faced >= 1):
                skip_reason = (
                    f"Predicted winner ({pred_name}) has 0 quality opposition sets won but high win rate ({pred_win_rate:.1%}) "
                    f"indicating inflation from weak competition. Faced {pred_quality_matches_faced} quality opponents but lost all. "
                    f"Win rate unreliable for prediction."
                )
                print(f"\n🚫 HARD SKIP: INFLATED WIN RATE DETECTED")
                print(f"   Predicted Winner: {pred_name}")
                print(f"   Win Rate: {pred_win_rate:.1%} (inflated)")
                print(f"   Quality Sets Won: {pred_quality_sets_won}")
                print(f"   Quality Matches Faced: {pred_quality_matches_faced} (lost all)")
                print(f"   Reason: {skip_reason}")
                self.skip_logger.log_skip(
                    reason_type="INFLATED_WIN_RATE",
                    player1_name=player1.name,
                    player2_name=player2.name,
                    tournament=tournament_name,
                    surface=surface,
                    reason=skip_reason
                )
                return None  # Skip this match
            
            # RANKING GAP PENALTY: Discount set_performance advantage when lower-ranked player looks better
            # This addresses "hot streak illusion" where #116 player looks better than #44 player
            ranking_gap_penalty1 = 1.0
            ranking_gap_penalty2 = 1.0
            
            if opponent_ranking_for_p1 and opponent_ranking_for_p2:
                ranking_gap = abs(opponent_ranking_for_p1 - opponent_ranking_for_p2)
                
                # Apply penalty if ranking gap > 50 places AND lower-ranked player has better set_performance
                if ranking_gap > 50:
                    if opponent_ranking_for_p1 > opponent_ranking_for_p2 and set_performance1 > set_performance2:
                        # P1 is lower ranked but looks better - apply penalty to P1
                        penalty_factor = min(ranking_gap / 200.0, 0.30)  # Max 30% penalty
                        ranking_gap_penalty1 = 1.0 - penalty_factor
                        print(f"\n⚠️ RANKING GAP PENALTY:")
                        print(f"   {player1.name} ranked #{opponent_ranking_for_p1} vs {player2.name} ranked #{opponent_ranking_for_p2}")
                        print(f"   Gap: {ranking_gap} places - Applying {penalty_factor:.1%} penalty to {player1.name}'s set performance")
                        print(f"   Reason: Lower-ranked player's hot streak may not hold against class")
                    elif opponent_ranking_for_p2 > opponent_ranking_for_p1 and set_performance2 > set_performance1:
                        # P2 is lower ranked but looks better - apply penalty to P2
                        penalty_factor = min(ranking_gap / 200.0, 0.30)  # Max 30% penalty
                        ranking_gap_penalty2 = 1.0 - penalty_factor
                        print(f"\n⚠️ RANKING GAP PENALTY:")
                        print(f"   {player2.name} ranked #{opponent_ranking_for_p2} vs {player1.name} ranked #{opponent_ranking_for_p1}")
                        print(f"   Gap: {ranking_gap} places - Applying {penalty_factor:.1%} penalty to {player2.name}'s set performance")
                        print(f"   Reason: Lower-ranked player's hot streak may not hold against class")
            
            # Apply ranking gap penalty
            set_performance1 *= ranking_gap_penalty1
            set_performance2 *= ranking_gap_penalty2
            
            set_diff = set_performance1 - set_performance2
            print(f"   📊 Performance Difference: {set_diff:+.3f}")
            
            print(f"\n⚖️ WEIGHT CALCULATION - SET PERFORMANCE (35% of total):")
            print(f"   📊 Weight: {self.WEIGHTS['set_performance']:.1%}")
            print(f"   📊 Threshold: ±5% difference required")
            
            # CRITICAL FIX: Enhanced micro-edge filtering for set performance
            # Differences < 3% are statistical noise (lesson from Diallo failure: 0.6% difference treated as meaningful)
            SET_PERFORMANCE_MINIMUM_THRESHOLD = 0.03  # 3% minimum threshold
            
            if abs(set_diff) < SET_PERFORMANCE_MINIMUM_THRESHOLD:
                print(f"   🔍 MICRO-EDGE FILTER: Set performance gap {abs(set_diff):.1%} < {SET_PERFORMANCE_MINIMUM_THRESHOLD:.1%} threshold")
                print(f"   ❌ Gap too small to be meaningful - treating as equal set performance")
                # No key factor added, no score adjustment
            elif abs(set_diff) > 0.05:  # 5% difference threshold
                if set_diff > 0:
                    score_contribution = self.WEIGHTS['set_performance'] * set_diff
                    player1_score += score_contribution
                    print(f"   ✅ {player1.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                    factor_desc = f"{player1.name} better set performance ({set_win_rate1:.1%} vs {set_win_rate2:.1%}"
                    if quality_perf1['has_sufficient_data'] and quality_bonus1 > 0:
                        factor_desc += f", {quality_perf1['set_win_rate']:.1%} vs top-{standardized_ranking_threshold}"
                    factor_desc += ")"
                    key_factors.append(factor_desc)
                else:
                    score_contribution = self.WEIGHTS['set_performance'] * abs(set_diff)
                    player2_score += score_contribution
                    print(f"   ✅ {player2.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                    factor_desc = f"{player2.name} better set performance ({set_win_rate2:.1%} vs {set_win_rate1:.1%}"
                    if quality_perf2['has_sufficient_data'] and quality_bonus2 > 0:
                        factor_desc += f", {quality_perf2['set_win_rate']:.1%} vs top-{standardized_ranking_threshold}"
                    factor_desc += ")"
                    key_factors.append(factor_desc)
            
            weight_breakdown['set_performance'] = f"P1: {set_win_rate1:.1%} (quality: {quality_perf1['set_win_rate']:.1%} on {quality_perf1['total_sets']} sets), P2: {set_win_rate2:.1%} (quality: {quality_perf2['set_win_rate']:.1%} on {quality_perf2['total_sets']} sets) vs top-{standardized_ranking_threshold}"
            
            # Log form analysis details
            if self.prediction_logger:
                self.prediction_logger.log_form_analysis(player1.name, player2.name, recent_form1, recent_form2)
            
        except (AttributeError, KeyError, TypeError, ZeroDivisionError) as e:
            print(f"\n⚠️ ERROR calculating set performance: {type(e).__name__}: {e}")
            print(f"   Using default values for set performance calculation")
            weight_breakdown['set_performance'] = "P1: N/A, P2: N/A"
        
        # 2A. UTR SKILL RATING (25%) - Pure skill assessment
        utr_factor = 0
        p1_utr = player1.utr_rating
        p2_utr = player2.utr_rating
        
        if p1_utr and p2_utr:
            utr_gap = abs(p1_utr - p2_utr)
            
            print(f"\n🎯 UTR SKILL ASSESSMENT (25% weight)")
            print(f"   📊 {player1.name}: {p1_utr:.2f} UTR {'✓' if player1.utr_verified else ''}")
            print(f"   📊 {player2.name}: {p2_utr:.2f} UTR {'✓' if player2.utr_verified else ''}")
            print(f"   💡 UTR = Game win % + opponent strength (last 30 matches)")
            print(f"   📏 UTR Gap: {utr_gap:.2f} points")
            
            # UTR micro-edge filtering - ENHANCED THRESHOLDS
            UTR_MINIMUM_THRESHOLD = 0.15  # Increased from 0.10 to reduce overconfidence in tiny gaps
            UTR_MAJOR_GAP_THRESHOLD = 1.5  # New: Major skill difference threshold
            
            if utr_gap < UTR_MINIMUM_THRESHOLD:
                print(f"   🔍 MICRO-EDGE FILTER: UTR gap {utr_gap:.2f} < {UTR_MINIMUM_THRESHOLD:.2f} threshold")
                print(f"   ❌ Gap too small to be meaningful - no UTR advantage")
                utr_factor = 0
                weight_breakdown['utr'] = f"UTR - P1: {p1_utr:.2f}, P2: {p2_utr:.2f} (gap < threshold)"
            else:
                # Apply UTR skill factor with enhanced major gap handling
                if p1_utr > p2_utr:  # Higher UTR = better skill
                    utr_diff = p1_utr - p2_utr
                    utr_factor = min(utr_diff / 1.5, 1.0)  # 1.5 UTR difference = max factor
                    
                    # MAJOR GAP OVERRIDE: Massive skill differences should dominate recent form
                    if utr_diff >= UTR_MAJOR_GAP_THRESHOLD:
                        print(f"   ⚠️ MAJOR SKILL GAP: UTR difference {utr_diff:.2f} ≥ {UTR_MAJOR_GAP_THRESHOLD}")
                        print(f"   🎯 Class should override recent form fluctuations")
                        utr_factor *= 1.25  # 25% boost for major gaps
                        key_factors.append(f"{player1.name} has MAJOR UTR advantage ({p1_utr:.2f} vs {p2_utr:.2f}) - Class over Form")
                    else:
                        key_factors.append(f"{player1.name} has superior UTR skill ({p1_utr:.2f} vs {p2_utr:.2f})")
                    
                    score_contribution = self.WEIGHTS.get('utr_rating', self.WEIGHTS.get('ranking_advantage', 0.10)) * utr_factor
                    player1_score += score_contribution
                    print(f"   ✅ {player1.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                    if player1.utr_verified:
                        key_factors.append("✓ Verified UTR (tournament-validated)")
                else:
                    utr_diff = p2_utr - p1_utr
                    utr_factor = min(utr_diff / 1.5, 1.0)
                    
                    # MAJOR GAP OVERRIDE: Massive skill differences should dominate recent form
                    if utr_diff >= UTR_MAJOR_GAP_THRESHOLD:
                        print(f"   ⚠️ MAJOR SKILL GAP: UTR difference {utr_diff:.2f} ≥ {UTR_MAJOR_GAP_THRESHOLD}")
                        print(f"   🎯 Class should override recent form fluctuations")
                        utr_factor *= 1.25  # 25% boost for major gaps
                        key_factors.append(f"{player2.name} has MAJOR UTR advantage ({p2_utr:.2f} vs {p1_utr:.2f}) - Class over Form")
                    else:
                        key_factors.append(f"{player2.name} has superior UTR skill ({p2_utr:.2f} vs {p1_utr:.2f})")
                    
                    score_contribution = self.WEIGHTS.get('utr_rating', self.WEIGHTS.get('ranking_advantage', 0.10)) * utr_factor
                    player2_score += score_contribution
                    print(f"   ✅ {player2.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                    if player2.utr_verified:
                        key_factors.append("✓ Verified UTR (tournament-validated)")
                
                weight_breakdown['utr'] = f"UTR - P1: {p1_utr:.2f}, P2: {p2_utr:.2f}"
        else:
            print(f"\n⚠️ NO UTR DATA AVAILABLE (0% UTR weight applied)")
            weight_breakdown['utr'] = "No UTR data available"
        
        # 2B. ATP/WTA RANKING (15%) - Tour performance & momentum
        atp_factor = 0
        p1_ranking = player1.atp_ranking or player1.wta_ranking
        p2_ranking = player2.atp_ranking or player2.wta_ranking
        
        if p1_ranking and p2_ranking:
            ranking_gap = abs(p1_ranking - p2_ranking)
            
            print(f"\n🏆 ATP/WTA TOUR RANKING (15% weight)")
            print(f"   📊 {player1.name}: #{p1_ranking} ATP/WTA")
            print(f"   📊 {player2.name}: #{p2_ranking} ATP/WTA")
            print(f"   💡 Reflects tour performance & competitive momentum")
            print(f"   📏 Ranking Gap: {ranking_gap} positions")
            
            # ATP micro-edge filtering - ENHANCED THRESHOLDS  
            ATP_WTA_MINIMUM_THRESHOLD = 15  # Increased from 10 to reduce overconfidence in small ranking gaps
            ATP_WTA_MAJOR_GAP_THRESHOLD = 200  # New: Major ranking difference threshold
            
            if ranking_gap < ATP_WTA_MINIMUM_THRESHOLD:
                print(f"   🔍 MICRO-EDGE FILTER: Ranking gap {ranking_gap} < {ATP_WTA_MINIMUM_THRESHOLD} threshold")
                print(f"   ❌ Gap too small to be meaningful - no ATP advantage")
                atp_factor = 0
                weight_breakdown['atp'] = f"ATP - P1: #{p1_ranking}, P2: #{p2_ranking} (gap < threshold)"
            else:
                # Apply ATP ranking factor with enhanced major gap handling
                if p1_ranking < p2_ranking:  # Lower rank number = better
                    ranking_diff = p2_ranking - p1_ranking
                    atp_factor = min(ranking_diff / 50.0, 1.0)  # Normalize to max 1.0
                    
                    # MAJOR RANKING GAP: Massive ranking differences suggest class advantage
                    if ranking_diff >= ATP_WTA_MAJOR_GAP_THRESHOLD:
                        print(f"   ⚠️ MAJOR RANKING GAP: {ranking_diff} positions ≥ {ATP_WTA_MAJOR_GAP_THRESHOLD}")
                        print(f"   🎯 Significant class difference - ranking should override form")
                        atp_factor *= 1.20  # 20% boost for major ranking gaps
                        key_factors.append(f"{player1.name} has MAJOR ranking advantage (#{p1_ranking} vs #{p2_ranking}) - Class over Form")
                    else:
                        key_factors.append(f"{player1.name} has better ATP/WTA ranking (#{p1_ranking} vs #{p2_ranking})")
                    
                    score_contribution = self.WEIGHTS.get('atp_ranking', self.WEIGHTS.get('ranking_advantage', 0.10)) * atp_factor
                    player1_score += score_contribution
                    print(f"   ✅ {player1.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                else:
                    ranking_diff = p1_ranking - p2_ranking
                    atp_factor = min(ranking_diff / 50.0, 1.0)
                    
                    # MAJOR RANKING GAP: Massive ranking differences suggest class advantage  
                    if ranking_diff >= ATP_WTA_MAJOR_GAP_THRESHOLD:
                        print(f"   ⚠️ MAJOR RANKING GAP: {ranking_diff} positions ≥ {ATP_WTA_MAJOR_GAP_THRESHOLD}")
                        print(f"   🎯 Significant class difference - ranking should override form")
                        atp_factor *= 1.20  # 20% boost for major ranking gaps
                        key_factors.append(f"{player2.name} has MAJOR ranking advantage (#{p2_ranking} vs #{p1_ranking}) - Class over Form")
                    else:
                        key_factors.append(f"{player2.name} has better ATP/WTA ranking (#{p2_ranking} vs #{p1_ranking})")
                    
                    score_contribution = self.WEIGHTS.get('atp_ranking', self.WEIGHTS.get('ranking_advantage', 0.10)) * atp_factor
                    player2_score += score_contribution
                    print(f"   ✅ {player2.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                
                weight_breakdown['atp'] = f"ATP - P1: #{p1_ranking}, P2: #{p2_ranking}"
        else:
            print(f"\n⚠️ NO ATP/WTA DATA AVAILABLE (0% ATP weight applied)")
            weight_breakdown['atp'] = "No ATP/WTA data available"
        
        # 3. Recent form (30%) - Apply data quality discount if triggered
        form_diff = player1.recent_form_score - player2.recent_form_score
        effective_form_weight = self.WEIGHTS['recent_form'] * form_discount  # Apply quality discount
        
        # NEW: ENHANCED FORM WEIGHT - Increase weight when form gap is significant (>30%)
        # This addresses the failure pattern where large form gaps were underweighted
        form_multiplier = 1.0
        if self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('enable_enhanced_form_weight', False):
            form_gap_threshold = self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('form_gap_threshold', 30.0)
            enhanced_multiplier = self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('enhanced_form_multiplier', 1.5)
            
            if abs(form_diff) > form_gap_threshold:
                form_multiplier = enhanced_multiplier
                print(f"\n🔥 ENHANCED FORM WEIGHT ACTIVATED:")
                print(f"   📊 Form gap {abs(form_diff):.1f} > {form_gap_threshold:.1f} threshold")
                print(f"   📈 Applying {enhanced_multiplier}x multiplier to form weight ({self.WEIGHTS['recent_form']:.1%} → {self.WEIGHTS['recent_form'] * enhanced_multiplier:.1%})")
                print(f"   💡 Large form differentials proved highly predictive in loss analysis")
        
        effective_form_weight = effective_form_weight * form_multiplier
        
        print(f"\n📊 RECENT FORM ASSESSMENT ({self.WEIGHTS['recent_form']:.1%} weight × {form_discount:.1f} discount × {form_multiplier:.1f} multiplier = {effective_form_weight:.1%})")
        print(f"   🎯 {player1.name}: {player1.recent_form_score:.1f}")
        print(f"   🎯 {player2.name}: {player2.recent_form_score:.1f}")
        print(f"   📏 Form Gap: {abs(form_diff):.1f} points (threshold: 5.0)")
        
        if abs(form_diff) > 5:  # Significant form difference
            if form_diff > 0:
                score_contribution = effective_form_weight * (form_diff / 100)
                player1_score += score_contribution
                print(f"   ✅ {player1.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                key_factors.append(f"{player1.name} has better recent form ({player1.recent_form_score:.1f} vs {player2.recent_form_score:.1f})")
            else:
                score_contribution = effective_form_weight * (abs(form_diff) / 100)
                player2_score += score_contribution
                print(f"   ✅ {player2.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                key_factors.append(f"{player2.name} has better recent form ({player2.recent_form_score:.1f} vs {player1.recent_form_score:.1f})")
        else:
            print(f"   ❌ Gap < 5.0 threshold - no form advantage")
        
        weight_breakdown['form'] = f"P1: {player1.recent_form_score:.1f}, P2: {player2.recent_form_score:.1f}"
        
        # 4. Clutch performance (8%) - Important for +1.5 sets but needs significant difference
        clutch_diff = player1.clutch_performance - player2.clutch_performance
        if abs(clutch_diff) > 0.20:  # Require 20% difference (was 10%)
            if clutch_diff > 0:
                score_contribution = self.WEIGHTS['clutch_factor'] * clutch_diff
                player1_score += score_contribution
                print(f"   🔥 CLUTCH: {player1.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                key_factors.append(f"{player1.name} more clutch in tight sets ({player1.clutch_performance:.1%} vs {player2.clutch_performance:.1%})")
            else:
                score_contribution = self.WEIGHTS['clutch_factor'] * abs(clutch_diff)
                player2_score += score_contribution
                print(f"   🔥 CLUTCH: {player2.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                key_factors.append(f"{player2.name} more clutch in tight sets ({player2.clutch_performance:.1%} vs {player1.clutch_performance:.1%})")
        
        weight_breakdown['clutch'] = f"P1: {player1.clutch_performance:.1%}, P2: {player2.clutch_performance:.1%}"
        
        # 5. OPTIONAL: Tiebreak Performance (only if enabled)
        if self.config.is_feature_enabled('tiebreak_performance'):
            print(f"\n🏆 TIEBREAK PERFORMANCE ANALYSIS:")
            print(f"{'='*60}")
            
            tiebreak_perf1 = self.calculate_enhanced_tiebreak_performance(player1.id, surface)
            tiebreak_perf2 = self.calculate_enhanced_tiebreak_performance(player2.id, surface)
            
            print(f"   🎾 {player1.name}: {tiebreak_perf1:.1%} tiebreak win rate")
            print(f"   🎾 {player2.name}: {tiebreak_perf2:.1%} tiebreak win rate")
            
            tiebreak_diff = tiebreak_perf1 - tiebreak_perf2
            if abs(tiebreak_diff) > 0.1:  # 10% difference threshold
                if tiebreak_diff > 0:
                    player1_score += self.WEIGHTS.get('tiebreak_performance', 0) * tiebreak_diff
                    key_factors.append(f"{player1.name} superior in tiebreaks ({tiebreak_perf1:.1%} vs {tiebreak_perf2:.1%})")
                    print(f"   ✅ {player1.name} advantage: +{self.WEIGHTS.get('tiebreak_performance', 0) * tiebreak_diff:.3f} points")
                else:
                    player2_score += self.WEIGHTS.get('tiebreak_performance', 0) * abs(tiebreak_diff)
                    key_factors.append(f"{player2.name} superior in tiebreaks ({tiebreak_perf2:.1%} vs {tiebreak_perf1:.1%})")
                    print(f"   ✅ {player2.name} advantage: +{self.WEIGHTS.get('tiebreak_performance', 0) * abs(tiebreak_diff):.3f} points")
            
            weight_breakdown['tiebreak'] = f"P1: {tiebreak_perf1:.1%}, P2: {tiebreak_perf2:.1%}"
        
        # 🆕 CLOSE MATCH MENTAL AMPLIFICATION (Post-Blinkova loss analysis)
        # For close matches, amplify mental/pressure factors by 1.5x
        # Blinkova won 7-6, 7-5 despite being underdog in aggregate stats - mental toughness mattered more
        # Detect close matches based on current score difference before mental/pressure factors
        close_match_mental_amplification = prediction_config.ENHANCED_FEATURES.get('close_match_mental_amplification', False)
        current_score_diff = abs(player1_score - player2_score)
        is_close_match = False
        
        if close_match_mental_amplification and current_score_diff < 0.05:
            is_close_match = True
            print(f"\n🧠 CLOSE MATCH MENTAL AMPLIFICATION ACTIVATED:")
            print(f"   📊 Score difference: {current_score_diff:.3f} < 0.05 threshold")
            print(f"   📈 Mental toughness and pressure performance weights will be amplified by 1.5x")
            print(f"   💡 In close matches, mental factors prove decisive (Blinkova case: 7-6, 7-5)")
        
        # 6. OPTIONAL: Pressure Performance (only if enabled)
        if self.config.is_feature_enabled('pressure_performance'):
            print(f"\n🔥 PRESSURE PERFORMANCE ANALYSIS:")
            print(f"{'='*60}")
            
            pressure_perf1 = self.calculate_enhanced_pressure_performance(player1.id, surface)
            pressure_perf2 = self.calculate_enhanced_pressure_performance(player2.id, surface)
            
            print(f"   🎾 {player1.name}: {pressure_perf1:.1%} pressure performance (break points)")
            print(f"   🎾 {player2.name}: {pressure_perf2:.1%} pressure performance (break points)")
            
            pressure_diff = pressure_perf1 - pressure_perf2
            if abs(pressure_diff) > 0.1:  # 10% difference threshold
                # Apply close match amplification if enabled
                pressure_weight = self.WEIGHTS.get('pressure_performance', 0)
                if is_close_match:
                    original_weight = pressure_weight
                    pressure_weight = pressure_weight * 1.5
                    print(f"   🧠 CLOSE MATCH BOOST: Pressure weight amplified {original_weight:.1%} → {pressure_weight:.1%}")
                
                if pressure_diff > 0:
                    player1_score += pressure_weight * pressure_diff
                    key_factors.append(f"{player1.name} better under pressure ({pressure_perf1:.1%} vs {pressure_perf2:.1%})")
                    print(f"   ✅ {player1.name} advantage: +{pressure_weight * pressure_diff:.3f} points")
                else:
                    player2_score += pressure_weight * abs(pressure_diff)
                    key_factors.append(f"{player2.name} better under pressure ({pressure_perf2:.1%} vs {pressure_perf1:.1%})")
                    print(f"   ✅ {player2.name} advantage: +{pressure_weight * abs(pressure_diff):.3f} points")
            
            weight_breakdown['pressure'] = f"P1: {pressure_perf1:.1%}, P2: {pressure_perf2:.1%}"
        
        # 7. RETURN OF SERVE PERFORMANCE (Hannah Fry Insight: "1% better at returning = amplified advantage")
        if self.config.is_feature_enabled('return_of_serve_focus'):
            print(f"\n🔄 RETURN OF SERVE ANALYSIS (Hannah Fry Insight):")
            print(f"{'='*60}")
            
            return_perf1 = self.calculate_return_of_serve_performance(player1.id, surface)
            return_perf2 = self.calculate_return_of_serve_performance(player2.id, surface)
            
            print(f"   🎾 {player1.name}: {return_perf1:.1%} return performance (break points + return games)")
            print(f"   🎾 {player2.name}: {return_perf2:.1%} return performance (break points + return games)")
            
            return_diff = return_perf1 - return_perf2
            
            # Hannah Fry's insight: Even small return advantages get amplified
            # Lower threshold since return performance is crucial
            if abs(return_diff) > 0.02:  # 2% difference threshold (lower than others)
                amplified_diff = return_diff
                
                # Apply Hannah Fry amplification if enabled
                if self.config.ENHANCED_FEATURES.get('hannah_fry_amplification', False):
                    amplified_diff = self.config.apply_hannah_fry_amplification(return_diff, 'return')
                    print(f"   🔬 Hannah Fry amplification: {return_diff:.3f} → {amplified_diff:.3f}")
                
                if amplified_diff > 0:
                    points_added = self.WEIGHTS.get('return_of_serve', 0) * amplified_diff
                    player1_score += points_added
                    key_factors.append(f"{player1.name} superior returner ({return_perf1:.1%} vs {return_perf2:.1%}) - Hannah Fry amplified")
                    print(f"   ✅ {player1.name} return advantage: +{points_added:.3f} points (amplified)")
                else:
                    points_added = self.WEIGHTS.get('return_of_serve', 0) * abs(amplified_diff)
                    player2_score += points_added
                    key_factors.append(f"{player2.name} superior returner ({return_perf2:.1%} vs {return_perf1:.1%}) - Hannah Fry amplified")
                    print(f"   ✅ {player2.name} return advantage: +{points_added:.3f} points (amplified)")
            
            weight_breakdown['return_serve'] = f"P1: {return_perf1:.1%}, P2: {return_perf2:.1%}"

        # 8. OPTIONAL: Serve Dominance (only if enabled)  
        if self.config.is_feature_enabled('serve_dominance'):
            print(f"\n🎯 SERVE DOMINANCE ANALYSIS:")
            print(f"{'='*60}")
            
            serve_dom1 = self.calculate_enhanced_serve_dominance(player1.id, surface)
            serve_dom2 = self.calculate_enhanced_serve_dominance(player2.id, surface)
            
            print(f"   🎾 {player1.name}: {serve_dom1:.1%} serve dominance")
            print(f"   🎾 {player2.name}: {serve_dom2:.1%} serve dominance")
            
            # 🆕 SURFACE-SPECIFIC SERVE AMPLIFICATION (Post-Ruud loss analysis)
            # Indoor hardcourt = serve-heavy surface → amplify serve weight by 1.5x
            serve_weight = self.WEIGHTS.get('serve_dominance', 0)
            surface_specific_boost_enabled = prediction_config.ENHANCED_FEATURES.get('surface_specific_serve_boost', False)
            
            if surface_specific_boost_enabled and surface and 'indoor' in surface.lower():
                original_weight = serve_weight
                serve_weight = min(serve_weight * 1.5, 0.30)  # Cap at 30%
                print(f"   🏠 INDOOR HARDCOURT DETECTED → Serve weight amplified: {original_weight:.1%} → {serve_weight:.1%}")
            
            serve_diff = serve_dom1 - serve_dom2
            if abs(serve_diff) > 0.1:  # 10% difference threshold
                if serve_diff > 0:
                    player1_score += serve_weight * serve_diff
                    key_factors.append(f"{player1.name} serves more effectively ({serve_dom1:.1%} vs {serve_dom2:.1%})")
                    print(f"   ✅ {player1.name} advantage: +{serve_weight * serve_diff:.3f} points")
                else:
                    player2_score += serve_weight * abs(serve_diff)
                    key_factors.append(f"{player2.name} serves more effectively ({serve_dom2:.1%} vs {serve_dom1:.1%})")
                    print(f"   ✅ {player2.name} advantage: +{serve_weight * abs(serve_diff):.3f} points")
            
            weight_breakdown['serve'] = f"P1: {serve_dom1:.1%}, P2: {serve_dom2:.1%}"
        
        # Log enhanced statistics to prediction logger (only if features are enabled)
        if self.prediction_logger:
            tiebreak_stats = None
            pressure_stats = None  
            serve_stats = None
            
            if self.config.is_feature_enabled('tiebreak_performance'):
                tiebreak_stats = {'player1': tiebreak_perf1, 'player2': tiebreak_perf2}
                
            if self.config.is_feature_enabled('pressure_performance'):
                pressure_stats = {'player1': pressure_perf1, 'player2': pressure_perf2}
                
            if self.config.is_feature_enabled('serve_dominance'):
                serve_stats = {'player1': serve_dom1, 'player2': serve_dom2}
            
            # Only log if at least one enhanced feature is enabled
            if any([tiebreak_stats, pressure_stats, serve_stats]):
                self.prediction_logger.log_enhanced_statistics(
                    player1.name, player2.name,
                    tiebreak_stats=tiebreak_stats,
                    pressure_stats=pressure_stats,
                    serve_stats=serve_stats
                )
        
        # 8. PSYCHOLOGICAL RESILIENCE (Hannah Fry: "mindset towards failure and resilience to losing")
        if self.config.ENHANCED_FEATURES.get('hannah_fry_amplification', False):
            print(f"\n🧠 PSYCHOLOGICAL RESILIENCE ANALYSIS (Hannah Fry Insight):")
            print(f"{'='*60}")
            
            # Calculate resilience based on recent performance under losses
            recent_losses1 = len([m for m in recent_matches1 if m.get('player_sets', 0) < m.get('opponent_sets', 0)])
            recent_losses2 = len([m for m in recent_matches2 if m.get('player_sets', 0) < m.get('opponent_sets', 0)])
            
            resilience1 = self.config.calculate_psychological_resilience(recent_losses1, len(recent_matches1))
            resilience2 = self.config.calculate_psychological_resilience(recent_losses2, len(recent_matches2))
            
            print(f"   🎾 {player1.name}: {resilience1:.1%} resilience (from {recent_losses1}/{len(recent_matches1)} recent losses)")
            print(f"   🎾 {player2.name}: {resilience2:.1%} resilience (from {recent_losses2}/{len(recent_matches2)} recent losses)")
            
            resilience_diff = resilience1 - resilience2
            if abs(resilience_diff) > 0.1:  # 10% difference threshold
                resilience_weight = self.config.HANNAH_FRY_FACTORS['resilience_factor']
                
                if resilience_diff > 0:
                    points_added = resilience_weight * resilience_diff
                    player1_score += points_added
                    key_factors.append(f"{player1.name} more resilient under pressure ({resilience1:.1%} vs {resilience2:.1%})")
                    print(f"   ✅ {player1.name} resilience advantage: +{points_added:.3f} points")
                else:
                    points_added = resilience_weight * abs(resilience_diff)
                    player2_score += points_added
                    key_factors.append(f"{player2.name} more resilient under pressure ({resilience2:.1%} vs {resilience1:.1%})")
                    print(f"   ✅ {player2.name} resilience advantage: +{points_added:.3f} points")
                    
            weight_breakdown['resilience'] = f"P1: {resilience1:.1%}, P2: {resilience2:.1%}"

        # 9. Enhanced Surface Performance (11%) - With intelligent fallbacks to prevent skewing
        print(f"\n🏟️ SURFACE PERFORMANCE ANALYSIS:")
        print(f"{'='*60}")
        
        # Get enhanced surface performance with data quality tracking
        surface_result1 = self.calculate_enhanced_surface_performance(player1.id, surface)
        surface_result2 = self.calculate_enhanced_surface_performance(player2.id, surface)
        
        # Handle both old 2-tuple and new 3-tuple formats
        if len(surface_result1) == 3:
            surface_perf1, actual_surface1, data_quality1 = surface_result1
            surface_perf2, actual_surface2, data_quality2 = surface_result2
        else:
            surface_perf1, actual_surface1 = surface_result1
            surface_perf2, actual_surface2 = surface_result2
            data_quality1 = data_quality2 = "legacy_format"
        
        # Extract and store match counts for data quality gates
        try:
            # Get enhanced stats to extract actual match counts
            enhanced_stats1 = self.stats_handler.get_enhanced_player_statistics(player1.id, surface)
            enhanced_stats2 = self.stats_handler.get_enhanced_player_statistics(player2.id, surface)
            
            # Store match counts for data quality gate access
            self._last_p1_surface_matches = enhanced_stats1.get('statistics', {}).get('matches', 0)
            self._last_p2_surface_matches = enhanced_stats2.get('statistics', {}).get('matches', 0)
        except Exception:
            # Fallback to 0 if stats unavailable
            self._last_p1_surface_matches = 0
            self._last_p2_surface_matches = 0
        
        # Check for poor data quality that could skew predictions
        poor_quality1 = "weak" in data_quality1 or "no_surface" in data_quality1 or "error" in data_quality1
        poor_quality2 = "weak" in data_quality2 or "no_surface" in data_quality2 or "error" in data_quality2
        either_poor_quality = poor_quality1 or poor_quality2
        
        # ALWAYS use the tournament surface for current match analysis
        # Historical surfaces may have different naming conventions, but the match is played on the tournament surface
        display_surface = surface  # Tournament surface is authoritative for current match
        
        # Log any surface mismatches for debugging (but don't change display)
        if actual_surface1 and actual_surface1.lower() != surface.lower():
            print(f"   📝 Note: {player1.name} historical data shows '{actual_surface1}' vs tournament '{surface}'")
        if actual_surface2 and actual_surface2.lower() != surface.lower():
            print(f"   📝 Note: {player2.name} historical data shows '{actual_surface2}' vs tournament '{surface}'")
        
        print(f"   🎾 {player1.name}: {surface_perf1:.1%} win rate on {display_surface}")
        print(f"   🎾 {player2.name}: {surface_perf2:.1%} win rate on {display_surface}")
        
        # Display data quality warnings
        if poor_quality1:
            print(f"   ⚠️ {player1.name}: Surface data quality: {data_quality1}")
        if poor_quality2:
            print(f"   ⚠️ {player2.name}: Surface data quality: {data_quality2}")
        
        # SURFACE DATA QUALITY GATES - Critical warnings for insufficient match surface data
        surface_data_issues = []
        
        # Check match counts from enhanced stats if available
        try:
            # Extract match counts from surface performance calculation
            player1_match_count = getattr(self, '_last_p1_surface_matches', 0)
            player2_match_count = getattr(self, '_last_p2_surface_matches', 0)
            
            # Warn for insufficient surface data
            if player1_match_count < 10:
                warning_msg = f"🚨 {player1.name}: VERY LIMITED {surface} data ({player1_match_count} matches) - predictions unreliable"
                print(f"   {warning_msg}")
                surface_data_issues.append(warning_msg)
            elif player1_match_count < 20:
                warning_msg = f"⚠️ {player1.name}: Limited {surface} data ({player1_match_count} matches) - use caution"
                print(f"   {warning_msg}")
                surface_data_issues.append(warning_msg)
                
            if player2_match_count < 10:
                warning_msg = f"🚨 {player2.name}: VERY LIMITED {surface} data ({player2_match_count} matches) - predictions unreliable"
                print(f"   {warning_msg}")
                surface_data_issues.append(warning_msg)
            elif player2_match_count < 20:
                warning_msg = f"⚠️ {player2.name}: Limited {surface} data ({player2_match_count} matches) - use caution"
                print(f"   {warning_msg}")
                surface_data_issues.append(warning_msg)
                
        except Exception:
            # Fallback: Use basic quality assessment
            if "weak" in data_quality1 or "minimal" in data_quality1:
                warning_msg = f"🚨 {player1.name}: Insufficient {surface} data quality - predictions unreliable"
                print(f"   {warning_msg}")
                surface_data_issues.append(warning_msg)
            if "weak" in data_quality2 or "minimal" in data_quality2:
                warning_msg = f"🚨 {player2.name}: Insufficient {surface} data quality - predictions unreliable"
                print(f"   {warning_msg}")
                surface_data_issues.append(warning_msg)
        
        # Dynamically adjust surface weight based on data quality and performance gap
        base_surface_weight = self.WEIGHTS['surface_performance']
        surface_diff = surface_perf1 - surface_perf2
        abs_surface_diff = abs(surface_diff)
        
        if either_poor_quality:
            # Reduce surface weight by 50% when data quality is poor to prevent skewing
            adjusted_surface_weight = base_surface_weight * 0.5
            print(f"   🔧 Reducing surface weight from {base_surface_weight:.1%} to {adjusted_surface_weight:.1%} due to poor data quality")
        else:
            # CRITICAL FIX: Boost surface weight for massive performance gaps with strong data
            confidence_boost = 1.0
            
            # Check for confident_strong data quality
            if "confident_strong" in data_quality1 or "confident_strong" in data_quality2:
                if abs_surface_diff >= 0.40:  # 40%+ gap = massive advantage
                    confidence_boost = 2.5
                    print(f"   🚀 MASSIVE surface advantage detected: {abs_surface_diff:.1%} gap with strong data - boosting weight 2.5x")
                elif abs_surface_diff >= 0.30:  # 30%+ gap = major advantage  
                    confidence_boost = 2.0
                    print(f"   🚀 MAJOR surface advantage detected: {abs_surface_diff:.1%} gap with strong data - boosting weight 2.0x")
                elif abs_surface_diff >= 0.20:  # 20%+ gap = significant advantage
                    confidence_boost = 1.5
                    print(f"   📈 SIGNIFICANT surface advantage detected: {abs_surface_diff:.1%} gap with strong data - boosting weight 1.5x")
            
            adjusted_surface_weight = base_surface_weight * confidence_boost
            if confidence_boost > 1.0:
                print(f"   ⚖️ Surface weight: {base_surface_weight:.1%} → {adjusted_surface_weight:.1%}")
            else:
                adjusted_surface_weight = base_surface_weight
        
        if abs(surface_diff) > 0.1:  # 10% difference
            if surface_diff > 0:
                score_contribution = adjusted_surface_weight * surface_diff
                player1_score += score_contribution
                key_factors.append(f"{player1.name} better on {display_surface} ({surface_perf1:.1%} vs {surface_perf2:.1%})")
                print(f"   ✅ {player1.name} advantage: +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
            else:
                score_contribution = adjusted_surface_weight * abs(surface_diff)
                player2_score += score_contribution
                key_factors.append(f"{player2.name} better on {display_surface} ({surface_perf2:.1%} vs {surface_perf1:.1%})")
                print(f"   ✅ {player2.name} advantage: +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
        
        quality_suffix = " (reduced weight)" if either_poor_quality else ""
        weight_breakdown['surface'] = f"P1: {surface_perf1:.1%} ({data_quality1}), P2: {surface_perf2:.1%} ({data_quality2}){quality_suffix}"
        
        # SURFACE MISMATCH DETECTION - Alert when predicted favorite is weak on match surface
        surface_mismatch_alerts = []
        current_leader = player1.name if player1_score > player2_score else player2.name
        leader_surface_perf = surface_perf1 if player1_score > player2_score else surface_perf2
        underdog_surface_perf = surface_perf2 if player1_score > player2_score else surface_perf1
        underdog_name = player2.name if player1_score > player2_score else player1.name
        
        # Critical alert: Current favorite is significantly weaker on match surface
        if abs(surface_diff) > 0.15:  # 15%+ surface gap
            if leader_surface_perf < underdog_surface_perf:
                surface_gap = underdog_surface_perf - leader_surface_perf
                if surface_gap >= 0.30:  # 30%+ gap = massive mismatch
                    alert_msg = f"🚨 MAJOR SURFACE MISMATCH: {current_leader} leads overall but {underdog_name} {surface_gap:.1%} better on {surface}!"
                    print(f"   {alert_msg}")
                    surface_mismatch_alerts.append(alert_msg)
                elif surface_gap >= 0.20:  # 20%+ gap = significant mismatch
                    alert_msg = f"⚠️ SURFACE MISMATCH: {current_leader} leads overall but {underdog_name} {surface_gap:.1%} better on {surface}!"
                    print(f"   {alert_msg}")
                    surface_mismatch_alerts.append(alert_msg)
                    
        # Alert for poor surface data quality on match surface
        if either_poor_quality and abs(surface_diff) > 0.20:
            alert_msg = f"⚠️ UNRELIABLE SURFACE DATA: Large {surface} performance gap but poor data quality - use extreme caution!"
            print(f"   {alert_msg}")
            surface_mismatch_alerts.append(alert_msg)
        
        # 9. Momentum (2%) - Reduced weight
        momentum_diff = player1.momentum_score - player2.momentum_score
        if abs(momentum_diff) > 0.2:
            if momentum_diff > 0:
                score_contribution = self.WEIGHTS['momentum'] * momentum_diff
                player1_score += score_contribution
                print(f"   🚀 MOMENTUM: {player1.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                key_factors.append(f"{player1.name} has better momentum ({player1.momentum_score:.2f} vs {player2.momentum_score:.2f})")
            else:
                score_contribution = self.WEIGHTS['momentum'] * abs(momentum_diff)
                player2_score += score_contribution
                print(f"   🚀 MOMENTUM: {player2.name} +{score_contribution:.3f} | Running total: P1={player1_score:.3f}, P2={player2_score:.3f}")
                key_factors.append(f"{player2.name} has better momentum ({player2.momentum_score:.2f} vs {player1.momentum_score:.2f})")
        
        weight_breakdown['momentum'] = f"P1: {player1.momentum_score:.2f}, P2: {player2.momentum_score:.2f}"
        
        # 8. Mental Toughness Factor (if enabled in configuration)
        if 'mental_toughness' in self.WEIGHTS and self.WEIGHTS['mental_toughness'] > 0:
            try:
                # Get mental toughness analysis for both players
                player1_mental = self.analyze_player_mental_toughness(player1.name, player1.id)
                player2_mental = self.analyze_player_mental_toughness(player2.name, player2.id)
                
                # Extract tiebreak rates
                p1_rate_str = player1_mental.get('tiebreak_rate', '50.0%')
                p2_rate_str = player2_mental.get('tiebreak_rate', '50.0%')
                p1_tiebreak = float(p1_rate_str.replace('%', '')) / 100.0
                p2_tiebreak = float(p2_rate_str.replace('%', '')) / 100.0
                
                # Calculate mental toughness differential with normalized scaling
                mental_diff = p1_tiebreak - p2_tiebreak
                
                # Apply mental toughness weight if there's a significant difference (>10%)
                if abs(mental_diff) > 0.10:
                    mental_factor = min(abs(mental_diff), 0.5) * 2.0  # Scale to 0-1.0 range
                    
                    # Apply close match amplification if enabled
                    mental_weight = self.WEIGHTS['mental_toughness']
                    if is_close_match:
                        original_weight = mental_weight
                        mental_weight = mental_weight * 1.5
                        print(f"   🧠 CLOSE MATCH BOOST: Mental toughness weight amplified {original_weight:.1%} → {mental_weight:.1%}")
                    
                    if mental_diff > 0:
                        player1_score += mental_weight * mental_factor
                        key_factors.append(f"{player1.name} mentally stronger ({p1_rate_str} vs {p2_rate_str} tiebreak rate)")
                    else:
                        player2_score += mental_weight * mental_factor
                        key_factors.append(f"{player2.name} mentally stronger ({p2_rate_str} vs {p1_rate_str} tiebreak rate)")
                
                weight_breakdown['mental_toughness'] = f"P1: {p1_rate_str}, P2: {p2_rate_str}"
                
            except Exception as e:
                print(f"⚠️ Mental toughness analysis failed: {e}")
                weight_breakdown['mental_toughness'] = "Analysis failed"
        
        # 9. Sets in Losses - Competitive Resilience Factor (if enabled in configuration)
        if 'sets_in_losses' in self.WEIGHTS and self.WEIGHTS['sets_in_losses'] > 0:
            try:
                print(f"\n🏆 COMPETITIVE RESILIENCE ANALYSIS:")
                print(f"{'='*60}")
                
                # Calculate competitive resilience for both players (surface-specific)
                p1_resilience, p1_sets_won, p1_total_sets, p1_losses = self.calculate_sets_in_losses(player1.id, surface)
                p2_resilience, p2_sets_won, p2_total_sets, p2_losses = self.calculate_sets_in_losses(player2.id, surface)
                
                # Log the data with surface context
                self._log_competitive_resilience(player1.name, player1.id, p1_resilience, p1_sets_won, p1_total_sets, p1_losses, surface)
                self._log_competitive_resilience(player2.name, player2.id, p2_resilience, p2_sets_won, p2_total_sets, p2_losses, surface)
                
                # Terminal output with surface context
                surface_context = f" on {surface}" if surface else " (all surfaces)"
                print(f"🎾 {player1.name}: {p1_resilience:.1f}% resilience ({p1_sets_won}/{p1_total_sets} sets in {p1_losses} losses{surface_context})")
                print(f"🎾 {player2.name}: {p2_resilience:.1f}% resilience ({p2_sets_won}/{p2_total_sets} sets in {p2_losses} losses{surface_context})")
                
                # Calculate resilience differential (normalize to 0-100 scale)
                resilience_diff = (p1_resilience - p2_resilience) / 100.0
                
                # Apply sets_in_losses weight if there's a significant difference (>10%)
                if abs(resilience_diff) > 0.10:
                    resilience_factor = min(abs(resilience_diff), 0.5) * 2.0  # Scale to 0-1.0 range
                    
                    if resilience_diff > 0:
                        player1_score += self.WEIGHTS['sets_in_losses'] * resilience_factor
                        surface_note = f" on {surface}" if surface else ""
                        key_factors.append(f"{player1.name} more competitive in losses ({p1_resilience:.1f}% vs {p2_resilience:.1f}% resilience{surface_note})")
                    else:
                        player2_score += self.WEIGHTS['sets_in_losses'] * resilience_factor
                        surface_note = f" on {surface}" if surface else ""
                        key_factors.append(f"{player2.name} more competitive in losses ({p2_resilience:.1f}% vs {p1_resilience:.1f}% resilience{surface_note})")
                
                weight_breakdown['sets_in_losses'] = f"P1: {p1_resilience:.1f}%, P2: {p2_resilience:.1f}%"
                
            except Exception as e:
                print(f"⚠️ Competitive resilience analysis failed: {e}")
                weight_breakdown['sets_in_losses'] = "Analysis failed"
        
        # NOTE: Crowd sentiment is now handled as confidence modifier only, not as a weight factor
        
        # Determine prediction with realistic probability bounds
        total_score = player1_score + player2_score
        if total_score > 0:
            # Calculate raw probabilities
            raw_player1_prob = player1_score / total_score
            raw_player2_prob = player2_score / total_score
            
            # Cap probabilities to prevent extreme values (max 95%, min 10%)
            # Increased cap from 85% to 95% to allow proper differentiation of clear favorites
            player1_match_prob = max(0.10, min(0.95, raw_player1_prob))
            player2_match_prob = max(0.10, min(0.95, raw_player2_prob))
            
            # Normalize to ensure they sum to 1.0
            total_capped = player1_match_prob + player2_match_prob
            player1_match_prob = player1_match_prob / total_capped
            player2_match_prob = player2_match_prob / total_capped
        else:
            player1_match_prob = player2_match_prob = 0.5
            
        # 🚨 CRITICAL: Apply data quality probability caps based on actual performance
        # This prevents overconfident predictions like our recent losses (76-84% for poor performers)
        player1_match_prob, player2_match_prob = self._apply_data_quality_probability_caps(
            player1_match_prob, player2_match_prob, player1, player2, surface
        )
            
        # Calculate "+1.5 sets" probabilities (probability of winning at least 1 set)
        # Based on match probability, tennis scoring dynamics, and match format
        is_best_of_five = match_format.is_best_of_five if match_format else False
        
        if match_format:
            print(f"\n🎾 MATCH FORMAT DETECTED:")
            print(f"   📋 Tournament: {match_format.tournament_name}")
            print(f"   🏆 Level: {match_format.tournament_level}")
            print(f"   👥 Gender: {match_format.gender}")
            print(f"   🎯 Format: {'Best-of-5' if is_best_of_five else 'Best-of-3'}")
            if is_best_of_five:
                print(f"   ⚠️ GRAND SLAM MEN'S SINGLES: Higher +1.5 sets probability due to best-of-5 format!")
        
        # FIXED: Calculate set probabilities correctly using _calculate_set_probability method
        # Each player's probability represents their chance of winning at least 1 set in this match
        # These are calculated independently based on their match win probability
        
        # TEMPORARY: Calculate initial set probabilities for early logic (will be recalculated with final values)
        print(f"\n🔢 CALCULATING INITIAL SET PROBABILITIES (+1.5 sets betting):")
        print(f"   Match format: {'Best-of-5' if is_best_of_five else 'Best-of-3'}")
        print(f"   Initial match probabilities: P1: {player1_match_prob:.1%}, P2: {player2_match_prob:.1%}")
        
        # Calculate initial set probabilities using early estimates (for upset detection logic)
        player1_set_prob = self._calculate_set_probability(player1_match_prob, is_best_of_five)
        player2_set_prob = self._calculate_set_probability(player2_match_prob, is_best_of_five)
        
        # 🆕 AGGRESSIVE SAMPLE SIZE CONFIDENCE CAP (Post-Ruud loss analysis)
        # If either player has insufficient data, hard cap confidence to prevent overconfidence
        aggressive_caps_enabled = prediction_config.ENHANCED_FEATURES.get('aggressive_sample_size_caps', False)
        if aggressive_caps_enabled:
            try:
                # Get sample sizes for both players
                enhanced_stats_p1 = self.stats_handler.get_enhanced_player_statistics(player1.id, surface)
                enhanced_stats_p2 = self.stats_handler.get_enhanced_player_statistics(player2.id, surface)
                
                sample_sizes_p1 = enhanced_stats_p1.get('sample_sizes', {})
                sample_sizes_p2 = enhanced_stats_p2.get('sample_sizes', {})
                
                # Get SETS count (not matches) for more accurate sample size assessment
                sets_p1 = sample_sizes_p1.get('sets', sample_sizes_p1.get('matches', 0) * 2)  # Fallback: estimate 2 sets/match
                sets_p2 = sample_sizes_p2.get('sets', sample_sizes_p2.get('matches', 0) * 2)
                
                min_sets = min(sets_p1, sets_p2)
                
                print(f"\n🎯 AGGRESSIVE SAMPLE SIZE CAPS:")
                print(f"   {player1.name}: {sets_p1} sets")
                print(f"   {player2.name}: {sets_p2} sets")
                print(f"   Minimum: {min_sets} sets")
                
                sample_size_cap = None
                if min_sets < 5:
                    sample_size_cap = 0.50
                    print(f"   ⚠️ <5 sets → HARD CAP: 50%")
                elif min_sets < 10:
                    sample_size_cap = 0.60
                    print(f"   ⚠️ <10 sets → HARD CAP: 60%")
                elif min_sets < 15:
                    sample_size_cap = 0.68
                    print(f"   ⚠️ <15 sets → HARD CAP: 68%")
                else:
                    print(f"   ✅ ≥15 sets → Normal 73% cap applies")
                
                if sample_size_cap:
                    player1_set_prob = min(player1_set_prob, sample_size_cap)
                    player2_set_prob = min(player2_set_prob, sample_size_cap)
                    print(f"   📉 Capped probabilities: P1: {player1_set_prob:.1%}, P2: {player2_set_prob:.1%}")
                    
            except Exception as e:
                print(f"   ⚠️ Error applying sample size caps: {e}")
        
        # Apply bounds with 73% OVERCONFIDENCE PROTECTION
        # This ensures set probabilities also respect our validation-based confidence cap
        player1_set_prob = max(0.25, min(0.73, player1_set_prob))
        player2_set_prob = max(0.25, min(0.73, player2_set_prob))
        
        print(f"   Initial set probabilities: P1: {player1_set_prob:.1%}, P2: {player2_set_prob:.1%}")
        print(f"   ⚠️ These will be recalculated using final prediction values")
        
        # Determine winner and confidence with MINIMUM THRESHOLD CHECK
        score_diff = abs(player1_score - player2_score)
        
        # CRITICAL: Initialize form protection for all code paths
        form_protection = {'apply_protection': False, 'terrible_form_detected': False}
        
        # CRITICAL: Don't make predictions unless there's meaningful difference
        coin_flip_threshold = self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('coin_flip_score_threshold', 0.05)
        should_skip_coin_flips = self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('skip_coin_flip_matches', False)
        
        if score_diff < coin_flip_threshold:  # Less than 5% total score difference
            # CRITICAL FIX: Use set probabilities for predicted winner, not UTR/ranking
            # This prevents contradictions between predicted_winner and recommended_bet fields
            if player1_set_prob > player2_set_prob:
                predicted_winner = player1.name
                win_probability = 0.55  # Slight edge only
            else:
                predicted_winner = player2.name
                win_probability = 0.55
                
            base_confidence = "Low"
            predicted_score = "Coin flip - slight edge"
            base_confidence_score = 0.05
            print(f"   ⚖️ CLOSE MATCH: Using set probabilities for winner ({predicted_winner}) to prevent data contradictions")
            
            # NEW: COIN FLIP SKIP - Skip low confidence matches with poor risk/reward ratio
            if should_skip_coin_flips:
                print(f"\n🚫 COIN FLIP SKIP ACTIVATED:")
                print(f"   📊 Score difference {score_diff:.3f} < {coin_flip_threshold} threshold")
                print(f"   ⚠️ Low confidence 'coin flip' matches have poor risk/reward")
                print(f"   💡 Both losses in analysis were coin flip predictions (55% confidence)")
                skip_match = True
                skip_reason = f"Coin flip match (score diff {score_diff:.1%} < {coin_flip_threshold:.1%}) - poor risk/reward ratio"
            else:
                skip_match = False
                skip_reason = ""
        else:
            # Normal prediction logic
            if player1_score > player2_score:
                predicted_winner = player1.name
                win_probability = player1_match_prob
                score_diff = player1_score - player2_score
            else:
                predicted_winner = player2.name
                win_probability = player2_match_prob
                score_diff = player2_score - player1_score
            
            # CRITICAL: NEW - Form protection based on failed prediction analysis  
            predicted_player_form = player1.recent_form_score if predicted_winner == player1.name else player2.recent_form_score
            form_protection = self.config.check_form_protection(
                player1.recent_form_score, 
                player2.recent_form_score, 
                predicted_player_form
            )
            
            # Apply form protection adjustments to final calculations
            if form_protection['apply_protection']:
                print(f"\n⚠️ FORM PROTECTION ACTIVATED!")
                print(f"   Protection Level: {form_protection['risk_level']}")
                print(f"   Reason: {form_protection['reason']}")
                
                for warning in form_protection['warnings']:
                    print(f"   • {warning}")
                
                if form_protection['terrible_form_detected']:
                    print(f"   🚨 TERRIBLE FORM DETECTED - High risk of bagel!")
                    # Apply severe confidence penalty for terrible form
                    score_diff *= 0.5  # Reduce advantage significantly
                    print(f"   📉 Score advantage reduced due to poor form")
            
            # NEW: CONFLICTING SIGNALS DETECTION - Skip when UTR+Form+Ranking align against set performance
            # This addresses the failure pattern where set performance favored the loser but all skill metrics favored the winner
            skip_match = False
            skip_reason = ""
            
            if self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('enable_conflicting_signals_skip', False):
                threshold = self.config.LOSS_ANALYSIS_IMPROVEMENTS.get('conflicting_signals_threshold', 2)
                
                # Determine who has the advantage in each metric
                utr_favors = None
                if p1_utr and p2_utr and abs(p1_utr - p2_utr) > 0.15:  # Meaningful UTR difference
                    utr_favors = player1.name if p1_utr > p2_utr else player2.name
                
                form_favors = None
                form_diff_check = player1.recent_form_score - player2.recent_form_score
                if abs(form_diff_check) > 10:  # Meaningful form difference
                    form_favors = player1.name if form_diff_check > 0 else player2.name
                
                ranking_favors = None
                if p1_ranking and p2_ranking and abs(p1_ranking - p2_ranking) > 30:  # Meaningful ranking difference
                    ranking_favors = player1.name if p1_ranking < p2_ranking else player2.name  # Lower rank = better
                
                set_perf_favors = None
                # Check who was favored by raw set performance BEFORE other factors were considered
                # We need to look at the key_factors to see if set performance was a deciding factor
                for factor in key_factors:
                    if 'better set performance' in factor.lower():
                        if player1.name in factor:
                            set_perf_favors = player1.name
                        elif player2.name in factor:
                            set_perf_favors = player2.name
                        break
                
                # Count how many skill metrics align
                skill_metrics = [utr_favors, form_favors, ranking_favors]
                skill_metrics = [m for m in skill_metrics if m is not None]  # Remove None values
                
                if len(skill_metrics) >= threshold and set_perf_favors is not None:
                    # Check if all non-None skill metrics agree
                    first_metric = skill_metrics[0]
                    all_agree = all(m == first_metric for m in skill_metrics)
                    
                    # Check if they oppose set performance
                    if all_agree and first_metric != set_perf_favors:
                        skip_match = True
                        opposing_player = first_metric
                        skip_reason = (f"Conflicting signals: {len(skill_metrics)} skill metrics (UTR, Form, Ranking) "
                                      f"favor {opposing_player} but set performance favors {set_perf_favors}. "
                                      f"Analysis of losses shows trusting skill metrics over inflated set performance.")
                        
                        print(f"\n🚫 CONFLICTING SIGNALS SKIP ACTIVATED:")
                        print(f"   📊 Skill metrics alignment:")
                        if utr_favors:
                            print(f"      - UTR favors: {utr_favors}")
                        if form_favors:
                            print(f"      - Recent Form favors: {form_favors}")
                        if ranking_favors:
                            print(f"      - ATP/WTA Ranking favors: {ranking_favors}")
                        print(f"   📊 Set Performance favors: {set_perf_favors}")
                        print(f"   ⚠️ {len(skill_metrics)} skill metrics oppose set performance indicator")
                        print(f"   💡 Both analyzed losses had this exact pattern - skill metrics proved more predictive")
            
            # Hannah Fry Enhanced Confidence Levels - Apply 3% rule and amplification
            base_confidence_score = score_diff
            
            # Apply Hannah Fry's insights to confidence calculation
            if self.config.ENHANCED_FEATURES.get('hannah_fry_amplification', False):
                three_percent_threshold = self.config.get_three_percent_threshold()
                
                # Hannah Fry: 3% better = dominance
                if score_diff >= three_percent_threshold:
                    # Apply amplification to significant advantages
                    amplified_score = self.config.apply_hannah_fry_amplification(score_diff, 'general')
                    print(f"\n🔬 HANNAH FRY CONFIDENCE AMPLIFICATION:")
                    print(f"   📊 Raw advantage: {score_diff:.3f}")
                    print(f"   📊 3% rule threshold: {three_percent_threshold:.3f}")
                    print(f"   🚀 Amplified advantage: {amplified_score:.3f}")
                    
                    if amplified_score > 0.25:  # Very strong amplified advantage
                        base_confidence = "Very High"
                        predicted_score = "Highly likely to win at least 1 set (Hannah Fry amplified)"
                    elif amplified_score > 0.15:
                        base_confidence = "High"
                        predicted_score = "Likely to win at least 1 set (amplified edge)"
                    else:
                        base_confidence = "Medium-High"
                        predicted_score = "Good amplified chance to win at least 1 set"
                        
                    # Update score_diff for further calculations
                    base_confidence_score = amplified_score
                else:
                    # Below 3% threshold - standard confidence levels
                    if score_diff > 0.15:
                        base_confidence = "High"
                        predicted_score = "Likely to win at least 1 set"
                    elif score_diff > 0.08:
                        base_confidence = "Medium"
                        predicted_score = "Good chance to win at least 1 set"
                    else:
                        base_confidence = "Low"
                        predicted_score = "May win at least 1 set"
            else:
                # Original confidence levels (no Hannah Fry amplification)
                if score_diff > 0.15:
                    base_confidence = "High"
                    predicted_score = "Likely to win at least 1 set"
                elif score_diff > 0.08:
                    base_confidence = "Medium"
                    predicted_score = "Good chance to win at least 1 set" 
                else:
                    base_confidence = "Low"
                    predicted_score = "May win at least 1 set"
        
        # Apply crowd sentiment confidence modifier (NEW FRAMEWORK)
        final_confidence = base_confidence
        crowd_reasoning = ""
        
        if event_id:
            # Get tournament level for high-profile considerations
            tournament_level = "Unknown"  # Could be enhanced with tournament data
            
            # 🆕 DATA QUALITY CROWD GATING (Post-Ruud loss analysis)
            # Only use crowd sentiment when both players have sufficient data
            use_crowd_sentiment = True
            crowd_gating_enabled = prediction_config.ENHANCED_FEATURES.get('data_quality_crowd_gating', False)
            
            if crowd_gating_enabled:
                try:
                    # Get sample sizes for both players
                    enhanced_stats_p1 = self.stats_handler.get_enhanced_player_statistics(player1.id, surface)
                    enhanced_stats_p2 = self.stats_handler.get_enhanced_player_statistics(player2.id, surface)
                    
                    sample_sizes_p1 = enhanced_stats_p1.get('sample_sizes', {})
                    sample_sizes_p2 = enhanced_stats_p2.get('sample_sizes', {})
                    
                    sets_p1 = sample_sizes_p1.get('sets', sample_sizes_p1.get('matches', 0) * 2)
                    sets_p2 = sample_sizes_p2.get('sets', sample_sizes_p2.get('matches', 0) * 2)
                    
                    min_sets = min(sets_p1, sets_p2)
                    
                    if min_sets < 10:
                        use_crowd_sentiment = False
                        print(f"\n🚫 CROWD SENTIMENT DISABLED (data quality gating):")
                        print(f"   Minimum sample size: {min_sets} sets < 10 sets threshold")
                        print(f"   Crowd often misled by rankings/reputation when players have thin data")
                except Exception as e:
                    print(f"   ⚠️ Error checking crowd gating: {e}")
            
            if use_crowd_sentiment:
                crowd_sentiment_data = self.analyze_crowd_sentiment_confidence(
                    event_id=event_id,
                    predicted_winner=predicted_winner, 
                    player1_name=player1.name,
                    player2_name=player2.name,
                    base_confidence=base_confidence_score,
                    tournament_level=tournament_level
                )
            else:
                # Skip crowd sentiment analysis - data quality too low
                crowd_sentiment_data = {
                    'adjusted_confidence': base_confidence_score,
                    'crowd_analysis': "Crowd sentiment disabled (insufficient player data)",
                    'confidence_adjustment': 0.0,
                    'crowd_favorite': 'Unknown',
                    'crowd_percentage': 0,
                    'vote_volume': 'Disabled'
                }
            
            # CIRCUIT BREAKER DISABLED - Trust the model over crowd sentiment
            # Contrarian betting is often where the value is. Objective data filters (TIER 0-3, form validation,
            # surface filtering, current-year performance) are sufficient for quality control.
            # Crowd disagreement can indicate value opportunities, not risks.
            
            # Circuit breaker code commented out:
            # if crowd_sentiment_data.get('circuit_breaker_triggered', False):
            #     [Skip bet due to crowd disagreement]
            
            # Update confidence based on crowd analysis
            adjusted_confidence_score = crowd_sentiment_data['adjusted_confidence']
            confidence_adjustment = crowd_sentiment_data['confidence_adjustment']
            
            # 🔍 MINIMUM DATA THRESHOLD CHECKS - Prevent overconfident predictions on thin data
            data_quality_downgrades = []
            
            # Check surface data quality for both players
            winner_id = player1.id if predicted_winner == player1.name else player2.id
            loser_id = player2.id if predicted_winner == player1.name else player1.id
            
            winner_matches, winner_confidence = self._get_surface_match_data(winner_id, surface)
            loser_matches, loser_confidence = self._get_surface_match_data(loser_id, surface)
            
            # Downgrade confidence if insufficient data
            if winner_matches < 15 or loser_matches < 15:  # Less than 15 matches for either player
                if adjusted_confidence_score > 0.08:  # Prevent High confidence
                    adjusted_confidence_score = min(adjusted_confidence_score, 0.08)
                    data_quality_downgrades.append(f"Insufficient surface data (W:{winner_matches}, L:{loser_matches} matches)")
                    
            if winner_confidence < 0.6 or loser_confidence < 0.6:  # Poor data quality
                if adjusted_confidence_score > 0.12:  # Prevent High confidence  
                    adjusted_confidence_score = min(adjusted_confidence_score, 0.12)
                    data_quality_downgrades.append(f"Poor data quality (W:{winner_confidence:.2f}, L:{loser_confidence:.2f} conf)")
            
            # Both players have NO surface data
            if winner_matches == 0 and loser_matches == 0:
                adjusted_confidence_score = min(adjusted_confidence_score, 0.05)  # Force to Low
                data_quality_downgrades.append("NO SURFACE DATA for both players - betting blind")
            
            if data_quality_downgrades:
                print(f"\n⚠️ DATA QUALITY DOWNGRADES:")
                for downgrade in data_quality_downgrades:
                    print(f"   🔻 {downgrade}")
                print(f"   Final adjusted confidence: {adjusted_confidence_score:.3f}")
            
            # Convert adjusted score back to categorical confidence
            if adjusted_confidence_score > 0.15:
                final_confidence = "High"
            elif adjusted_confidence_score > 0.08:
                final_confidence = "Medium"
            else:
                final_confidence = "Low"
            
            # Add crowd analysis to reasoning if significant
            if abs(confidence_adjustment) > 0.05:  # Only mention if >5% adjustment
                crowd_reasoning = f" {crowd_sentiment_data['crowd_analysis']}"
                
            # Add crowd data to weight breakdown
            weight_breakdown['crowd_sentiment'] = crowd_sentiment_data['crowd_analysis']
        else:
            weight_breakdown['crowd_sentiment'] = "No event ID provided"
        
        # CLOSE MATCH PENALTY - Apply confidence reduction for small UTR gaps
        utr_gap = 0.0
        close_match_penalty = 0.0
        
        if p1_utr and p2_utr:
            utr_gap = abs(float(p1_utr) - float(p2_utr))
            
            # Apply penalty for close matches (small UTR gaps)
            if utr_gap < 0.5:
                # Very close match - significant penalty
                close_match_penalty = 0.15  # -15% confidence
                final_confidence = "Medium" if final_confidence == "High" else final_confidence
                print(f"   ⚠️  CLOSE MATCH PENALTY: UTR gap {utr_gap:.2f} < 0.5 → -15% confidence")
            elif utr_gap < 1.0:
                # Moderately close match - moderate penalty  
                close_match_penalty = 0.08  # -8% confidence
                if final_confidence == "High":
                    final_confidence = "Medium"
                print(f"   ⚠️  CLOSE MATCH PENALTY: UTR gap {utr_gap:.2f} < 1.0 → -8% confidence")
        
        # Apply lower-tier tournament penalty (players ranked >200)
        ranking_penalty = 0.0
        if (p1_ranking and p1_ranking > 200) or (p2_ranking and p2_ranking > 200):
            ranking_penalty = 0.05  # -5% confidence for lower-tier players
            if final_confidence == "High":
                final_confidence = "Medium"
            print(f"   ⚠️  LOWER-TIER PENALTY: Player(s) ranked >200 → -5% confidence")
        
        # Apply clay court penalty - clay has higher upset rate (15/27 failures were on clay)
        clay_penalty = 0.0
        if surface and 'clay' in surface.lower():
            clay_penalty = 0.05  # -5% confidence for clay courts
            if final_confidence == "High" and utr_gap < 1.5:
                final_confidence = "Medium"
            print(f"   🟤 CLAY COURT PENALTY: {surface} → -5% confidence (higher upset rate)")
            
        # Apply enhanced confidence penalties (if enabled)
        calibrated_penalties = self._apply_calibrated_confidence_penalties(
            utr_gap, p1_ranking, p2_ranking, surface, tournament_name, final_confidence,
            player1, player2, player1.surface_win_rate, player2.surface_win_rate
        )
        if calibrated_penalties['applied']:
            final_confidence = calibrated_penalties['adjusted_confidence']
            for penalty_reason in calibrated_penalties['reasons']:
                print(f"   🎯 CALIBRATED PENALTY: {penalty_reason}")
        
        # CRITICAL: Apply upset prediction protection - UTR FIRST, then ATP/WTA fallback
        # Use UTR for more accurate upset detection (higher UTR = better skill)
        if (p1_utr and p2_utr) or (p1_ranking and p2_ranking):
            # Determine who is predicted to win based on set probabilities  
            predicted_set_winner = player1.name if player1_set_prob > player2_set_prob else player2.name
            
            if p1_utr and p2_utr:
                # UTR-based upset detection (more accurate)
                predicted_set_winner_utr = p1_utr if predicted_set_winner == player1.name else p2_utr
                opponent_utr = p2_utr if predicted_set_winner == player1.name else p1_utr
                
                # Convert UTR to equivalent ranking for protection logic compatibility
                # Higher UTR = lower equivalent ranking (UTR 15.0 ≈ Top 10, UTR 12.0 ≈ Top 100)
                predicted_set_winner_ranking = max(1, int((16.5 - predicted_set_winner_utr) * 20))
                opponent_ranking = max(1, int((16.5 - opponent_utr) * 20))
                
                print(f"\n🎯 UPSET DETECTION USING UTR (Gold Standard)")
                print(f"   Predicted Winner: {predicted_set_winner} (UTR {predicted_set_winner_utr:.2f})")
                print(f"   Opponent: UTR {opponent_utr:.2f}")
            else:
                # Fallback to ATP/WTA rankings
                predicted_set_winner_ranking = p1_ranking if predicted_set_winner == player1.name else p2_ranking
                opponent_ranking = p2_ranking if predicted_set_winner == player1.name else p1_ranking
                
                print(f"\n⚠️ UPSET DETECTION USING ATP/WTA FALLBACK")
                print(f"   Predicted Winner: {predicted_set_winner} (#{predicted_set_winner_ranking})")
                print(f"   Opponent: #{opponent_ranking}")
            
            # Convert final confidence to numeric for protection check
            confidence_numeric = 0.8 if final_confidence == "High" else 0.5 if final_confidence == "Medium" else 0.2
            
            upset_protection = self.config.check_upset_prediction_protection(
                predicted_set_winner_ranking, opponent_ranking, confidence_numeric
            )
            
            if upset_protection['apply_protection']:
                print(f"\n⚠️ UPSET PREDICTION PROTECTION ACTIVATED!")
                print(f"   Protection Level: {upset_protection['risk_level']}")
                print(f"   Reason: {upset_protection['reason']}")
                
                if upset_protection['cap_confidence']:
                    new_confidence_numeric = upset_protection['new_confidence']
                    if new_confidence_numeric <= 0.3:
                        final_confidence = "Low"
                    elif new_confidence_numeric <= 0.6:
                        final_confidence = "Medium"  
                    else:
                        final_confidence = "High"
                        
                    print(f"   📉 Confidence Capped: {final_confidence}")
                    
                if upset_protection['require_extra_factors']:
                    strong_factors = len([f for f in key_factors if any(word in f.lower() for word in ['better', 'higher', 'superior'])])
                    required_factors = self.config.RISK_MANAGEMENT['upset_multiple_factors_required']
                    
                    if strong_factors < required_factors:
                        print(f"   🚨 INSUFFICIENT SUPPORTING FACTORS!")
                        print(f"   Found: {strong_factors} strong factors")
                        print(f"   Required: {required_factors} factors for upset prediction")
                        print(f"   🛑 FORCING CONFIDENCE TO LOW")
                        final_confidence = "Low"
        
        # CRITICAL: NEW - Bagel protection based on failed prediction analysis
        confidence_numeric = 0.8 if final_confidence == "High" else 0.5 if final_confidence == "Medium" else 0.2
        form_issues_detected = form_protection.get('apply_protection', False)
        crowd_disagreement_detected = crowd_sentiment_data.get('skip_bet', False) if 'crowd_sentiment_data' in locals() else False
        
        bagel_protection = self.config.check_bagel_protection(
            confidence=confidence_numeric,
            red_flags_count=0,  # Will be calculated inside the method
            form_issues=form_issues_detected,
            crowd_disagreement=crowd_disagreement_detected
        )
        
        if bagel_protection['apply_protection']:
            print(f"\n⚠️ BAGEL PROTECTION ACTIVATED!")
            print(f"   Protection Level: {bagel_protection['risk_level']}")
            print(f"   Reason: {bagel_protection['reason']}")
            print(f"   Red Flags: {', '.join(bagel_protection['red_flags'])}")
            
            # Cap confidence to prevent bagel scenarios
            new_confidence_numeric = bagel_protection['confidence_cap']
            if new_confidence_numeric <= 0.3:
                final_confidence = "Low"
            elif new_confidence_numeric <= 0.6:
                final_confidence = "Medium"  
            else:
                final_confidence = "High"
                
            print(f"   📉 Confidence Capped: {final_confidence} (was {confidence_numeric:.1%}, now {new_confidence_numeric:.1%})")
        
        # ENHANCED: Determine optimal betting strategy (Sets vs Games)
        betting_analysis = self._analyze_optimal_betting_strategy(
            player1, player2, p1_utr, p2_utr, player1_set_prob, player2_set_prob
        )
        
        # Generate reasoning based on selected betting strategy
        if betting_analysis['betting_type'] == 'GAMES':
            recommended_winner = betting_analysis['game_handicap_recommendation']['recommended_player']
            handicap_value = betting_analysis['game_handicap_recommendation']['handicap_value']
            reasoning = f"Recommended bet: {recommended_winner} {handicap_value} games based on "
            reasoning += f"close match analysis: {betting_analysis['market_selection_reason']}. "
            if key_factors:
                reasoning += f"Key factors: {'; '.join(key_factors[:2])}. "
            reasoning += f"Game handicap preferred due to closely matched opponents."
        else:
            # Original set betting logic
            set_bet_winner = player1.name if player1_set_prob > player2_set_prob else player2.name
            reasoning = f"Recommended bet: {set_bet_winner} +1.5 sets based on "
        if key_factors:
            reasoning += f"key advantages: {'; '.join(key_factors[:3])}. "
        else:
            reasoning += "marginal overall advantage across multiple factors. "
        
        reasoning += f"Strong set-level performance analysis indicates {win_probability:.0%} chance of winning at least one set."
        
        # Add crowd sentiment reasoning if significant
        if crowd_reasoning:
            reasoning += crowd_reasoning
        
        # Display comprehensive prediction breakdown
        print(f"\n🎯 FINAL PREDICTION BREAKDOWN:")
        print(f"{'='*70}")
        print(f"🏆 Predicted Winner: {predicted_winner}")
        print(f"📈 Win Probability: {win_probability:.1%}")
        print(f"⭐ Confidence Level: {final_confidence}")
        print(f"🎾 Predicted Score: {predicted_score}")
        
        print(f"\n📊 FINAL SCORES:")
        print(f"   🎾 {player1.name}: {player1_score:.3f}")
        print(f"   🎾 {player2.name}: {player2_score:.3f}")
        print(f"   📊 Difference: {abs(player1_score - player2_score):.3f}")
        
        # Initialize enhanced statistics variables for display
        tiebreak_perf1 = tiebreak_perf2 = 0.5
        pressure_perf1 = pressure_perf2 = 0.5  
        serve_dom1 = serve_dom2 = 0.5
        
        # Only show enhanced statistics summary if any are enabled
        enhanced_features_enabled = any([
            self.config.is_feature_enabled('tiebreak_performance'),
            self.config.is_feature_enabled('pressure_performance'),
            self.config.is_feature_enabled('serve_dominance')
        ])
        
        if enhanced_features_enabled:
            print(f"\n⭐ ENHANCED STATISTICS SUMMARY:")
            
            if self.config.is_feature_enabled('tiebreak_performance'):
                tiebreak_perf1 = self.calculate_enhanced_tiebreak_performance(player1.id, surface)
                tiebreak_perf2 = self.calculate_enhanced_tiebreak_performance(player2.id, surface)
                print(f"   🏆 Tiebreak Performance: {player1.name} {tiebreak_perf1:.1%} vs {player2.name} {tiebreak_perf2:.1%}")
                
            if self.config.is_feature_enabled('pressure_performance'):
                pressure_perf1 = self.calculate_enhanced_pressure_performance(player1.id, surface)
                pressure_perf2 = self.calculate_enhanced_pressure_performance(player2.id, surface)
                print(f"   🔥 Pressure Performance: {player1.name} {pressure_perf1:.1%} vs {player2.name} {pressure_perf2:.1%}")
                
            if self.config.is_feature_enabled('serve_dominance'):
                serve_dom1 = self.calculate_enhanced_serve_dominance(player1.id, surface)
                serve_dom2 = self.calculate_enhanced_serve_dominance(player2.id, surface)
                print(f"   🎯 Serve Dominance: {player1.name} {serve_dom1:.1%} vs {player2.name} {serve_dom2:.1%}")
        
        # Always show surface performance since it's a base feature
        print(f"\n🏟️ SURFACE PERFORMANCE:")
        print(f"   {player1.name}: {surface_perf1:.1%} vs {player2.name}: {surface_perf2:.1%}")
        
        print(f"\n🔍 SET PROBABILITIES (+1.5 Sets - Win At Least 1 Set):")
        print(f"   🎾 {player1.name}: {player1_set_prob:.1%} chance to win at least 1 set")
        print(f"   🎾 {player2.name}: {player2_set_prob:.1%} chance to win at least 1 set")
        print(f"   📊 Note: These are independent probabilities for +1.5 sets betting")
        
        print(f"\n🎯 KEY FACTORS ({len(key_factors)} total):")
        for i, factor in enumerate(key_factors[:5], 1):
            print(f"   {i}. {factor}")
        
        print(f"\n⚖️ WEIGHT BREAKDOWN:")
        for factor, breakdown in weight_breakdown.items():
            print(f"   📊 {factor}: {breakdown}")
        
        print(f"\n💡 REASONING:")
        print(f"   {reasoning}")
        print(f"{'='*70}")
        
        # FIXED: Recalculate set probabilities using FINAL win_probability (not early estimates)
        print(f"\n🔢 RECALCULATING SET PROBABILITIES USING FINAL PREDICTION:")
        print(f"   Match format: {'Best-of-5' if is_best_of_five else 'Best-of-3'}")
        
        # Convert final win_probability back to individual player match probabilities
        if predicted_winner == player1.name:
            final_player1_match_prob = win_probability
            final_player2_match_prob = 1.0 - win_probability
        else:
            final_player1_match_prob = 1.0 - win_probability  
            final_player2_match_prob = win_probability
            
        print(f"   Final match probabilities: P1: {final_player1_match_prob:.1%}, P2: {final_player2_match_prob:.1%}")
        
        # MENTAL TOUGHNESS ANALYSIS - Analyze BOTH players BEFORE set probability calculation
        # Note: tournament_name already extracted at start of method
            
        # Analyze mental toughness for BOTH players
        player1_mental = self.analyze_player_mental_toughness(player1.name, player1.id)
        player2_mental = self.analyze_player_mental_toughness(player2.name, player2.id)
        
        # Convert final confidence to numeric for mental toughness analysis
        confidence_numeric = 0.8 if final_confidence == "High" else 0.5 if final_confidence == "Medium" else 0.2
        
        # Apply mental toughness differential to MATCH probabilities
        mental_toughness_adjustment = self.analyze_mental_toughness_differential(
            event_id, predicted_winner, player1.name, player2.name,
            confidence_numeric, tournament_name, player1.id, player2.id,
            player1_mental, player2_mental
        )
        
        # Apply mental toughness to match probabilities BEFORE calculating set probabilities
        if mental_toughness_adjustment['apply_adjustment']:
            confidence_adjustment = mental_toughness_adjustment['confidence_adjustment']
            
            # Convert confidence adjustment to match probability adjustment
            # Scale the adjustment for match probabilities (smaller than confidence adjustment)
            match_prob_adjustment = confidence_adjustment * 0.5  # 50% of confidence adjustment
            
            if predicted_winner == player1.name:
                # Adjust player 1's match probability
                adjusted_p1_match_prob = max(0.05, min(0.95, final_player1_match_prob + match_prob_adjustment))
                adjusted_p2_match_prob = 1.0 - adjusted_p1_match_prob
            else:
                # Adjust player 2's match probability  
                adjusted_p2_match_prob = max(0.05, min(0.95, final_player2_match_prob + match_prob_adjustment))
                adjusted_p1_match_prob = 1.0 - adjusted_p2_match_prob
                
            print(f"\n🧠 MENTAL TOUGHNESS MATCH PROBABILITY ADJUSTMENT:")
            print(f"   Original: P1: {final_player1_match_prob:.1%}, P2: {final_player2_match_prob:.1%}")
            print(f"   Adjusted: P1: {adjusted_p1_match_prob:.1%}, P2: {adjusted_p2_match_prob:.1%}")
            print(f"   Change: {match_prob_adjustment:+.1%} to predicted winner")
            
            # Use adjusted probabilities
            final_player1_match_prob = adjusted_p1_match_prob
            final_player2_match_prob = adjusted_p2_match_prob
        
        # Calculate each player's probability of winning at least 1 set using MENTAL-ADJUSTED probabilities
        player1_set_prob = self._calculate_set_probability(final_player1_match_prob, is_best_of_five)
        player2_set_prob = self._calculate_set_probability(final_player2_match_prob, is_best_of_five)
        
        # CRITICAL VALIDATION: These probabilities should both be reasonable for +1.5 sets betting
        # Ensure minimum realistic probabilities (even heavy underdogs can win sets)
        player1_set_prob = max(0.25, player1_set_prob)
        player2_set_prob = max(0.25, player2_set_prob)
        
        # Cap maximum probabilities to prevent overconfidence - 73% ULTIMATE PROTECTION
        # Based on validation analysis: 80%+ predictions often result in straight-set losses
        player1_set_prob = min(0.73, player1_set_prob)
        player2_set_prob = min(0.73, player2_set_prob)
        
        # Final validation and logging
        total_set_prob = player1_set_prob + player2_set_prob
        print(f"✅ FINAL CORRECTED SET PROBABILITIES:")
        print(f"   {player1.name}: {player1_set_prob:.1%} chance to win ≥1 set")
        print(f"   {player2.name}: {player2_set_prob:.1%} chance to win ≥1 set")
        print(f"   Total probability: {total_set_prob:.1%} (both can win sets in same match)")
        
        # Calculate Over 2.5 Sets probability (with H2H and event context)
        over_2_5_sets_prob = self._calculate_over_2_5_sets_probability(
            player1_set_prob, player2_set_prob, player1, player2, surface, match_format, event_id
        )
        print(f"\n📊 OVER 2.5 SETS PROBABILITY:")
        print(f"   Match likely to go to 3 sets: {over_2_5_sets_prob:.1%}")
        if over_2_5_sets_prob > 0.60:
            print(f"   ✅ HIGH PROBABILITY: Competitive match with both players likely to win sets")
        elif over_2_5_sets_prob > 0.45:
            print(f"   ⚖️ MODERATE PROBABILITY: Match could go either way")
        else:
            print(f"   📉 LOW PROBABILITY: Likely to finish in 2 sets")
        
        # Calculate Total Games prediction
        total_games_data = self._calculate_total_games_prediction(
            player1, player2, over_2_5_sets_prob, player1_set_prob, player2_set_prob, surface, match_format
        )
        print(f"\n🎯 TOTAL GAMES PREDICTION:")
        print(f"   Expected Total: {total_games_data['expected_total_games']} games")
        print(f"   Over 20.5: {total_games_data['over_20_5_prob']:.1%}")
        print(f"   Over 21.5: {total_games_data['over_21_5_prob']:.1%}")
        print(f"   Over 22.5: {total_games_data['over_22_5_prob']:.1%}")
        print(f"   Over 23.5: {total_games_data['over_23_5_prob']:.1%}")
        print(f"   💡 Serve Strength: {total_games_data['serve_strength']:.1%}, Tiebreak Likelihood: {total_games_data['tiebreak_likelihood']:.1%}")
        
        if player1_set_prob > 0.70 or player2_set_prob > 0.70:
            print(f"⚠️  HIGH SET PROBABILITY WARNING:")
            print(f"   Approaching 73% confidence cap - prediction based on strong supporting factors")
        
        # Mental toughness analysis already performed above before set probability calculation
        
        # LOG MENTAL TOUGHNESS DATA FOR BOTH PLAYERS
        try:
            self.mental_logger.log_match_mental_analysis(
                event_id=event_id,
                tournament_name=tournament_name,
                player1_name=player1.name,
                player1_id=player1.id,
                player2_name=player2.name, 
                player2_id=player2.id,
                predicted_winner=predicted_winner,
                player1_mental_data=player1_mental,
                player2_mental_data=player2_mental,
                final_adjustment=mental_toughness_adjustment
            )
        except Exception as log_error:
            print(f"⚠️ Mental toughness logging failed: {log_error}")
        
        # Apply mental toughness adjustment to final confidence (analysis already done above)
        if mental_toughness_adjustment['apply_adjustment']:
            original_confidence = final_confidence
            adjusted_numeric = mental_toughness_adjustment['adjusted_confidence']
            
            # Convert back to confidence level
            if adjusted_numeric <= 0.35:
                final_confidence = "Low"
            elif adjusted_numeric <= 0.65:
                final_confidence = "Medium"  
            else:
                final_confidence = "High"
            
            print(f"\n🧠 MENTAL TOUGHNESS CONFIDENCE ADJUSTMENT:")
            print(f"   Analysis: {mental_toughness_adjustment['analysis']}")
            print(f"   Confidence: {original_confidence} → {final_confidence}")
            print(f"   Adjustment: {mental_toughness_adjustment['confidence_adjustment']:+.0%}")
            
        # Display both players' mental toughness summary with differential
        print(f"\n🧠 MENTAL TOUGHNESS DIFFERENTIAL ANALYSIS:")
        print(f"   {player1.name}: {player1_mental['category']} ({player1_mental['tiebreak_rate']} tiebreak rate)")
        print(f"   {player2.name}: {player2_mental['category']} ({player2_mental['tiebreak_rate']} tiebreak rate)")
        
        mental_advantage = mental_toughness_adjustment.get('mental_advantage', 'Unknown')
        differential = mental_toughness_adjustment.get('differential', 0.0)
        
        if mental_advantage == "Equal":
            print(f"   🟡 Mental Edge: Equal mental toughness")
        elif mental_advantage != 'Unknown':
            print(f"   🎯 Mental Edge: {mental_advantage} (+{differential:.1%} advantage)")
            
            # Show strategic implications
            if mental_advantage != predicted_winner:
                print(f"   ⚠️  CONTRARIAN SIGNAL: Predicted winner has weaker mental game")
                print(f"   💡 Consider: {mental_advantage} may perform better in tight sets")
        
        # CRITICAL SAFEGUARD: Ensure predicted_winner ALWAYS aligns with set probabilities
        # This prevents data contradictions like the Bernabe/Trey bug
        set_probability_winner = player1.name if player1_set_prob > player2_set_prob else player2.name
        if predicted_winner != set_probability_winner:
            print(f"   🚨 PREDICTED WINNER MISMATCH DETECTED!")
            print(f"   🔄 Correcting: {predicted_winner} → {set_probability_winner}")
            print(f"   📊 Set probabilities: {player1.name}={player1_set_prob:.1%}, {player2.name}={player2_set_prob:.1%}")
            predicted_winner = set_probability_winner  # Fix the contradiction
        
        # ENHANCED FORM SCORE VALIDATION - Prevent illogical predictions like Noah Schachter bug
        form_gap = abs(player1.recent_form_score - player2.recent_form_score)
        if form_gap > 30:  # Huge form difference (e.g., 48.9 vs 13.4)
            better_form_player = player1.name if player1.recent_form_score > player2.recent_form_score else player2.name
            worse_form_player = player2.name if player1.recent_form_score > player2.recent_form_score else player1.name
            better_form_score = max(player1.recent_form_score, player2.recent_form_score)
            worse_form_score = min(player1.recent_form_score, player2.recent_form_score)
            
            # If predicted winner has MUCH worse form, flag it
            if predicted_winner == worse_form_player:
                print(f"\n   ⚠️  FORM CONTRADICTION DETECTED!")
                print(f"   🎯 Predicted Winner: {predicted_winner} (Form: {worse_form_score:.1f})")
                print(f"   🔥 Better Form Player: {better_form_player} (Form: {better_form_score:.1f})")
                print(f"   📊 Form Gap: {form_gap:.1f} points - This is a HUGE difference!")
                
                # Check if ALL other key stats also favor the better form player
                stats_favoring_better_form = 0
                total_comparable_stats = 0
                
                if player1.atp_ranking and player2.atp_ranking:
                    total_comparable_stats += 1
                    if (better_form_player == player1.name and player1.atp_ranking < player2.atp_ranking) or \
                       (better_form_player == player2.name and player2.atp_ranking < player1.atp_ranking):
                        stats_favoring_better_form += 1
                
                if player1.utr_rating and player2.utr_rating:
                    total_comparable_stats += 1
                    if (better_form_player == player1.name and player1.utr_rating > player2.utr_rating) or \
                       (better_form_player == player2.name and player2.utr_rating > player1.utr_rating):
                        stats_favoring_better_form += 1
                
                # Surface win rate
                if player1.surface_win_rate and player2.surface_win_rate:
                    total_comparable_stats += 1
                    if (better_form_player == player1.name and player1.surface_win_rate > player2.surface_win_rate) or \
                       (better_form_player == player2.name and player2.surface_win_rate > player1.surface_win_rate):
                        stats_favoring_better_form += 1
                
                # If most stats favor the better form player, consider correcting
                if total_comparable_stats > 0 and stats_favoring_better_form / total_comparable_stats >= 0.67:
                    print(f"   🚨 CRITICAL: {stats_favoring_better_form}/{total_comparable_stats} key stats favor {better_form_player}")
                    print(f"   🔄 CORRECTING PREDICTION: {predicted_winner} → {better_form_player}")
                    predicted_winner = better_form_player
                    # Also correct win probability
                    win_probability = max(win_probability, 0.55)  # At least slight edge
                else:
                    print(f"   ⚠️  WARNING: Possible upset or model confusion - validate this prediction!")
        
        # Log key factors and prediction result
        if self.prediction_logger:
            self.prediction_logger.log_key_factors(key_factors)
            self.prediction_logger.log_prediction_result(predicted_winner, win_probability, final_confidence, reasoning)
        
        return SetPrediction(
            predicted_winner=predicted_winner,
            confidence_level=final_confidence,
            predicted_score=predicted_score,
            win_probability=win_probability,
            key_factors=key_factors,
            weight_breakdown=weight_breakdown,
            reasoning=reasoning,
            player1_probability=player1_set_prob,  # Actual set probabilities
            player2_probability=player2_set_prob,
            over_2_5_sets_probability=over_2_5_sets_prob,  # Probability match goes over 2.5 sets
            expected_total_games=total_games_data['expected_total_games'],
            over_20_5_games_prob=total_games_data['over_20_5_prob'],
            over_21_5_games_prob=total_games_data['over_21_5_prob'],
            over_22_5_games_prob=total_games_data['over_22_5_prob'],
            over_23_5_games_prob=total_games_data['over_23_5_prob'],
            betting_type="SETS",  # Default to sets betting
            game_handicap_recommendation=None,
            alternative_markets=[],
            market_selection_reason="Standard set betting",
            should_skip=skip_match,
            skip_reason=skip_reason
        )
    
    def _generate_recommended_bet_text(self, prediction: SetPrediction, player1_name: str, player2_name: str) -> str:
        """Generate recommended bet text that matches the reasoning logic"""
        if prediction.betting_type == 'GAMES' and prediction.game_handicap_recommendation:
            # Use game handicap recommendation
            recommended_player = prediction.game_handicap_recommendation['recommended_player']
            handicap_value = prediction.game_handicap_recommendation['handicap_value']
            return f"{recommended_player} {handicap_value}"
        else:
            # Use set betting logic - bet on player with higher set probability
            if prediction.player1_probability > prediction.player2_probability:
                return f"{player1_name} +1.5 sets"
            else:
                return f"{player2_name} +1.5 sets"

    def _analyze_optimal_betting_strategy(self, player1: PlayerProfile, player2: PlayerProfile, 
                                        p1_utr: float, p2_utr: float, p1_set_prob: float, p2_set_prob: float) -> Dict[str, Any]:
        """
        SIMPLIFIED: UTR-based betting strategy analysis (UTR already captures performance dimensions)
        
        UTR incorporates: game win %, opponent strength, recent form, surface performance
        No need to double-count what UTR already measures!
        """
        
        print(f"\n🎯 BETTING STRATEGY ANALYSIS:")
        print(f"{'='*60}")
        
        # PRIMARY: UTR-based analysis (UTR = the gold standard)
        if p1_utr and p2_utr:
            utr_gap = abs(p1_utr - p2_utr)
            print(f"   🎾 UTR Analysis: {player1.name} {p1_utr:.2f} vs {player2.name} {p2_utr:.2f}")
            print(f"   📏 UTR Gap: {utr_gap:.2f} points")
            
            # UTR gap thresholds for game handicap consideration (empirically derived)
            utr_threshold = self.config.BETTING_STRATEGY['active_utr_threshold']
            if utr_gap <= utr_threshold:  # Close UTR skill levels
                print(f"   ✅ CLOSE MATCH: UTR gap {utr_gap:.2f} ≤ {utr_threshold} threshold")
                print(f"   💡 UTR accounts for: game win %, opponent strength, recent form, surface adaptation")
                
                # Calculate optimal game handicap
                game_handicap = self._calculate_optimal_game_handicap(
                    player1, player2, p1_set_prob, p2_set_prob, utr_gap
                )
                
                return {
                    'betting_type': 'GAMES',
                    'game_handicap_recommendation': game_handicap,
                    'market_selection_reason': f"UTR indicates close match (gap: {utr_gap:.2f})",
                    'utr_gap': utr_gap,
                    'alternative_markets': [
                        {'type': 'SETS', 'reason': 'Fallback if game handicap unavailable'}
                    ]
                }
            else:
                print(f"   ❌ CLEAR SKILL DIFFERENCE: UTR gap {utr_gap:.2f} > {utr_threshold} threshold")
                
                # CHECK FOR CONFLICTING PREDICTIONS (set performance vs UTR skill)
                utr_favorite = player1 if p1_utr > p2_utr else player2
                set_favorite = player1 if p1_set_prob > p2_set_prob else player2
                
                if utr_favorite.name != set_favorite.name:
                    print(f"   🔀 CONFLICTING PREDICTION DETECTED!")
                    print(f"   🎯 UTR Favorite: {utr_favorite.name} ({max(p1_utr, p2_utr):.2f})")
                    print(f"   📊 Set Favorite: {set_favorite.name} ({max(p1_set_prob, p2_set_prob):.1%})")
                    print(f"   💡 Perfect scenario for GAME HANDICAP betting")
                    
                    # Calculate game handicap for conflicting prediction scenario
                    game_handicap = self._calculate_optimal_game_handicap(
                        player1, player2, p1_set_prob, p2_set_prob, utr_gap
                    )
                    
                    return {
                        'betting_type': 'GAMES',
                        'game_handicap_recommendation': game_handicap,
                        'market_selection_reason': f"Conflicting predictions: UTR favors {utr_favorite.name}, sets favor {set_favorite.name}",
                        'utr_gap': utr_gap,
                        'conflict_type': 'utr_vs_set_performance',
                        'utr_favorite': utr_favorite.name,
                        'set_favorite': set_favorite.name,
                        'alternative_markets': [
                            {'type': 'SETS', 'reason': 'Fallback if game handicap unavailable'}
                        ]
                    }
                
                return {
                    'betting_type': 'SETS',
                    'market_selection_reason': f"Clear skill difference in UTR (gap: {utr_gap:.2f})",
                    'utr_gap': utr_gap,
                    'alternative_markets': [
                        {'type': 'GAMES', 'reason': 'Consider if set odds are poor'}
                    ]
                }
        
        # FALLBACK: ATP/WTA ranking analysis (when UTR unavailable)
        else:
            print(f"   ⚠️ UTR unavailable - using ATP/WTA ranking fallback")
            p1_ranking = getattr(player1, 'atp_ranking', None) or getattr(player1, 'wta_ranking', None)
            p2_ranking = getattr(player2, 'atp_ranking', None) or getattr(player2, 'wta_ranking', None)
            
            if p1_ranking and p2_ranking:
                ranking_gap = abs(p1_ranking - p2_ranking)
                print(f"   🏆 Ranking Analysis: #{p1_ranking} vs #{p2_ranking} (gap: {ranking_gap})")
                
                ranking_threshold = self.config.BETTING_STRATEGY['ranking_close_match_threshold']
                if ranking_gap <= ranking_threshold:  # Close rankings
                    print(f"   ✅ CLOSE RANKINGS: Gap {ranking_gap} ≤ {ranking_threshold} positions")
                    
                    # Simplified game handicap for ranking-based analysis
                    game_handicap = self._calculate_ranking_based_game_handicap(
                        player1, player2, p1_set_prob, p2_set_prob, ranking_gap
                    )
                    
                    return {
                        'betting_type': 'GAMES',
                        'game_handicap_recommendation': game_handicap,
                        'market_selection_reason': f"Close ATP/WTA rankings (gap: {ranking_gap})",
                        'ranking_gap': ranking_gap,
                        'alternative_markets': [
                            {'type': 'SETS', 'reason': 'Fallback if game handicap unavailable'}
                        ]
                    }
                else:
                    print(f"   ❌ CLEAR RANKING DIFFERENCE: Gap {ranking_gap} > {ranking_threshold} positions")
                    return {
                        'betting_type': 'SETS',
                        'market_selection_reason': f"Clear ranking difference (gap: {ranking_gap})",
                        'ranking_gap': ranking_gap,
                        'alternative_markets': [
                            {'type': 'GAMES', 'reason': 'Consider if set odds are poor'}
                        ]
                    }
            else:
                print(f"   ❌ No ranking data available - defaulting to set betting")
                return {
                    'betting_type': 'SETS',
                    'market_selection_reason': 'No UTR or ranking data for close match detection',
                    'alternative_markets': [
                        {'type': 'GAMES', 'reason': 'Manual override if match appears close'}
                    ]
                }
    
    def _calculate_optimal_game_handicap(self, player1: PlayerProfile, player2: PlayerProfile, 
                                       p1_set_prob: float, p2_set_prob: float, utr_gap: float) -> Dict[str, Any]:
        """Calculate optimal game handicap based on UTR gap and set probabilities"""
        
        # Determine slight favorite based on set probabilities
        if p1_set_prob > p2_set_prob:
            favorite = player1.name
            favorite_prob = p1_set_prob
            underdog = player2.name
            prob_gap = p1_set_prob - p2_set_prob
        else:
            favorite = player2.name
            favorite_prob = p2_set_prob
            underdog = player1.name
            prob_gap = p2_set_prob - p1_set_prob
        
        # Calculate handicap based on UTR gap (simpler, more accurate)
        if utr_gap <= 0.2:  # Very close UTR
            handicap_value = "+2.5 games"
            confidence = "Medium"
        elif utr_gap <= 0.3:  # Close UTR
            handicap_value = "+3.5 games"
            confidence = "Medium"
        else:  # Moderate UTR gap (≤0.4)
            handicap_value = "+4.5 games"
            confidence = "Low-Medium"
        
        print(f"\n🎮 UTR-BASED GAME HANDICAP:")
        print(f"   Favorite: {favorite} ({favorite_prob:.1%} set probability)")
        print(f"   Recommended bet: {underdog} {handicap_value}")
        print(f"   Confidence: {confidence}")
        print(f"   Logic: UTR gap {utr_gap:.2f} + {prob_gap:.1%} probability difference")
        
        return {
            'recommended_player': underdog,
            'handicap_value': handicap_value,
            'confidence': confidence,
            'favorite': favorite,
            'probability_gap': prob_gap,
            'utr_gap': utr_gap,
            'reasoning': f"Close UTR match (gap: {utr_gap:.2f}) with slight edge to {favorite}"
        }
    
    def _calculate_ranking_based_game_handicap(self, player1: PlayerProfile, player2: PlayerProfile, 
                                             p1_set_prob: float, p2_set_prob: float, ranking_gap: int) -> Dict[str, Any]:
        """Calculate game handicap based on ATP/WTA ranking gap (fallback when UTR unavailable)"""
        
        # Determine favorite based on set probabilities
        if p1_set_prob > p2_set_prob:
            favorite = player1.name
            favorite_prob = p1_set_prob
            underdog = player2.name
            prob_gap = p1_set_prob - p2_set_prob
        else:
            favorite = player2.name
            favorite_prob = p2_set_prob
            underdog = player1.name
            prob_gap = p2_set_prob - p1_set_prob
        
        # Calculate handicap based on ranking gap (less precise than UTR)
        if ranking_gap <= 5:  # Very close rankings
            handicap_value = "+3.5 games"
            confidence = "Low-Medium"
        elif ranking_gap <= 10:  # Close rankings
            handicap_value = "+4.5 games"
            confidence = "Low-Medium"
        else:  # Moderate ranking gap (≤threshold)
            handicap_value = "+5.5 games"
            confidence = "Low"
        
        print(f"\n🎮 RANKING-BASED GAME HANDICAP:")
        print(f"   Favorite: {favorite} ({favorite_prob:.1%} set probability)")
        print(f"   Recommended bet: {underdog} {handicap_value}")
        print(f"   Confidence: {confidence}")
        print(f"   Logic: Ranking gap {ranking_gap} + {prob_gap:.1%} probability difference")
        print(f"   ⚠️ Note: Less accurate than UTR-based analysis")
        
        return {
            'recommended_player': underdog,
            'handicap_value': handicap_value,
            'confidence': confidence,
            'favorite': favorite,
            'probability_gap': prob_gap,
            'ranking_gap': ranking_gap,
            'reasoning': f"Close ranking match (gap: {ranking_gap}) with slight edge to {favorite}"
        }
    
    def _apply_calibrated_confidence_penalties(self, utr_gap: float, p1_ranking: int, p2_ranking: int, 
                                             surface: str, tournament_name: str, current_confidence: str,
                                             player1: PlayerProfile = None, player2: PlayerProfile = None,
                                             p1_surface_perf: float = None, p2_surface_perf: float = None) -> Dict[str, Any]:
        """
        Apply enhanced confidence penalties based on loss analysis insights.
        
        Enhanced to address specific patterns from Cobolli/Tien and Kasintseva/Lepchenko losses:
        - Surface performance vs ranking contradictions
        - Age/experience factor mismatches  
        - Performance metric conflicts
        """
        try:
            config_manager_import = __import__('weight_config_manager', fromlist=['config_manager'])
            current_config = config_manager_import.config_manager.get_active_config()
            
            # Apply if confidence penalties are enabled (works for any config now)
            if not current_config.get('features', {}).get('confidence_penalties', False):
                return {'applied': False, 'adjusted_confidence': current_confidence, 'reasons': []}
            
            penalties = current_config.get('confidence_penalties', {})
            reasons = []
            confidence_reduction = 0
            
            # 1. Close UTR gap penalty (overconfidence in close matches)
            close_utr = penalties.get('close_utr_gap', {})
            if utr_gap and utr_gap < close_utr.get('threshold', 0.5):
                penalty = close_utr.get('penalty', -8)
                confidence_reduction += abs(penalty)
                reasons.append(f"Close UTR gap ({utr_gap:.2f} < {close_utr.get('threshold', 0.5)}) → {penalty}% confidence")
            
            # 2. Lower-tier tournament penalties (based on rankings)
            lower_tier = penalties.get('lower_tier_tournament', {})
            max_ranking = max([r for r in [p1_ranking, p2_ranking] if r is not None], default=0)
            
            if max_ranking > 400:
                penalty = lower_tier.get('ranking_over_400', -10)
                confidence_reduction += abs(penalty)
                reasons.append(f"Player ranked >{400} (#{max_ranking}) → {penalty}% confidence")
            elif max_ranking > 200:
                penalty = lower_tier.get('ranking_over_200', -5)
                confidence_reduction += abs(penalty)
                reasons.append(f"Player ranked >{200} (#{max_ranking}) → {penalty}% confidence")
            
            # Check for ITF/Challenger tournaments
            if tournament_name and tournament_name != "Unknown" and any(keyword in tournament_name.lower() for keyword in ['itf', 'challenger']):
                penalty = lower_tier.get('itf_challenger', -5)
                confidence_reduction += abs(penalty)
                reasons.append(f"ITF/Challenger tournament → {penalty}% confidence")
            
            # 3. Surface-specific penalties
            surface_penalties = penalties.get('surface_specific', {})
            if surface:
                surface_lower = surface.lower()
                if 'clay' in surface_lower:
                    penalty = surface_penalties.get('clay_court', -5)
                    confidence_reduction += abs(penalty)
                    reasons.append(f"Clay court surface → {penalty}% confidence")
                elif ('hard' in surface_lower and tournament_name and tournament_name != "Unknown" and 
                      any(region in tournament_name.lower() for region in ['hong kong', 'china', 'asia'])):
                    penalty = surface_penalties.get('hard_court_asia', -3)
                    confidence_reduction += abs(penalty)
                    reasons.append(f"Hard court Asia tournament → {penalty}% confidence")
            
            # 4. NEW: Surface performance contradiction penalty (Cobolli/Tien pattern)
            if (player1 and player2 and p1_surface_perf is not None and p2_surface_perf is not None):
                # Check if predicted winner (based on ranking) has worse surface performance
                p1_better_ranking = (p1_ranking and p2_ranking and p1_ranking < p2_ranking)
                p2_better_ranking = (p1_ranking and p2_ranking and p2_ranking < p1_ranking)
                
                # Surface contradiction: better ranked player has worse surface performance
                if p1_better_ranking and p2_surface_perf > p1_surface_perf + 0.10:  # 10% gap
                    penalty = -12  # Strong penalty for surface contradiction
                    confidence_reduction += abs(penalty)
                    reasons.append(f"Surface contradiction: Better ranked {player1.name} has worse surface performance ({p1_surface_perf:.1%} vs {p2_surface_perf:.1%}) → {penalty}% confidence")
                elif p2_better_ranking and p1_surface_perf > p2_surface_perf + 0.10:
                    penalty = -12
                    confidence_reduction += abs(penalty)
                    reasons.append(f"Surface contradiction: Better ranked {player2.name} has worse surface performance ({p2_surface_perf:.1%} vs {p1_surface_perf:.1%}) → {penalty}% confidence")
            
            # 5. NEW: Age/experience mismatch penalty (Kasintseva/Lepchenko pattern)
            if player1 and player2 and player1.age and player2.age:
                age_gap = abs(player1.age - player2.age)
                if age_gap >= 15:  # Significant age gap
                    # Young player (≤22) vs veteran (≥35) gets penalty
                    young_player = player1 if player1.age <= 22 else (player2 if player2.age <= 22 else None)
                    veteran_player = player1 if player1.age >= 35 else (player2 if player2.age >= 35 else None)
                    
                    if young_player and veteran_player:
                        penalty = -10  # Penalty for youth vs experience
                        confidence_reduction += abs(penalty)
                        reasons.append(f"Experience mismatch: {young_player.name} ({young_player.age}) vs veteran {veteran_player.name} ({veteran_player.age}) → {penalty}% confidence")
            
            # 6. NEW: Multiple contradictory signals penalty
            contradiction_count = 0
            if p1_surface_perf is not None and p2_surface_perf is not None:
                # Count contradictions where better-ranked player has worse performance
                if p1_ranking and p2_ranking:
                    if (p1_ranking < p2_ranking and p1_surface_perf < p2_surface_perf - 0.10):
                        contradiction_count += 1
                    elif (p2_ranking < p1_ranking and p2_surface_perf < p1_surface_perf - 0.10):
                        contradiction_count += 1
            
            # Add form contradiction check if we can access it
            if hasattr(player1, 'recent_form_score') and hasattr(player2, 'recent_form_score'):
                if p1_ranking and p2_ranking:
                    if (p1_ranking < p2_ranking and player1.recent_form_score < player2.recent_form_score - 10):
                        contradiction_count += 1
                    elif (p2_ranking < p1_ranking and player2.recent_form_score < player1.recent_form_score - 10):
                        contradiction_count += 1
            
            if contradiction_count >= 2:
                penalty = -15  # Strong penalty for multiple contradictions
                confidence_reduction += abs(penalty)
                reasons.append(f"Multiple contradictory signals ({contradiction_count}) between ranking and performance → {penalty}% confidence")
            
            # Apply confidence adjustments
            if confidence_reduction > 0:
                # Convert current confidence to numeric for adjustment
                confidence_numeric = {'High': 0.8, 'Medium': 0.5, 'Low': 0.2}.get(current_confidence, 0.5)
                adjusted_numeric = max(0.2, confidence_numeric - (confidence_reduction / 100.0))
                
                # Convert back to categorical
                if adjusted_numeric >= 0.7:
                    adjusted_confidence = 'High'
                elif adjusted_numeric >= 0.4:
                    adjusted_confidence = 'Medium'
                else:
                    adjusted_confidence = 'Low'
                
                return {
                    'applied': True,
                    'adjusted_confidence': adjusted_confidence,
                    'reasons': reasons,
                    'total_reduction': confidence_reduction
                }
            
            return {'applied': False, 'adjusted_confidence': current_confidence, 'reasons': []}
            
        except Exception as e:
            print(f"⚠️ Error applying calibrated confidence penalties: {e}")
            return {'applied': False, 'adjusted_confidence': current_confidence, 'reasons': []}
    
    def analyze_scheduled_matches(self, target_date: str = None, csv_file_path: str = None, append_mode: bool = False) -> List[Dict[str, Any]]:
        """Analyze all scheduled matches for betting with incremental CSV writing"""
        
        if not target_date:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"🎾 Analyzing tennis matches for {target_date}")
        
        # Initialize CSV file variables to prevent "referenced before assignment" errors
        csv_file = None
        config_csv_file = None
        config_csv_writer = None
        config_csv_path = None
        
        # Network failure circuit breaker (thread-safe)
        consecutive_network_failures = 0
        network_failure_threshold = 3  # Stop after 3 consecutive network failures
        network_failure_wait_time = 60  # Wait 60 seconds before retrying
        import threading
        network_failure_lock = threading.Lock()
        network_paused = threading.Event()
        network_paused.set()  # Start in "running" state (not paused)
        
        try:
            # Get scheduled events from MatchDataProvider
            from datetime import date
            event_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            events_response = self.match_data_service.get_scheduled_events(event_date)
            events = events_response.events if hasattr(events_response, 'events') else []
            
            print(f"📊 Found {len(events)} total events")
            
            # STEP 1: Filter to singles matches only (quick filter)
            singles_matches = []
            seen_event_ids = set()  # Track duplicate event IDs
            
            for event in events:
                # Skip duplicate events by ID
                if event.id in seen_event_ids:
                    print(f"⚠️ Duplicate event ID detected: {event.id} - skipping")
                    continue
                seen_event_ids.add(event.id)
                
                # Access Pydantic model attributes directly
                home_team = event.home_team
                away_team = event.away_team
                player1_name = home_team.name if home_team else 'Unknown'
                player2_name = away_team.name if away_team else 'Unknown'
                
                # Skip doubles (check for "/" in names)
                if '/' in player1_name or '/' in player2_name:
                    continue
                
                # Skip matches that are not "not started" (filter to upcoming matches only)
                if not event.status.is_not_started:
                    continue
                
                # Extract tournament and surface information
                tournament_name = 'Unknown'
                surface = 'Unknown'
                
                if hasattr(event, 'tournament') and event.tournament:
                    # Try to get tournament name from multiple sources
                    if hasattr(event.tournament, 'name') and event.tournament.name:
                        tournament_name = event.tournament.name
                    elif hasattr(event.tournament, 'unique_tournament') and event.tournament.unique_tournament:
                        if hasattr(event.tournament.unique_tournament, 'name') and event.tournament.unique_tournament.name:
                            tournament_name = event.tournament.unique_tournament.name
                # For dict access (if event comes as dict instead of object)
                elif isinstance(event, dict) and 'tournament' in event:
                    tournament_dict = event['tournament']
                    if 'name' in tournament_dict:
                        tournament_name = tournament_dict['name']
                    elif 'uniqueTournament' in tournament_dict and 'name' in tournament_dict['uniqueTournament']:
                        tournament_name = tournament_dict['uniqueTournament']['name']
                
                # Get surface/ground type (from actual data structure)
                if hasattr(event, 'ground_type') and event.ground_type:
                    surface = event.ground_type
                elif hasattr(event, 'groundType') and event.groundType:
                    surface = event.groundType
                # For dict access (if event comes as dict instead of object)
                elif isinstance(event, dict):
                    surface = event.get('groundType', event.get('ground_type', 'Unknown'))
                    
                singles_matches.append({
                    'event': event,
                    'player1_name': player1_name,
                    'player2_name': player2_name,
                    'event_id': event.id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'tournament_name': tournament_name,
                    'surface': surface
                })
            
            print(f"🎾 Found {len(singles_matches)} upcoming singles matches (after deduplication)")
            
            # STEP 2: Get OddsProvider matches (fetches ALL, filters client-side by target_date)
            print(f"🔍 Fetching OddsProvider markets for {target_date}...")
            odds_provider_matches_raw = self.bookmaker.get_available_matches(target_date=target_date)
            
            # Deduplicate OddsProvider matches by event_id
            odds_provider_matches = []
            seen_sb_event_ids = set()
            for sb_match in odds_provider_matches_raw:
                if sb_match.event_id in seen_sb_event_ids:
                    print(f"⚠️ Duplicate OddsProvider event ID detected: {sb_match.event_id} - skipping")
                    continue
                seen_sb_event_ids.add(sb_match.event_id)
                odds_provider_matches.append(sb_match)
            
            print(f"📊 Found {len(odds_provider_matches)} matches on OddsProvider (after deduplication)")
            
            # Debug: List all OddsProvider matches
            print("📋 All OddsProvider matches available:")
            for i, sb_match in enumerate(odds_provider_matches, 1):
                print(f"   {i:2d}. {sb_match.player1} vs {sb_match.player2} (ID: {sb_match.event_id})")
            
            if not odds_provider_matches:
                print("⚠️ No matches available on OddsProvider for betting")
                return []
            
            # Summary counters
            total_singles = len(singles_matches)
            matched_on_odds_provider = 0
            with_set_market = 0
            locked_or_missing_market = 0
            insufficient_data_skipped = 0
            
            # STEP 3: Match MatchDataProvider singles with OddsProvider singles (1:1 matching)
            print("🔍 Matching MatchDataProvider events with OddsProvider markets...")
            available_matches = []
            used_odds_provider_matches = set()  # Track used OddsProvider matches to prevent duplicates
            used_match_data_matches = set()  # Track used MatchDataProvider matches to prevent duplicates
            
            for match in singles_matches:
                # Skip if this MatchDataProvider match is already used
                if match['event_id'] in used_match_data_matches:
                    print(f"⚠️ MatchDataProvider match already processed: {match['event_id']} - skipping")
                    continue
                
                # Check if this MatchDataProvider match is available on OddsProvider
                odds_provider_match = None
                for sb_match in odds_provider_matches:
                    # Skip if this OddsProvider match is already used
                    if sb_match.event_id in used_odds_provider_matches:
                        continue
                        
                    # Try to fuzzy match both players (order independent) with relaxed threshold
                    p1_ok = (self.bookmaker.fuzzy_match_player(match['player1_name'], [sb_match.player1, sb_match.player2], threshold=65) is not None)
                    p2_ok = (self.bookmaker.fuzzy_match_player(match['player2_name'], [sb_match.player1, sb_match.player2], threshold=65) is not None)
                    if p1_ok and p2_ok:
                        odds_provider_match = sb_match
                        used_odds_provider_matches.add(sb_match.event_id)
                        break
                
                if not odds_provider_match:
                    print(f"   🚫 Not on OddsProvider: {match['player1_name']} vs {match['player2_name']}")
                    continue
                
                # Mark this MatchDataProvider match as used
                used_match_data_matches.add(match['event_id'])
                matched_on_odds_provider += 1
                
                # Check for injured/retired players before analyzing
                p1_injured = self.injury_checker.is_player_injured(match['player1_name'])
                p2_injured = self.injury_checker.is_player_injured(match['player2_name'])
                
                if p1_injured or p2_injured:
                    injured_player = match['player1_name'] if p1_injured else match['player2_name']
                    injury_info = self.injury_checker.get_injury_info(injured_player)
                    reason = injury_info.get('reason', 'injured/retired') if injury_info else 'injured/retired'
                    date = injury_info.get('date', 'recently') if injury_info else 'recently'
                    
                    skip_reason = f"Player recently {reason} ({date})"
                    self.skip_logger.log_skip(
                        reason_type="INJURY/RETIREMENT",
                        player1_name=match['player1_name'],
                        player2_name=match['player2_name'],
                        tournament=match['tournament_name'],
                        surface=match.get('surface', 'Unknown'),
                        reason=skip_reason
                    )
                    print(f"   🚑 SKIPPED (Injury): {match['player1_name']} vs {match['player2_name']} - {injured_player} {reason} on {date}")
                    continue
                
                # Check if +1.5 set market present (odds filled during OddsProvider fetch)
                if odds_provider_match.odds_player1_1_5 == 0.0 or odds_provider_match.odds_player2_1_5 == 0.0:
                    locked_or_missing_market += 1
                    print(f"   🔒 Market locked / absent: {match['player1_name']} vs {match['player2_name']}")
                    continue
                
                with_set_market += 1
                available_matches.append({'match_data_match': match, 'odds_provider_match': odds_provider_match})
                print(f"   ✅ Matched: {match['player1_name']} vs {match['player2_name']} → {odds_provider_match.player1} vs {odds_provider_match.player2}")
            
            print(f"💰 Found {with_set_market} real tennis matches with active +1.5 markets")
            print("📊 DAY SUMMARY " + target_date)
            print(f"    MatchDataProvider singles       : {total_singles}")
            print(f"    Matched on OddsProvider    : {matched_on_odds_provider}")
            print(f"       ↳ real tennis +1.5    : {with_set_market}")
            print(f"       ↳ locked / missing    : {locked_or_missing_market}")
            print(f"       ↳ insufficient data   : {insufficient_data_skipped}")
            print(f"    📄 SRL virtual matches filtered at source")
            
            if not available_matches:
                print("⚠️ No matching pairs found between MatchDataProvider and OddsProvider")
                return []
            
            # STEP 4: Initialize CSV for incremental writing
            csv_writer = None
            csv_fieldnames = None
            
            if csv_file_path:
                try:
                    # Prepare CSV headers
                    csv_fieldnames = [
                        'date', 'time', 'event_id', 'tournament', 'surface',
                        'player1_id', 'player1_name', 'player1_age', 'player1_gender', 'player1_country', 'player1_ranking', 'player1_utr_rating', 'player1_form_score',
                        'player2_id', 'player2_name', 'player2_age', 'player2_gender', 'player2_country', 'player2_ranking', 'player2_utr_rating', 'player2_form_score',
                        'predicted_winner', 'predicted_score', 'confidence', 'win_probability',
                        'player1_set_probability', 'player2_set_probability', 'over_2_5_sets_probability',  # Set probabilities
                        'expected_total_games',  # Our total games prediction
                        'bookmaker_total_games_lines',  # JSON string of all bookmaker Total Games lines (dynamic)
                        'recommended_total_games_line', 'recommended_total_games_bet', 'recommended_total_games_odds', 'total_games_edge',  # Best Total Games bet
                        'recommended_bet', 'key_factors', 'reasoning', 'weight_breakdown',
                        'odds_provider_event_id', 'player1_odds_1_5', 'player2_odds_1_5', 'player1_odds_2_5', 'player2_odds_2_5', 'matched_player1', 'matched_player2'
                    ]
                    
                    # Open CSV file for writing (append mode for subsequent dates)
                    file_mode = 'a' if append_mode else 'w'
                    csv_file = open(csv_file_path, file_mode, newline='', encoding='utf-8')
                    csv_writer = csv.DictWriter(csv_file, fieldnames=csv_fieldnames)
                    
                    # Only write header if creating new file
                    if not append_mode:
                        csv_writer.writeheader()
                        print(f"📄 CSV initialized: {csv_file_path}")
                    else:
                        print(f"📄 Appending to CSV: {csv_file_path}")
                    
                    # ✅ ALSO WRITE TO CONFIG-SPECIFIC CSV FILE
                    config_csv_file = None
                    config_csv_writer = None
                    try:
                        from weight_config_manager import config_manager
                        from prediction_config import PredictionConfig
                        
                        active_config_name = config_manager.get_active_code_name()
                        
                        # Check if 3-year mode is enabled and append suffix
                        pred_config = PredictionConfig()
                        year_suffix = ""
                        if pred_config.MULTI_YEAR_STATS.get('enable_three_year_stats', False):
                            year_suffix = "_3YEAR"
                        
                        config_csv_path = f"all_{active_config_name}{year_suffix}.csv"
                        
                        # Check if config file exists to determine append mode
                        import os
                        config_file_exists = os.path.exists(config_csv_path)
                        config_file_mode = 'a' if config_file_exists else 'w'
                        
                        config_csv_file = open(config_csv_path, config_file_mode, newline='', encoding='utf-8')
                        config_csv_writer = csv.DictWriter(config_csv_file, fieldnames=csv_fieldnames)
                        
                        # Only write header if creating new file
                        if not config_file_exists:
                            config_csv_writer.writeheader()
                            print(f"📄 Config CSV created: {config_csv_path}")
                        else:
                            print(f"📄 Appending to config CSV: {config_csv_path}")
                    except Exception as e:
                        print(f"⚠️ Warning: Could not initialize config-specific CSV: {e}")
                        config_csv_writer = None
                        
                except Exception as e:
                    print(f"❌ Error initializing CSV: {e}")
                    csv_writer = None
                    config_csv_writer = None
            
            # STEP 5: Now do expensive analysis only on matched pairs (CONCURRENT PROCESSING)
            analysis_results = []
            analyzed_count = 0
            analysis_insufficient_data_skipped = 0
            
            # Process matches concurrently (like Go goroutines)
            max_concurrent_matches = 4  # Process 4 matches simultaneously
            print(f"🚀 Processing {len(available_matches)} matches concurrently (max {max_concurrent_matches} at once)...")
            
            def analyze_single_match(match_pair):
                """Analyze a single match - this function runs in its own thread"""
                nonlocal consecutive_network_failures  # Allow modification of outer variable
                
                # Wait if network is paused (circuit breaker active)
                if not network_paused.is_set():
                    import threading
                    thread_id = threading.current_thread().ident % 1000
                    print(f"[Thread-{thread_id}] ⏸️  Waiting for network recovery...")
                    network_paused.wait()  # Block until network is available again
                    print(f"[Thread-{thread_id}] ✅ Network recovered, resuming...")
                
                try:
                    # Extract MatchDataProvider and OddsProvider data
                    match_data_match = match_pair['match_data_match']
                    odds_provider_match = match_pair['odds_provider_match']
                    
                    event = match_data_match['event']
                    player1_name = match_data_match['player1_name']
                    player2_name = match_data_match['player2_name']
                    
                    # Create unique match ID for thread-safe logging
                    match_id = f"{player1_name}_{player2_name}_{match_data_match['event_id']}"
                    
                    # Start thread-safe logging for this match
                    if self.prediction_logger:
                        self.prediction_logger.start_match_logging(match_id)
                    
                    # Use thread-safe logging to avoid interleaved output
                    import threading
                    thread_id = threading.current_thread().ident % 1000
                    
                    print(f"\n{'='*90}")
                    print(f"[Thread-{thread_id}] 🎾 ANALYZING MATCH: {player1_name} vs {player2_name}")
                    print(f"{'='*90}")
                    print(f"[Thread-{thread_id}] 📊 OddsProvider Match: {odds_provider_match.player1} vs {odds_provider_match.player2}")
                    print(f"[Thread-{thread_id}] 💰 OddsProvider Odds (+1.5): {odds_provider_match.odds_player1_1_5} / {odds_provider_match.odds_player2_1_5}")
                    if odds_provider_match.odds_player1_2_5 and odds_provider_match.odds_player2_2_5:
                        print(f"[Thread-{thread_id}] 💰 OddsProvider Odds (+2.5): {odds_provider_match.odds_player1_2_5} / {odds_provider_match.odds_player2_2_5}")
                    print(f"[Thread-{thread_id}] 🆔 OddsProvider Event ID: {odds_provider_match.event_id}")
                    print(f"[Thread-{thread_id}] 🏆 Tournament: {match_data_match.get('tournament_name', 'Unknown')}")
                    print(f"[Thread-{thread_id}] 🎯 Surface: {match_data_match.get('surface', 'Unknown')}")
                    print(f"[Thread-{thread_id}] 📅 Date: {target_date}")
                    print(f"{'='*90}")
                    
                    # Get match details
                    tournament = event.tournament.unique_tournament if event.tournament and hasattr(event.tournament, 'unique_tournament') else None
                    
                    # Get surface from multiple sources (priority order)
                    surface = None
                    
                    # 1. Try from processed match_data_match data
                    if match_data_match.get('surface'):
                        surface = match_data_match.get('surface')
                    
                    # 2. Try from event ground_type field
                    elif hasattr(event, 'ground_type') and event.ground_type:
                        surface = event.ground_type
                    elif hasattr(event, 'groundType') and event.groundType:
                        surface = event.groundType
                    
                    # 3. Try from tournament unique_tournament groundType
                    elif tournament and hasattr(tournament, 'ground_type') and tournament.ground_type:
                        surface = tournament.ground_type
                    elif tournament and hasattr(tournament, 'groundType') and tournament.groundType:
                        surface = tournament.groundType
                    
                    # 4. Fallback to Unknown (no hardcoded surface)
                    if not surface:
                        surface = 'Unknown'
                    
                    # Log match analysis start (thread-safe)
                    if self.prediction_logger:
                        tournament_name = tournament.name if tournament else 'Unknown'
                        self.prediction_logger.log_match_message("")
                        self.prediction_logger.log_match_message("🎾 " + "=" * 70)
                        self.prediction_logger.log_match_message(f"MATCH ANALYSIS: {player1_name} vs {player2_name}")
                        self.prediction_logger.log_match_message("🎾 " + "=" * 70)
                        self.prediction_logger.log_match_message(f"Tournament: {tournament_name}")
                        self.prediction_logger.log_match_message(f"Surface: {surface}")
                        self.prediction_logger.log_match_message(f"Event ID: {match_data_match['event_id']}")
                        self.prediction_logger.log_match_message("")
                    
                    # Get enhanced player profiles with retry logic (no defaults fallback)
                    print(f"[Thread-{thread_id}] 📊 STEP 1: FETCHING PLAYER PROFILES")
                    print(f"[Thread-{thread_id}] {'-'*50}")
                    
                    player1_profile = None
                    player2_profile = None
                    
                    # Try concurrent first, then fallback to sequential with retries
                    try:
                        print(f"[Thread-{thread_id}] 🚀 Fetching profiles concurrently...")
                        print(f"[Thread-{thread_id}]    P1: {player1_name} (ID: {match_data_match['home_team'].id})")
                        print(f"[Thread-{thread_id}]    P2: {player2_name} (ID: {match_data_match['away_team'].id})")
                        
                        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                            future1 = executor.submit(self.get_enhanced_player_profile, match_data_match['home_team'].id, surface=surface)
                            future2 = executor.submit(self.get_enhanced_player_profile, match_data_match['away_team'].id, surface=surface)
                            
                            player1_profile = future1.result(timeout=45)
                            player2_profile = future2.result(timeout=45)
                            
                        print(f"[Thread-{thread_id}] ✅ Concurrent fetch successful!")
                        with network_failure_lock:
                            consecutive_network_failures = 0  # Reset on success
                            
                    except (concurrent.futures.TimeoutError, Exception) as e:
                        print(f"[Thread-{thread_id}]    ⚠️ Concurrent fetch failed ({type(e).__name__}), trying sequential with retries...")
                        
                        # Track last error for network failure detection
                        last_error = None
                        
                        # Sequential retry for player 1
                        for attempt in range(3):
                            try:
                                player1_profile = self.get_enhanced_player_profile(match_data_match['home_team'].id, surface=surface)
                                break
                            except Exception as e:
                                last_error = e
                                if attempt == 2:
                                    print(f"[Thread-{thread_id}]    ❌ Failed to fetch {player1_name} profile after 3 attempts: {e}")
                                    break
                                print(f"[Thread-{thread_id}]    🔄 Retry {attempt + 1}/3 for {player1_name}...")
                                
                        # Sequential retry for player 2
                        for attempt in range(3):
                            try:
                                player2_profile = self.get_enhanced_player_profile(match_data_match['away_team'].id, surface=surface)
                                break
                            except Exception as e:
                                last_error = e
                                if attempt == 2:
                                    print(f"[Thread-{thread_id}]    ❌ Failed to fetch {player2_name} profile after 3 attempts: {e}")
                                    break
                                print(f"[Thread-{thread_id}]    🔄 Retry {attempt + 1}/3 for {player2_name}...")
                    
                    # CRITICAL: Check if we have valid player profiles (no fallbacks allowed)
                    if not player1_profile or not player2_profile:
                        missing_players = []
                        if not player1_profile:
                            missing_players.append(player1_name)
                        if not player2_profile:
                            missing_players.append(player2_name)
                        
                        # Check if this is a network failure (DNS, connection timeout, etc.)
                        # If so, increment the consecutive failure counter
                        error_str = str(last_error) if 'last_error' in locals() and last_error else ""
                        is_network_failure = (
                            'Connection timed out' in error_str or 
                            'curl: (28)' in error_str or
                            'Could not resolve host' in error_str or  # DNS failure
                            'curl: (6)' in error_str or  # DNS resolution error
                            'curl: (7)' in error_str or  # Failed to connect
                            'curl: (35)' in error_str  # SSL/connection error
                        )
                        
                        # Thread-safe network failure handling
                        with network_failure_lock:
                            if is_network_failure:
                                consecutive_network_failures += 1
                                print(f"[Thread-{thread_id}] 🌐 Network failure detected ({consecutive_network_failures}/{network_failure_threshold})")
                                print(f"[Thread-{thread_id}]    Error: {error_str[:100]}")
                                
                                # Check if we've hit the threshold
                                if consecutive_network_failures >= network_failure_threshold:
                                    # PAUSE ALL THREADS
                                    network_paused.clear()  # Signal all threads to pause
                                    
                                    print(f"\n{'='*90}")
                                    print(f"⚠️⚠️⚠️ NETWORK FAILURE CIRCUIT BREAKER TRIGGERED ⚠️⚠️⚠️")
                                    print(f"{'='*90}")
                                    print(f"   🚨 Detected {consecutive_network_failures} consecutive network failures")
                                    print(f"   🌐 Network is likely down - ALL THREADS PAUSED")
                                    print(f"   🔍 Error type: DNS/Connection failure")
                                    print(f"   ⏸️  All other threads are now waiting...")
                                    print(f"")
                                    print(f"   💡 Check your network connection")
                                    print(f"   ⌨️  Press ENTER to continue when ready (Ctrl+C to abort)")
                                    print(f"{'='*90}\n")
                                    
                                    # INTERACTIVE: Wait for user to press ENTER
                                    try:
                                        input()  # Wait for ENTER key
                                    except (KeyboardInterrupt, EOFError):
                                        print(f"\n❌ User aborted - exiting gracefully")
                                        import sys
                                        sys.exit(0)
                                    
                                    print(f"\n{'='*90}")
                                    print(f"✅ RESUMING PROCESSING (User confirmed)")
                                    print(f"{'='*90}")
                                    print(f"   🔄 Attempting to continue...")
                                    print(f"   🚀 All threads will resume processing")
                                    print(f"{'='*90}\n")
                                    
                                    consecutive_network_failures = 0  # Reset after user confirmation
                                    network_paused.set()  # Resume all threads
                                    
                                    # RETRY this match after network recovery
                                    print(f"[Thread-{thread_id}] 🔄 RETRYING MATCH AFTER NETWORK RECOVERY: {player1_name} vs {player2_name}")
                                    try:
                                        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                                            future1 = executor.submit(self.get_enhanced_player_profile, match_data_match['home_team'].id, surface=surface)
                                            future2 = executor.submit(self.get_enhanced_player_profile, match_data_match['away_team'].id, surface=surface)
                                            
                                            player1_profile = future1.result(timeout=45)
                                            player2_profile = future2.result(timeout=45)
                                            
                                        print(f"[Thread-{thread_id}] ✅ Retry successful after network recovery!")
                                        # If successful, clear missing_players so we can continue
                                        missing_players = []
                                    except Exception as e:
                                        print(f"[Thread-{thread_id}] ❌ Retry failed after network recovery: {e}")
                                        # Keep missing_players list, will skip below
                            else:
                                # Not a network failure, reset counter
                                consecutive_network_failures = 0
                        
                        # Only skip if we still don't have profiles (either non-network failure or retry failed)
                        if not player1_profile or not player2_profile:
                            print(f"[Thread-{thread_id}] ❌ SKIPPING MATCH: {player1_name} vs {player2_name}")
                            print(f"[Thread-{thread_id}]    Reason: Unable to fetch real data for: {', '.join(missing_players)}")
                            print(f"[Thread-{thread_id}]    🚫 NO FALLBACK PROFILES - Cannot make reliable predictions")
                            return None  # Skip this match completely
                    
                    # ADDITIONAL: Check data quality issues in the profiles we did get
                    should_skip, skip_reason = self.should_skip_match_due_to_data_quality(player1_profile, player2_profile)
                    if should_skip:
                        print(f"[Thread-{thread_id}] ❌ SKIPPING MATCH: {player1_name} vs {player2_name}")
                        print(f"[Thread-{thread_id}]    Reason: {skip_reason}")
                        print(f"[Thread-{thread_id}]    ⚠️ Data quality insufficient for reliable prediction")
                        
                        # Log data quality skip
                        self.skip_logger.log_skip(
                            reason_type="DATA_QUALITY",
                            player1_name=player1_name,
                            player2_name=player2_name,
                            tournament=tournament_name,
                            surface=surface,
                            reason=skip_reason
                        )
                        
                        return None  # Skip this match and return early
                    
                    # CRITICAL: Check current-year performance on this surface
                    # Don't bet on players with poor recent performance (< 40% win rate in current year)
                    current_year = datetime.now().year
                    should_skip_poor_form, poor_form_reason = self.should_skip_due_to_poor_current_year_performance(
                        player1_profile, player2_profile, surface, current_year
                    )
                    if should_skip_poor_form:
                        print(f"[Thread-{thread_id}] ❌ SKIPPING MATCH: {player1_name} vs {player2_name}")
                        print(f"[Thread-{thread_id}]    Reason: {poor_form_reason}")
                        print(f"[Thread-{thread_id}]    ⚠️ Poor {current_year} performance - not bettable")
                        
                        # Log skip with detailed stats
                        self._log_skip_with_stats(
                            poor_form_reason, player1_profile, player2_profile, 
                            tournament_name, surface
                        )
                        
                        return None  # Skip this match
                    
                    # Display player profile summaries
                    if player1_profile and player2_profile:
                        print(f"[Thread-{thread_id}] 📋 PLAYER PROFILE SUMMARY:")
                        print(f"[Thread-{thread_id}] {'-'*50}")
                        
                        # Player 1 profile
                        ranking1 = player1_profile.atp_ranking or player1_profile.wta_ranking or "Unranked"
                        print(f"[Thread-{thread_id}] 🎾 {player1_profile.name}:")
                        print(f"[Thread-{thread_id}]    🏆 Ranking: #{ranking1}")
                        print(f"[Thread-{thread_id}]    🌍 Country: {player1_profile.country}")
                        print(f"[Thread-{thread_id}]    👤 Age: {player1_profile.age or 'Unknown'}")
                        print(f"[Thread-{thread_id}]    🎯 Surface Win Rate: {player1_profile.surface_win_rate:.1%}")
                        print(f"[Thread-{thread_id}]    📈 Recent Form Score: {player1_profile.recent_form_score:.1f}")
                        print(f"[Thread-{thread_id}]    ⚡ Momentum Score: {player1_profile.momentum_score:.2f}")
                        print(f"[Thread-{thread_id}]    🔥 Clutch Performance: {player1_profile.clutch_performance:.1%}")
                        
                        # Player 2 profile  
                        ranking2 = player2_profile.atp_ranking or player2_profile.wta_ranking or "Unranked"
                        print(f"[Thread-{thread_id}] 🎾 {player2_profile.name}:")
                        print(f"[Thread-{thread_id}]    🏆 Ranking: #{ranking2}")
                        print(f"[Thread-{thread_id}]    🌍 Country: {player2_profile.country}")
                        print(f"[Thread-{thread_id}]    👤 Age: {player2_profile.age or 'Unknown'}")
                        print(f"[Thread-{thread_id}]    🎯 Surface Win Rate: {player2_profile.surface_win_rate:.1%}")
                        print(f"[Thread-{thread_id}]    📈 Recent Form Score: {player2_profile.recent_form_score:.1f}")
                        print(f"[Thread-{thread_id}]    ⚡ Momentum Score: {player2_profile.momentum_score:.2f}")
                        print(f"[Thread-{thread_id}]    🔥 Clutch Performance: {player2_profile.clutch_performance:.1%}")
                        print()
                    
                    # Enhanced diagnostics for None profile issues
                    if not player1_profile or not player2_profile:
                        print(f"[Thread-{thread_id}] ❌ SKIPPING MATCH - Player profile data issues")
                        print(f"[Thread-{thread_id}]    Player 1 Profile: {'✅ Valid' if player1_profile else '❌ None/Invalid'}")
                        print(f"[Thread-{thread_id}]    Player 2 Profile: {'✅ Valid' if player2_profile else '❌ None/Invalid'}")
                        
                        # Try to diagnose the issue
                        if not player1_profile:
                            print(f"[Thread-{thread_id}]    P1 Issue: {player1_name} (ID: {match_data_match['home_team'].id})")
                        if not player2_profile:
                            print(f"[Thread-{thread_id}]    P2 Issue: {player2_name} (ID: {match_data_match['away_team'].id})")
                        
                        # Check if this is a gender-specific issue
                        if hasattr(match_data_match['home_team'], 'gender') or hasattr(match_data_match['away_team'], 'gender'):
                            p1_gender = getattr(match_data_match['home_team'], 'gender', 'Unknown')
                            p2_gender = getattr(match_data_match['away_team'], 'gender', 'Unknown')
                            print(f"[Thread-{thread_id}]    Gender info: P1={p1_gender}, P2={p2_gender}")
                        
                        # Log skip reason with more detail
                        skip_reason = f"Profile fetch failed - P1: {'OK' if player1_profile else 'FAIL'}, P2: {'OK' if player2_profile else 'FAIL'}"
                        if self.prediction_logger:
                            self.prediction_logger.log_betting_recommendation(
                                "", 0, False, skip_reason
                            )
                        return None
                        
                    # Update player2 with opponent ranking context if available
                    if player1_profile.atp_ranking:
                        try:
                            player2_profile = self.get_enhanced_player_profile(match_data_match['away_team'].id, player1_profile.atp_ranking, surface)
                        except:
                            pass  # Keep the original profile if context update fails
                    
                    # Log player profiles (thread-safe)
                    if self.prediction_logger:
                        # Convert profiles to dict format for logging
                        p1_dict = {
                            'name': player1_profile.name,
                            'age': player1_profile.age,
                            'country': player1_profile.country,
                            'atp_ranking': player1_profile.atp_ranking,
                            'wta_ranking': player1_profile.wta_ranking,
                            'recent_form_score': player1_profile.recent_form_score,
                            'surface_win_rate': player1_profile.surface_win_rate,
                            'clutch_performance': player1_profile.clutch_performance,
                            'momentum_score': player1_profile.momentum_score,
                            'injury_status': player1_profile.injury_status
                        }
                        p2_dict = {
                            'name': player2_profile.name,
                            'age': player2_profile.age,
                            'country': player2_profile.country,
                            'atp_ranking': player2_profile.atp_ranking,
                            'wta_ranking': player2_profile.wta_ranking,
                            'recent_form_score': player2_profile.recent_form_score,
                            'surface_win_rate': player2_profile.surface_win_rate,
                            'clutch_performance': player2_profile.clutch_performance,
                            'momentum_score': player2_profile.momentum_score,
                            'injury_status': player2_profile.injury_status
                        }
                        
                        # Log player profiles using thread-safe logging
                        self.prediction_logger.log_match_message("👤 PLAYER PROFILES:")
                        self.prediction_logger.log_match_message("-" * 40)
                        
                        for i, (name, profile) in enumerate([(player1_profile.name, p1_dict), (player2_profile.name, p2_dict)], 1):
                            self.prediction_logger.log_match_message(f"Player {i}: {name}")
                            self.prediction_logger.log_match_message(f"  Age: {profile['age']}")
                            self.prediction_logger.log_match_message(f"  Country: {profile['country']}")
                            self.prediction_logger.log_match_message(f"  ATP Ranking: {profile['atp_ranking']}")
                            self.prediction_logger.log_match_message(f"  WTA Ranking: {profile['wta_ranking']}")
                            self.prediction_logger.log_match_message(f"  Recent Form Score: {profile['recent_form_score']:.1f}")
                            self.prediction_logger.log_match_message(f"  Surface Win Rate: {profile['surface_win_rate']:.1%}")
                            self.prediction_logger.log_match_message(f"  Clutch Performance: {profile['clutch_performance']:.1%}")
                            self.prediction_logger.log_match_message(f"  Momentum Score: {profile['momentum_score']:.2f}")
                            self.prediction_logger.log_match_message(f"  Injury Status: {profile['injury_status']}")
                            self.prediction_logger.log_match_message("")
                    
                    match_time = datetime.fromtimestamp(event.start_timestamp)
                    
                    # Detect match format (best-of-3 vs best-of-5) using actual event structure
                    match_format = None
                    try:
                        # Extract tournament information from actual MatchDataProvider structure
                        tournament_name = event.tournament.unique_tournament.name if (event.tournament and hasattr(event.tournament, 'unique_tournament')) else "Unknown"
                        category = event.tournament.category.slug if (event.tournament and hasattr(event.tournament, 'category')) else "unknown"
                        season_name = event.season.name if hasattr(event, 'season') else ""
                        
                        # Extract player genders
                        player1_gender = match_data_match['home_team'].gender if hasattr(match_data_match['home_team'], 'gender') else 'M'
                        player2_gender = match_data_match['away_team'].gender if hasattr(match_data_match['away_team'], 'gender') else 'M'
                        
                        # Create match format detection
                        match_format = self.detect_match_format(tournament_name, category, player1_gender, player2_gender)
                        
                        print(f"[Thread-{thread_id}] 🎾 MATCH FORMAT ANALYSIS:")
                        print(f"[Thread-{thread_id}]    📋 Tournament: {tournament_name}")
                        print(f"[Thread-{thread_id}]    🏆 Level: {match_format.tournament_level}")
                        print(f"[Thread-{thread_id}]    👥 Category: {category.upper()}")
                        print(f"[Thread-{thread_id}]    ⚽ Gender: {match_format.gender}")
                        print(f"[Thread-{thread_id}]    🎯 Format: {'BEST-OF-5' if match_format.is_best_of_five else 'BEST-OF-3'}")
                        if match_format.is_best_of_five:
                            print(f"[Thread-{thread_id}]    ⚠️ GRAND SLAM MEN'S SINGLES: Enhanced +1.5 sets probability!")
                        print()
                        
                    except Exception as e:
                        print(f"[Thread-{thread_id}]    ⚠️ Match format detection failed: {e}")
                        # Use default format (best-of-3)
                        match_format = MatchFormat(
                            is_best_of_five=False,
                            tournament_name="Unknown",
                            category="unknown",
                            tournament_level="Other", 
                            gender="Unknown"
                        )
                    
                    # Calculate prediction with detailed debug output
                    print(f"[Thread-{thread_id}] 📊 STEP 2: CALCULATING SET PREDICTION")
                    print(f"[Thread-{thread_id}] {'-'*50}")
                    
                    prediction = self.calculate_weighted_prediction(player1_profile, player2_profile, surface, match_data_match['event_id'], match_format)
                    
                    # Display prediction results
                    print(f"[Thread-{thread_id}] 🎯 FINAL PREDICTION RESULTS:")
                    print(f"[Thread-{thread_id}] {'-'*50}")
                    print(f"[Thread-{thread_id}] 🏆 Predicted Winner: {prediction.predicted_winner}")
                    print(f"[Thread-{thread_id}] 📈 Win Probability: {prediction.win_probability:.1%}")
                    print(f"[Thread-{thread_id}] ⭐ Confidence: {prediction.confidence_level}")
                    print(f"[Thread-{thread_id}] 🎾 Predicted Score: {prediction.predicted_score}")
                    print(f"[Thread-{thread_id}] 💡 Key Factors: {', '.join(prediction.key_factors[:3])}")
                    print(f"[Thread-{thread_id}] 📝 Reasoning: {prediction.reasoning[:100]}...")
                    print()
                    
                    # NEW: CHECK SKIP SIGNAL - Skip match if coin flip or conflicting signals detected
                    if prediction.should_skip:
                        print(f"[Thread-{thread_id}] 🚫 SKIPPING MATCH:")
                        print(f"[Thread-{thread_id}]    Reason: {prediction.skip_reason}")
                        print()
                        
                        # Log the skip
                        self.skip_logger.log_skip(
                            reason_type="LOSS_ANALYSIS_FILTER",
                            player1_name=player1_name,
                            player2_name=player2_name,
                            tournament=tournament.name if tournament else 'Unknown',
                            surface=surface,
                            reason=prediction.skip_reason,
                            player1_stats={'form': player1_profile.recent_form_score, 'utr': player1_profile.utr_rating},
                            player2_stats={'form': player2_profile.recent_form_score, 'utr': player2_profile.utr_rating}
                        )
                        
                        # Don't add to results - return None to skip this match
                        return None
                    
                    # Compile results with odds information
                    result = {
                        'date': target_date,
                        'time': match_time.strftime('%H:%M'),
                        'event_id': match_data_match['event_id'],
                        'tournament': tournament.name if tournament else 'Unknown',
                        'surface': surface,
                        'player1_id': match_data_match['home_team'].id,
                        'player1_name': player1_name,
                        'player1_age': player1_profile.age,
                        'player1_gender': self._convert_gender(player1_profile.gender),
                        'player1_country': player1_profile.country,
                        'player1_ranking': player1_profile.atp_ranking or player1_profile.wta_ranking,
                        'player1_utr_rating': player1_profile.utr_rating,
                        'player1_form_score': player1_profile.recent_form_score,
                        'player2_id': match_data_match['away_team'].id,
                        'player2_name': player2_name,
                        'player2_age': player2_profile.age,
                        'player2_gender': self._convert_gender(player2_profile.gender),
                        'player2_country': player2_profile.country,
                        'player2_ranking': player2_profile.atp_ranking or player2_profile.wta_ranking,
                        'player2_utr_rating': player2_profile.utr_rating,
                        'player2_form_score': player2_profile.recent_form_score,
                        'predicted_winner': prediction.predicted_winner,
                        'predicted_score': prediction.predicted_score,
                        'confidence': prediction.confidence_level,
                        'win_probability': prediction.win_probability,
                        'player1_set_probability': prediction.player1_probability,
                        'player2_set_probability': prediction.player2_probability,
                        'over_2_5_sets_probability': prediction.over_2_5_sets_probability,
                        'expected_total_games': prediction.expected_total_games,
                    }
                    
                    # Calculate Total Games edge and recommendation
                    import json
                    bookmaker_lines_json = None
                    total_games_recommendation = {
                        'recommended_line': None,
                        'recommended_bet': None,
                        'recommended_odds': None,
                        'edge': None
                    }
                    
                    if odds_provider_match.total_games_lines:
                        # Store bookmaker lines as JSON
                        bookmaker_lines_json = json.dumps(odds_provider_match.total_games_lines)
                        
                        # Calculate edge and recommendation
                        # Get match_competitiveness from prediction (stored during calculation)
                        match_competitiveness = 1.0 - abs(prediction.player1_probability - prediction.player2_probability)
                        
                        total_games_recommendation = self._calculate_total_games_edge_and_recommendation(
                            expected_total_games=prediction.expected_total_games,
                            match_competitiveness=match_competitiveness,
                            bookmaker_lines=odds_provider_match.total_games_lines
                        )
                    
                    # Add Total Games fields to result
                    result.update({
                        'bookmaker_total_games_lines': bookmaker_lines_json,
                        'recommended_total_games_line': total_games_recommendation['recommended_line'],
                        'recommended_total_games_bet': f"{total_games_recommendation['recommended_bet']} {total_games_recommendation['recommended_line']}" if total_games_recommendation['recommended_bet'] else None,
                        'recommended_total_games_odds': total_games_recommendation['recommended_odds'],
                        'total_games_edge': f"{total_games_recommendation['edge']:.1%}" if total_games_recommendation['edge'] else None,
                        'recommended_bet': self._generate_recommended_bet_text(prediction, player1_name, player2_name),
                        'key_factors': '; '.join(prediction.key_factors[:3]),
                        'reasoning': prediction.reasoning,
                        'weight_breakdown': prediction.weight_breakdown,
                        'odds_provider_event_id': odds_provider_match.event_id,
                        'player1_odds_1_5': odds_provider_match.odds_player1_1_5,
                        'player2_odds_1_5': odds_provider_match.odds_player2_1_5,
                        'player1_odds_2_5': odds_provider_match.odds_player1_2_5,
                        'player2_odds_2_5': odds_provider_match.odds_player2_2_5,
                        'matched_player1': odds_provider_match.player1,
                        'matched_player2': odds_provider_match.player2
                    })
                    
                    # Log prediction results using thread-safe logging
                    if self.prediction_logger:
                        self.prediction_logger.log_match_message("⚖️ WEIGHT CALCULATIONS:")
                        self.prediction_logger.log_match_message("-" * 40)
                        self.prediction_logger.log_match_message("Model weights configuration:")
                        for weight_name, weight_value in self.WEIGHTS.items():
                            self.prediction_logger.log_match_message(f"  {weight_name}: {weight_value:.1%}")
                        self.prediction_logger.log_match_message("")
                        self.prediction_logger.log_match_message("Factor analysis breakdown:")
                        self.prediction_logger.log_match_message("")
                        
                        # Log key factors
                        self.prediction_logger.log_match_message("🔑 KEY DECIDING FACTORS:")
                        self.prediction_logger.log_match_message("-" * 40)
                        for i, factor in enumerate(prediction.key_factors, 1):
                            self.prediction_logger.log_match_message(f"   {i}. {factor}")
                        self.prediction_logger.log_match_message("")
                        
                        # Log prediction result
                        self.prediction_logger.log_match_message("🎯 PREDICTION RESULT:")
                        self.prediction_logger.log_match_message("-" * 40)
                        self.prediction_logger.log_match_message(f"Predicted Winner: {prediction.predicted_winner}")
                        self.prediction_logger.log_match_message(f"Win Probability: {prediction.win_probability:.1%}")
                        self.prediction_logger.log_match_message(f"Confidence Level: {prediction.confidence_level}")
                        self.prediction_logger.log_match_message(f"Reasoning: {prediction.reasoning}")
                        self.prediction_logger.log_match_message("")
                        
                        # Flush all logs for this match to the main log file
                        self.prediction_logger.flush_match_logs(match_id)
                    
                    print(f"[Thread-{thread_id}]    ✅ Analysis complete")
                    return result
                    
                except Exception as e:
                    import traceback
                    print(f"[Thread-{thread_id}]    ❌ Error analyzing match: {e}")
                    print(f"[Thread-{thread_id}]    📍 Full traceback:")
                    traceback.print_exc()
                    return None
            
            # Process all matches concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_matches) as executor:
                # Submit all matches for concurrent processing
                future_to_match = {
                    executor.submit(analyze_single_match, match_pair): match_pair
                    for match_pair in available_matches
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_match):
                    result = future.result()
                    if result:
                        analysis_results.append(result)
                        analyzed_count += 1
                        
                        # Write to CSV immediately when result is ready (thread-safe)
                        if csv_writer:
                            csv_writer.writerow(result)
                            csv_file.flush()  # Force write to disk
                        
                        # Also write to config-specific CSV
                        if config_csv_writer:
                            config_csv_writer.writerow(result)
                            config_csv_file.flush()  # Force write to disk
                    else:
                        analysis_insufficient_data_skipped += 1
                    
                    # Progress update
                    total_processed = analyzed_count + analysis_insufficient_data_skipped
                    print(f"📊 Progress: {total_processed}/{len(available_matches)} matches completed")
            
            # Close CSV file
            if csv_file:
                try:
                    csv_file.close()
                    print(f"📄 CSV file closed: {csv_file_path}")
                except Exception as e:
                    print(f"❌ Error closing CSV file: {e}")
            
            # Close config-specific CSV file
            if config_csv_file:
                try:
                    config_csv_file.close()
                    print(f"📄 Config CSV file closed: {config_csv_path}")
                except Exception as e:
                    print(f"❌ Error closing config CSV file: {e}")
            
            print(f"✅ Completed analysis of {analyzed_count} matches")
            if analysis_insufficient_data_skipped > 0:
                print(f"⚠️ Skipped {analysis_insufficient_data_skipped} matches during analysis due to insufficient player data")
            return analysis_results
            
        except Exception as e:
            print(f"Error analyzing scheduled matches: {e}")
            # Make sure to close CSV files even on error
            if csv_file:
                try:
                    csv_file.close()
                except:
                    pass
            if config_csv_file:
                try:
                    config_csv_file.close()
                except:
                    pass
            return []
    
    def write_to_csv(self, analysis_results: List[Dict[str, Any]], filename: str = None):
        """Write betting analysis results to CSV"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"tennis_betting_analysis_{timestamp}.csv"
        
        if not analysis_results:
            print("No analysis results to write")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=analysis_results[0].keys())
                writer.writeheader()
                writer.writerows(analysis_results)
            
            print(f"✅ Analysis written to {filename}")
            print(f"📊 {len(analysis_results)} matches analyzed and saved")
            
        except Exception as e:
            print(f"Error writing CSV: {e}")

def main():
    """Main execution function"""
    
    print("🎾 TENNIS +1.5 SETS BETTING ANALYSIS (ODDS_PROVIDER)")
    print("=" * 55)
    print("📊 Analyzing tennis matches for +1.5 sets betting opportunities")
    print("🎯 Focus: Players likely to win at least one set in their matches")
    print()
    
    # Initialize analyzer with OddsProvider credentials
    user_id = input("Enter Odds Provider User ID (or press Enter for default from api_secrets.py): ").strip()
    if not user_id:
        # Load from api_secrets.py
        try:
            from api_secrets import ODDS_PROVIDER_CONFIG
            user_id = ODDS_PROVIDER_CONFIG.get('user_id')
        except ImportError:
            print("⚠️ api_secrets.py not found - please provide user ID")
            user_id = input("Enter User ID: ").strip()
    
    access_token = input("Enter Access Token (optional, or press Enter for default from api_secrets.py): ").strip()
    if not access_token:
        try:
            from api_secrets import ODDS_PROVIDER_CONFIG
            access_token = ODDS_PROVIDER_CONFIG.get('access_token')
        except ImportError:
            access_token = None
    
    analyzer = TennisBettingAnalyzer(user_id=user_id, access_token=access_token)
    
    # Analyze today's matches
    target_date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
    if not target_date:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n🔍 Starting analysis for {target_date}...")
    
    # Run analysis
    results = analyzer.analyze_scheduled_matches(target_date)
    
    if results:
        # Write to CSV
        analyzer.write_to_csv(results)
        
        # Print summary
        print(f"\n📈 ANALYSIS SUMMARY:")
        print(f"   Total matches analyzed: {len(results)}")
        
        high_confidence = [r for r in results if r['confidence'] == 'High']
        medium_confidence = [r for r in results if r['confidence'] == 'Medium']
        low_confidence = [r for r in results if r['confidence'] == 'Low']
        
        print(f"   High confidence predictions: {len(high_confidence)}")
        print(f"   Medium confidence predictions: {len(medium_confidence)}")
        print(f"   Low confidence predictions: {len(low_confidence)}")
        
        if high_confidence:
            print(f"\n🔥 HIGH CONFIDENCE +1.5 SETS RECOMMENDATIONS:")
            for match in high_confidence:
                print(f"   • BET: {match['predicted_winner']} +1.5 sets")
                print(f"     Probability: {match['win_probability']:.1%}")
                print(f"     Reasoning: {match['reasoning'][:100]}...")
                print(f"     Tournament: {match.get('tournament', 'N/A')}")
                print()
    else:
        print("❌ No matches found for analysis")

if __name__ == "__main__":
    main()
