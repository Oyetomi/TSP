"""
Skip Logger for Tennis Prediction System

Logs all skipped matches with detailed reasoning, player stats, and tier classification.
Helps understand which matches are being filtered out and why.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any


class SkipLogger:
    """Handles logging of all skipped matches with detailed context"""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize skip logger with automatic file clearing"""
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Create skip log file (clear existing on startup)
        self.log_file = os.path.join(log_dir, "skipped_matches.log")
        
        # Clear the log file on initialization
        with open(self.log_file, 'w') as f:
            f.write(f"{'='*100}\n")
            f.write(f"TENNIS PREDICTION SYSTEM - SKIPPED MATCHES LOG\n")
            f.write(f"{'='*100}\n")
            f.write(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*100}\n\n")
        
        # Setup logger
        self.logger = logging.getLogger('skip_logger')
        self.logger.setLevel(logging.INFO)
        self.logger.handlers = []  # Clear existing handlers
        
        # File handler
        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.INFO)
        
        # Formatter with timestamp
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.propagate = False  # Don't propagate to root logger
        
        self.skip_count = 0
        self.tier_counts = {
            'TIER_0': 0,  # Insufficient data
            'TIER_1': 0,  # Zero current-year data
            'TIER_2': 0,  # Poor performance
            'TIER_3': 0,  # Verification failure
            'DATA_QUALITY': 0,  # Existing data quality issues
            'CIRCUIT_BREAKER': 0,  # Crowd disagreement
            'OTHER': 0
        }
    
    def log_skip(
        self,
        reason_type: str,
        player1_name: str,
        player2_name: str,
        tournament: str,
        surface: str,
        reason: str,
        player1_stats: Optional[Dict[str, Any]] = None,
        player2_stats: Optional[Dict[str, Any]] = None,
        additional_context: Optional[str] = None
    ):
        """
        Log a skipped match with full details
        
        Args:
            reason_type: TIER_0, TIER_1, TIER_2, TIER_3, DATA_QUALITY, CIRCUIT_BREAKER, OTHER
            player1_name: Name of player 1
            player2_name: Name of player 2
            tournament: Tournament name
            surface: Surface type
            reason: Skip reason text
            player1_stats: Dict with current year stats (matches, wins, win_rate, etc.)
            player2_stats: Dict with current year stats
            additional_context: Any additional context to log
        """
        self.skip_count += 1
        self.tier_counts[reason_type] = self.tier_counts.get(reason_type, 0) + 1
        
        # Build log entry
        separator = "-" * 100
        self.logger.info(f"\n{separator}")
        self.logger.info(f"SKIP #{self.skip_count:03d} - {reason_type}")
        self.logger.info(separator)
        
        # Match info
        self.logger.info(f"🎾 MATCH: {player1_name} vs {player2_name}")
        self.logger.info(f"📍 TOURNAMENT: {tournament}")
        self.logger.info(f"🏟️  SURFACE: {surface}")
        self.logger.info("")
        
        # Skip reason
        self.logger.info(f"❌ SKIP REASON:")
        self.logger.info(f"   {reason}")
        self.logger.info("")
        
        # Player 1 stats
        if player1_stats:
            self.logger.info(f"📊 {player1_name} STATS:")
            self._log_player_stats(player1_stats)
        
        # Player 2 stats
        if player2_stats:
            self.logger.info(f"📊 {player2_name} STATS:")
            self._log_player_stats(player2_stats)
        
        # Additional context
        if additional_context:
            self.logger.info(f"ℹ️  ADDITIONAL CONTEXT:")
            self.logger.info(f"   {additional_context}")
            self.logger.info("")
        
        self.logger.info(separator)
        self.logger.info("")  # Extra newline for readability
    
    def _log_player_stats(self, stats: Dict[str, Any]):
        """Helper to format and log player stats"""
        current_year = stats.get('current_year', 2025)
        
        # Current year stats
        if 'current_year_matches' in stats:
            matches = stats.get('current_year_matches', 0)
            wins = stats.get('current_year_wins', 0)
            win_rate = stats.get('current_year_win_rate', 0.0)
            
            self.logger.info(f"   🎯 {current_year} Performance: {wins}/{matches} ({win_rate:.1%})")
        
        # Blended stats (if different)
        if 'blended_matches' in stats:
            blended_matches = stats.get('blended_matches', 0)
            blended_wins = stats.get('blended_wins', 0)
            blended_win_rate = stats.get('blended_win_rate', 0.0)
            
            self.logger.info(f"   📊 Blended (2024+2025): {blended_wins:.1f}/{blended_matches:.1f} ({blended_win_rate:.1%})")
        
        # Form score
        if 'form_score' in stats:
            self.logger.info(f"   📈 Form Score: {stats['form_score']:.1f}/100")
        
        # Ranking
        if 'ranking' in stats:
            self.logger.info(f"   🏆 Ranking: #{stats['ranking']}")
        
        # UTR
        if 'utr' in stats:
            self.logger.info(f"   ⭐ UTR: {stats['utr']:.2f}")
        
        # Additional stats
        if 'aces_per_match' in stats:
            self.logger.info(f"   🎯 Aces/match: {stats['aces_per_match']:.1f}")
        
        if 'tiebreak_rate' in stats:
            self.logger.info(f"   🔥 Tiebreak Win: {stats['tiebreak_rate']:.1%}")
        
        if 'break_point_conversion' in stats:
            self.logger.info(f"   💪 Break Point Conv: {stats['break_point_conversion']:.1%}")
        
        self.logger.info("")
    
    def log_summary(self):
        """Log summary statistics at the end of the session"""
        separator = "=" * 100
        self.logger.info(f"\n{separator}")
        self.logger.info(f"SESSION SUMMARY - SKIPPED MATCHES")
        self.logger.info(separator)
        self.logger.info(f"📊 Total Skipped: {self.skip_count}")
        self.logger.info("")
        self.logger.info("📈 Breakdown by Reason:")
        
        for tier, count in sorted(self.tier_counts.items()):
            if count > 0:
                percentage = (count / self.skip_count * 100) if self.skip_count > 0 else 0
                self.logger.info(f"   {tier:20s}: {count:3d} ({percentage:5.1f}%)")
        
        self.logger.info(separator)
        self.logger.info(f"Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(separator)
    
    def close(self):
        """Close logger and write summary"""
        self.log_summary()
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)

