"""
MatchDataProvider Tennis Data Fetcher

This module fetches tennis match data from MatchDataProvider API
using curl-cffi to impersonate a real browser.
"""

import json
from datetime import datetime
from curl_cffi import requests

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


def fetch_scheduled_tennis_events(date: str) -> dict:
    """
    Fetch scheduled tennis events from MatchDataProvider API for a specific date.
    
    Args:
        date: Date in YYYY-MM-DD format
        
    Returns:
        dict: JSON response from MatchDataProvider API
    """
    
    base_url = MATCH_DATA_CONFIG.get('base_url', 'https://www.matchdata-api.example.com/api/v1')
    url = f"{base_url}/sport/tennis/scheduled-events/{date}"
    
    headers = MATCH_DATA_CONFIG.get('headers', {}).copy()
    # Update referer for the specific date
    headers['referer'] = f'https://www.matchdata-api.example.com/tennis/{date}'
    
    cookies = MATCH_DATA_CONFIG.get('cookies', {})
    
    try:
        # Use curl-cffi with Chrome impersonation
        response = requests.get(
            url,
            headers=headers,
            cookies=cookies,
            impersonate="chrome120",
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.RequestException as e:
        print(f"Error fetching data from MatchDataProvider: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return {}


def dump_response_structure(data: dict, filename: str = "match_data_response_structure.json") -> None:
    """
    Dump the API response structure to a JSON file for analysis.
    
    Args:
        data: Response data from MatchDataProvider API
        filename: Output filename
    """
    
    if not data:
        print("No data to dump")
        return
    
    # Create a pretty-printed JSON file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Response structure saved to {filename}")
    print(f"Response contains {len(data)} top-level keys")
    
    # Print summary of top-level structure
    print("\nTop-level keys:")
    for key, value in data.items():
        if isinstance(value, list):
            print(f"  {key}: list with {len(value)} items")
        elif isinstance(value, dict):
            print(f"  {key}: dict with {len(value)} keys")
        else:
            print(f"  {key}: {type(value).__name__}")


def analyze_events_structure(data: dict) -> None:
    """
    Analyze the structure of events in the response.
    
    Args:
        data: Response data from MatchDataProvider API
    """
    
    if 'events' not in data:
        print("No 'events' key found in response")
        return
    
    events = data['events']
    if not events:
        print("No events found in response")
        return
    
    print(f"\nFound {len(events)} events")
    
    # Analyze first event structure
    first_event = events[0]
    print(f"\nFirst event structure:")
    print(f"Event keys: {list(first_event.keys())}")
    
    # Print some key information about the first event
    event_info = {
        'id': first_event.get('id'),
        'tournament': first_event.get('tournament', {}).get('name'),
        'homeTeam': first_event.get('homeTeam', {}).get('name'),
        'awayTeam': first_event.get('awayTeam', {}).get('name'),
        'status': first_event.get('status', {}).get('description'),
        'startTimestamp': first_event.get('startTimestamp')
    }
    
    print(f"Sample event info:")
    for key, value in event_info.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    # Fetch data for the date specified in the original curl command
    date = "2025-08-20"
    
    print(f"Fetching tennis events for {date}...")
    data = fetch_scheduled_tennis_events(date)
    
    if data:
        # Dump complete response structure
        dump_response_structure(data)
        
        # Analyze events structure
        analyze_events_structure(data)
    else:
        print("Failed to fetch data from MatchDataProvider API")
