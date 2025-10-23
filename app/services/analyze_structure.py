"""
Analyze MatchDataProvider API response structure
"""

import json
from typing import Any, Dict, List


def analyze_nested_structure(obj: Any, path: str = "", max_depth: int = 3, current_depth: int = 0) -> None:
    """Recursively analyze the structure of nested objects."""
    
    if current_depth >= max_depth:
        return
    
    if isinstance(obj, dict):
        print(f"{path} (dict with {len(obj)} keys)")
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            if isinstance(value, (dict, list)):
                analyze_nested_structure(value, new_path, max_depth, current_depth + 1)
            else:
                print(f"  {new_path}: {type(value).__name__} - {str(value)[:50]}")
    
    elif isinstance(obj, list) and obj:
        print(f"{path} (list with {len(obj)} items)")
        if obj:
            print(f"  First item type: {type(obj[0]).__name__}")
            analyze_nested_structure(obj[0], f"{path}[0]", max_depth, current_depth + 1)


def extract_sample_event(data: Dict) -> Dict:
    """Extract a sample event with all its details."""
    
    if 'events' not in data or not data['events']:
        return {}
    
    return data['events'][0]


def create_structure_summary(data: Dict) -> Dict:
    """Create a summary of the data structure."""
    
    summary = {}
    
    if 'events' in data:
        events = data['events']
        summary['total_events'] = len(events)
        
        if events:
            sample_event = events[0]
            summary['event_structure'] = {
                'top_level_keys': list(sample_event.keys()),
                'tournament_keys': list(sample_event.get('tournament', {}).keys()),
                'homeTeam_keys': list(sample_event.get('homeTeam', {}).keys()),
                'awayTeam_keys': list(sample_event.get('awayTeam', {}).keys()),
                'status_keys': list(sample_event.get('status', {}).keys()),
            }
            
            # Extract some sample values
            summary['sample_data'] = {
                'event_id': sample_event.get('id'),
                'tournament_name': sample_event.get('tournament', {}).get('name'),
                'home_player': sample_event.get('homeTeam', {}).get('name'),
                'away_player': sample_event.get('awayTeam', {}).get('name'),
                'status': sample_event.get('status', {}).get('description'),
                'start_timestamp': sample_event.get('startTimestamp'),
                'ground_type': sample_event.get('groundType'),
                'home_score': sample_event.get('homeScore'),
                'away_score': sample_event.get('awayScore'),
            }
    
    return summary


def main():
    """Main function to analyze the MatchDataProvider response structure."""
    
    try:
        with open('match_data_response_structure.json', 'r') as f:
            data = json.load(f)
        
        print("=== MATCH_DATA API RESPONSE ANALYSIS ===\n")
        
        # Basic overview
        print("1. BASIC OVERVIEW:")
        print(f"   Total top-level keys: {len(data)}")
        print(f"   Keys: {list(data.keys())}\n")
        
        # Events analysis
        if 'events' in data:
            events = data['events']
            print("2. EVENTS OVERVIEW:")
            print(f"   Total events: {len(events)}")
            
            if events:
                print(f"   First event ID: {events[0].get('id')}")
                print(f"   Sample tournament: {events[0].get('tournament', {}).get('name')}")
                print(f"   Sample match: {events[0].get('homeTeam', {}).get('name')} vs {events[0].get('awayTeam', {}).get('name')}\n")
        
        # Detailed structure analysis
        print("3. DETAILED STRUCTURE:")
        if 'events' in data and data['events']:
            sample_event = data['events'][0]
            analyze_nested_structure(sample_event, "event", max_depth=3)
        
        # Create and save summary
        summary = create_structure_summary(data)
        with open('structure_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n4. SUMMARY SAVED:")
        print("   Detailed summary saved to 'structure_summary.json'")
        print(f"   Found {summary.get('total_events', 0)} tennis events")
        
        # Show key fields for prediction system
        print("\n5. KEY FIELDS FOR PREDICTION:")
        sample = summary.get('sample_data', {})
        for key, value in sample.items():
            print(f"   {key}: {value}")
            
    except FileNotFoundError:
        print("Error: match_data_response_structure.json not found")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
