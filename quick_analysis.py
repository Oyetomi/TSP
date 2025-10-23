#!/usr/bin/env python3

import asyncio
import sys
from scripts.validate_tennis_predictions import TennisPredictionValidator

async def quick_analysis():
    """Quick analysis of a few matches to test game statistics"""
    
    print("🎾 Quick Tennis Analysis")
    print("="*30)
    
    async with TennisPredictionValidator() as validator:
        predictions = validator.load_predictions('all_HOT_STREAK_74PCT_BACKUP.csv')
        
        if not predictions:
            print("❌ No predictions found")
            return
            
        # Test on first 20 predictions
        print(f"Testing on first 20 predictions...")
        results = await validator.validate_all(predictions[:20], batch_size=2)
        
        # Quick summary
        finished = [r for r in results if r.get("finished")]
        wins = [r for r in finished if r.get("set_bet_correct")]
        
        total_games = 0
        games_data_count = 0
        
        for win in wins:
            games = win.get('bet_player_games', 0)
            if games > 0:
                total_games += games
                games_data_count += 1
                print(f"✅ {win['bet_on']} won {win['bet_player_sets']} sets, {games} games")
        
        print(f"\n📊 QUICK SUMMARY:")
        print(f"   🎾 Wins: {len(wins)}/{len(finished)}")
        print(f"   🎯 Total Games Won: {total_games} games")
        print(f"   📊 Avg Games per Win: {total_games/games_data_count:.1f}" if games_data_count > 0 else "   📊 No game data available")

if __name__ == "__main__":
    asyncio.run(quick_analysis())

