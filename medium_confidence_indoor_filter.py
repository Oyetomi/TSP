#!/usr/bin/env python3
"""
Medium-Confidence Indoor Hardcourt Filter

Based on analysis of 100W-16L serve v3 data:
- Medium-confidence (55-73%) indoor hardcourt bets: 60.0% win rate (9W-6L)
- High-confidence (>=73%) indoor hardcourt bets: 95.7% win rate (45W-2L)
- All other bets: 88.5% win rate (46W-6L)

Root Causes Identified:
1. Close UTR gaps (<0.2) on fast indoor hardcourt = coin flip (33% of losses)
2. Low clutch performance (<10% advantage) = execution failures (50% of losses)

This filter implements targeted downgrades for medium-confidence indoor bets
to push them below betting thresholds when risk factors are present.
"""

import re
from typing import Dict, Optional, Tuple


class MediumConfidenceIndoorFilter:
    """Filter for medium-confidence (55-73%) indoor hardcourt bets"""
    
    def __init__(self):
        self.filter_stats = {
            'total_checked': 0,
            'total_downgraded': 0,
            'close_utr_downgrades': 0,
            'low_clutch_downgrades': 0
        }
    
    @staticmethod
    def extract_metric_from_weight_breakdown(weight_breakdown: Dict, metric_name: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Extract P1 and P2 values from weight_breakdown format.
        
        Expected format: "P1: 31.3%, P2: 19.6%"
        
        Args:
            weight_breakdown: Dictionary containing weight breakdown data
            metric_name: Name of metric to extract ('clutch', 'pressure', 'resilience')
        
        Returns:
            Tuple of (p1_value, p2_value) as floats (0-100 scale), or (None, None) if not found
        """
        if not weight_breakdown or metric_name not in weight_breakdown:
            return None, None
        
        text = weight_breakdown[metric_name]
        if not text or not isinstance(text, str):
            return None, None
        
        # Try to match "P1: 31.3%, P2: 19.6%" format
        match = re.search(r'P1:\s*([\d.]+)%.*?P2:\s*([\d.]+)%', text)
        if match:
            return float(match.group(1)), float(match.group(2))
        
        return None, None
    
    def check_medium_confidence_indoor(
        self,
        surface: str,
        confidence: float,
        utr_gap: float,
        weight_breakdown: Dict,
        predicted_winner: str,
        player1_name: str,
        player2_name: str,
        tournament_name: str = "Unknown"
    ) -> Dict:
        """
        Check if medium-confidence indoor hardcourt bet should be downgraded.
        
        Args:
            surface: Surface type (e.g., "Hardcourt indoor")
            confidence: Prediction confidence (0-1 scale)
            utr_gap: Absolute UTR difference between players
            weight_breakdown: Dictionary containing clutch/pressure/resilience metrics
            predicted_winner: Name of predicted winner
            player1_name: Name of player 1
            player2_name: Name of player 2
            tournament_name: Tournament name for context
        
        Returns:
            dict: {
                'should_downgrade': bool,
                'reason': str,
                'details': str,
                'severity': str,  # 'severe' or 'moderate'
                'original_confidence': float,
                'adjusted_confidence': float
            }
        """
        self.filter_stats['total_checked'] += 1
        
        # Only applies to indoor hardcourt
        if not surface or 'indoor' not in surface.lower() or 'hardcourt' not in surface.lower():
            return {
                'should_downgrade': False,
                'reason': 'Not indoor hardcourt',
                'details': f'Surface: {surface}',
                'severity': 'none',
                'original_confidence': confidence,
                'adjusted_confidence': confidence
            }
        
        # Only applies to medium-confidence (55-73%)
        if confidence < 0.55 or confidence >= 0.73:
            return {
                'should_downgrade': False,
                'reason': 'Not in medium-confidence range',
                'details': f'Confidence: {confidence:.1%} (filter only applies to 55-73%)',
                'severity': 'none',
                'original_confidence': confidence,
                'adjusted_confidence': confidence
            }
        
        # CHECK 1: Close UTR (<0.2) = severe downgrade
        # Analysis: 2 out of 6 medium-confidence indoor losses (33%) had close UTR
        # Analysis: 0 out of 9 medium-confidence indoor wins (0%) had close UTR
        # Conclusion: Close UTR on indoor hardcourt = coin flip
        if utr_gap < 0.20:
            self.filter_stats['total_downgraded'] += 1
            self.filter_stats['close_utr_downgrades'] += 1
            
            adjusted_confidence = confidence * 0.60  # Drop 58% → 35%, 72% → 43%
            
            return {
                'should_downgrade': True,
                'reason': 'CLOSE_UTR_INDOOR',
                'details': f'UTR gap {utr_gap:.2f} < 0.20 on {surface}. Fast surface + close skill = coin flip. '
                          f'Medium-confidence indoor bets with close UTR: 0% win rate in analysis.',
                'severity': 'severe',
                'original_confidence': confidence,
                'adjusted_confidence': adjusted_confidence
            }
        
        # CHECK 2: Low clutch performance (<10% advantage) = moderate downgrade
        # Analysis: Medium-confidence indoor WINS averaged +17.9% clutch advantage
        # Analysis: Medium-confidence indoor LOSSES averaged +4.9% clutch advantage
        # Conclusion: Low clutch = execution failures on fast indoor surface
        
        # Extract clutch metrics
        clutch_p1, clutch_p2 = self.extract_metric_from_weight_breakdown(weight_breakdown, 'clutch')
        
        if clutch_p1 is not None and clutch_p2 is not None:
            # Determine our player's clutch vs opponent's clutch
            if predicted_winner == player1_name:
                our_clutch = clutch_p1
                opp_clutch = clutch_p2
            else:
                our_clutch = clutch_p2
                opp_clutch = clutch_p1
            
            clutch_gap = our_clutch - opp_clutch
            
            # If clutch advantage < 10%, downgrade confidence
            if clutch_gap < 10.0:
                self.filter_stats['total_downgraded'] += 1
                self.filter_stats['low_clutch_downgrades'] += 1
                
                adjusted_confidence = confidence * 0.75  # Drop 58% → 44%, 72% → 54%
                
                return {
                    'should_downgrade': True,
                    'reason': 'LOW_CLUTCH_INDOOR',
                    'details': f'Clutch gap {clutch_gap:+.1f}% < +10% on {surface}. '
                              f'Indoor hardcourt requires strong clutch execution. '
                              f'Our player: {our_clutch:.1f}%, Opponent: {opp_clutch:.1f}%. '
                              f'Medium-confidence indoor wins averaged +17.9% clutch advantage.',
                    'severity': 'moderate',
                    'original_confidence': confidence,
                    'adjusted_confidence': adjusted_confidence
                }
        
        # Passed all checks - no downgrade needed
        return {
            'should_downgrade': False,
            'reason': 'Passed all checks',
            'details': f'UTR gap: {utr_gap:.2f} (adequate), Clutch data available and strong',
            'severity': 'none',
            'original_confidence': confidence,
            'adjusted_confidence': confidence
        }
    
    def get_stats(self) -> Dict:
        """Get filter statistics"""
        return self.filter_stats.copy()
    
    def reset_stats(self):
        """Reset filter statistics"""
        self.filter_stats = {
            'total_checked': 0,
            'total_downgraded': 0,
            'close_utr_downgrades': 0,
            'low_clutch_downgrades': 0
        }


# Example usage
if __name__ == "__main__":
    filter_system = MediumConfidenceIndoorFilter()
    
    # Example 1: Close UTR on indoor hardcourt (should downgrade severely)
    result = filter_system.check_medium_confidence_indoor(
        surface="Hardcourt indoor",
        confidence=0.58,
        utr_gap=0.15,
        weight_breakdown={'clutch': 'P1: 25.0%, P2: 20.0%'},
        predicted_winner="Daniil Glinka",
        player1_name="Daniil Glinka",
        player2_name="Alfredo Perez",
        tournament_name="Knoxville, USA"
    )
    
    print("Example 1: Close UTR Test")
    print(f"  Should downgrade: {result['should_downgrade']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Original confidence: {result['original_confidence']:.1%}")
    print(f"  Adjusted confidence: {result['adjusted_confidence']:.1%}")
    print(f"  Details: {result['details']}\n")
    
    # Example 2: Low clutch on indoor hardcourt (should downgrade moderately)
    result = filter_system.check_medium_confidence_indoor(
        surface="Hardcourt indoor",
        confidence=0.72,
        utr_gap=0.98,
        weight_breakdown={'clutch': 'P1: 25.0%, P2: 25.0%'},  # 0% clutch gap
        predicted_winner="Marin Čilić",
        player1_name="Marin Čilić",
        player2_name="Stefano Napolitano",
        tournament_name="Helsinki, Finland"
    )
    
    print("Example 2: Low Clutch Test")
    print(f"  Should downgrade: {result['should_downgrade']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Original confidence: {result['original_confidence']:.1%}")
    print(f"  Adjusted confidence: {result['adjusted_confidence']:.1%}")
    print(f"  Details: {result['details']}\n")
    
    # Example 3: Good conditions (should pass)
    result = filter_system.check_medium_confidence_indoor(
        surface="Hardcourt indoor",
        confidence=0.65,
        utr_gap=0.50,
        weight_breakdown={'clutch': 'P1: 35.0%, P2: 20.0%'},  # +15% clutch gap
        predicted_winner="Player A",
        player1_name="Player A",
        player2_name="Player B",
        tournament_name="Test Tournament"
    )
    
    print("Example 3: Good Conditions Test")
    print(f"  Should downgrade: {result['should_downgrade']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Original confidence: {result['original_confidence']:.1%}")
    print(f"  Adjusted confidence: {result['adjusted_confidence']:.1%}")
    print(f"  Details: {result['details']}\n")
    
    # Print stats
    print("Filter Statistics:")
    stats = filter_system.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

