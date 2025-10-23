#!/usr/bin/env python3
"""
Quick script to analyze game statistics from our first validation run
"""
import csv

def analyze_validation_results():
    """Analyze the validation results from the earlier HOT_STREAK_74PCT_BACKUP run"""
    
    # Data from the earlier validation run summary
    total_predictions = 458
    finished_matches = 332
    winning_bets = 262
    
    # From the detailed output, we can see patterns:
    # Most winning bets were either 2-0 straight sets or 2-1 three sets
    
    # Based on the output pattern, let's estimate game totals:
    # For 2-0 wins: typically around 12-14 games per match
    # For 2-1 wins: typically around 18-24 games per match
    
    print("🎾 TENNIS SET BETTING GAME ANALYSIS")
    print("="*50)
    print(f"📊 Total Predictions: {total_predictions}")
    print(f"🏁 Finished Matches: {finished_matches}")
    print(f"🎾 Set Betting Results: {winning_bets}/{finished_matches} = {(winning_bets/finished_matches*100):.1f}%")
    
    # From the sample of 50 predictions, we had:
    # 30 wins total, with 16 straight sets (53.3%) and 13 three sets (43.3%)
    
    # Extrapolating to full dataset:
    estimated_straight_sets = int(winning_bets * 0.533)  # 53.3%
    estimated_three_sets = int(winning_bets * 0.433)    # 43.3%
    estimated_other = winning_bets - estimated_straight_sets - estimated_three_sets
    
    print(f"\n📊 ESTIMATED SET SCORE BREAKDOWN:")
    print(f"   🎾 Total Wins (2-0 or 2-1): {estimated_straight_sets + estimated_three_sets}")
    print(f"      - Straight Sets (2-0): {estimated_straight_sets}")
    print(f"      - Three Sets (2-1): {estimated_three_sets}")
    print(f"      - Other (incomplete/walkover): {estimated_other}")
    
    # Estimate total games won based on typical tennis scores:
    # 2-0 straight sets: average ~13 games (6-4, 6-3, 7-5, etc.)
    # 2-1 three sets: average ~21 games (6-4, 4-6, 6-3, etc.)
    
    games_from_straight_sets = estimated_straight_sets * 13  # 13 games average per 2-0 win
    games_from_three_sets = estimated_three_sets * 21       # 21 games average per 2-1 win
    games_from_other = estimated_other * 8                  # 8 games average for incomplete
    
    total_games_won = games_from_straight_sets + games_from_three_sets + games_from_other
    avg_games_per_win = total_games_won / winning_bets if winning_bets > 0 else 0
    
    print(f"\n🎯 ESTIMATED TOTAL GAMES WON:")
    print(f"   📊 From Straight Sets (2-0): {games_from_straight_sets} games")
    print(f"   📊 From Three Sets (2-1): {games_from_three_sets} games") 
    print(f"   📊 From Other matches: {games_from_other} games")
    print(f"   🏆 TOTAL GAMES WON: {total_games_won} games")
    print(f"   📈 Average Games per Winning Bet: {avg_games_per_win:.1f} games")
    
    print(f"\n💰 PERFORMANCE SUMMARY:")
    print(f"   🎯 Win Rate: {(winning_bets/finished_matches*100):.1f}%")
    print(f"   🎾 Straight Sets: {(estimated_straight_sets/winning_bets*100):.1f}%")
    print(f"   ⚖️  Three Sets: {(estimated_three_sets/winning_bets*100):.1f}%")

if __name__ == "__main__":
    analyze_validation_results()
