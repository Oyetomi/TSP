"""
Prediction Logger for detailed match analysis logging.

This module provides comprehensive logging for each match's prediction process,
capturing all factors, weights, calculations, and decision-making steps.
"""

import os
import json
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from contextvars import ContextVar
from contextlib import contextmanager


@dataclass
class MatchLoggingData:
    """Data structure for match logging"""
    match_id: str
    event_id: int
    player1_name: str
    player2_name: str
    tournament: str
    surface: str
    timestamp: str
    
    # Player profiles
    player1_profile: Dict[str, Any]
    player2_profile: Dict[str, Any]
    
    # Weight breakdown
    weights_used: Dict[str, float]
    factor_scores: Dict[str, Any]
    
    # Prediction results
    predicted_winner: str
    win_probability: float
    confidence: str
    reasoning: str
    key_factors: List[str]
    
    # OddsProvider data
    odds_provider_odds: Dict[str, float]
    has_set_market: bool
    
    # Additional analysis
    crowd_sentiment: Optional[Dict[str, Any]] = None
    form_analysis: Optional[Dict[str, Any]] = None


class PredictionLogger:
    """Comprehensive logging system for tennis set predictions"""
    
    def __init__(self, log_file: str = "logs/match_predictions.log"):
        """Initialize the prediction logger"""
        self.log_file = log_file
        self.detailed_log_file = "logs/detailed_match_analysis.json"
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Clear log files on initialization (fresh start each run)
        self.clear_logs()
        
        # Set up logging
        self.logger = logging.getLogger('tennis_predictions')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler for main log
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Storage for detailed JSON data
        self.detailed_matches = []

        # Thread-safe logging support
        self._lock = threading.Lock()
        self._match_buffers: Dict[str, List[str]] = {}
        self._current_match_id: ContextVar = ContextVar('current_match_id', default=None)
        
        # Buffered logging support for ordered logs in async contexts
        self._buffering_enabled: bool = False
        self._ctx_match_id: ContextVar = ContextVar('prediction_logger_match_id', default=None)
        self._buffers: Dict[str, List[tuple]] = {}

    def enable_buffering(self, enabled: bool = True):
        """Enable/disable per-match buffering mode."""
        self._buffering_enabled = enabled

    @contextmanager
    def match_context(self, match_id: str):
        """Context manager to bind subsequent logs to a match_id buffer."""
        token = self._ctx_match_id.set(match_id)
        try:
            yield
        finally:
            self._ctx_match_id.reset(token)

    def _buffer_or_write(self, method_name: str, *args, **kwargs) -> bool:
        """If buffering is active and a match_id is set, buffer the call and return True.
        Otherwise return False to indicate the caller should perform the real write now.
        """
        match_id = self._ctx_match_id.get()
        if self._buffering_enabled and match_id:
            self._buffers.setdefault(str(match_id), []).append((method_name, args, kwargs))
            return True
        return False

    def replay_and_clear(self, match_ids_in_order: List[str]):
        """Replay buffered log calls for the provided match IDs in order, then clear them."""
        if not match_ids_in_order:
            return
        # Temporarily disable buffering while replaying to avoid re-buffering
        prev = self._buffering_enabled
        self._buffering_enabled = False
        try:
            for mid in match_ids_in_order:
                calls = self._buffers.pop(str(mid), [])
                for method_name, args, kwargs in calls:
                    # Dispatch to the original public methods
                    getattr(self, method_name)(*args, **kwargs)
        finally:
            self._buffering_enabled = prev
        
    def clear_logs(self):
        """Clear existing log files for fresh start"""
        for log_path in [self.log_file, self.detailed_log_file]:
            if os.path.exists(log_path):
                try:
                    os.remove(log_path)
                    print(f"🗑️ Cleared previous log: {log_path}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not clear {log_path}: {e}")
    
    def start_match_logging(self, match_id: str):
        """Start logging for a specific match (thread-safe)"""
        with self._lock:
            self._match_buffers[match_id] = []
            self._current_match_id.set(match_id)
    
    def log_match_message(self, message: str, match_id: str = None):
        """Log a message for a specific match (thread-safe)"""
        if match_id is None:
            match_id = self._current_match_id.get()
        
        if match_id:
            with self._lock:
                if match_id not in self._match_buffers:
                    self._match_buffers[match_id] = []
                self._match_buffers[match_id].append(message)
        else:
            # Fallback to regular logging
            self.logger.info(message)
    
    def flush_match_logs(self, match_id: str):
        """Flush all buffered logs for a match to the main log file (thread-safe)"""
        with self._lock:
            if match_id in self._match_buffers:
                messages = self._match_buffers[match_id]
                for message in messages:
                    self.logger.info(message)
                del self._match_buffers[match_id]
    
    def log_session_start(self, target_dates: List[str]):
        """Log the start of a prediction session"""
        self.logger.info("=" * 80)
        self.logger.info("TENNIS SET PREDICTION ANALYSIS SESSION STARTED")
        self.logger.info("=" * 80)
        self.logger.info(f"Target dates: {', '.join(target_dates)}")
        self.logger.info(f"Session started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("")
    
    def log_daily_analysis_start(self, target_date: str, total_events: int):
        """Log the start of daily analysis"""
        self.logger.info("-" * 60)
        self.logger.info(f"DAILY ANALYSIS: {target_date}")
        self.logger.info("-" * 60)
        self.logger.info(f"Total events found: {total_events}")
    
    def log_match_filtering(self, total_events: int, singles_matches: int, odds_provider_matches: int):
        """Log match filtering results"""
        self.logger.info(f"Match filtering results:")
        self.logger.info(f"  - Total events: {total_events}")
        self.logger.info(f"  - Singles matches: {singles_matches}")
        self.logger.info(f"  - OddsProvider matches available: {odds_provider_matches}")
    
    def log_odds_provider_matches(self, odds_provider_matches: List[Any]):
        """Log all OddsProvider matches for reference"""
        self.logger.info(f"OddsProvider matches available for betting:")
        for i, match in enumerate(odds_provider_matches, 1):
            self.logger.info(f"  {i:2d}. {match.player1} vs {match.player2} (ID: {match.event_id})")
    
    def log_match_analysis_start(self, player1_name: str, player2_name: str, 
                                tournament: str, surface: str, event_id: int):
        """Log the start of individual match analysis"""
        if self._buffer_or_write('log_match_analysis_start', player1_name, player2_name, tournament, surface, event_id):
            return
        self.logger.info("")
        self.logger.info("🎾 " + "=" * 70)
        self.logger.info(f"MATCH ANALYSIS: {player1_name} vs {player2_name}")
        self.logger.info("🎾 " + "=" * 70)
        self.logger.info(f"Tournament: {tournament}")
        self.logger.info(f"Surface: {surface}")
        self.logger.info(f"Event ID: {event_id}")
        self.logger.info("")
    
    def log_player_profiles(self, player1_profile: Dict[str, Any], player2_profile: Dict[str, Any]):
        """Log detailed player profiles"""
        if self._buffer_or_write('log_player_profiles', player1_profile, player2_profile):
            return
        self.logger.info("👤 PLAYER PROFILES:")
        self.logger.info("-" * 40)
        
        for i, (name, profile) in enumerate([(player1_profile.get('name', 'Player 1'), player1_profile),
                                           (player2_profile.get('name', 'Player 2'), player2_profile)], 1):
            self.logger.info(f"Player {i}: {name}")
            self.logger.info(f"  Age: {profile.get('age', 'Unknown')}")
            self.logger.info(f"  Country: {profile.get('country', 'Unknown')}")
            self.logger.info(f"  ATP Ranking: {profile.get('atp_ranking', 'N/A')}")
            self.logger.info(f"  WTA Ranking: {profile.get('wta_ranking', 'N/A')}")
            self.logger.info(f"  Recent Form Score: {profile.get('recent_form_score', 0):.1f}")
            self.logger.info(f"  Surface Win Rate: {profile.get('surface_win_rate', 0):.1%}")
            self.logger.info(f"  Clutch Performance: {profile.get('clutch_performance', 0):.1%}")
            self.logger.info(f"  Momentum Score: {profile.get('momentum_score', 0):.2f}")
            self.logger.info(f"  Injury Status: {profile.get('injury_status', 'Unknown')}")
            self.logger.info("")
    
    def log_form_analysis(self, player1_name: str, player2_name: str, 
                         form1: Dict[str, Any], form2: Dict[str, Any]):
        """Log detailed form analysis"""
        if self._buffer_or_write('log_form_analysis', player1_name, player2_name, form1, form2):
            return
        self.logger.info("📊 RECENT FORM ANALYSIS:")
        self.logger.info("-" * 40)
        
        for name, form_data in [(player1_name, form1), (player2_name, form2)]:
            self.logger.info(f"{name}:")
            form = form_data.get('form_data', {})
            self.logger.info(f"  Set Win Rate (Recent 10): {form.get('set_win_rate', 0):.1%}")
            self.logger.info(f"  Sets Won vs Higher Ranked: {form.get('sets_vs_higher_ranked', form.get('sets_won_vs_higher_ranked', 0))}")
            self.logger.info(f"  Form Quality Score: {form.get('form_quality_score', 0):.1f}")
            self.logger.info(f"  Losses to Lower Ranked: {form.get('losses_to_lower_ranked', 0)}")
            if 'lower_ranked_penalty' in form:
                self.logger.info(f"  Lower Ranked Penalty: -{form.get('lower_ranked_penalty', 0):.1f}%")
            self.logger.info(f"  Recent Matches Analyzed: {form_data.get('matches_analyzed', form.get('total_matches', 0))}")
            self.logger.info("")
    
    def log_weight_calculations(self, weights: Dict[str, float], factor_scores: Dict[str, Any]):
        """Log detailed weight calculations and factor analysis"""
        if self._buffer_or_write('log_weight_calculations', weights, factor_scores):
            return
        self.logger.info("⚖️ WEIGHT CALCULATIONS:")
        self.logger.info("-" * 40)
        self.logger.info(f"Model weights configuration:")
        for factor, weight in weights.items():
            self.logger.info(f"  {factor}: {weight:.1%}")
        self.logger.info("")
        
        self.logger.info("Factor analysis breakdown:")
        for factor, analysis in factor_scores.items():
            self.logger.info(f"  {factor}: {analysis}")
        self.logger.info("")
    
    def log_enhanced_statistics(self, player1_name: str, player2_name: str,
                               tiebreak_stats: Dict[str, float],
                               pressure_stats: Dict[str, float], 
                               serve_stats: Dict[str, float]):
        """Log enhanced statistics analysis"""
        if self._buffer_or_write('log_enhanced_statistics', player1_name, player2_name, 
                                tiebreak_stats, pressure_stats, serve_stats):
            return
        
        self.logger.info("🏆 ENHANCED STATISTICS ANALYSIS:")
        self.logger.info("-" * 50)
        
        # Tiebreak Performance
        self.logger.info("🏆 Tiebreak Performance:")
        self.logger.info(f"  {player1_name}: {tiebreak_stats['player1']:.1%}")
        self.logger.info(f"  {player2_name}: {tiebreak_stats['player2']:.1%}")
        if abs(tiebreak_stats['player1'] - tiebreak_stats['player2']) > 0.1:
            advantage = player1_name if tiebreak_stats['player1'] > tiebreak_stats['player2'] else player2_name
            self.logger.info(f"  ✅ Advantage: {advantage}")
        self.logger.info("")
        
        # Pressure Performance
        self.logger.info("🔥 Pressure Performance (Break Points):")
        self.logger.info(f"  {player1_name}: {pressure_stats['player1']:.1%}")
        self.logger.info(f"  {player2_name}: {pressure_stats['player2']:.1%}")
        if abs(pressure_stats['player1'] - pressure_stats['player2']) > 0.1:
            advantage = player1_name if pressure_stats['player1'] > pressure_stats['player2'] else player2_name
            self.logger.info(f"  ✅ Advantage: {advantage}")
        self.logger.info("")
        
        # Serve Dominance
        self.logger.info("🎯 Serve Dominance:")
        self.logger.info(f"  {player1_name}: {serve_stats['player1']:.1%}")
        self.logger.info(f"  {player2_name}: {serve_stats['player2']:.1%}")
        if abs(serve_stats['player1'] - serve_stats['player2']) > 0.1:
            advantage = player1_name if serve_stats['player1'] > serve_stats['player2'] else player2_name
            self.logger.info(f"  ✅ Advantage: {advantage}")
        self.logger.info("")

    def log_key_factors(self, key_factors: List[str]):
        """Log key deciding factors"""
        if self._buffer_or_write('log_key_factors', key_factors):
            return
        self.logger.info("🔑 KEY DECIDING FACTORS:")
        self.logger.info("-" * 40)
        if key_factors:
            for i, factor in enumerate(key_factors, 1):
                self.logger.info(f"  {i}. {factor}")
        else:
            self.logger.info("  No significant factors identified")
        self.logger.info("")
    
    def log_prediction_result(self, predicted_winner: str, win_probability: float, 
                            confidence: str, reasoning: str):
        """Log final prediction result"""
        if self._buffer_or_write('log_prediction_result', predicted_winner, win_probability, confidence, reasoning):
            return
        self.logger.info("🎯 PREDICTION RESULT:")
        self.logger.info("-" * 40)
        self.logger.info(f"Predicted Winner: {predicted_winner}")
        self.logger.info(f"Win Probability: {win_probability:.1%}")
        self.logger.info(f"Confidence Level: {confidence}")
        self.logger.info(f"Reasoning: {reasoning}")
        self.logger.info("")
    
    def log_odds_provider_odds(self, player1_name: str, player2_name: str, 
                          odds_data: Dict[str, Any], has_set_market: bool):
        """Log OddsProvider odds and market availability"""
        if self._buffer_or_write('log_odds_provider_odds', player1_name, player2_name, odds_data, has_set_market):
            return
        self.logger.info("💰 ODDS_PROVIDER ODDS & MARKETS:")
        self.logger.info("-" * 40)
        self.logger.info(f"{player1_name} odds: {odds_data.get('player1_odds', 'N/A')}")
        self.logger.info(f"{player2_name} odds: {odds_data.get('player2_odds', 'N/A')}")
        self.logger.info(f"Has +1.5 sets market: {'Yes' if has_set_market else 'No'}")
        if has_set_market:
            self.logger.info(f"  Market locked: {odds_data.get('market_locked', 'Unknown')}")
        self.logger.info("")
    
    def log_betting_recommendation(self, recommendation: str, edge: float, 
                                  value_bet: bool, skip_reason: Optional[str] = None):
        """Log final betting recommendation"""
        if self._buffer_or_write('log_betting_recommendation', recommendation, edge, value_bet, skip_reason):
            return
        self.logger.info("💡 BETTING RECOMMENDATION:")
        self.logger.info("-" * 40)
        if skip_reason:
            self.logger.info(f"SKIP REASON: {skip_reason}")
        else:
            self.logger.info(f"Recommendation: {recommendation}")
            self.logger.info(f"Betting Edge: {edge:+.1%}")
            self.logger.info(f"Value Bet: {'Yes' if value_bet else 'No'}")
        self.logger.info("")
    
    def log_match_complete(self, match_data: MatchLoggingData):
        """Log match analysis completion and store detailed data"""
        if self._buffer_or_write('log_match_complete', match_data):
            return
        self.logger.info("✅ MATCH ANALYSIS COMPLETE")
        self.logger.info("=" * 70)
        self.logger.info("")
        
        # Store detailed match data for JSON export
        self.detailed_matches.append(asdict(match_data))
    
    def log_session_summary(self, total_matches: int, high_conf: int, 
                           medium_conf: int, low_conf: int, skipped: int):
        """Log session summary"""
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("PREDICTION SESSION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Total matches analyzed: {total_matches}")
        self.logger.info(f"High confidence predictions: {high_conf}")
        self.logger.info(f"Medium confidence predictions: {medium_conf}")
        self.logger.info(f"Low confidence predictions: {low_conf}")
        self.logger.info(f"Matches skipped: {skipped}")
        self.logger.info(f"Session completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 80)
    
    def save_detailed_json(self):
        """Save detailed match data to JSON file"""
        try:
            with open(self.detailed_log_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'session_info': {
                        'timestamp': datetime.now().isoformat(),
                        'total_matches': len(self.detailed_matches)
                    },
                    'matches': self.detailed_matches
                }, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Detailed analysis saved to: {self.detailed_log_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save detailed JSON: {e}")
    
    def close(self):
        """Close logger and save all data"""
        self.save_detailed_json()
        
        # Close handlers
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)
