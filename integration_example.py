#!/usr/bin/env python3
"""
Integration example showing how to modify the existing betting analysis 
to support flexible player selection.
"""

import sys
import os
sys.path.append('.')

from betting_analysis_script import TennisBettingAnalyzer
from betting_selection_backend import enhance_prediction_with_selection
import json

class EnhancedBettingAnalyzer(TennisBettingAnalyzer):
    """Enhanced analyzer with flexible player selection support"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.market_odds_provider = None  # Could integrate with odds API
    
    def analyze_match_with_selection(self, 
                                   player1_profile, 
                                   player2_profile,
                                   surface='Unknown',
                                   event_id=None,
                                   match_format=None,
                                   market_odds=None):
        """
        Enhanced match analysis with flexible player selection.
        
        Returns both the standard prediction AND selection options.
        """
        
        # Get standard prediction
        prediction = self.calculate_weighted_prediction(
            player1_profile, player2_profile, surface, event_id, match_format
        )
        
        # Convert to dictionary format for selection engine
        prediction_dict = {
            'player1_name': player1_profile.name,
            'player2_name': player2_profile.name,
            'player1_id': player1_profile.id,
            'player2_id': player2_profile.id,
            'player1_set_probability': prediction.player1_set_probability,
            'player2_set_probability': prediction.player2_set_probability,
            'confidence': prediction.confidence,
            'event_id': event_id,
            'surface': surface,
            'tournament': match_format.tournament_name if match_format else 'Unknown'
        }
        
        # Enhance with selection options
        enhanced_prediction = enhance_prediction_with_selection(
            prediction_dict, market_odds
        )
        
        return enhanced_prediction
    
    def get_market_odds(self, event_id):
        """
        Fetch market odds for a match. 
        In a real implementation, this would call an odds API.
        """
        # Mock implementation - replace with real odds API
        mock_odds = {
            '14644107': {'player1': 1.20, 'player2': 1.80},  # Kukushkin vs Couacaud
            '14633454': {'player1': 2.10, 'player2': 1.70},  # Example odds
        }
        
        return mock_odds.get(str(event_id))

def demo_flexible_selection():
    """Demo of the flexible selection system"""
    
    print("🎾 FLEXIBLE PLAYER SELECTION DEMO")
    print("=" * 60)
    
    # Initialize enhanced analyzer
    analyzer = EnhancedBettingAnalyzer()
    
    # Mock match data (normally from MatchDataProvider)
    mock_match = {
        'event_id': '14644107',
        'player1_name': 'Mikhail Kukushkin',
        'player2_name': 'Enzo Couacaud',
        'player1_id': 12345,
        'player2_id': 67890,
        'surface': 'Hard',
        'tournament': 'ATP 250'
    }
    
    # Mock probabilities (from our model)
    mock_prediction = {
        'player1_name': mock_match['player1_name'],
        'player2_name': mock_match['player2_name'],
        'player1_id': mock_match['player1_id'],
        'player2_id': mock_match['player2_id'],
        'player1_set_probability': 0.772,  # 77.2%
        'player2_set_probability': 0.529,  # 52.9%
        'confidence': 'Medium',
        'event_id': mock_match['event_id'],
        'surface': mock_match['surface'],
        'tournament': mock_match['tournament']
    }
    
    # Mock market odds
    market_odds = {
        'player1': 1.20,  # Kukushkin (implied 83.3%)
        'player2': 1.80   # Couacaud (implied 55.6%)
    }
    
    # Enhance with selection options
    enhanced = enhance_prediction_with_selection(mock_prediction, market_odds)
    
    # Display results
    print(f"🆔 Match: {enhanced['player1_name']} vs {enhanced['player2_name']}")
    print(f"📍 Event ID: {enhanced['event_id']}")
    print(f"🎾 Surface: {enhanced['surface']} | Tournament: {enhanced['tournament']}")
    print()
    
    selection = enhanced['betting_selection']
    print(f"🎯 Selection Type: {selection['selection_type'].upper()}")
    print(f"📊 Available Options: {len(selection['options'])}")
    print()
    
    print("BETTING OPTIONS:")
    print("-" * 40)
    
    for i, option in enumerate(selection['options'], 1):
        print(f"\n{i}. 🏆 {option['player_name']}")
        print(f"   📊 Set Win Probability: {option['set_probability']:.1%}")
        
        if option['is_recommended']:
            print(f"   ⭐ RECOMMENDED (highest probability)")
        elif option['is_value_option']:
            print(f"   💰 VALUE OPTION (still viable)")
        
        if option['market_odds']:
            print(f"   💱 Market Odds: {option['market_odds']:.2f}")
            implied = 1.0 / option['market_odds']
            print(f"   📈 Implied Probability: {implied:.1%}")
            
        if option['edge_vs_market']:
            edge_sign = "+" if option['edge_vs_market'] > 0 else ""
            color = "🟢" if option['edge_vs_market'] > 0 else "🔴"
            print(f"   {color} Market Edge: {edge_sign}{option['edge_vs_market']:.1%}")
    
    print(f"\n🎯 PRIMARY RECOMMENDATION:")
    rec = selection['primary_recommendation']
    print(f"   Player: {rec['player_name']}")
    print(f"   Reason: {rec['reason'].replace('_', ' ').title()}")
    
    if selection['confidence_notes']:
        print(f"\n💡 ANALYSIS NOTES:")
        for note in selection['confidence_notes']:
            print(f"   • {note}")
    
    # Show value betting insight
    print(f"\n💰 VALUE BETTING INSIGHT:")
    kukushkin_option = next(opt for opt in selection['options'] if 'Kukushkin' in opt['player_name'])
    couacaud_option = next(opt for opt in selection['options'] if 'Couacaud' in opt['player_name'])
    
    print(f"   Kukushkin: {kukushkin_option['edge_vs_market']:.1%} edge (model {kukushkin_option['set_probability']:.1%} vs market {1/kukushkin_option['market_odds']:.1%})")
    print(f"   Couacaud: {couacaud_option['edge_vs_market']:.1%} edge (model {couacaud_option['set_probability']:.1%} vs market {1/couacaud_option['market_odds']:.1%})")
    
    if couacaud_option['edge_vs_market'] > kukushkin_option['edge_vs_market']:
        print(f"   ✅ BETTER VALUE: Bet on Couacaud despite lower probability!")
    else:
        print(f"   ✅ STICK WITH: Kukushkin has better value")
    
    return enhanced

def generate_frontend_json(enhanced_prediction):
    """Generate JSON for frontend consumption"""
    
    frontend_data = {
        'match': {
            'player1_name': enhanced_prediction['player1_name'],
            'player2_name': enhanced_prediction['player2_name'],
            'surface': enhanced_prediction['surface'],
            'tournament': enhanced_prediction['tournament'],
            'event_id': enhanced_prediction['event_id']
        },
        'betting_selection': enhanced_prediction['betting_selection'],
        'metadata': {
            'generated_at': '2025-01-09T15:30:00Z',
            'model_version': 'CALIBRATED_V1',
            'has_market_odds': any(opt['market_odds'] for opt in enhanced_prediction['betting_selection']['options'])
        }
    }
    
    return json.dumps(frontend_data, indent=2)

if __name__ == "__main__":
    # Run demo
    enhanced_result = demo_flexible_selection()
    
    print("\n" + "=" * 60)
    print("🌐 FRONTEND JSON OUTPUT:")
    print("=" * 60)
    
    # Generate frontend JSON
    frontend_json = generate_frontend_json(enhanced_result)
    print(frontend_json)
    
    # Save to file for frontend integration
    with open('demo_match_selection.json', 'w') as f:
        f.write(frontend_json)
    
    print(f"\n✅ Frontend JSON saved to: demo_match_selection.json")
    print(f"🎮 Use this with the PlayerSelectionUI component!")
