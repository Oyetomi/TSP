#!/usr/bin/env python3
"""
Calculate accuracy from validation log CSV
"""

import csv
import sys

def calculate_accuracy(log_file):
    """Calculate win rate from validation log"""
    
    print(f"📊 Analyzing: {log_file}")
    print("=" * 80)
    
    with open(log_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Total rows: {len(rows)}")
    
    # Filter for finished matches with valid predictions
    finished = [r for r in rows if r['Match_Finished'] == 'True']
    print(f"Finished matches: {len(finished)}")
    
    # Count wins and losses (for +1.5 sets betting)
    wins = [r for r in finished if r['Prediction_Correct'] == 'True']
    losses = [r for r in finished if r['Prediction_Correct'] == 'False']
    
    total_bets = len(wins) + len(losses)
    
    if total_bets == 0:
        print("No valid bets found!")
        return
    
    win_rate = len(wins) / total_bets * 100
    
    print(f"\n{'='*80}")
    print(f"🎯 BETTING RESULTS (+1.5 SETS)")
    print(f"{'='*80}")
    print(f"✅ Wins: {len(wins)}")
    print(f"❌ Losses: {len(losses)}")
    print(f"📊 Total Bets: {total_bets}")
    print(f"🎯 Win Rate: {win_rate:.1f}%")
    print(f"{'='*80}")
    
    # Show some winning bets
    print(f"\n✅ Sample Winning Bets (first 10):")
    for i, r in enumerate(wins[:10], 1):
        print(f"   {i}. {r['Match']} - Bet on {r['Predicted_Winner']} +1.5 sets → {r['Actual_Sets']} (Won {r['Bet_Player_Sets']} sets)")
    
    # Show some losing bets
    print(f"\n❌ Sample Losing Bets (first 10):")
    for i, r in enumerate(losses[:10], 1):
        print(f"   {i}. {r['Match']} - Bet on {r['Predicted_Winner']} +1.5 sets → {r['Actual_Sets']} (Won {r['Bet_Player_Sets']} sets)")
    
    return win_rate

if __name__ == "__main__":
    log_file = "logs/validation_all_HOT_STREAK_74PCT_BACKUP_20250930_105100.csv"
    
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    
    calculate_accuracy(log_file)

