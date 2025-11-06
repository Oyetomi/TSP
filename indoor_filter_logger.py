"""
Indoor Filter Logger - Dedicated logging for medium-confidence indoor hardcourt filter
"""

import os
from datetime import datetime
from typing import Dict


class IndoorFilterLogger:
    """Logger for tracking medium-confidence indoor hardcourt filter activity"""
    
    def __init__(self, log_file: str = "logs/indoor_filter.log"):
        self.log_file = log_file
        self._ensure_log_dir()
        self._initialize_log()
        
    def _ensure_log_dir(self):
        """Create logs directory if it doesn't exist"""
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def _initialize_log(self):
        """Clear log file and write header on startup"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("MEDIUM-CONFIDENCE INDOOR HARDCOURT FILTER LOG\n")
            f.write("="*100 + "\n")
            f.write(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*100 + "\n\n")
    
    def log_filter_check(
        self,
        match: str,
        tournament: str,
        surface: str,
        confidence: float,
        utr_gap: float,
        result: Dict
    ):
        """
        Log a filter check result
        
        Args:
            match: Match description (e.g., "Player A vs Player B")
            tournament: Tournament name
            surface: Surface type
            confidence: Confidence level (0-1)
            utr_gap: UTR gap between players
            result: Filter result dictionary from check_medium_confidence_indoor()
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{timestamp}\n")
            f.write("-"*100 + "\n")
            
            if result['should_downgrade']:
                f.write(f"🚨 FILTER TRIGGERED\n")
            else:
                f.write(f"✅ FILTER PASSED\n")
            
            f.write("-"*100 + "\n")
            f.write(f"🎾 MATCH: {match}\n")
            f.write(f"📍 TOURNAMENT: {tournament}\n")
            f.write(f"🏟️  SURFACE: {surface}\n")
            f.write(f"\n")
            
            f.write(f"📊 FILTER INPUT:\n")
            f.write(f"   Original Confidence: {result['original_confidence']:.1%}\n")
            f.write(f"   UTR Gap: {utr_gap:.2f}\n")
            f.write(f"\n")
            
            f.write(f"🎯 FILTER RESULT:\n")
            f.write(f"   Reason: {result['reason']}\n")
            f.write(f"   Severity: {result['severity'].upper()}\n")
            
            if result['should_downgrade']:
                f.write(f"   Adjusted Confidence: {result['adjusted_confidence']:.1%}\n")
                f.write(f"   Confidence Change: {result['adjusted_confidence'] - result['original_confidence']:.1%}\n")
                f.write(f"\n")
                f.write(f"📝 DETAILS:\n")
                f.write(f"   {result['details']}\n")
                
                # Determine action
                if result['adjusted_confidence'] < 0.50:
                    f.write(f"\n")
                    f.write(f"❌ ACTION: BET SKIPPED (confidence < 50%)\n")
                else:
                    f.write(f"\n")
                    f.write(f"⚠️  ACTION: BET DOWNGRADED (confidence reduced but still above 50%)\n")
            else:
                f.write(f"   No adjustments needed\n")
                if result['details']:
                    f.write(f"\n")
                    f.write(f"📝 DETAILS:\n")
                    f.write(f"   {result['details']}\n")
            
            f.write(f"\n")
            f.write("-"*100 + "\n")
    
    def log_summary(self, filter_stats: Dict):
        """
        Log session summary statistics
        
        Args:
            filter_stats: Statistics dictionary from filter.get_stats()
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n\n")
            f.write("="*100 + "\n")
            f.write(f"SESSION SUMMARY - {timestamp}\n")
            f.write("="*100 + "\n\n")
            
            f.write(f"📊 FILTER STATISTICS:\n")
            f.write(f"   Total Checked: {filter_stats['total_checked']}\n")
            f.write(f"   Total Downgraded: {filter_stats['total_downgraded']}\n")
            
            if filter_stats['total_checked'] > 0:
                downgrade_rate = filter_stats['total_downgraded'] / filter_stats['total_checked'] * 100
                f.write(f"   Downgrade Rate: {downgrade_rate:.1f}%\n")
            
            f.write(f"\n")
            f.write(f"🎯 BREAKDOWN BY REASON:\n")
            f.write(f"   Close UTR Downgrades: {filter_stats['close_utr_downgrades']}\n")
            f.write(f"   Low Clutch Downgrades: {filter_stats['low_clutch_downgrades']}\n")
            
            f.write(f"\n")
            f.write("="*100 + "\n")


# Example usage
if __name__ == "__main__":
    logger = IndoorFilterLogger()
    
    # Example filter check
    result = {
        'should_downgrade': True,
        'reason': 'CLOSE_UTR_INDOOR',
        'severity': 'severe',
        'original_confidence': 0.58,
        'adjusted_confidence': 0.35,
        'details': 'UTR gap 0.15 < 0.20 on Hardcourt indoor. Fast surface + close skill = coin flip.'
    }
    
    logger.log_filter_check(
        match="Test Player vs Opponent",
        tournament="Test Tournament",
        surface="Hardcourt indoor",
        confidence=0.58,
        utr_gap=0.15,
        result=result
    )
    
    print("✅ Log file created successfully")
    print(f"📄 Location: {logger.log_file}")

