"""
Match Data Provider Service
============================

This service fetches tennis match data from external APIs.
Provider details are configured in api_secrets.py

Handles:
- Match scheduling
- Event data
- Head-to-head statistics
- Tournament information
"""

import json
import asyncio
import time
from functools import partial
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from curl_cffi import requests as curl_requests
from curl_cffi.requests import BrowserType
from pydantic import ValidationError

from ..models.tennis_models import TennisEventResponse, TennisEvent

# Import API configuration (abstracted - actual source in api_secrets.py)
try:
    from api_secrets import PRIMARY_DATA_CONFIG, MATCH_DATA_CONFIG  # MATCH_DATA_CONFIG is alias
except ImportError:
    print("⚠️  WARNING: api_secrets.py not found! Using default configuration.")
    print("   Copy api_secrets.example.py to api_secrets.py and configure it.")
    PRIMARY_DATA_CONFIG = {
        'base_url': 'https://api.example.com/v1',
        'headers': {},
        'cookies': {},
        'impersonate': 'chrome120',
        'timeout': 30
    }
    MATCH_DATA_CONFIG = PRIMARY_DATA_CONFIG  # Fallback alias


class MatchDataProviderError(Exception):
    """Custom exception for match data provider errors."""
    pass


class MatchDataProvider:
    """Service for fetching tennis match data from external provider."""
    
    BASE_URL = PRIMARY_DATA_CONFIG['base_url']
    
    def __init__(self):
        """Initialize the match data provider service."""
        self.session = None
        self._headers = self._get_default_headers()
        self._cookies = PRIMARY_DATA_CONFIG.get('cookies', {})
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests."""
        return PRIMARY_DATA_CONFIG.get('headers', {}).copy()
    
    def _make_request(self, url: str, max_retries: int = 3, **kwargs) -> Dict[str, Any]:
        """
        Make a request to data provider API with browser impersonation and retry logic.
        
        Args:
            url: The API endpoint URL
            max_retries: Maximum number of retry attempts (default: 3)
            **kwargs: Additional parameters for the request
            
        Returns:
            Dict containing the JSON response
            
        Raises:
            MatchDataProviderError: If the request fails after all retries
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = curl_requests.get(
                    url,
                    headers=self._headers,
                    cookies=self._cookies,
                    impersonate=BrowserType.chrome120,
                    timeout=30,
                    **kwargs
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Success - return immediately
                if attempt > 0:
                    print(f"   ✅ Retry #{attempt} succeeded")
                
                return result
                
            except KeyboardInterrupt:
                print("   ⚠️ Request cancelled by user")
                raise
                
            except json.JSONDecodeError as e:
                # JSON errors are usually not transient - don't retry
                print(f"❌ JSON decode error: {url}")
                raise MatchDataProviderError(f"Failed to decode JSON response: {e}")
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check if it's a 404 (permanent error - don't retry)
                if "404" in error_str or "HTTP Error 404" in error_str:
                    raise MatchDataProviderError(f"Failed to fetch data: {e}")
                
                # Transient errors (timeouts, connection issues) - retry with backoff
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    print(f"   ⚠️ Request timeout/error (attempt {attempt + 1}/{max_retries})")
                    print(f"   🔄 Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    print(f"❌ Request failed after {max_retries} attempts")
                    raise MatchDataProviderError(f"Failed to fetch data after {max_retries} attempts: {e}")
    
    async def _make_request_async(self, url: str, max_retries: int = 3, **kwargs) -> Dict[str, Any]:
        """
        Async wrapper for _make_request.
        
        Args:
            url: The API endpoint URL
            max_retries: Maximum number of retry attempts (default: 3)
            **kwargs: Additional parameters for the request
            
        Returns:
            Dict containing the JSON response
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Use partial to bind kwargs to the function
        func = partial(self._make_request, url, max_retries, **kwargs)
        return await loop.run_in_executor(None, func)
    
    async def get_head_to_head(self, event_id: str) -> Dict[str, Any]:
        """
        Get head-to-head match history for a given event.
        
        Args:
            event_id: The event ID
            
        Returns:
            Dict containing H2H match history and statistics
            
        Raises:
            MatchDataProviderError: If the request fails
        """
        url = f"{self.BASE_URL}/event/{event_id}/h2h/events"
        
        try:
            # Update x-requested-with header with random value
            self._headers['x-requested-with'] = 'f6ed52'
            
            response = await self._make_request_async(url)
            
            if not response:
                return {'events': [], 'statistics': {}}
                
            # Process and structure the H2H data
            h2h_data = {
                'events': response.get('events', []),
                'statistics': {
                    'total_matches': len(response.get('events', [])),
                    'surface_breakdown': self._analyze_surface_breakdown(response.get('events', [])),
                    'recent_form': self._analyze_recent_form(response.get('events', []))
                }
            }
            
            return h2h_data
            
        except Exception as e:
            print(f"❌ Failed to fetch H2H data for event {event_id}: {e}")
            return {'events': [], 'statistics': {}}
            
    def _analyze_surface_breakdown(self, matches: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze matches by surface type"""
        surface_counts = {}
        for match in matches:
            surface = match.get('tournament', {}).get('surface', 'Unknown')
            surface_counts[surface] = surface_counts.get(surface, 0) + 1
        return surface_counts
        
    def _analyze_recent_form(self, matches: List[Dict[str, Any]], max_matches: int = 5) -> Dict[str, Any]:
        """Analyze recent matches for form assessment"""
        recent = matches[:max_matches] if matches else []
        return {
            'matches_analyzed': len(recent),
            'avg_sets_per_match': sum(len(m.get('sets', [])) for m in recent) / len(recent) if recent else 0,
            'straight_sets_wins': sum(1 for m in recent if len(m.get('sets', [])) == 2),
            'three_set_matches': sum(1 for m in recent if len(m.get('sets', [])) == 3)
        }
    
    def get_scheduled_events(self, event_date) -> TennisEventResponse:
        """
        Get scheduled tennis events for a specific date.
        
        Args:
            event_date: Date to fetch events for (date object or string in YYYY-MM-DD format)
            
        Returns:
            TennisEventResponse containing all events for the date
            
        Raises:
            MatchDataProviderError: If the request fails or data is invalid
        """
        if isinstance(event_date, str):
            date_str = event_date
        else:
            date_str = event_date.strftime("%Y-%m-%d")
        url = f"{self.BASE_URL}/sport/tennis/scheduled-events/{date_str}"
        
        # Update referer header for the specific date
        headers = self._headers.copy()
        headers['referer'] = f"https://www.example.com/tennis/{date_str}"  # Generic referer
        
        try:
            data = self._make_request(url)
            return TennisEventResponse(**data)
            
        except ValidationError as e:
            raise MatchDataProviderError(f"Failed to validate response data: {e}")
    
    def get_events_by_tournament(self, event_date: date, tournament_slug: str) -> List[TennisEvent]:
        """Get events for a specific tournament on a given date."""
        response = self.get_scheduled_events(event_date)
        return [
            event for event in response.events 
            if event.tournament.slug == tournament_slug
        ]
    
    def get_events_by_category(self, event_date: date, category: str) -> List[TennisEvent]:
        """Get events for a specific category (ATP, WTA, etc.) on a given date."""
        response = self.get_scheduled_events(event_date)
        return [
            event for event in response.events 
            if event.tournament.category.slug.lower() == category.lower()
        ]
    
    def get_ongoing_matches(self, event_date: date) -> List[TennisEvent]:
        """Get currently ongoing matches for a specific date."""
        response = self.get_scheduled_events(event_date)
        return response.ongoing_matches
    
    def get_upcoming_matches(self, event_date: date) -> List[TennisEvent]:
        """Get upcoming matches for a specific date."""
        response = self.get_scheduled_events(event_date)
        return response.upcoming_matches
    
    def get_match_by_id(self, event_date: date, event_id: int) -> Optional[TennisEvent]:
        """Get a specific match by its ID."""
        response = self.get_scheduled_events(event_date)
        for event in response.events:
            if event.id == event_id:
                return event
        return None
    
    async def get_scheduled_events_async(self, event_date: date) -> TennisEventResponse:
        """Async version of get_scheduled_events."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_scheduled_events, event_date)
    
    def save_events_to_file(self, events: TennisEventResponse, filename: str) -> None:
        """Save events data to a JSON file."""
        data = events.model_dump(by_alias=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_tournament_levels(self, event_date: date) -> Dict[str, int]:
        """Get count of matches by tournament level for a given date."""
        response = self.get_scheduled_events(event_date)
        level_counts = {}
        
        for event in response.events:
            level = event.tournament_level
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return level_counts
    
    def get_surface_distribution(self, event_date: date) -> Dict[str, int]:
        """Get distribution of matches by court surface."""
        response = self.get_scheduled_events(event_date)
        surface_counts = {}
        
        for event in response.events:
            surface = event.ground_type
            surface_counts[surface] = surface_counts.get(surface, 0) + 1
        
        return surface_counts
    
    def get_player_rankings(self, player_id: int) -> Dict[str, Any]:
        """
        Get player rankings including UTR rating.
        
        Args:
            player_id: Player ID
            
        Returns:
            Dictionary containing ATP/WTA and UTR rankings
        """
        url = f"{self.BASE_URL}/team/{player_id}/rankings"
        
        try:
            response = curl_requests.get(
                url,
                headers=self._headers,
                cookies=self._cookies,
                impersonate="chrome120"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                rankings = {
                    'atp_ranking': None,
                    'atp_points': None,
                    'wta_ranking': None,
                    'wta_points': None,
                    'utr_rating': None,
                    'utr_position': None,
                    'utr_previous': None,
                    'utr_best': None,
                    'utr_verified': False,
                    'raw_data': data
                }
                
                if 'rankings' in data:
                    for ranking_info in data['rankings']:
                        ranking_class = ranking_info.get('rankingClass', '').lower()
                        ranking_type = ranking_info.get('type')
                        
                        if ranking_class == 'utr':
                            rankings['utr_rating'] = ranking_info.get('points')
                            rankings['utr_position'] = ranking_info.get('ranking')
                            rankings['utr_previous'] = ranking_info.get('previousPoints')
                            rankings['utr_best'] = ranking_info.get('bestRanking')
                            rankings['utr_verified'] = False
                        
                        elif ranking_class == 'team' or ranking_type == 5:
                            rankings['atp_ranking'] = ranking_info.get('ranking')
                            rankings['atp_points'] = ranking_info.get('points')
                        
                        elif ranking_type in [1, 2, 3, 4]:
                            if not rankings['atp_ranking']:
                                rankings['atp_ranking'] = ranking_info.get('ranking')
                                rankings['atp_points'] = ranking_info.get('points')
                
                return rankings
            else:
                print(f"⚠️ Failed to fetch rankings for player {player_id}: {response.status_code}")
                return {'atp_ranking': None, 'atp_points': None, 'wta_ranking': None, 'wta_points': None, 'utr_rating': None, 'utr_position': None, 'utr_verified': False}
                
        except Exception as e:
            print(f"❌ Error fetching rankings for player {player_id}: {e}")
            return {'atp_ranking': None, 'atp_points': None, 'wta_ranking': None, 'wta_points': None, 'utr_rating': None, 'utr_position': None, 'utr_verified': False}


# Backwards compatibility alias
MatchDataProviderService = MatchDataProvider
MatchDataProviderServiceError = MatchDataProviderError

