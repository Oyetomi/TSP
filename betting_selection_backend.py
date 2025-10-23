#!/usr/bin/env python3
"""
Backend modifications to support flexible player selection
when both players have >50% probability to win at least one set.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

class SelectionType(Enum):
    SINGLE_OPTION = "single"
    DUAL_OPTION = "dual" 
    BALANCED = "balanced"

@dataclass
class PlayerBettingOption:
    """Individual player betting option with value metrics"""
    player_name: str
    player_id: int
    set_probability: float
    confidence_level: str
    is_recommended: bool
    is_value_option: bool
    edge_vs_market: Optional[float] = None
    market_odds: Optional[float] = None
    implied_probability: Optional[float] = None

@dataclass
class BettingSelection:
    """Complete betting selection with all viable options"""
    match_id: str
    player1_name: str
    player2_name: str
    selection_type: SelectionType
    options: List[PlayerBettingOption]
    primary_recommendation: PlayerBettingOption
    surface: str
    tournament: str
    confidence_notes: List[str]

class BettingSelectionEngine:
    """Enhanced betting selection engine supporting dual player options"""
    
    def __init__(self, minimum_probability: float = 0.5, balance_threshold: float = 0.1):
        self.minimum_probability = minimum_probability
        self.balance_threshold = balance_threshold
    
    def create_betting_selection(self, 
                               match_prediction: dict,
                               market_odds: Optional[Dict[str, float]] = None) -> BettingSelection:
        """
        Create betting selection from match prediction with flexible player options.
        
        Args:
            match_prediction: Standard match prediction from TennisBettingAnalyzer
            market_odds: Optional market odds {'player1': 1.5, 'player2': 2.1}
        """
        
        # Extract prediction data
        player1_name = match_prediction.get('player1_name')
        player2_name = match_prediction.get('player2_name')
        player1_prob = match_prediction.get('player1_set_probability', 0)
        player2_prob = match_prediction.get('player2_set_probability', 0)
        confidence = match_prediction.get('confidence', 'Medium')
        
        # Determine selection type
        selection_type = self._determine_selection_type(player1_prob, player2_prob)
        
        # Create player options
        options = []
        
        # Player 1 option
        if player1_prob >= self.minimum_probability:
            p1_option = self._create_player_option(
                player_name=player1_name,
                player_id=match_prediction.get('player1_id'),
                probability=player1_prob,
                confidence=confidence,
                is_higher_prob=player1_prob > player2_prob,
                market_odds=market_odds.get('player1') if market_odds else None
            )
            options.append(p1_option)
        
        # Player 2 option  
        if player2_prob >= self.minimum_probability:
            p2_option = self._create_player_option(
                player_name=player2_name,
                player_id=match_prediction.get('player2_id'),
                probability=player2_prob,
                confidence=confidence,
                is_higher_prob=player2_prob > player1_prob,
                market_odds=market_odds.get('player2') if market_odds else None
            )
            options.append(p2_option)
        
        # Determine primary recommendation
        primary_recommendation = self._get_primary_recommendation(options)
        
        # Generate confidence notes
        confidence_notes = self._generate_confidence_notes(selection_type, options)
        
        return BettingSelection(
            match_id=match_prediction.get('event_id', 'unknown'),
            player1_name=player1_name,
            player2_name=player2_name,
            selection_type=selection_type,
            options=options,
            primary_recommendation=primary_recommendation,
            surface=match_prediction.get('surface', 'Unknown'),
            tournament=match_prediction.get('tournament', 'Unknown'),
            confidence_notes=confidence_notes
        )
    
    def _determine_selection_type(self, p1_prob: float, p2_prob: float) -> SelectionType:
        """Determine what type of selection interface to show"""
        viable_count = sum([p1_prob >= self.minimum_probability, p2_prob >= self.minimum_probability])
        
        if viable_count == 1:
            return SelectionType.SINGLE_OPTION
        elif viable_count == 2:
            prob_diff = abs(p1_prob - p2_prob)
            if prob_diff <= self.balance_threshold:
                return SelectionType.BALANCED
            else:
                return SelectionType.DUAL_OPTION
        else:
            return SelectionType.SINGLE_OPTION  # Fallback
    
    def _create_player_option(self, 
                            player_name: str,
                            player_id: int, 
                            probability: float,
                            confidence: str,
                            is_higher_prob: bool,
                            market_odds: Optional[float] = None) -> PlayerBettingOption:
        """Create individual player betting option"""
        
        # Calculate market edge if odds available
        edge_vs_market = None
        implied_probability = None
        
        if market_odds:
            implied_probability = 1.0 / market_odds
            edge_vs_market = probability - implied_probability
        
        return PlayerBettingOption(
            player_name=player_name,
            player_id=player_id,
            set_probability=probability,
            confidence_level=confidence,
            is_recommended=is_higher_prob,
            is_value_option=not is_higher_prob and probability >= self.minimum_probability,
            edge_vs_market=edge_vs_market,
            market_odds=market_odds,
            implied_probability=implied_probability
        )
    
    def _get_primary_recommendation(self, options: List[PlayerBettingOption]) -> PlayerBettingOption:
        """Get primary recommendation based on edge or probability"""
        if not options:
            return None
            
        # If we have market edges, recommend best edge (if positive)
        options_with_edge = [opt for opt in options if opt.edge_vs_market is not None]
        if options_with_edge:
            positive_edges = [opt for opt in options_with_edge if opt.edge_vs_market > 0]
            if positive_edges:
                return max(positive_edges, key=lambda x: x.edge_vs_market)
        
        # Fallback to highest probability
        return max(options, key=lambda x: x.set_probability)
    
    def _generate_confidence_notes(self, selection_type: SelectionType, options: List[PlayerBettingOption]) -> List[str]:
        """Generate helpful confidence notes for the selection"""
        notes = []
        
        if selection_type == SelectionType.DUAL_OPTION:
            notes.append("Both players viable - choose based on market odds for best value")
            
        if selection_type == SelectionType.BALANCED:
            notes.append("Probabilities very close - consider match context and odds")
            
        # Add edge-based notes
        positive_edges = [opt for opt in options if opt.edge_vs_market and opt.edge_vs_market > 0]
        if positive_edges:
            best_edge = max(positive_edges, key=lambda x: x.edge_vs_market)
            notes.append(f"Best value: {best_edge.player_name} (+{best_edge.edge_vs_market:.1%} edge)")
        
        return notes

# Integration function for existing system
def enhance_prediction_with_selection(prediction_result: dict, 
                                    market_odds: Optional[Dict[str, float]] = None) -> dict:
    """
    Enhance existing prediction result with flexible selection options.
    
    Usage in main betting analysis:
    ```python
    prediction = analyzer.calculate_weighted_prediction(...)
    enhanced = enhance_prediction_with_selection(prediction, market_odds)
    ```
    """
    engine = BettingSelectionEngine()
    selection = engine.create_betting_selection(prediction_result, market_odds)
    
    # Add selection data to existing prediction
    prediction_result['betting_selection'] = {
        'selection_type': selection.selection_type.value,
        'options': [
            {
                'player_name': opt.player_name,
                'player_id': opt.player_id,
                'set_probability': opt.set_probability,
                'is_recommended': opt.is_recommended,
                'is_value_option': opt.is_value_option,
                'edge_vs_market': opt.edge_vs_market,
                'market_odds': opt.market_odds
            } for opt in selection.options
        ],
        'primary_recommendation': {
            'player_name': selection.primary_recommendation.player_name,
            'player_id': selection.primary_recommendation.player_id,
            'reason': 'highest_probability' if not selection.primary_recommendation.edge_vs_market 
                     else f'best_edge_{selection.primary_recommendation.edge_vs_market:.1%}'
        },
        'confidence_notes': selection.confidence_notes
    }
    
    return prediction_result

if __name__ == "__main__":
    # Test example
    test_prediction = {
        'player1_name': 'Kukushkin',
        'player2_name': 'Couacaud', 
        'player1_id': 12345,
        'player2_id': 67890,
        'player1_set_probability': 0.772,
        'player2_set_probability': 0.529,
        'confidence': 'Medium',
        'event_id': '14644107',
        'surface': 'Hard',
        'tournament': 'ATP 250'
    }
    
    test_odds = {
        'player1': 1.20,  # Kukushkin  
        'player2': 1.80   # Couacaud
    }
    
    enhanced = enhance_prediction_with_selection(test_prediction, test_odds)
    
    print("🎾 ENHANCED PREDICTION WITH SELECTION:")
    print("=" * 50)
    selection = enhanced['betting_selection']
    print(f"Selection Type: {selection['selection_type']}")
    print(f"Options Available: {len(selection['options'])}")
    
    for option in selection['options']:
        print(f"\n📊 {option['player_name']}:")
        print(f"   Probability: {option['set_probability']:.1%}")
        print(f"   Recommended: {option['is_recommended']}")
        print(f"   Value Option: {option['is_value_option']}")
        if option['edge_vs_market']:
            print(f"   Market Edge: {option['edge_vs_market']:.1%}")
    
    print(f"\n🎯 Primary Recommendation: {selection['primary_recommendation']['player_name']}")
    print(f"💡 Notes: {selection['confidence_notes']}")
