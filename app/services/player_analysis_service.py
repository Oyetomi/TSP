"""
Player Analysis Service for tennis set prediction.

This service fetches detailed player information, rankings, recent matches,
and statistics for match analysis and set prediction.
"""

import json
import asyncio
import aiohttp
import time
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from curl_cffi import requests as curl_requests
from curl_cffi.requests import BrowserType
from pydantic import ValidationError

try:
    from .match_data_service import MatchDataProviderServiceError
except ImportError:
    # For standalone testing
    class MatchDataProviderServiceError(Exception):
        """Custom exception for MatchDataProvider service errors."""
        pass

# Import API secrets (keep endpoints and headers private)
try:
    from api_secrets import MATCH_DATA_CONFIG
except ImportError:
    print("⚠️  WARNING: api_secrets.py not found! Using default configuration.")
    MATCH_DATA_CONFIG = {
        'base_url': 'https://www.matchdata-api.example.com/api/v1',
        'headers': {},
        'cookies': {},
        'impersonate': 'chrome120',
        'timeout': 30
    }


class PlayerAnalysisService:
    """Service for analyzing tennis players for set prediction."""
    
    BASE_URL = MATCH_DATA_CONFIG['base_url']
    
    def __init__(self):
        """Initialize the player analysis service."""
        self.session = None
        self._headers = self._get_default_headers()
        self._cookies = MATCH_DATA_CONFIG.get('cookies', {})
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests (loaded from api_secrets.py)."""
        return MATCH_DATA_CONFIG.get('headers', {}).copy()
    
    def _make_request(self, url: str, max_retries: int = 3, **kwargs) -> Dict[str, Any]:
        """
        Make a request to MatchDataProvider API with browser impersonation and retry logic.
        
        Args:
            url: The API endpoint URL
            max_retries: Maximum number of retry attempts (default: 3)
            **kwargs: Additional parameters for the request
            
        Returns:
            Dict containing the JSON response
            
        Raises:
            MatchDataProviderServiceError: If the request fails after all retries
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = curl_requests.get(
                    url,
                    headers=self._headers,
                    cookies=self._cookies,
                    impersonate="chrome",
                    timeout=30,
                    **kwargs
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Success - return immediately
                if attempt > 0:
                    print(f"   ✅ Retry #{attempt} succeeded for {url.split('/')[-2:]}")
                
                return result
                
            except KeyboardInterrupt:
                print("   ⚠️ Request cancelled by user")
                raise
                
            except json.JSONDecodeError as e:
                # JSON errors are usually not transient - don't retry
                print(f"❌ API JSON ERROR: {url} - Error: {e}")
                raise MatchDataProviderServiceError(f"Failed to decode JSON response: {e}")
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check if it's a 404 (permanent error - don't retry)
                if "404" in error_str or "HTTP Error 404" in error_str:
                    print(f"❌ API 404: {url} - Resource not found")
                    raise MatchDataProviderServiceError(f"Failed to fetch data from MatchDataProvider: {e}")
                
                # Transient errors (timeouts, connection issues) - retry with backoff
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    print(f"   ⚠️ API timeout/error (attempt {attempt + 1}/{max_retries}): {error_str[:100]}")
                    print(f"   🔄 Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    print(f"❌ API FAILED after {max_retries} attempts: {url}")
                    print(f"   Error: {error_str[:200]}")
                    raise MatchDataProviderServiceError(f"Failed to fetch data from MatchDataProvider after {max_retries} attempts: {e}")
    
    async def _make_request_async(self, url: str, session: aiohttp.ClientSession, **kwargs) -> Dict[str, Any]:
        """Make an async request to MatchDataProvider API."""
        
    async def analyze_head_to_head(self, event_id: str, player1_id: int, player2_id: int, surface: str = None) -> Dict[str, Any]:
        """
        Analyze head-to-head history with recency weighting.
        
        Args:
            event_id: The MatchDataProvider event ID
            player1_id: First player's ID
            player2_id: Second player's ID
            surface: Optional surface type to filter matches
            
        Returns:
            Dict containing detailed H2H analysis
        """
        try:
            # Get H2H data
            h2h_data = await self.match_data_service.get_head_to_head(event_id)
            if not h2h_data['events']:
                return self._create_empty_h2h_analysis()
            
            # Filter and sort matches
            matches = h2h_data['events']
            def safe_timestamp_h2h(x):
                timestamp = x.get('startTimestamp', 0)
                if isinstance(timestamp, str):
                    try:
                        return int(timestamp)
                    except (ValueError, TypeError):
                        return 0
                return timestamp if isinstance(timestamp, int) else 0
            
            matches.sort(key=safe_timestamp_h2h, reverse=True)
            
            # Apply surface filter if specified
            if surface:
                matches = [m for m in matches if m.get('tournament', {}).get('surface') == surface]
            
            # Calculate recency-weighted statistics
            stats = self._calculate_weighted_h2h_stats(matches, player1_id, player2_id)
            
            return {
                'total_matches': len(matches),
                'player1_wins': stats['player1_wins'],
                'player2_wins': stats['player2_wins'],
                'weighted_advantage': stats['weighted_advantage'],
                'recent_momentum': stats['recent_momentum'],
                'avg_match_time': stats['avg_match_time'],
                'surface_stats': self._get_surface_stats(matches),
                'set_stats': stats['set_stats'],
                'recent_matches': self._format_recent_matches(matches[:5]),
                'confidence_score': self._calculate_h2h_confidence(stats)
            }
            
        except Exception as e:
            print(f"❌ Error analyzing H2H data: {e}")
            return self._create_empty_h2h_analysis()
    
    def _calculate_weighted_h2h_stats(self, matches: List[Dict[str, Any]], player1_id: int, player2_id: int) -> Dict[str, Any]:
        """Calculate recency-weighted H2H statistics based on actual API response structure"""
        total_weight = 0
        weighted_p1_wins = 0
        weighted_p2_wins = 0
        set_stats = {'p1_sets_won': 0, 'p2_sets_won': 0, 'total_sets': 0}
        
        for i, match in enumerate(matches):
            # Skip unfinished matches
            if match.get('status', {}).get('type') != 'finished':
                continue
                
            # Calculate recency weight (more recent matches have higher weight)
            weight = 1.0 / (1 + i * 0.5)  # Decay factor of 0.5 per match
            total_weight += weight
            
            # Determine winner using winnerCode (1 = home, 2 = away)
            winner_code = match.get('winnerCode')
            is_player1_home = match.get('homeTeam', {}).get('id') == player1_id
            
            # Calculate if player1 won based on position and winner code
            player1_won = (is_player1_home and winner_code == 1) or (not is_player1_home and winner_code == 2)
            
            if player1_won:
                weighted_p1_wins += weight
            else:
                weighted_p2_wins += weight
            
            # Analyze sets using period scores
            home_sets = 0
            away_sets = 0
            
            # Count sets won by looking at period scores
            home_score = match.get('homeScore', {})
            away_score = match.get('awayScore', {})
            
            for period in ['period1', 'period2', 'period3']:
                home_set = home_score.get(period)
                away_set = away_score.get(period)
                
                if home_set is not None and away_set is not None:
                    set_stats['total_sets'] += 1
                    if home_set > away_set:
                        home_sets += 1
                        if is_player1_home:
                            set_stats['p1_sets_won'] += 1
                        else:
                            set_stats['p2_sets_won'] += 1
                    elif away_set > home_set:
                        away_sets += 1
                        if is_player1_home:
                            set_stats['p2_sets_won'] += 1
                        else:
                            set_stats['p1_sets_won'] += 1
        
        # Calculate weighted advantage (-1 to 1, positive means player1 advantage)
        if total_weight > 0:
            weighted_advantage = (weighted_p1_wins - weighted_p2_wins) / total_weight
        else:
            weighted_advantage = 0
            
        # Calculate recent momentum (last 3 matches)
        recent_momentum = self._calculate_momentum(matches[:3], player1_id)
        
        # Calculate average match time
        avg_match_time = sum((m.get('endTimestamp', 0) - m.get('startTimestamp', 0)) 
                           for m in matches if m.get('endTimestamp') and m.get('startTimestamp')) / len(matches) if matches else 0
        
        return {
            'player1_wins': weighted_p1_wins,
            'player2_wins': weighted_p2_wins,
            'weighted_advantage': weighted_advantage,
            'recent_momentum': recent_momentum,
            'avg_match_time': avg_match_time,
            'set_stats': set_stats
        }
    
    def _calculate_momentum(self, recent_matches: List[Dict[str, Any]], player1_id: int) -> float:
        """Calculate recent momentum score (-1 to 1)"""
        if not recent_matches:
            return 0
            
        momentum = 0
        for i, match in enumerate(recent_matches):
            weight = 1.0 / (1 + i)  # Most recent match has weight 1, then 0.5, then 0.33
            winner_id = match.get('winner', {}).get('id')
            if winner_id == player1_id:
                momentum += weight
            elif winner_id:  # Only count if there was a winner
                momentum -= weight
                
        return momentum / sum(1.0 / (1 + i) for i in range(len(recent_matches)))
    
    def _create_empty_h2h_analysis(self) -> Dict[str, Any]:
        """Create empty H2H analysis structure"""
        return {
            'total_matches': 0,
            'player1_wins': 0,
            'player2_wins': 0,
            'weighted_advantage': 0,
            'recent_momentum': 0,
            'avg_match_time': 0,
            'surface_stats': {},
            'set_stats': {'p1_sets_won': 0, 'p2_sets_won': 0, 'total_sets': 0},
            'recent_matches': [],
            'confidence_score': 0
        }
    
    def _format_recent_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format recent matches for easy consumption"""
        return [{
            'date': datetime.fromtimestamp(m.get('startTimestamp', 0)).strftime('%Y-%m-%d'),
            'tournament': m.get('tournament', {}).get('name', 'Unknown'),
            'surface': m.get('tournament', {}).get('surface', 'Unknown'),
            'score': self._format_score(m.get('sets', [])),
            'winner': m.get('winner', {}).get('name', 'Unknown')
        } for m in matches]
    
    def _format_score(self, sets: List[Dict[str, Any]]) -> str:
        """Format match score from sets data"""
        return ' '.join(f"{s.get('score1', 0)}-{s.get('score2', 0)}" for s in sets)
    
    def _get_surface_stats(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze H2H record by surface type with recency weighting.
        Returns detailed surface-specific statistics based on actual API response.
        """
        surface_stats = {}
        
        for match in matches:
            # Skip unfinished matches
            if match.get('status', {}).get('type') != 'finished':
                continue
                
            # Get surface from groundType field
            surface = match.get('groundType', 'Unknown')
            if surface not in surface_stats:
                surface_stats[surface] = {
                    'total_matches': 0,
                    'player1_wins': 0,
                    'player2_wins': 0,
                    'total_sets': 0,
                    'player1_sets': 0,
                    'player2_sets': 0,
                    'avg_match_time': 0,
                    'recent_matches': []
                }
            
            # Update match count
            surface_stats[surface]['total_matches'] += 1
            
            # Determine winner using winnerCode (1 = home, 2 = away)
            winner_code = match.get('winnerCode')
            is_player1_home = match.get('homeTeam', {}).get('id') == self.player1_id
            player1_won = (is_player1_home and winner_code == 1) or (not is_player1_home and winner_code == 2)
            
            if player1_won:
                surface_stats[surface]['player1_wins'] += 1
            else:
                surface_stats[surface]['player2_wins'] += 1
            
            # Count sets using period scores
            home_score = match.get('homeScore', {})
            away_score = match.get('awayScore', {})
            
            for period in ['period1', 'period2', 'period3']:
                home_set = home_score.get(period)
                away_set = away_score.get(period)
                
                if home_set is not None and away_set is not None:
                    surface_stats[surface]['total_sets'] += 1
                    if home_set > away_set:
                        if is_player1_home:
                            surface_stats[surface]['player1_sets'] += 1
                        else:
                            surface_stats[surface]['player2_sets'] += 1
                    elif away_set > home_set:
                        if is_player1_home:
                            surface_stats[surface]['player2_sets'] += 1
                        else:
                            surface_stats[surface]['player1_sets'] += 1
            
            # Calculate match time if available
            if match.get('time', {}).get('current'):
                match_time = match['time']['current']
                current_avg = surface_stats[surface]['avg_match_time']
                current_matches = len(surface_stats[surface]['recent_matches'])
                new_avg = (current_avg * current_matches + match_time) / (current_matches + 1)
                surface_stats[surface]['avg_match_time'] = new_avg
            
            # Add to recent matches
            surface_stats[surface]['recent_matches'].append({
                'date': datetime.fromtimestamp(match.get('startTimestamp', 0)).strftime('%Y-%m-%d'),
                'tournament': match.get('tournament', {}).get('name', 'Unknown'),
                'score': f"{home_score.get('period1', 0)}-{away_score.get('period1', 0)}, "
                        f"{home_score.get('period2', 0)}-{away_score.get('period2', 0)}"
                        + (f", {home_score.get('period3', 0)}-{away_score.get('period3', 0)}" 
                           if home_score.get('period3') is not None else ""),
                'winner': match.get('homeTeam' if winner_code == 1 else 'awayTeam', {}).get('name', 'Unknown')
            })
            
            # Update match time
            if match.get('startTimestamp') and match.get('endTimestamp'):
                match_time = match['endTimestamp'] - match['startTimestamp']
                current_avg = surface_stats[surface]['avg_match_time']
                current_matches = len(surface_stats[surface]['recent_matches'])
                new_avg = (current_avg * current_matches + match_time) / (current_matches + 1)
                surface_stats[surface]['avg_match_time'] = new_avg
            
            # Add to recent matches (keep last 3)
            surface_stats[surface]['recent_matches'].append({
                'date': datetime.fromtimestamp(match.get('startTimestamp', 0)).strftime('%Y-%m-%d'),
                'score': self._format_score(sets),
                'winner': match.get('winner', {}).get('name', 'Unknown')
            })
            surface_stats[surface]['recent_matches'] = surface_stats[surface]['recent_matches'][-3:]
        
        # Calculate win rates and dominance scores
        for surface in surface_stats:
            stats = surface_stats[surface]
            total_matches = stats['total_matches']
            if total_matches > 0:
                stats['player1_win_rate'] = stats['player1_wins'] / total_matches
                stats['player2_win_rate'] = stats['player2_wins'] / total_matches
                
                # Calculate dominance score (-1 to 1, positive means player1 dominance)
                total_sets = stats['player1_sets'] + stats['player2_sets']
                if total_sets > 0:
                    stats['set_dominance'] = (stats['player1_sets'] - stats['player2_sets']) / total_sets
                else:
                    stats['set_dominance'] = 0
            
        return surface_stats
    
    def _calculate_h2h_confidence(self, stats: Dict[str, Any]) -> float:
        """Calculate confidence score for H2H analysis (0-1)"""
        if stats['total_matches'] == 0:
            return 0
            
        # Factors that increase confidence:
        # 1. Number of matches (more matches = more confident)
        # 2. Recency of matches
        # 3. Consistency of results
        
        match_count_factor = min(stats['total_matches'] / 5, 1.0)  # Max confidence at 5+ matches
        consistency = abs(stats['weighted_advantage'])  # How consistent is the H2H record
        momentum_factor = abs(stats['recent_momentum'])  # How clear is recent form
        
        confidence = (match_count_factor * 0.4 + 
                     consistency * 0.4 + 
                     momentum_factor * 0.2)
                     
        return min(max(confidence, 0), 1)  # Ensure between 0 and 1
        
    async def _make_request_async(self, url: str, session: aiohttp.ClientSession, **kwargs) -> Dict[str, Any]:
        """
        Make an async request to MatchDataProvider API.
        
        Args:
            url: The API endpoint URL
            session: aiohttp ClientSession
            **kwargs: Additional parameters for the request
            
        Returns:
            Dict containing the JSON response
            
        Raises:
            MatchDataProviderServiceError: If the request fails
        """
        try:
            async with session.get(
                url,
                headers=self._headers,
                cookies=self._cookies,
                timeout=aiohttp.ClientTimeout(total=10),
                **kwargs
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result
                
        except asyncio.TimeoutError:
            print(f"⏰ API TIMEOUT: {url}")
            raise MatchDataProviderServiceError(f"Request timeout: {url}")
        except Exception as e:
            print(f"❌ API FAILED: {url} - Error: {e}")
            raise MatchDataProviderServiceError(f"Failed to fetch data from MatchDataProvider: {e}")
    
    def get_player_rankings(self, player_id: int) -> Dict[str, Any]:
        """
        Get player rankings (ATP/WTA/UTR).
        
        Args:
            player_id: MatchDataProvider player/team ID
            
        Returns:
            Dict containing player rankings data
        """
        url = f"{self.BASE_URL}/team/{player_id}/rankings"
        return self._make_request(url)
    
    def get_player_details(self, player_id: int) -> Dict[str, Any]:
        """
        Get detailed player information.
        
        Args:
            player_id: MatchDataProvider player/team ID
            
        Returns:
            Dict containing detailed player data
        """
        url = f"{self.BASE_URL}/team/{player_id}"
        return self._make_request(url)
    
    def get_player_recent_matches(self, player_id: int, page: int = 0) -> Dict[str, Any]:
        """
        Get player's recent matches using the more reliable /events/last/{page} endpoint.
        Filters out doubles matches and current/upcoming matches.
        
        Args:
            player_id: MatchDataProvider player/team ID
            page: Page number for pagination (default: 0)
            
        Returns:
            Dict containing recent singles matches data (excluding current/upcoming matches)
        """
        # Use the endpoint with proper pagination support
        url = f"{self.BASE_URL}/team/{player_id}/events/last/{page}"
        response = self._make_request(url)
        
        if not response or 'events' not in response:
            return response
        
        # Filter out doubles and current/upcoming matches
        singles_matches = []
        for event in response['events']:
            # Skip doubles matches
            tournament_name = event.get('tournament', {}).get('name', '')
            home_name = event.get('homeTeam', {}).get('name', '')
            away_name = event.get('awayTeam', {}).get('name', '')
            
            is_doubles = (' / ' in home_name or ' / ' in away_name or 
                         'Doubles' in tournament_name or 'doubles' in tournament_name.lower())
            
            if is_doubles:
                continue
                
            # Skip current/upcoming matches (not finished)
            status = event.get('status', {}).get('type', '')
            if status in ['inprogress', 'notstarted', 'postponed']:
                continue
                
            # Only include finished matches
            if status == 'finished':
                singles_matches.append(event)
        
        # CRITICAL: Sort by timestamp in descending order (most recent first)
        # API returns data in ascending order (oldest first), but we need newest first
        def safe_timestamp(x):
            timestamp = x.get('startTimestamp', 0)
            # Convert string timestamps to int
            if isinstance(timestamp, str):
                try:
                    return int(timestamp)
                except (ValueError, TypeError):
                    return 0
            return timestamp if isinstance(timestamp, int) else 0
        
        singles_matches.sort(key=safe_timestamp, reverse=True)
        
        # Return in the same format as the original API
        return {
            'events': singles_matches,
            'hasNextPage': response.get('hasNextPage', False)  # Preserve pagination info
        }
    
    def get_player_singles_matches(self, player_id: int, page: int = 0) -> Dict[str, Any]:
        """
        Get player's recent singles matches only (no doubles).
        Now uses the same reliable endpoint as get_player_recent_matches.
        
        Args:
            player_id: MatchDataProvider player/team ID
            page: Page number for pagination (default: 0, unused with new endpoint)
            
        Returns:
            Dict containing singles matches data (properly sorted, most recent first)
        """
        # Use the same logic as get_player_recent_matches for consistency
        return self.get_player_recent_matches(player_id, page)
    
    def get_match_votes(self, event_id: int) -> Dict[str, Any]:
        """
        Get community votes/predictions for a match.
        
        Args:
            event_id: MatchDataProvider event ID
            
        Returns:
            Dict containing match voting data
        """
        url = f"{self.BASE_URL}/event/{event_id}/votes"
        return self._make_request(url)
    
    def get_player_year_statistics(self, player_id: int, year: int = None) -> Dict[str, Any]:
        """
        Get player statistics for a specific year.
        
        Args:
            player_id: MatchDataProvider player/team ID
            year: Year for statistics (default: current year)
            
        Returns:
            Dict containing yearly statistics
        """
        if year is None:
            year = datetime.now().year
        
        url = f"{self.BASE_URL}/team/{player_id}/year-statistics/{year}"
        return self._make_request(url)
    
    def get_player_recent_tournaments(self, player_id: int) -> Dict[str, Any]:
        """
        Get player's recent unique tournaments.
        
        Args:
            player_id: MatchDataProvider player/team ID
            
        Returns:
            Dict containing recent tournaments data
        """
        url = f"{self.BASE_URL}/team/{player_id}/recent-unique-tournaments"
        return self._make_request(url)
    
    def filter_singles_matches(self, matches_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter out doubles matches, keeping only singles.
        
        NOTE: This method is now deprecated. Use get_player_singles_matches() 
        or get_comprehensive_singles_matches() for better performance.
        
        Args:
            matches_data: Raw matches data from API
            
        Returns:
            List of singles matches only
        """
        if 'events' not in matches_data:
            return []
        
        singles_matches = []
        for match in matches_data['events']:
            # Check if it's singles by looking for "/" in player names (indicates doubles)
            home_name = match.get('homeTeam', {}).get('name', '')
            away_name = match.get('awayTeam', {}).get('name', '')
            
            # Skip if either name contains "/" (doubles indicator)
            if '/' not in home_name and '/' not in away_name:
                singles_matches.append(match)
        
        return singles_matches
    
    def get_comprehensive_singles_matches(self, player_id: int, max_matches: int = 15, max_pages: int = 5) -> Dict[str, Any]:
        """
        Get comprehensive singles matches using pagination for better coverage.
        
        Args:
            player_id: MatchDataProvider player/team ID
            max_matches: Maximum number of matches to collect (default: 50)
            max_pages: Maximum pages to fetch (safety limit)
            
        Returns:
            Dict containing comprehensive singles matches
        """
        try:
            import time
            
            print(f"     🚀 Fetching comprehensive matches for player {player_id}...")
            start_time = time.time()
            
            all_matches = []
            page = 0
            total_matches = 0
            pages_fetched = 0
            
            # Fetch pages until we have enough matches or hit limits
            while page < max_pages and total_matches < max_matches:
                page_data = self.get_player_recent_matches(player_id, page)
                
                if not page_data or 'events' not in page_data:
                    break
                
                matches = page_data['events']
                if not matches:
                    break
                
                # Add matches up to our limit
                remaining_slots = max_matches - total_matches
                matches_to_add = matches[:remaining_slots]
                all_matches.extend(matches_to_add)
                total_matches += len(matches_to_add)
                pages_fetched += 1
                
                # Check if we have more pages or reached our limit
                if not page_data.get('hasNextPage', False) or total_matches >= max_matches:
                    break
                    
                page += 1
            
            # Sort all collected matches by timestamp (most recent first)
            # Individual pages are sorted, but we need to sort across pages too
            def safe_timestamp_comprehensive(x):
                timestamp = x.get('startTimestamp', 0)
                if isinstance(timestamp, str):
                    try:
                        return int(timestamp)
                    except (ValueError, TypeError):
                        return 0
                return timestamp if isinstance(timestamp, int) else 0
            
            all_matches.sort(key=safe_timestamp_comprehensive, reverse=True)
                
            elapsed = time.time() - start_time
            print(f"     ⚡ Fetching completed in {elapsed:.2f}s - {total_matches} matches from {pages_fetched} pages")
            
            return {
                'events': all_matches,
                'total_matches': total_matches,
                'pages_fetched': pages_fetched,
                'has_more_data': page_data.get('hasNextPage', False) if 'page_data' in locals() and page_data else False
            }
            
        except Exception as e:
            print(f"❌ Error fetching matches for player {player_id}: {e}")
            # Fallback to sequential method
            print(f"     🔄 Falling back to sequential fetching...")
            return self._get_sequential_fallback(player_id, max_matches, max_pages)
    
    def _get_sequential_fallback(self, player_id: int, max_matches: int, max_pages: int) -> Dict[str, Any]:
        """
        Sequential fallback for when concurrent fetching fails.
        Since we now use /events/last/0 which doesn't paginate, this is simplified.
        """
        try:
            # Just call the single endpoint since it gets all data at once
            matches_data = self.get_player_recent_matches(player_id)
            
            if not matches_data or 'events' not in matches_data:
                return {'events': []}
            
            all_matches = matches_data['events']
            
            # Limit to max_matches if needed
            if len(all_matches) > max_matches:
                all_matches = all_matches[:max_matches]
            
            return {
                'events': all_matches,
                'total_matches': len(all_matches),
                'pages_fetched': 1,
                'has_more_data': False  # New endpoint gets all data
            }
            
        except Exception as e:
            print(f"❌ Sequential fallback failed for player {player_id}: {e}")
            return {
                'events': [],
                'total_matches': 0,
                'pages_fetched': 0,
                'error': str(e)
            }
    
    def get_recent_comprehensive_form(self, player_id: int, 
                                    current_year: bool = True, 
                                    previous_year: bool = False,
                                    max_matches_per_year: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive form analysis spanning current/previous years.
        
        Args:
            player_id: MatchDataProvider player/team ID
            current_year: Include current year matches
            previous_year: Include previous year matches
            max_matches_per_year: Max matches per year to analyze
            
        Returns:
            Dict containing comprehensive form analysis
        """
        try:
            all_matches = []
            years_analyzed = []
            
            # Get comprehensive singles data
            comprehensive_data = self.get_comprehensive_singles_matches(
                player_id, 
                max_matches=max_matches_per_year * (1 + int(previous_year))
            )
            
            matches = comprehensive_data.get('events', [])
            
            if not matches:
                return {
                    'player_id': player_id,
                    'matches_analyzed': 0,
                    'years_covered': [],
                    'form_data': {},
                    'error': 'No singles matches found'
                }
            
            # Filter by year if specified
            from datetime import datetime
            current_year_val = datetime.now().year
            previous_year_val = current_year_val - 1
            
            for match in matches:
                match_timestamp = match.get('startTimestamp', 0)
                if match_timestamp:
                    match_year = datetime.fromtimestamp(match_timestamp).year
                    
                    include_match = False
                    if current_year and match_year == current_year_val:
                        include_match = True
                        if current_year_val not in years_analyzed:
                            years_analyzed.append(current_year_val)
                    
                    if previous_year and match_year == previous_year_val:
                        include_match = True
                        if previous_year_val not in years_analyzed:
                            years_analyzed.append(previous_year_val)
                    
                    if include_match:
                        all_matches.append(match)
            
            return {
                'player_id': player_id,
                'matches_analyzed': len(all_matches),
                'years_covered': sorted(years_analyzed, reverse=True),
                'total_available': comprehensive_data.get('total_matches', 0),
                'pages_fetched': comprehensive_data.get('pages_fetched', 0),
                'matches_data': all_matches,
                'collection_info': {
                    'max_matches_requested': max_matches_per_year,
                    'has_more_data': comprehensive_data.get('has_more_data', False)
                }
            }
            
        except Exception as e:
            return {
                'player_id': player_id,
                'matches_analyzed': 0,
                'years_covered': [],
                'error': str(e)
            }
    
    def analyze_recent_form(self, player_id: int, num_matches: int = 10, opponent_ranking: Optional[int] = None, surface: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze player's recent form for set prediction with sophisticated set analysis.
        
        This analysis considers:
        1. Set wins even in losing matches
        2. Quality of opposition (ranking comparison)
        3. Performance against higher/lower ranked opponents
        4. Surface-specific performance (CRITICAL for accurate predictions)
        
        Args:
            player_id: MatchDataProvider player/team ID
            num_matches: Number of recent matches to analyze
            opponent_ranking: Current opponent's ranking for comparison
            surface: Surface to filter matches by (e.g., "Hard", "Clay", "Grass")
            
        Returns:
            Dict containing detailed form analysis
        """
        try:
            # Get MORE singles matches than requested to account for surface filtering
            # Request 3x matches to ensure we have enough after surface filtering
            fetch_count = num_matches * 3 if surface else num_matches
            singles_data = self.get_comprehensive_singles_matches(player_id, max_matches=fetch_count)
            singles_matches = singles_data.get('events', [])
            
            if not singles_matches:
                return {
                    'player_id': player_id,
                    'matches_analyzed': 0,
                    'form_data': {},
                    'error': 'No singles matches found'
                }
            
            # CRITICAL: Filter by surface if specified
            if surface:
                original_count = len(singles_matches)
                print(f"\n   🔍 SURFACE FILTERING FOR PLAYER {player_id}:")
                print(f"   📊 Total matches fetched: {original_count}")
                
                # Show surface distribution BEFORE filtering
                surface_counts = {}
                for m in singles_matches:
                    surf = m.get('groundType', 'Unknown')
                    surface_counts[surf] = surface_counts.get(surf, 0) + 1
                print(f"   📈 Surface breakdown:")
                for surf, count in sorted(surface_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"      - {surf}: {count} matches")
                
                # Apply filter
                singles_matches = [m for m in singles_matches if m.get('groundType', '').lower() == surface.lower()]
                filtered_count = len(singles_matches)
                print(f"   ✅ After filtering to '{surface}': {filtered_count} matches")
                print(f"   🎯 Using {min(filtered_count, num_matches)} matches for form analysis")
                
                if not singles_matches:
                    print(f"   ❌ ERROR: No matches found on {surface} surface!")
                    return {
                        'player_id': player_id,
                        'matches_analyzed': 0,
                        'form_data': {},
                        'error': f'No matches found on {surface} surface'
                    }
            
            # Use the matches we got (limit to requested number after filtering)
            matches_to_analyze = singles_matches[:num_matches]
            print(f"   ✓ Analyzing {len(matches_to_analyze)} matches for form score")
            
            # Enhanced form analysis
            match_results = []
            total_sets_won = 0
            total_sets_lost = 0
            matches_won = 0
            matches_lost = 0
            
            # Quality indicators
            sets_vs_higher_ranked = 0  # Sets won against higher-ranked opponents
            total_sets_vs_higher_ranked = 0  # Total sets played against higher-ranked opponents
            sets_vs_lower_ranked = 0   # Sets won against lower-ranked opponents  
            matches_vs_higher_ranked = 0
            matches_vs_lower_ranked = 0
            
            # Performance metrics
            clutch_sets = 0  # Sets won in losing matches
            total_sets_in_losses = 0  # Total sets played in losing matches (for proper clutch rate)
            dominant_wins = 0  # Straight set wins
            losses_to_lower_ranked = 0  # NEW: Track losses to lower-ranked opponents
            
            for match in matches_to_analyze:
                match_analysis = self._analyze_single_match(match, player_id, opponent_ranking)
                if match_analysis:
                    match_results.append(match_analysis)
                    
                    # Update totals
                    total_sets_won += match_analysis['player_sets']
                    total_sets_lost += match_analysis['opponent_sets']
                    
                    if match_analysis['match_won']:
                        matches_won += 1
                        if match_analysis['player_sets'] >= 2 and match_analysis['opponent_sets'] == 0:
                            dominant_wins += 1
                    else:
                        matches_lost += 1
                        # Track sets in losing matches for proper clutch rate calculation
                        total_sets_in_loss = match_analysis['player_sets'] + match_analysis['opponent_sets']
                        total_sets_in_losses += total_sets_in_loss
                        # Count sets won in losing matches as "clutch sets"
                        if match_analysis['player_sets'] > 0:
                            clutch_sets += match_analysis['player_sets']
                    
                    # Quality analysis based on opponent ranking vs CURRENT OPPONENT'S ranking
                    # FIXED: Ensure we correctly count sets vs higher-ranked opponents
                    match_opponent_ranking = match_analysis.get('opponent_ranking')
                    player_sets_won = match_analysis.get('player_sets', 0)
                    match_won = match_analysis.get('match_won', False)
                    
                    if match_opponent_ranking and opponent_ranking and isinstance(match_opponent_ranking, int) and isinstance(opponent_ranking, int):
                        if match_opponent_ranking < opponent_ranking:
                            # Opponent was ranked HIGHER than current opponent (quality opposition)
                            sets_vs_higher_ranked += player_sets_won
                            total_sets_vs_higher_ranked += (player_sets_won + match_analysis.get('opponent_sets', 0))
                            if match_won:
                                matches_vs_higher_ranked += 1
                        elif match_opponent_ranking > opponent_ranking:
                            # Opponent was ranked LOWER than current opponent
                            sets_vs_lower_ranked += player_sets_won
                            if match_won:
                                matches_vs_lower_ranked += 1
                            else:
                                # Track losses to opponents ranked lower than current opponent
                                losses_to_lower_ranked += 1
                    elif match_analysis['opponent_ranking'] and not opponent_ranking:
                        # Fallback: if no current opponent ranking provided, use player's own ranking for context
                        player_ranking = self._get_player_current_ranking(player_id)
                        if player_ranking and match_analysis['opponent_ranking'] < player_ranking:
                            sets_vs_higher_ranked += match_analysis['player_sets']
                            total_sets_vs_higher_ranked += (match_analysis['player_sets'] + match_analysis.get('opponent_sets', 0))
                            if match_analysis['match_won']:
                                matches_vs_higher_ranked += 1
                        elif player_ranking and match_analysis['opponent_ranking'] > player_ranking:
                            sets_vs_lower_ranked += match_analysis['player_sets']
                            if match_analysis['match_won']:
                                matches_vs_lower_ranked += 1
                            else:
                                losses_to_lower_ranked += 1
            
            total_matches = len(match_results)
            total_sets = total_sets_won + total_sets_lost
            
            # Calculate rates
            match_win_rate = (matches_won / total_matches) if total_matches > 0 else 0
            set_win_rate = (total_sets_won / total_sets) if total_sets > 0 else 0
            # FIXED: Proper clutch rate = sets won / total sets in losing matches (not sets per loss!)
            clutch_rate = (clutch_sets / total_sets_in_losses) if total_sets_in_losses > 0 else 0
            
            # Form quality score (0-100)
            base_form_score = self._calculate_form_quality_score({
                'match_win_rate': match_win_rate,
                'set_win_rate': set_win_rate,
                'clutch_rate': clutch_rate,
                'sets_vs_higher_ranked': sets_vs_higher_ranked,
                'total_sets_won': total_sets_won,
                'dominant_wins': dominant_wins,
                'total_matches': total_matches
            })
            
            # NEW: Apply penalty for losses to lower-ranked opponents (-9% per loss)
            lower_ranked_penalty = losses_to_lower_ranked * 9.0  # 9% penalty per loss
            form_score = max(0.0, base_form_score - lower_ranked_penalty)  # Can't go below 0
            
            # LOG FINAL FORM ANALYSIS RESULTS (surface-specific)
            if surface:
                print(f"\n   📊 FORM SCORE CALCULATED (SURFACE: {surface}):")
                print(f"      Matches analyzed: {total_matches}")
                print(f"      Match record: {matches_won}W-{matches_lost}L ({match_win_rate:.1%})")
                print(f"      Set record: {total_sets_won}W-{total_sets_lost}L ({set_win_rate:.1%})")
                print(f"      Clutch rate: {clutch_rate:.1%} ({clutch_sets}/{total_sets_in_losses} sets in losses)")
                print(f"      Base form score: {base_form_score:.1f}/100")
                if lower_ranked_penalty > 0:
                    print(f"      ⚠️  Penalty: -{lower_ranked_penalty:.1f} (losses to lower-ranked)")
                print(f"      ✅ FINAL FORM SCORE: {form_score:.1f}/100")
            
            result = {
                'player_id': player_id,
                'matches_analyzed': total_matches,
                'opponent_ranking': opponent_ranking,
                'form_data': {
                    # Basic stats
                    'matches_won': matches_won,
                    'matches_lost': matches_lost,
                    'match_win_rate': round(match_win_rate, 3),
                    'total_sets_won': total_sets_won,
                    'total_sets_lost': total_sets_lost,
                    'set_win_rate': round(set_win_rate, 3),
                    
                    # Quality indicators
                    'sets_vs_higher_ranked': sets_vs_higher_ranked,
                    'total_sets_vs_higher_ranked': total_sets_vs_higher_ranked,
                    'sets_vs_lower_ranked': sets_vs_lower_ranked,
                    'matches_vs_higher_ranked': matches_vs_higher_ranked,
                    'matches_vs_lower_ranked': matches_vs_lower_ranked,
                    
                    # Performance indicators
                    'clutch_sets': clutch_sets,
                    'total_sets_in_losses': total_sets_in_losses,
                    'clutch_rate': round(clutch_rate, 3),
                    'dominant_wins': dominant_wins,
                    'form_quality_score': round(form_score, 1),
                    
                    # NEW: Ranking-based penalty tracking
                    'losses_to_lower_ranked': losses_to_lower_ranked,
                    'base_form_score': round(base_form_score, 1),
                    'lower_ranked_penalty': round(lower_ranked_penalty, 1),
                    
                    # Match details
                    'recent_matches': match_results
                }
            }
            
            return result
            
        except Exception as e:
            return {
                'player_id': player_id,
                'matches_analyzed': 0,
                'form_data': {},
                'error': str(e)
            }
    
    def _analyze_single_match(self, match: Dict[str, Any], player_id: int, opponent_ranking: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze a single match for detailed set performance.
        
        Args:
            match: Match data from MatchDataProvider
            player_id: Player's ID
            opponent_ranking: Current opponent's ranking for comparison
            
        Returns:
            Dict with match analysis or None if invalid
        """
        try:
            # Determine player position and opponent
            home_team_id = match.get('homeTeam', {}).get('id')
            away_team_id = match.get('awayTeam', {}).get('id')
            
            if home_team_id == player_id:
                is_home = True
                opponent_data = match.get('awayTeam', {})
                player_score = match.get('homeScore', {})
                opponent_score = match.get('awayScore', {})
            elif away_team_id == player_id:
                is_home = False
                opponent_data = match.get('homeTeam', {})
                player_score = match.get('awayScore', {})
                opponent_score = match.get('homeScore', {})
            else:
                return None
            
            # Check if match is finished
            if match.get('status', {}).get('type') != 'finished':
                return None
            
            # Extract set scores
            player_sets = player_score.get('current', 0)
            opponent_sets = opponent_score.get('current', 0)
            
            # Get opponent info
            opponent_name = opponent_data.get('name', 'Unknown')
            opponent_id = opponent_data.get('id')
            
            # Extract opponent ranking from match data
            opponent_rank = self._extract_opponent_ranking(match, opponent_data)
            
            # Determine match result
            match_won = player_sets > opponent_sets
            
            # Get tournament info
            tournament = match.get('tournament', {})
            tournament_name = tournament.get('uniqueTournament', {}).get('name', 'Unknown')
            surface = match.get('groundType', 'Unknown')
            
            # Calculate set details
            individual_sets = []
            for period in ['period1', 'period2', 'period3', 'period4', 'period5']:
                player_games = player_score.get(period)
                opponent_games = opponent_score.get(period)
                
                if player_games is not None and opponent_games is not None:
                    # Check for tiebreak
                    tb_key = f"{period}TieBreak"
                    player_tb = player_score.get(tb_key)
                    opponent_tb = opponent_score.get(tb_key)
                    
                    set_info = {
                        'set_number': len(individual_sets) + 1,
                        'player_games': player_games,
                        'opponent_games': opponent_games,
                        'player_won_set': player_games > opponent_games,
                        'tiebreak': player_tb is not None and opponent_tb is not None,
                        'player_tb_score': player_tb,
                        'opponent_tb_score': opponent_tb
                    }
                    individual_sets.append(set_info)
            
            # Format the date properly
            match_timestamp = match.get('startTimestamp', 0)
            if match_timestamp:
                try:
                    match_date = datetime.fromtimestamp(match_timestamp).strftime('%Y-%m-%d')
                except:
                    match_date = 'Unknown'
            else:
                match_date = 'Unknown'
            
            return {
                'match_id': match.get('id'),
                'opponent_name': opponent_name,
                'opponent_ranking': opponent_rank,
                'tournament': tournament_name,
                'surface': surface,
                'match_won': match_won,
                'player_sets': player_sets,
                'opponent_sets': opponent_sets,
                'individual_sets': individual_sets,
                'is_home': is_home,
                'match_date': match_date,  # Properly formatted date
                'timestamp': match_timestamp,  # Keep original timestamp too
                'ranking_comparison': self._compare_rankings(opponent_rank, opponent_ranking) if opponent_rank and opponent_ranking else None
            }
            
        except Exception as e:
            print(f"Error analyzing match: {e}")
            return None
    
    def _extract_opponent_ranking(self, match: Dict[str, Any], opponent_data: Dict[str, Any]) -> Optional[int]:
        """
        Extract opponent ranking from match data
        
        Args:
            match: Full match data from MatchDataProvider
            opponent_data: Opponent team data from match
            
        Returns:
            Opponent's ATP/WTA ranking if available, None otherwise
        """
        try:
            # First try to get ranking directly from opponent data
            ranking = opponent_data.get('ranking')
            if ranking and isinstance(ranking, int) and ranking > 0:
                return ranking
            
            # If not found, try to get from other team data in the match
            # (sometimes the ranking is nested differently)
            if 'homeTeam' in match and 'awayTeam' in match:
                home_team = match['homeTeam']
                away_team = match['awayTeam']
                
                # Check if opponent is home team or away team
                if opponent_data.get('id') == home_team.get('id'):
                    ranking = home_team.get('ranking')
                elif opponent_data.get('id') == away_team.get('id'):
                    ranking = away_team.get('ranking')
                
                if ranking and isinstance(ranking, int) and ranking > 0:
                    return ranking
            
            # No ranking found
            return None
            
        except Exception as e:
            print(f"   📊 Note: Could not extract opponent ranking: {e}")
            return None
    
    def _compare_rankings(self, opponent_rank: int, current_opponent_rank: int) -> str:
        """Compare opponent ranking to current opponent."""
        if opponent_rank < current_opponent_rank:
            return f"higher_ranked_{current_opponent_rank - opponent_rank}_spots"
        elif opponent_rank > current_opponent_rank:
            return f"lower_ranked_{opponent_rank - current_opponent_rank}_spots"  
        else:
            return "same_ranking"
    
    def _get_player_current_ranking(self, player_id: int) -> Optional[int]:
        """Get player's current ATP or WTA ranking."""
        try:
            rankings_data = self.get_player_rankings(player_id)
            rankings = rankings_data.get('rankings', [])
            
            # Look for ATP ranking (type 5) or WTA ranking (type 6)
            for ranking in rankings:
                if ranking.get('type') in [5, 6]:  # ATP or WTA
                    return ranking.get('ranking')
            return None
        except:
            return None
    
    def _calculate_form_quality_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate a comprehensive form quality score (0-100).
        
        Factors:
        - Match win rate (40% weight)
        - Set win rate (25% weight) 
        - Sets vs higher ranked (20% weight)
        - Clutch performance (10% weight)
        - Dominant wins (5% weight)
        """
        score = 0.0
        
        # Match win rate (0-40 points)
        score += metrics['match_win_rate'] * 40
        
        # Set win rate (0-25 points)
        score += metrics['set_win_rate'] * 25
        
        # Quality bonus for sets against higher ranked (0-20 points)
        # FIXED: Use proper denominator - total sets played vs higher ranked, not total sets won
        if metrics.get('total_sets_vs_higher_ranked', 0) > 0:
            higher_ranked_ratio = metrics['sets_vs_higher_ranked'] / metrics['total_sets_vs_higher_ranked']
            score += higher_ranked_ratio * 20
        elif metrics['sets_vs_higher_ranked'] > 0:
            # Fallback: if no denominator data, give modest bonus for any higher-ranked sets
            score += min(metrics['sets_vs_higher_ranked'] / 10, 2.0)  # Max 2 points fallback
        
        # Clutch performance bonus (0-10 points)
        score += metrics['clutch_rate'] * 10
        
        # Dominant wins bonus (0-5 points)
        if metrics['total_matches'] > 0:
            dominant_ratio = metrics['dominant_wins'] / metrics['total_matches']
            score += dominant_ratio * 5
        
        return min(score, 100.0)  # Cap at 100
    
    def compare_players_for_set_prediction(self, player1_id: int, player2_id: int) -> Dict[str, Any]:
        """
        Compare two players for set prediction analysis with enhanced form analysis.
        
        Args:
            player1_id: First player's MatchDataProvider ID
            player2_id: Second player's MatchDataProvider ID
            
        Returns:
            Dict containing comprehensive comparison data
        """
        try:
            # Get data for both players
            player1_rankings = self.get_player_rankings(player1_id)
            player2_rankings = self.get_player_rankings(player2_id)
            
            player1_details = self.get_player_details(player1_id)
            player2_details = self.get_player_details(player2_id)
            
            # Extract rankings for context-aware form analysis
            p1_ranking = None
            p2_ranking = None
            
            # Get ATP ranking for each player
            for ranking in player1_rankings.get('rankings', []):
                if ranking.get('type') == 5:  # ATP ranking
                    p1_ranking = ranking.get('ranking')
                    break
                    
            for ranking in player2_rankings.get('rankings', []):
                if ranking.get('type') == 5:  # ATP ranking
                    p2_ranking = ranking.get('ranking')
                    break
            
            # Enhanced form analysis with opponent context
            player1_form = self.analyze_recent_form(player1_id, 10, p2_ranking)
            player2_form = self.analyze_recent_form(player2_id, 10, p1_ranking)
            
            player1_stats = self.get_player_year_statistics(player1_id)
            player2_stats = self.get_player_year_statistics(player2_id)
            
            return {
                'comparison_date': datetime.now().isoformat(),
                'player1': {
                    'id': player1_id,
                    'rankings': player1_rankings,
                    'details': player1_details,
                    'recent_form': player1_form,
                    'year_statistics': player1_stats
                },
                'player2': {
                    'id': player2_id,
                    'rankings': player2_rankings,
                    'details': player2_details,
                    'recent_form': player2_form,
                    'year_statistics': player2_stats
                },
                'prediction_factors': self._calculate_enhanced_prediction_factors(
                    player1_rankings, player2_rankings,
                    player1_form, player2_form
                )
            }
            
        except Exception as e:
            return {
                'comparison_date': datetime.now().isoformat(),
                'error': str(e),
                'player1_id': player1_id,
                'player2_id': player2_id
            }
    
    def _calculate_enhanced_prediction_factors(self, p1_rankings: Dict, p2_rankings: Dict,
                                             p1_form: Dict, p2_form: Dict) -> Dict[str, Any]:
        """
        Calculate enhanced prediction factors considering set performance and opponent quality.
        
        Args:
            p1_rankings: Player 1 rankings data
            p2_rankings: Player 2 rankings data
            p1_form: Player 1 enhanced form data
            p2_form: Player 2 enhanced form data
            
        Returns:
            Dict containing sophisticated prediction factors
        """
        factors = {
            'ranking_advantage': None,
            'form_advantage': None,
            'set_performance_advantage': None,
            'clutch_advantage': None,
            'quality_opposition_advantage': None,
            'overall_recommendation': None,
            'confidence_level': 'Low',
            'key_insights': []
        }
        
        try:
            # Extract ATP rankings
            p1_atp_rank = None
            p2_atp_rank = None
            
            for ranking in p1_rankings.get('rankings', []):
                if ranking.get('type') == 5:  # ATP ranking
                    p1_atp_rank = ranking.get('ranking')
                    break
            
            for ranking in p2_rankings.get('rankings', []):
                if ranking.get('type') == 5:  # ATP ranking
                    p2_atp_rank = ranking.get('ranking')
                    break
            
            # Ranking analysis
            ranking_diff = 0
            if p1_atp_rank and p2_atp_rank:
                ranking_diff = p2_atp_rank - p1_atp_rank  # Positive if P1 is higher ranked
                if abs(ranking_diff) >= 20:
                    factors['ranking_advantage'] = 'player1' if ranking_diff > 0 else 'player2'
                    factors['key_insights'].append(f"Significant ranking gap: #{p1_atp_rank} vs #{p2_atp_rank}")
                elif abs(ranking_diff) >= 10:
                    factors['ranking_advantage'] = 'player1' if ranking_diff > 0 else 'player2'
                    factors['key_insights'].append(f"Notable ranking difference: #{p1_atp_rank} vs #{p2_atp_rank}")
                else:
                    factors['ranking_advantage'] = 'close'
                    factors['key_insights'].append(f"Similar rankings: #{p1_atp_rank} vs #{p2_atp_rank}")
            
            # Enhanced form analysis
            p1_form_data = p1_form.get('form_data', {})
            p2_form_data = p2_form.get('form_data', {})
            
            p1_form_score = p1_form_data.get('form_quality_score', 0)
            p2_form_score = p2_form_data.get('form_quality_score', 0)
            
            form_diff = p1_form_score - p2_form_score
            if abs(form_diff) >= 15:
                factors['form_advantage'] = 'player1' if form_diff > 0 else 'player2'
                factors['key_insights'].append(f"Clear form advantage: {p1_form_score:.1f} vs {p2_form_score:.1f}")
            elif abs(form_diff) >= 8:
                factors['form_advantage'] = 'player1' if form_diff > 0 else 'player2'
                factors['key_insights'].append(f"Slight form edge: {p1_form_score:.1f} vs {p2_form_score:.1f}")
            else:
                factors['form_advantage'] = 'close'
                factors['key_insights'].append(f"Similar form: {p1_form_score:.1f} vs {p2_form_score:.1f}")
            
            # Set performance analysis
            p1_set_rate = p1_form_data.get('set_win_rate', 0)
            p2_set_rate = p2_form_data.get('set_win_rate', 0)
            
            set_diff = p1_set_rate - p2_set_rate
            if abs(set_diff) >= 0.15:
                factors['set_performance_advantage'] = 'player1' if set_diff > 0 else 'player2'
                factors['key_insights'].append(f"Set win rate: {p1_set_rate:.1%} vs {p2_set_rate:.1%}")
            else:
                factors['set_performance_advantage'] = 'close'
            
            # Clutch performance (sets won in losing matches)
            p1_clutch = p1_form_data.get('clutch_rate', 0)
            p2_clutch = p2_form_data.get('clutch_rate', 0)
            
            if p1_clutch > 0.5 and p1_clutch > p2_clutch:
                factors['clutch_advantage'] = 'player1'
                factors['key_insights'].append(f"Player 1 shows clutch performance: {p1_clutch:.1%} sets in losses")
            elif p2_clutch > 0.5 and p2_clutch > p1_clutch:
                factors['clutch_advantage'] = 'player2'
                factors['key_insights'].append(f"Player 2 shows clutch performance: {p2_clutch:.1%} sets in losses")
            
            # Quality of opposition analysis
            p1_vs_higher = p1_form_data.get('sets_vs_higher_ranked', 0)
            p2_vs_higher = p2_form_data.get('sets_vs_higher_ranked', 0)
            
            if p1_vs_higher > p2_vs_higher and p1_vs_higher > 0:
                factors['quality_opposition_advantage'] = 'player1'
                factors['key_insights'].append(f"Player 1 has {p1_vs_higher} sets vs higher-ranked opponents")
            elif p2_vs_higher > p1_vs_higher and p2_vs_higher > 0:
                factors['quality_opposition_advantage'] = 'player2'
                factors['key_insights'].append(f"Player 2 has {p2_vs_higher} sets vs higher-ranked opponents")
            
            # Overall recommendation with scoring
            p1_total_score = 0
            p2_total_score = 0
            
            # Ranking weight (30%)
            if factors['ranking_advantage'] == 'player1':
                p1_total_score += 3
            elif factors['ranking_advantage'] == 'player2':
                p2_total_score += 3
            elif factors['ranking_advantage'] == 'close':
                p1_total_score += 1
                p2_total_score += 1
            
            # Form weight (25%)
            if factors['form_advantage'] == 'player1':
                p1_total_score += 2.5
            elif factors['form_advantage'] == 'player2':
                p2_total_score += 2.5
            
            # Set performance weight (20%)
            if factors['set_performance_advantage'] == 'player1':
                p1_total_score += 2
            elif factors['set_performance_advantage'] == 'player2':
                p2_total_score += 2
            
            # Clutch performance weight (15%)
            if factors['clutch_advantage'] == 'player1':
                p1_total_score += 1.5
            elif factors['clutch_advantage'] == 'player2':
                p2_total_score += 1.5
            
            # Quality opposition weight (10%)
            if factors['quality_opposition_advantage'] == 'player1':
                p1_total_score += 1
            elif factors['quality_opposition_advantage'] == 'player2':
                p2_total_score += 1
            
            # Determine recommendation and confidence
            score_diff = abs(p1_total_score - p2_total_score)
            
            if p1_total_score > p2_total_score:
                factors['overall_recommendation'] = 'player1'
            elif p2_total_score > p1_total_score:
                factors['overall_recommendation'] = 'player2'
            else:
                factors['overall_recommendation'] = 'toss_up'
            
            # Confidence level based on score difference
            if score_diff >= 4:
                factors['confidence_level'] = 'High'
            elif score_diff >= 2:
                factors['confidence_level'] = 'Medium'
            else:
                factors['confidence_level'] = 'Low'
            
            factors['player1_total_score'] = round(p1_total_score, 1)
            factors['player2_total_score'] = round(p2_total_score, 1)
            
        except Exception as e:
            factors['calculation_error'] = str(e)
        
        return factors
    
    def _calculate_prediction_factors(self, p1_rankings: Dict, p2_rankings: Dict,
                                    p1_form: Dict, p2_form: Dict) -> Dict[str, Any]:
        """
        Legacy method - redirects to enhanced version for backward compatibility.
        """
        return self._calculate_enhanced_prediction_factors(p1_rankings, p2_rankings, p1_form, p2_form)
    
    def dump_response_structure(self, data: Dict[str, Any], filename: str) -> None:
        """
        Dump API response structure to a JSON file for analysis.
        
        Args:
            data: Response data from MatchDataProvider API
            filename: Output filename
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"Response structure dumped to {filename}")
            
        except Exception as e:
            print(f"Error dumping response structure: {e}")


# Test script for the new service
if __name__ == "__main__":
    service = PlayerAnalysisService()
    
    # Test with Tsitsipas and Yunchaokete IDs from the user's example
    tsitsipas_id = 122366
    yunchaokete_id = 254227
    test_event_id = 14428710
    
    print("=== TESTING PLAYER ANALYSIS SERVICE ===\n")
    
    # Test all endpoints and dump structures
    print("1. Testing Tsitsipas rankings...")
    try:
        rankings = service.get_player_rankings(tsitsipas_id)
        service.dump_response_structure(rankings, "data/tsitsipas_rankings.json")
        print("   ✓ Rankings fetched successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n2. Testing Yunchaokete rankings...")
    try:
        rankings = service.get_player_rankings(yunchaokete_id)
        service.dump_response_structure(rankings, "data/yunchaokete_rankings.json")
        print("   ✓ Rankings fetched successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n3. Testing Tsitsipas recent matches...")
    try:
        matches = service.get_player_recent_matches(tsitsipas_id)
        service.dump_response_structure(matches, "data/tsitsipas_recent_matches.json")
        print("   ✓ Recent matches fetched successfully")
        
        # Test singles filtering
        singles = service.filter_singles_matches(matches)
        print(f"   ✓ Found {len(singles)} singles matches out of {len(matches.get('events', []))}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n4. Testing match votes...")
    try:
        votes = service.get_match_votes(test_event_id)
        service.dump_response_structure(votes, "data/match_votes.json")
        print("   ✓ Match votes fetched successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n5. Testing Tsitsipas player details...")
    try:
        details = service.get_player_details(tsitsipas_id)
        service.dump_response_structure(details, "data/tsitsipas_details.json")
        print("   ✓ Player details fetched successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n6. Testing Tsitsipas year statistics...")
    try:
        stats = service.get_player_year_statistics(tsitsipas_id)
        service.dump_response_structure(stats, "data/tsitsipas_statistics.json")
        print("   ✓ Year statistics fetched successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n7. Testing Tsitsipas recent tournaments...")
    try:
        tournaments = service.get_player_recent_tournaments(tsitsipas_id)
        service.dump_response_structure(tournaments, "data/tsitsipas_tournaments.json")
        print("   ✓ Recent tournaments fetched successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n8. Testing form analysis...")
    try:
        form = service.analyze_recent_form(tsitsipas_id, 5)
        service.dump_response_structure(form, "data/tsitsipas_form_analysis.json")
        print("   ✓ Form analysis completed successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n9. Testing full player comparison...")
    try:
        comparison = service.compare_players_for_set_prediction(tsitsipas_id, yunchaokete_id)
        service.dump_response_structure(comparison, "data/players_comparison.json")
        print("   ✓ Full comparison completed successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n✅ ALL TESTS COMPLETED!")
    print("\nCheck the data/ directory for all dumped response structures.")
