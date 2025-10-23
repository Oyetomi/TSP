"""
Mental Toughness Service

Data-driven mental toughness analysis using performance metrics and behavioral patterns.
No hardcoded player names - uses statistical indicators of mental strength/weakness.

Key metrics:
- Tiebreak performance (7-6, 6-7 sets)
- Decisive set performance (3rd/5th sets)
- Comeback ability (winning after losing first set)
- Performance consistency (standard deviation)
- Pressure situation handling (break point conversion)
"""

from typing import Dict, Optional, List, Tuple
from datetime import datetime
import statistics

class MentalToughnessService:
    """Data-driven mental toughness analysis service."""
    
    def __init__(self):
        """Initialize the mental toughness service."""
        self.adjustments_made = []
        
        # Thresholds for mental toughness classification
        self.TIEBREAK_STRONG_THRESHOLD = 0.65  # >65% tiebreak win rate = strong
        self.TIEBREAK_WEAK_THRESHOLD = 0.35    # <35% tiebreak win rate = weak
        self.DECISIVE_SET_STRONG = 0.65        # >65% decisive set win rate = strong
        self.DECISIVE_SET_WEAK = 0.35          # <35% decisive set win rate = weak
        self.COMEBACK_STRONG = 0.40            # >40% comeback rate = strong
        self.COMEBACK_WEAK = 0.15              # <15% comeback rate = weak
        self.CONSISTENCY_WEAK = 0.25           # StdDev >0.25 in recent form = inconsistent
    
    def analyze_player_mental_toughness(self, recent_matches: List[Dict], 
                                      player_name: str = "Unknown") -> Dict:
        """
        Analyze player's mental toughness using match data.
        
        Args:
            recent_matches: List of recent match data with scores and details
            player_name: Player name (for logging purposes)
            
        Returns:
            Dictionary containing mental toughness analysis and adjustment
        """
        if not recent_matches:
            return self._no_adjustment_result(player_name, "No match data available")
        
        # Calculate mental toughness metrics
        tiebreak_performance = self._calculate_tiebreak_performance(recent_matches)
        decisive_set_performance = self._calculate_decisive_set_performance(recent_matches)
        comeback_ability = self._calculate_comeback_ability(recent_matches)
        consistency_score = self._calculate_consistency(recent_matches)
        
        # Determine overall mental toughness score
        mental_score = self._calculate_mental_toughness_score(
            tiebreak_performance, decisive_set_performance, 
            comeback_ability, consistency_score
        )
        
        # Generate confidence adjustment based on mental score
        adjustment = self._generate_confidence_adjustment(mental_score)
        
        return {
            'player_name': player_name,
            'mental_toughness_score': mental_score,
            'adjustment': adjustment['penalty'],
            'type': adjustment['type'],
            'reason': adjustment['reason'],
            'severity': adjustment['severity'],
            'metrics': {
                'tiebreak_performance': tiebreak_performance,
                'decisive_set_performance': decisive_set_performance,
                'comeback_ability': comeback_ability,
                'consistency_score': consistency_score
            },
            'sample_size': len(recent_matches)
        }
    
    def _calculate_tiebreak_performance(self, matches: List[Dict]) -> Dict:
        """Calculate tiebreak win rate from match data."""
        tiebreak_wins = 0
        tiebreak_losses = 0
        
        for match in matches:
            # Look for sets that ended 7-6 or 6-7 (potential tiebreaks)
            home_periods = match.get('home_periods', [])
            away_periods = match.get('away_periods', [])
            
            if home_periods and away_periods:
                for home_games, away_games in zip(home_periods, away_periods):
                    # Identify tiebreak sets
                    if (home_games == 7 and away_games == 6) or (home_games == 6 and away_games == 7):
                        # Determine if our player won this tiebreak
                        player_won_set = home_games > away_games  # Assuming player is home
                        
                        if player_won_set:
                            tiebreak_wins += 1
                        else:
                            tiebreak_losses += 1
        
        total_tiebreaks = tiebreak_wins + tiebreak_losses
        win_rate = tiebreak_wins / total_tiebreaks if total_tiebreaks > 0 else 0.5
        
        return {
            'win_rate': win_rate,
            'wins': tiebreak_wins,
            'losses': tiebreak_losses,
            'total': total_tiebreaks,
            'reliability': min(1.0, total_tiebreaks / 5)  # More reliable with more data
        }
    
    def _calculate_decisive_set_performance(self, matches: List[Dict]) -> Dict:
        """Calculate performance in decisive sets (3rd sets, final sets)."""
        decisive_wins = 0
        decisive_losses = 0
        
        for match in matches:
            home_sets = match.get('home_sets', 0)
            away_sets = match.get('away_sets', 0)
            total_sets = home_sets + away_sets
            
            # Count matches that went to decisive sets (3+ sets)
            if total_sets >= 3:
                player_won = home_sets > away_sets  # Assuming player is home
                
                if player_won:
                    decisive_wins += 1
                else:
                    decisive_losses += 1
        
        total_decisive = decisive_wins + decisive_losses
        win_rate = decisive_wins / total_decisive if total_decisive > 0 else 0.5
        
        return {
            'win_rate': win_rate,
            'wins': decisive_wins,
            'losses': decisive_losses,
            'total': total_decisive,
            'reliability': min(1.0, total_decisive / 5)
        }
    
    def _calculate_comeback_ability(self, matches: List[Dict]) -> Dict:
        """Calculate ability to comeback from set deficits."""
        comeback_attempts = 0
        successful_comebacks = 0
        
        for match in matches:
            home_sets = match.get('home_sets', 0)
            away_sets = match.get('away_sets', 0)
            
            # Look for matches where player was down a set but won
            if home_sets > away_sets and away_sets >= 1:
                # Player came back to win
                comeback_attempts += 1
                successful_comebacks += 1
            elif away_sets > home_sets and home_sets >= 1:
                # Player tried to comeback but failed
                comeback_attempts += 1
        
        comeback_rate = successful_comebacks / comeback_attempts if comeback_attempts > 0 else 0.3
        
        return {
            'rate': comeback_rate,
            'successful': successful_comebacks,
            'attempts': comeback_attempts,
            'reliability': min(1.0, comeback_attempts / 5)
        }
    
    def _calculate_consistency(self, matches: List[Dict]) -> Dict:
        """Calculate performance consistency (lower std deviation = more consistent)."""
        if len(matches) < 3:
            return {'score': 0.5, 'std_dev': 0.0, 'reliability': 0.0}
        
        # Calculate a simple performance score for each match
        performance_scores = []
        
        for match in matches:
            home_sets = match.get('home_sets', 0)
            away_sets = match.get('away_sets', 0)
            total_sets = home_sets + away_sets
            
            if total_sets > 0:
                # Performance score based on sets won/total and dominance
                sets_won_ratio = home_sets / total_sets  # Assuming player is home
                dominance_factor = abs(home_sets - away_sets) / total_sets
                
                performance_score = sets_won_ratio + (dominance_factor * 0.2)  # Bonus for dominant wins
                performance_scores.append(min(1.0, performance_score))
        
        if performance_scores:
            std_dev = statistics.stdev(performance_scores)
            consistency_score = 1.0 - min(1.0, std_dev * 2)  # Convert to 0-1 scale
        else:
            std_dev = 0.0
            consistency_score = 0.5
        
        return {
            'score': consistency_score,
            'std_dev': std_dev,
            'reliability': min(1.0, len(performance_scores) / 8)
        }
    
    def _calculate_mental_toughness_score(self, tiebreak_perf: Dict, decisive_perf: Dict,
                                        comeback_ability: Dict, consistency: Dict) -> float:
        """Calculate overall mental toughness score (0.0 = weak, 1.0 = strong)."""
        
        # Weight metrics based on reliability and importance
        tiebreak_weight = tiebreak_perf['reliability'] * 0.35
        decisive_weight = decisive_perf['reliability'] * 0.30
        comeback_weight = comeback_ability['reliability'] * 0.20
        consistency_weight = consistency['reliability'] * 0.15
        
        total_weight = tiebreak_weight + decisive_weight + comeback_weight + consistency_weight
        
        if total_weight == 0:
            return 0.5  # Neutral if no data
        
        # Calculate weighted average
        score = (
            tiebreak_perf['win_rate'] * tiebreak_weight +
            decisive_perf['win_rate'] * decisive_weight +
            comeback_ability['rate'] * comeback_weight +
            consistency['score'] * consistency_weight
        ) / total_weight
        
        return max(0.0, min(1.0, score))
    
    def _generate_confidence_adjustment(self, mental_score: float) -> Dict:
        """Generate confidence adjustment based on mental toughness score."""
        
        if mental_score >= 0.70:
            # Strong mental toughness
            return {
                'penalty': +5,
                'type': 'strength',
                'reason': f'Strong mental toughness detected (score: {mental_score:.2f}) - good pressure performance',
                'severity': 'positive'
            }
        elif mental_score <= 0.30:
            # Weak mental toughness 
            return {
                'penalty': -20,
                'type': 'weakness', 
                'reason': f'Mental fragility detected (score: {mental_score:.2f}) - poor pressure performance',
                'severity': 'high'
            }
        elif mental_score <= 0.40:
            # Moderate mental concerns
            return {
                'penalty': -12,
                'type': 'weakness',
                'reason': f'Mental concerns detected (score: {mental_score:.2f}) - inconsistent under pressure',
                'severity': 'moderate'
            }
        else:
            # Neutral mental toughness
            return {
                'penalty': 0,
                'type': 'neutral',
                'reason': f'Average mental toughness (score: {mental_score:.2f}) - no significant adjustment needed',
                'severity': 'none'
            }
    
    def _no_adjustment_result(self, player_name: str, reason: str) -> Dict:
        """Return no adjustment result."""
        return {
            'player_name': player_name,
            'mental_toughness_score': 0.5,
            'adjustment': 0,
            'type': 'neutral',
            'reason': reason,
            'severity': 'none',
            'metrics': {},
            'sample_size': 0
        }
    
    def adjust_confidence(self, original_confidence: float, recent_matches: List[Dict], 
                         player_name: str = "Unknown") -> Dict:
        """
        Adjust betting confidence based on mental toughness analysis.
        
        Args:
            original_confidence: Original prediction confidence (0-100)
            recent_matches: List of recent match data for analysis
            player_name: Name of the player being analyzed
            
        Returns:
            Dictionary containing adjustment details
        """
        mental_analysis = self.analyze_player_mental_toughness(recent_matches, player_name)
        
        if mental_analysis['adjustment'] == 0:
            return {
                'original_confidence': original_confidence,
                'adjusted_confidence': original_confidence,
                'adjustment': 0,
                'mental_factor': 'neutral',
                'reason': mental_analysis['reason'],
                'applied': False,
                'mental_score': mental_analysis['mental_toughness_score']
            }
        
        # Apply adjustment with bounds checking
        adjustment = mental_analysis['adjustment']
        adjusted_confidence = max(5.0, min(95.0, original_confidence + adjustment))
        
        # Log the adjustment
        adjustment_record = {
            'player_name': player_name,
            'original_confidence': original_confidence,
            'adjusted_confidence': adjusted_confidence,
            'adjustment': adjustment,
            'mental_analysis': mental_analysis
        }
        self.adjustments_made.append(adjustment_record)
        
        return {
            'original_confidence': original_confidence,
            'adjusted_confidence': adjusted_confidence,
            'adjustment': adjustment,
            'mental_factor': mental_analysis['type'],
            'reason': mental_analysis['reason'],
            'severity': mental_analysis['severity'],
            'mental_score': mental_analysis['mental_toughness_score'],
            'metrics': mental_analysis['metrics'],
            'sample_size': mental_analysis['sample_size'],
            'applied': True
        }
    
    def get_adjustment_summary(self) -> Dict:
        """Get summary of all mental toughness adjustments made."""
        if not self.adjustments_made:
            return {
                'total_adjustments': 0,
                'avg_adjustment': 0,
                'weakness_adjustments': 0,
                'strength_adjustments': 0,
                'avg_mental_score': 0.5
            }
        
        weakness_count = sum(1 for adj in self.adjustments_made if adj['adjustment'] < 0)
        strength_count = sum(1 for adj in self.adjustments_made if adj['adjustment'] > 0)
        avg_adjustment = sum(adj['adjustment'] for adj in self.adjustments_made) / len(self.adjustments_made)
        avg_mental_score = sum(adj['mental_analysis']['mental_toughness_score'] for adj in self.adjustments_made) / len(self.adjustments_made)
        
        return {
            'total_adjustments': len(self.adjustments_made),
            'avg_adjustment': avg_adjustment,
            'avg_mental_score': avg_mental_score,
            'weakness_adjustments': weakness_count,
            'strength_adjustments': strength_count,
            'adjustments': self.adjustments_made
        }
    
    def test_with_sample_data(self, player_name: str = "Test Player") -> Dict:
        """Test the mental toughness analysis with sample data."""
        # Generate realistic sample match data for testing
        import random
        
        matches = []
        for i in range(10):  # Last 10 matches
            # Simulate match result
            home_sets = random.randint(0, 3)
            away_sets = random.randint(0, 3)
            
            # Generate period data (games in each set)
            home_periods = []
            away_periods = []
            
            total_sets = home_sets + away_sets
            for set_num in range(total_sets):
                if random.random() < 0.15:  # 15% chance of tiebreak
                    if random.random() < 0.5:
                        home_periods.append(7)
                        away_periods.append(6)
                    else:
                        home_periods.append(6)
                        away_periods.append(7)
                else:
                    # Regular set - winner gets 6, loser gets random 0-5
                    if random.random() < 0.5:
                        home_periods.append(6)
                        away_periods.append(random.randint(0, 5))
                    else:
                        home_periods.append(random.randint(0, 5))
                        away_periods.append(6)
            
            matches.append({
                'home_sets': home_sets,
                'away_sets': away_sets,
                'home_periods': home_periods,
                'away_periods': away_periods
            })
        
        return self.analyze_player_mental_toughness(matches, player_name)

# Global instance for easy import
mental_toughness_service = MentalToughnessService()