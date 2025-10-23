"""
Mental Toughness Logger - Tracks psychological resilience data for both players in each match
Clears log file on each main.py run for fresh analysis tracking
"""

import os
import datetime
from typing import Dict, Any, Optional
import threading


class MentalToughnessLogger:
    """Logger specifically for mental toughness analysis data"""
    
    def __init__(self, log_file: str = "logs/mental_toughness.log"):
        self.log_file = log_file
        self.lock = threading.Lock()
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Clear log file on initialization (fresh start each run)
        self.clear_log()
        
        # Write header
        self.write_header()
    
    def clear_log(self):
        """Clear the mental toughness log file for fresh start"""
        try:
            with open(self.log_file, 'w') as f:
                f.write("")  # Clear content
        except Exception as e:
            print(f"Warning: Could not clear mental toughness log: {e}")
    
    def write_header(self):
        """Write header information to log file"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"""
🧠 MENTAL TOUGHNESS ANALYSIS LOG
=====================================
Started: {timestamp}
Purpose: Track psychological resilience factors for tennis predictions
Data Source: Real tiebreak performance from MatchDataProvider API

Format:
- Tiebreak Win Rate: Player's historical performance in tiebreaks
- Mental Category: Extreme Fragility/Fragility/Average/Strength/Extreme Strength  
- Confidence Impact: How mental toughness affects prediction confidence
- Analysis: Detailed breakdown of mental factors

=====================================

"""
        self._write_to_file(header)
    
    def log_match_mental_analysis(self, 
                                 event_id: int,
                                 tournament_name: str,
                                 player1_name: str, 
                                 player1_id: int,
                                 player2_name: str, 
                                 player2_id: int,
                                 predicted_winner: str,
                                 player1_mental_data: Dict[str, Any],
                                 player2_mental_data: Dict[str, Any],
                                 final_adjustment: Dict[str, Any]):
        """Log complete mental toughness analysis for both players in a match"""
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        log_entry = f"""
[{timestamp}] 🎾 MATCH ANALYSIS - Event #{event_id}
{'='*60}
🏆 Tournament: {tournament_name}
👤 Players: {player1_name} vs {player2_name}
🎯 Predicted Winner: {predicted_winner}

🧠 PLAYER 1 - {player1_name} (ID: {player1_id})
   📊 Tiebreak Win Rate: {player1_mental_data.get('tiebreak_rate', 'N/A')}
   🏷️  Mental Category: {player1_mental_data.get('category', 'Unknown')}
   📈 Raw Analysis: {player1_mental_data.get('analysis', 'No data')}

🧠 PLAYER 2 - {player2_name} (ID: {player2_id})  
   📊 Tiebreak Win Rate: {player2_mental_data.get('tiebreak_rate', 'N/A')}
   🏷️  Mental Category: {player2_mental_data.get('category', 'Unknown')}
   📈 Raw Analysis: {player2_mental_data.get('analysis', 'No data')}

🎯 PREDICTION IMPACT:
   ✅ Applied: {final_adjustment.get('apply_adjustment', False)}
   📊 Confidence Change: {final_adjustment.get('confidence_adjustment', 0):+.0%}
   💭 Final Analysis: {final_adjustment.get('analysis', 'No adjustment')}

"""
        
        self._write_to_file(log_entry)
    
    def log_mental_error(self, event_id: int, player_name: str, error_msg: str):
        """Log mental toughness analysis errors"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        error_entry = f"[{timestamp}] ❌ ERROR - Event #{event_id}, Player: {player_name}, Error: {error_msg}\n"
        self._write_to_file(error_entry)
    
    def log_summary_stats(self, total_matches: int, successful_analyses: int, 
                         adjustments_applied: int):
        """Log session summary statistics"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        success_rate = (successful_analyses / total_matches * 100) if total_matches > 0 else 0
        adjustment_rate = (adjustments_applied / successful_analyses * 100) if successful_analyses > 0 else 0
        
        summary = f"""
[{timestamp}] 📊 SESSION SUMMARY
{'='*40}
🎾 Total Matches Analyzed: {total_matches}
✅ Successful Mental Analyses: {successful_analyses} ({success_rate:.1f}%)
🎯 Confidence Adjustments Applied: {adjustments_applied} ({adjustment_rate:.1f}%)

"""
        self._write_to_file(summary)
    
    def _write_to_file(self, content: str):
        """Thread-safe file writing"""
        with self.lock:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()  # Ensure immediate write
            except Exception as e:
                print(f"Warning: Could not write to mental toughness log: {e}")


# Global instance for easy access
mental_logger = None

def get_mental_logger() -> MentalToughnessLogger:
    """Get or create the global mental toughness logger instance"""
    global mental_logger
    if mental_logger is None:
        mental_logger = MentalToughnessLogger()
    return mental_logger


def clear_mental_log():
    """Clear mental toughness log - called at start of main.py"""
    global mental_logger
    mental_logger = MentalToughnessLogger()  # Creates fresh instance with cleared log
    return mental_logger
