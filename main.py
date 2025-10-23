#!/usr/bin/env python3
"""
Main Tennis Set Prediction System Runner

This script:
1. Runs the complete tennis set prediction analysis
2. Writes results to tennis_predictions.csv (overwrites each run)
3. Archives results to timestamped CSV for historical tracking
4. Can be run multiple times per day for fresh predictions
"""

import os
import sys
import csv
import shutil
from datetime import datetime
from typing import List, Dict, Any

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from betting_analysis_script import TennisBettingAnalyzer
from prediction_logger import PredictionLogger
from app.services.mental_toughness_logger import clear_mental_log

class TennisPredictionManager:
    """Manages tennis prediction execution and CSV file handling"""
    
    def __init__(self):
        self.current_csv = "tennis_predictions.csv"
        self.archive_dir = "prediction_archive"
        self.analyzer = None
        self.logger = None
        
        # Ensure archive directory exists
        os.makedirs(self.archive_dir, exist_ok=True)
        
    def initialize_analyzer(self) -> bool:
        """Initialize the betting analyzer and prediction logger"""
        try:
            print("🔧 Initializing Tennis Prediction System...")
            
            # Initialize prediction logger
            self.logger = PredictionLogger()
            print("✅ Prediction logger initialized")
            
            # Load odds provider credentials from api_secrets.py
            try:
                from api_secrets import ODDS_PROVIDER_CONFIG
                user_id = ODDS_PROVIDER_CONFIG.get('user_id')
                access_token = ODDS_PROVIDER_CONFIG.get('access_token')
            except ImportError:
                print("⚠️ api_secrets.py not found - odds provider features may not work")
                user_id = None
                access_token = None
            
            self.analyzer = TennisBettingAnalyzer(
                user_id=user_id,
                access_token=access_token,
                prediction_logger=self.logger  # Pass logger to analyzer
            )
            
            print("✅ Betting analyzer initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing analyzer: {e}")
            return False
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp for file naming"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def get_display_timestamp(self) -> str:
        """Get human-readable timestamp for display"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def clear_current_csv(self) -> None:
        """Clear the current predictions CSV file"""
        if os.path.exists(self.current_csv):
            try:
                os.remove(self.current_csv)
                print(f"🗑️ Cleared previous {self.current_csv}")
            except Exception as e:
                print(f"⚠️ Warning: Could not clear {self.current_csv}: {e}")
        else:
            print(f"📄 {self.current_csv} doesn't exist, starting fresh")
    
    def run_predictions(self, target_dates: List[str] = None) -> List[Dict[str, Any]]:
        """Run the tennis set predictions for the specified dates"""
        if not self.analyzer:
            print("❌ Analyzer not initialized")
            return []
        
        try:
            print(f"\n🎾 Running Tennis Set Predictions...")
            
            # Automatically get 3 days of matches if no dates provided
            if not target_dates:
                from datetime import datetime, timedelta
                today = datetime.now()
                tomorrow = today + timedelta(days=1)
                day_after = today + timedelta(days=2)
                target_dates = [
                    today.strftime('%Y-%m-%d'),
                    tomorrow.strftime('%Y-%m-%d'),
                    day_after.strftime('%Y-%m-%d')
                ]
                print(f"📅 Auto-analyzing 3 days: {target_dates[0]} (today), {target_dates[1]} (tomorrow) & {target_dates[2]} (day after)")
            else:
                print(f"📅 Target Dates: {', '.join(target_dates)}")
            
            # Log session start
            if self.logger:
                self.logger.log_session_start(target_dates)
            
            # Run analysis for all dates with incremental CSV writing
            all_results = []
            for i, target_date in enumerate(target_dates):
                print(f"\n🔍 Analyzing matches for {target_date}...")
                
                # First date creates new CSV, subsequent dates append
                append_mode = i > 0
                results = self.analyzer.analyze_scheduled_matches(target_date, self.current_csv, append_mode)
                
                if results:
                    all_results.extend(results)
                    print(f"   ✅ Found {len(results)} matches for {target_date}")
                else:
                    print(f"   ⚠️ No matches found for {target_date}")
            
            results = all_results
            
            if results:
                print(f"✅ Analysis completed: {len(results)} matches analyzed")
                
                # Display summary
                high_confidence = [r for r in results if r['confidence'] == 'High']
                medium_confidence = [r for r in results if r['confidence'] == 'Medium']
                low_confidence = [r for r in results if r['confidence'] == 'Low']
                
                print(f"📊 PREDICTION SUMMARY:")
                print(f"   🔥 High confidence: {len(high_confidence)} matches")
                print(f"   ⚡ Medium confidence: {len(medium_confidence)} matches") 
                print(f"   ⚠️ Low confidence: {len(low_confidence)} matches")
                
                # Log session summary
                if self.logger:
                    self.logger.log_session_summary(
                        total_matches=len(results),
                        high_conf=len(high_confidence),
                        medium_conf=len(medium_confidence),
                        low_conf=len(low_confidence),
                        skipped=0  # We don't track skipped matches yet
                    )
                
                return results
            else:
                print("❌ No matches found for analysis")
                
                # Log empty session
                if self.logger:
                    self.logger.log_session_summary(0, 0, 0, 0, 0)
                
                return []
                
        except Exception as e:
            print(f"❌ Error during prediction analysis: {e}")
            return []
    
    def write_current_csv(self, results: List[Dict[str, Any]]) -> bool:
        """Write results to current CSV file (overwrites existing)"""
        if not results:
            print("⚠️ No results to write to CSV")
            return False
        
        try:
            with open(self.current_csv, 'w', newline='', encoding='utf-8') as csvfile:
                # Add metadata header
                writer = csv.writer(csvfile)
                writer.writerow([f"# Tennis Set Predictions - Generated: {self.get_display_timestamp()}"])
                writer.writerow([f"# Auto-Analysis: Today + Tomorrow + Day After matches (3 days)"])
                writer.writerow([f"# Total Matches Analyzed: {len(results)}"])
                writer.writerow([f"# Focus: +1.5 Sets Betting with OddsProvider Integration"])
                writer.writerow([])  # Empty row for separation
                
                # Write actual data
                dict_writer = csv.DictWriter(csvfile, fieldnames=results[0].keys())
                dict_writer.writeheader()
                dict_writer.writerows(results)
            
            print(f"✅ Predictions written to {self.current_csv}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing current CSV: {e}")
            return False
    
    def create_archive_copy(self) -> bool:
        """Create timestamped archive copy of the current CSV"""
        if not os.path.exists(self.current_csv):
            print("⚠️ No current CSV to archive")
            return False
        
        try:
            timestamp = self.get_current_timestamp()
            archive_filename = f"tennis_predictions_{timestamp}.csv"
            archive_path = os.path.join(self.archive_dir, archive_filename)
            
            # Copy current CSV to archive
            shutil.copy2(self.current_csv, archive_path)
            
            print(f"📁 Archive created: {archive_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating archive: {e}")
            return False
    
    def display_high_confidence_predictions(self, results: List[Dict[str, Any]]) -> None:
        """Display high confidence predictions for quick review"""
        high_confidence = [r for r in results if r['confidence'] == 'High']
        
        if high_confidence:
            print(f"\n🔥 HIGH CONFIDENCE +1.5 SETS RECOMMENDATIONS:")
            print("=" * 60)
            
            for i, match in enumerate(high_confidence, 1):
                print(f"\n   {i}. 🎾 {match['player1_name']} vs {match['player2_name']}")
                print(f"      📍 {match['tournament']} ({match['surface']})")
                print(f"      🎯 RECOMMENDATION: {match['recommended_bet']}")
                print(f"      📈 Probability: {match['win_probability']:.1%}")
                print(f"      💰 Odds: {match.get('player1_odds', 'N/A')} / {match.get('player2_odds', 'N/A')}")
                print(f"      📊 Reasoning: {match['reasoning'][:100]}...")
        else:
            print(f"\n⚠️ No high confidence predictions found")
    
    def cleanup_old_archives(self, keep_days: int = 30) -> None:
        """Clean up archive files older than specified days"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            archive_files = []
            if os.path.exists(self.archive_dir):
                for filename in os.listdir(self.archive_dir):
                    if filename.startswith('tennis_predictions_') and filename.endswith('.csv'):
                        file_path = os.path.join(self.archive_dir, filename)
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_time < cutoff_date:
                            os.remove(file_path)
                            archive_files.append(filename)
            
            if archive_files:
                print(f"🗑️ Cleaned up {len(archive_files)} old archive files (>{keep_days} days)")
                
        except Exception as e:
            print(f"⚠️ Warning: Error during archive cleanup: {e}")

def main():
    """Main execution function"""
    print("🎾 TENNIS SET PREDICTION SYSTEM")
    print("=" * 50)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target: +1.5 Sets Betting Analysis")
    print(f"📊 Features: Comprehensive match analysis with detailed debug output")
    print(f"🔍 Debug Mode: ENABLED - Full data visibility")
    print()
    
    # Clear mental toughness log for fresh analysis tracking
    print("🧠 Initializing mental toughness logging system...")
    mental_logger = clear_mental_log()
    print("✅ Mental toughness log cleared and ready")
    print()
    
    # Initialize prediction manager
    manager = TennisPredictionManager()
    
    # Initialize the analyzer
    if not manager.initialize_analyzer():
        print("❌ Failed to initialize analyzer. Exiting.")
        return
    
    # Clear current CSV for fresh start
    print(f"\n🔄 Preparing CSV files...")
    manager.clear_current_csv()
    
    # Run predictions (automatically for today + tomorrow)
    results = manager.run_predictions()
    
    if results:
        # Write to current CSV
        if manager.write_current_csv(results):
            # Create timestamped archive
            manager.create_archive_copy()
            
            # Display high confidence predictions
            manager.display_high_confidence_predictions(results)
            
            # Cleanup old archives
            manager.cleanup_old_archives(keep_days=30)
            
            print(f"\n✅ PREDICTION RUN COMPLETED SUCCESSFULLY")
            print(f"📄 Current predictions: {manager.current_csv}")
            print(f"📁 Archive directory: {manager.archive_dir}")
            print(f"🕒 Completed at: {manager.get_display_timestamp()}")
            
            # Final summary
            total_matches = len(results)
            high_conf = len([r for r in results if r['confidence'] == 'High'])
            medium_conf = len([r for r in results if r['confidence'] == 'Medium'])
            
            print(f"\n📊 FINAL SUMMARY:")
            print(f"   Total matches analyzed: {total_matches}")
            print(f"   High confidence bets: {high_conf}")
            print(f"   Medium confidence bets: {medium_conf}")
            print(f"   Ready for betting decisions!")
            
        else:
            print("❌ Failed to write predictions to CSV")
    else:
        print("❌ No predictions generated")
    
    # Close logger and save detailed logs
    if manager.logger:
        manager.logger.close()
        print(f"📄 Detailed logs saved to logs/ directory")
    
    # Close skip logger and save summary
    if manager.analyzer and manager.analyzer.skip_logger:
        manager.analyzer.skip_logger.close()
        print(f"📄 Skip analysis saved to logs/skipped_matches.log")
    
    print(f"\n💡 TIP: System automatically analyzes today + tomorrow matches")
    print(f"💡 TIP: Run multiple times per day for fresh market analysis")
    print(f"💡 TIP: Each run creates timestamped archive in prediction_archive/")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑  Interrupted by user – exiting cleanly.")
