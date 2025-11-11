#!/usr/bin/env python3
"""
V3.5 Logger - Modular and Decoupled
====================================

Provides detailed logging for V3.5 predictions with:
- Match-by-match analysis
- Weight breakdowns for each player
- Elo integration details
- Dual output (file + terminal)
- Auto-clears on each run

Usage:
    from v3_5_logger import V35Logger
    
    logger = V35Logger()
    logger.log_match_prediction(match_data, weights, elo_data)
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class V35Logger:
    """
    Dedicated logger for V3.5 predictions
    - Modular and decoupled from main system
    - Clears log file on initialization
    - Dual output (file + terminal)
    - Rich match statistics and weight breakdowns
    """
    
    def __init__(self, log_file: str = "logs/v3_5_predictions.log", 
                 terminal_output: bool = True, clear_on_init: bool = True):
        """
        Initialize V3.5 logger
        
        Args:
            log_file: Path to log file
            terminal_output: Whether to also output to terminal
            clear_on_init: Whether to clear log file on initialization
        """
        self.log_file = log_file
        self.terminal_output = terminal_output
        self.session_start = datetime.now()
        
        # Ensure logs directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Clear log file on initialization (fresh start each run)
        if clear_on_init:
            self._clear_log_file()
        
        # Initialize counters
        self.match_count = 0
        self.elo_available_count = 0
        
        # Write session header
        self._write_session_header()
    
    def _clear_log_file(self):
        """Clear the log file for a fresh start"""
        try:
            with open(self.log_file, 'w') as f:
                f.write("")  # Clear file
            if self.terminal_output:
                print(f"🗑️  Cleared V3.5 log file: {self.log_file}")
        except Exception as e:
            print(f"⚠️  Warning: Could not clear log file: {e}")
    
    def _write_session_header(self):
        """Write session header to log file"""
        header = f"""
{'=' * 100}
🎾 V3.5 PREDICTION SYSTEM - SESSION LOG
{'=' * 100}
Session Started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}
Configuration: SERVE_STRENGTH_V3.5_NOV2025
Log File: {self.log_file}
{'=' * 100}

"""
        self._write(header)
    
    def _write(self, message: str, to_terminal: bool = True):
        """
        Write message to log file and optionally terminal
        
        Args:
            message: Message to write
            to_terminal: Whether to also output to terminal
        """
        # Write to file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message)
        except Exception as e:
            print(f"⚠️  Error writing to log file: {e}")
        
        # Write to terminal if enabled
        if to_terminal and self.terminal_output:
            print(message, end='')
    
    def log_match_prediction(self, match_data: Dict[str, Any], 
                            player1_factors: Optional[Dict[str, float]] = None,
                            player2_factors: Optional[Dict[str, float]] = None,
                            elo_data: Optional[Dict[str, Any]] = None,
                            prediction_result: Optional[Dict[str, Any]] = None):
        """
        Log detailed match prediction with weights and Elo data
        
        Args:
            match_data: Basic match information (players, tournament, surface)
            player1_factors: Factor scores for player 1
            player2_factors: Factor scores for player 2
            elo_data: Elo rating data (if available)
            prediction_result: Final prediction (winner, probabilities, confidence)
        """
        self.match_count += 1
        
        # Extract match info
        player1 = match_data.get('player1_name', 'Player 1')
        player2 = match_data.get('player2_name', 'Player 2')
        tournament = match_data.get('tournament', 'Unknown')
        surface = match_data.get('surface', 'Unknown')
        
        # Check if Elo is available
        has_elo = elo_data and elo_data.get('elo_available', False)
        if has_elo:
            self.elo_available_count += 1
        
        # Build match header
        header = f"""
{'=' * 100}
MATCH #{self.match_count}: {player1} vs {player2}
{'=' * 100}
Tournament: {tournament}
Surface: {surface}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Elo Available: {'✅ YES' if has_elo else '❌ NO'}
{'=' * 100}

"""
        self._write(header)
        
        # Log Elo data (if available)
        if has_elo and elo_data:
            self._log_elo_section(elo_data, player1, player2)
        
        # Log weight breakdown for Player 1
        if player1_factors:
            self._log_player_factors(player1, player1_factors, match_data.get('player1_weights'))
        
        # Log weight breakdown for Player 2
        if player2_factors:
            self._log_player_factors(player2, player2_factors, match_data.get('player2_weights'))
        
        # Log prediction result
        if prediction_result:
            self._log_prediction_result(prediction_result, player1, player2)
        
        # Match footer
        footer = f"\n{'-' * 100}\n\n"
        self._write(footer)
    
    def _log_elo_section(self, elo_data: Dict[str, Any], player1: str, player2: str):
        """Log Elo rating details"""
        elo_section = f"""
🎯 ELO RATINGS (Tennis Abstract):
{'-' * 100}
{player1:30s} | Elo: {elo_data.get('player1_elo', 'N/A'):>7} | Surface Elo: {elo_data.get('player1_surface_elo', 'N/A'):>7}
{player2:30s} | Elo: {elo_data.get('player2_elo', 'N/A'):>7} | Surface Elo: {elo_data.get('player2_surface_elo', 'N/A'):>7}

Elo Difference: {elo_data.get('elo_difference', 'N/A'):>+7} (positive = {player1} favored)
Elo Probability: {elo_data.get('elo_probability', 'N/A')} ({player1} wins)
Elo Confidence: {elo_data.get('elo_confidence', 'N/A')}
Elo Blend Factor: {elo_data.get('elo_blend_factor', 'N/A')} (influence on prediction)
Enhancement Level: {elo_data.get('elo_enhancement_level', 'Baseline')}
{'-' * 100}

"""
        self._write(elo_section)
    
    def _log_player_factors(self, player_name: str, factors: Dict[str, float], 
                           weights: Optional[Dict[str, float]] = None):
        """
        Log factor scores and weights for a player
        
        Args:
            player_name: Player name
            factors: Factor scores (0-1)
            weights: Weight configuration (0-1, should sum to 1)
        """
        section = f"""
📊 FACTOR BREAKDOWN: {player_name}
{'-' * 100}
{'Factor':<30s} {'Score':<10s} {'Weight':<10s} {'Contribution':<15s}
{'-' * 100}
"""
        
        total_contribution = 0.0
        
        # Sort factors by contribution (highest first)
        if weights:
            factor_items = sorted(
                [(name, score) for name, score in factors.items()],
                key=lambda x: x[1] * weights.get(x[0], 0.0),
                reverse=True
            )
        else:
            factor_items = sorted(factors.items(), key=lambda x: x[1], reverse=True)
        
        for factor_name, score in factor_items:
            weight = weights.get(factor_name, 0.0) if weights else 0.0
            contribution = score * weight
            total_contribution += contribution
            
            # Format factor name for display
            display_name = factor_name.replace('_', ' ').title()
            
            section += f"{display_name:<30s} {score:>7.3f}   {weight:>7.1%}   {contribution:>12.3f}\n"
        
        section += f"{'-' * 100}\n"
        section += f"{'TOTAL WEIGHTED SCORE':<30s} {'':<10s} {'':<10s} {total_contribution:>12.3f}\n"
        section += f"{'-' * 100}\n\n"
        
        self._write(section)
    
    def _log_prediction_result(self, result: Dict[str, Any], player1: str, player2: str):
        """Log final prediction result"""
        predicted_winner = result.get('predicted_winner', 'Unknown')
        confidence = result.get('confidence', 'Unknown')
        p1_prob = result.get('player1_set_probability', 0.0)
        p2_prob = result.get('player2_set_probability', 0.0)
        
        result_section = f"""
🎯 PREDICTION RESULT:
{'-' * 100}
Predicted Winner: {predicted_winner}
Confidence Level: {confidence}

Set Win Probabilities:
  {player1}: {p1_prob:.1%}
  {player2}: {p2_prob:.1%}

Recommended Bet: {result.get('recommended_bet', 'Unknown')}
Key Factors: {', '.join(result.get('key_factors', [])[:3])}
{'-' * 100}

"""
        self._write(result_section)
    
    def log_session_summary(self):
        """Log session summary at the end"""
        session_duration = datetime.now() - self.session_start
        
        summary = f"""

{'=' * 100}
📊 V3.5 SESSION SUMMARY
{'=' * 100}
Session Duration: {session_duration}
Total Matches Analyzed: {self.match_count}
Matches with Elo Data: {self.elo_available_count} ({self.elo_available_count/self.match_count*100:.1f}% coverage)
Matches without Elo: {self.match_count - self.elo_available_count}

Log File: {self.log_file}
Session Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 100}

"""
        self._write(summary)
    
    def log_weight_config(self, config: Dict[str, Any]):
        """
        Log active weight configuration
        
        Args:
            config: Weight configuration dictionary
        """
        config_section = f"""
⚙️  ACTIVE WEIGHT CONFIGURATION: V3.5
{'-' * 100}
Name: {config.get('name', 'Unknown')}
Description: {config.get('description', 'N/A')}
Created: {config.get('created', 'Unknown')}

Weights (must sum to 100%):
"""
        
        weights = config.get('weights', {})
        total_weight = sum(weights.values())
        
        # Sort weights by value (highest first)
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        
        for factor, weight in sorted_weights:
            if weight > 0:
                display_name = factor.replace('_', ' ').title()
                config_section += f"  {display_name:<35s} {weight:>6.1%}\n"
        
        config_section += f"{'-' * 100}\n"
        config_section += f"{'TOTAL':<37s} {total_weight:>6.1%}\n"
        config_section += f"{'-' * 100}\n\n"
        
        # Log features
        features = config.get('features', {})
        enabled_features = [name for name, enabled in features.items() if enabled]
        
        config_section += f"Enabled Features ({len(enabled_features)}):\n"
        for feature in enabled_features:
            display_name = feature.replace('_', ' ').title()
            config_section += f"  ✅ {display_name}\n"
        
        config_section += f"{'-' * 100}\n\n"
        
        self._write(config_section, to_terminal=False)  # Only to file for config
    
    def close(self):
        """Close logger and write session summary"""
        self.log_session_summary()
        
        if self.terminal_output:
            print(f"\n✅ V3.5 logs saved to: {self.log_file}")
            print(f"📊 Analyzed {self.match_count} matches ({self.elo_available_count} with Elo data)")


# Example usage
if __name__ == "__main__":
    # Test the logger
    logger = V35Logger()
    
    # Test match data
    match_data = {
        'player1_name': 'Carlos Alcaraz',
        'player2_name': 'Jannik Sinner',
        'tournament': 'ATP Finals',
        'surface': 'hardcourt indoor'
    }
    
    player1_factors = {
        'set_performance': 0.85,
        'serve_dominance': 0.78,
        'return_of_serve': 0.72,
        'recent_form': 0.90,
        'psychological_resilience': 0.82
    }
    
    player2_factors = {
        'set_performance': 0.88,
        'serve_dominance': 0.80,
        'return_of_serve': 0.75,
        'recent_form': 0.85,
        'psychological_resilience': 0.80
    }
    
    weights = {
        'set_performance': 0.20,
        'serve_dominance': 0.16,
        'return_of_serve': 0.13,
        'recent_form': 0.16,
        'psychological_resilience': 0.14
    }
    
    elo_data = {
        'elo_available': True,
        'player1_elo': 2268.4,
        'player2_elo': 2267.6,
        'elo_difference': 0.8,
        'elo_probability': '50.1%',
        'elo_confidence': '100.0%',
        'elo_blend_factor': '15.0%',
        'elo_enhancement_level': 'ELO+'
    }
    
    prediction_result = {
        'predicted_winner': 'Carlos Alcaraz',
        'confidence': 'High',
        'player1_set_probability': 0.72,
        'player2_set_probability': 0.68,
        'recommended_bet': 'Carlos Alcaraz +1.5 sets @ 1.35',
        'key_factors': ['Recent form advantage', 'Psychological edge', 'Serve dominance']
    }
    
    match_data['player1_weights'] = weights
    match_data['player2_weights'] = weights
    
    logger.log_match_prediction(
        match_data=match_data,
        player1_factors=player1_factors,
        player2_factors=player2_factors,
        elo_data=elo_data,
        prediction_result=prediction_result
    )
    
    logger.close()
    
    print("\n✅ Test complete! Check logs/v3_5_predictions.log")

