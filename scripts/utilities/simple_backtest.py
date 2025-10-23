#!/usr/bin/env python3
"""
Simple Backtest - Uses Our Existing TennisBettingAnalyzer
Just import and use the functions we already have!
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time
from curl_cffi import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our existing analyzer
from betting_analysis_script import TennisBettingAnalyzer
from weight_config_manager import config_manager

class SimpleBacktest:
    """Simple backtest using our existing TennisBettingAnalyzer"""
    
    def __init__(self):
        self.session = requests.Session()
        
    def fetch_completed_matches(self, days_ago: int = 1) -> List[Dict]:
        """Fetch completed matches from days ago"""
        
        target_date = datetime.now() - timedelta(days=days_ago)
        date_str = target_date.strftime('%Y-%m-%d')
        
        print(f"📅 Fetching completed matches from {date_str}...")
        
        url = f"https://www.matchdata-api.example.com/api/v1/sport/tennis/scheduled-events/{date_str}"
        
        try:
            response = self.session.get(url, impersonate="chrome", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                
                completed_matches = []
                for event in events:
                    try:
                        # Only completed singles matches
                        status = event.get('status', {})
                        if status.get('type') != 'finished':
                            continue
                        
                        home_team = event.get('homeTeam', {})
                        away_team = event.get('awayTeam', {})
                        
                        if home_team.get('type', -1) != 1 or away_team.get('type', -1) != 1:
                            continue
                        
                        # Parse actual match result
                        match_result = self._parse_match_result(event)
                        
                        if match_result:
                            match_result['match_date'] = date_str
                            completed_matches.append(match_result)
                            
                            if len(completed_matches) >= 20:  # Test with 20 matches
                                break
                        
                    except Exception as e:
                        continue
                
                print(f"   ✅ Found {len(completed_matches)} completed matches")
                return completed_matches
                
            else:
                print(f"   ❌ HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []
    
    def _parse_match_result(self, event: Dict) -> Optional[Dict]:
        """Parse actual match result from event data"""
        
        try:
            home_team = event.get('homeTeam', {})
            away_team = event.get('awayTeam', {})
            home_score = event.get('homeScore', {})
            away_score = event.get('awayScore', {})
            
            if not home_score or not away_score:
                return None
            
            # Count actual sets won
            p1_sets = 0
            p2_sets = 0
            
            for period_num in range(1, 6):
                period_key = f'period{period_num}'
                
                p1_games = home_score.get(period_key)
                p2_games = away_score.get(period_key)
                
                if p1_games is None or p2_games is None:
                    break
                
                # Determine set winner
                tb_key = f'{period_key}TieBreak'
                p1_tb = home_score.get(tb_key, 0)
                p2_tb = away_score.get(tb_key, 0)
                
                if p1_tb > 0 or p2_tb > 0:
                    set_winner = 1 if p1_tb > p2_tb else 2
                else:
                    set_winner = 1 if p1_games > p2_games else 2
                
                if set_winner == 1:
                    p1_sets += 1
                else:
                    p2_sets += 1
            
            total_sets = p1_sets + p2_sets
            
            if total_sets < 2:  # Invalid match
                return None
            
            return {
                'event_id': event.get('id'),
                'player1_id': home_team.get('id'),
                'player2_id': away_team.get('id'),
                'player1_name': home_team.get('name', 'Unknown'),
                'player2_name': away_team.get('name', 'Unknown'),
                'surface': event.get('tournament', {}).get('uniqueTournament', {}).get('groundType', 'Hard'),
                'tournament': event.get('tournament', {}).get('name', 'Unknown'),
                
                # ACTUAL KNOWN RESULTS
                'actual_player1_sets': p1_sets,
                'actual_player2_sets': p2_sets,
                'actual_total_sets': total_sets,
                'actual_good_for_plus_sets': total_sets >= 3,  # This is what we want to predict
                
                # Who actually won
                'actual_winner': 1 if p1_sets > p2_sets else 2
            }
            
        except Exception as e:
            return None
    
    def test_weight_config(self, matches: List[Dict], weight_config_name: str) -> Dict[str, Any]:
        """Test a specific weight configuration using our existing analyzer"""
        
        print(f"\n🧪 TESTING WEIGHT CONFIG: {weight_config_name}")
        print("=" * 50)
        
        # Set the weight configuration
        original_active = config_manager.get_active_code_name()
        config_manager.set_active_config(weight_config_name)
        
        try:
            # Create our existing analyzer
            analyzer = TennisBettingAnalyzer()
            
            correct_predictions = 0
            total_predictions = 0
            detailed_results = []
            
            for i, match in enumerate(matches):
                print(f"\n   {i+1}. {match['player1_name']} vs {match['player2_name']}")
                print(f"      Actual: {match['actual_player1_sets']}-{match['actual_player2_sets']} sets")
                
                try:
                    # Create match data structure that our analyzer expects
                    match_data = {
                        'player1_id': match['player1_id'],
                        'player2_id': match['player2_id'],
                        'player1_name': match['player1_name'],
                        'player2_name': match['player2_name'],
                        'surface': match['surface'],
                        'tournament_name': match['tournament']
                    }
                    
                    # Use our existing analyzer to make prediction
                    player1_profile = analyzer.get_enhanced_player_profile(match['player1_id'], surface=match['surface'])
                    player2_profile = analyzer.get_enhanced_player_profile(match['player2_id'], surface=match['surface'])
                    
                    prediction = analyzer.calculate_weighted_prediction(player1_profile, player2_profile, match['surface'])
                    
                    # Determine if we predict 3+ sets
                    # Use the highest set probability as our confidence
                    p1_prob = prediction.player1_probability
                    p2_prob = prediction.player2_probability
                    
                    highest_prob = max(p1_prob, p2_prob)
                    predicted_plus_sets = highest_prob >= 0.55  # If confident, predict 3 sets
                    
                    actual_plus_sets = match['actual_good_for_plus_sets']
                    is_correct = predicted_plus_sets == actual_plus_sets
                    
                    if is_correct:
                        correct_predictions += 1
                    
                    total_predictions += 1
                    
                    status = "✅ CORRECT" if is_correct else "❌ WRONG"
                    print(f"      Predicted +1.5: {predicted_plus_sets} (confidence: {highest_prob:.1%}) - {status}")
                    
                    detailed_results.append({
                        'match_id': match['event_id'],
                        'players': f"{match['player1_name']} vs {match['player2_name']}",
                        'actual_sets': f"{match['actual_player1_sets']}-{match['actual_player2_sets']}",
                        'actual_plus_sets': actual_plus_sets,
                        'predicted_plus_sets': predicted_plus_sets,
                        'correct': is_correct,
                        'confidence': highest_prob,
                        'p1_prob': p1_prob,
                        'p2_prob': p2_prob
                    })
                    
                except Exception as e:
                    print(f"      ❌ Prediction failed: {e}")
                    total_predictions += 1
                    detailed_results.append({
                        'match_id': match['event_id'],
                        'players': f"{match['player1_name']} vs {match['player2_name']}",
                        'actual_sets': f"{match['actual_player1_sets']}-{match['actual_player2_sets']}",
                        'actual_plus_sets': match['actual_good_for_plus_sets'],
                        'predicted_plus_sets': False,
                        'correct': False,
                        'confidence': 0.0,
                        'error': str(e)
                    })
                
                time.sleep(1)  # Rate limiting
            
            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
            
            print(f"\n📊 RESULTS FOR {weight_config_name}:")
            print(f"   Correct predictions: {correct_predictions}/{total_predictions}")
            print(f"   Accuracy: {accuracy:.1%}")
            
            return {
                'config_name': weight_config_name,
                'accuracy': accuracy,
                'correct_predictions': correct_predictions,
                'total_predictions': total_predictions,
                'detailed_results': detailed_results
            }
            
        finally:
            # Restore original config
            if original_active:
                config_manager.set_active_config(original_active)
    
    def run_simple_backtest(self):
        """Run simple backtest using our existing analyzer"""
        
        print("🎾 SIMPLE BACKTEST")
        print("📊 Using Our Existing TennisBettingAnalyzer")
        print("🎯 Test completed matches against known results")
        print("=" * 60)
        
        # Fetch completed matches from yesterday
        completed_matches = self.fetch_completed_matches(days_ago=1)
        
        if len(completed_matches) < 5:
            print(f"⚠️ Only {len(completed_matches)} matches found. Need more for testing.")
            return
        
        print(f"\n📊 TESTING ON {len(completed_matches)} COMPLETED MATCHES")
        
        # Show dataset characteristics
        plus_sets_count = sum(1 for m in completed_matches if m['actual_good_for_plus_sets'])
        print(f"   Good for +1.5 sets: {plus_sets_count}/{len(completed_matches)} ({plus_sets_count/len(completed_matches):.1%})")
        
        # Test different weight configurations
        available_configs = list(config_manager.configs.get('configs', {}).keys()) if hasattr(config_manager, 'configs') else []
        
        print(f"\n🎯 AVAILABLE WEIGHT CONFIGURATIONS:")
        for config in available_configs:
            print(f"   - {config}")
        
        # Test all available configurations
        test_configs = available_configs  # Test ALL configs
        
        # If too many, prioritize the new ones
        if len(test_configs) > 8:
            priority_configs = ['CONSERVATIVE_V1', 'RANKING_DOMINANT_V1', 'FORM_SURFACE_V1', 'MINIMAL_V1', 'ANTI_CLUTCH_V1']
            test_configs = [c for c in priority_configs if c in available_configs]
        
        if not test_configs:
            print("⚠️ No test configurations found. Using default.")
            return
        
        results = []
        
        for config_name in test_configs:
            result = self.test_weight_config(completed_matches, config_name)
            if result:
                results.append(result)
        
        # Compare results
        if results:
            results.sort(key=lambda x: x['accuracy'], reverse=True)
            
            print(f"\n🏆 WEIGHT CONFIGURATION COMPARISON:")
            print("=" * 50)
            
            for i, result in enumerate(results, 1):
                status = "🎯" if result['accuracy'] >= 0.60 else "📊"
                print(f"{i}. {result['config_name']:<20}: {result['accuracy']:>6.1%} ({result['correct_predictions']}/{result['total_predictions']}) {status}")
            
            # Show best configuration
            best = results[0]
            print(f"\n🥇 BEST CONFIGURATION: {best['config_name']} ({best['accuracy']:.1%})")
            
            if best['accuracy'] >= 0.70:
                print(f"🎉 EXCELLENT! This configuration works great!")
            elif best['accuracy'] >= 0.60:
                print(f"👍 GOOD! This configuration is solid!")
            elif best['accuracy'] >= 0.50:
                print(f"📈 DECENT! Better than random!")
            else:
                print(f"📊 Need to improve weights!")
        
        # Save results
        with open('data/simple_backtest_results.json', 'w') as f:
            json.dump({
                'backtest_date': datetime.now().isoformat(),
                'method': 'existing_analyzer',
                'matches_tested': len(completed_matches),
                'results': results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to data/simple_backtest_results.json")
        
        return results

def main():
    """Run simple backtest"""
    
    print("🎾 SIMPLE TENNIS BACKTEST")
    print("📊 Using Our Existing TennisBettingAnalyzer")
    print("🎯 No reinventing the wheel!")
    print("📅 August 21st, 2025")
    print("=" * 60)
    
    backtester = SimpleBacktest()
    results = backtester.run_simple_backtest()
    
    if results and results[0]['accuracy'] >= 0.60:
        print(f"\n🎉 SUCCESS! Best accuracy: {results[0]['accuracy']:.1%}")
    else:
        print(f"\n💡 Need to tune weights for better accuracy!")

if __name__ == "__main__":
    main()
