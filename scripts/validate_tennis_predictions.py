#!/usr/bin/env python3
"""
Tennis Prediction Validation Script
===================================

Validates tennis predictions against actual match results using MatchDataProvider API.
Checks +1.5 sets betting performance and provides detailed win/loss analysis.
"""

import os
import sys
import csv
import time
import asyncio
from curl_cffi import requests
from curl_cffi.requests import AsyncSession
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Add parent directory to path to import api_secrets
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from api_secrets import PRIMARY_DATA_CONFIG
except ImportError:
    print("⚠️  Warning: api_secrets.py not found. Using placeholder config.")
    PRIMARY_DATA_CONFIG = {
        'base_url': 'https://www.example.com',
        'headers': {},
        'cookies': {}
    }

class TennisPredictionValidator:
    def __init__(self):
        self.results = []
        self.session = None
        self.base_url = PRIMARY_DATA_CONFIG.get('base_url', 'https://www.example.com')
        self.headers = PRIMARY_DATA_CONFIG.get('headers', {})
        self.cookies = PRIMARY_DATA_CONFIG.get('cookies', {})
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = AsyncSession(
            headers=self.headers,
            cookies=self.cookies,
            impersonate="chrome120",
            timeout=30
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        
    def load_predictions(self, file_path: str) -> List[Dict]:
        """Load predictions from CSV, skipping comment lines"""
        predictions = []
        seen_matches = set()
        duplicates_removed = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Skip comment lines that start with # and empty lines
                lines = [line for line in f if not line.strip().startswith('#') and line.strip()]
                
            # Parse the cleaned lines
            if not lines:
                print("❌ No data lines found after skipping comments")
                return []
                
            # Create CSV reader from cleaned lines
            reader = csv.DictReader(lines)
            for row in reader:
                # Create match key from player names
                if 'player1_name' in row and 'player2_name' in row:
                    match_key = f"{row['player1_name']} vs {row['player2_name']}"
                    row['Match'] = match_key  # Add for compatibility
                    row['Date'] = row.get('date', '')  # Add for compatibility
                    
                    if match_key not in seen_matches:
                        predictions.append(row)
                        seen_matches.add(match_key)
                    else:
                        duplicates_removed += 1
                        
            print(f"📊 Loaded {len(predictions)} unique predictions")
            if duplicates_removed > 0:
                print(f"🗑️  Removed {duplicates_removed} duplicate matches")
            return predictions
        except Exception as e:
            print(f"❌ Error loading predictions: {e}")
            return []
    
    async def get_tennis_matches_for_date(self, date_str: str) -> List[Dict]:
        """Get tennis matches for a specific date using MatchDataProvider API"""
        try:
            url = f"{self.base_url}/sport/tennis/scheduled-events/{date_str}"
            
            response = await self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                matches = []
                
                for event in data.get('events', []):
                    matches.append({
                        'id': event.get('id'),
                        'homeTeam': event.get('homeTeam', {}),
                        'awayTeam': event.get('awayTeam', {}),
                        'status': event.get('status', {}),
                        'tournament': event.get('tournament', {})
                    })
                
                print(f"Found {len(matches)} matches for {date_str}")
                return matches
            else:
                print(f"❌ Failed to fetch matches for {date_str}: {response.status_code}")
                return []
                        
        except Exception as e:
            print(f"❌ Error fetching matches for {date_str}: {e}")
            return []
    
    async def find_event_id(self, prediction: Dict) -> Optional[Dict]:
        """Find event ID and player mapping for a match"""
        try:
            print(f"   🔍 Finding event ID...")
            
            # Get matches for the prediction date
            matches = await self.get_tennis_matches_for_date(prediction['Date'])
            
            if not matches:
                print(f"   ❌ No matches found for {prediction['Date']}")
                return None
                
            # Parse match name
            match_parts = prediction['Match'].split(' vs ')
            if len(match_parts) != 2:
                return None
                
            p1_name, p2_name = match_parts[0].strip(), match_parts[1].strip()
            
            # Search for matching event with fuzzy name matching
            for match in matches:
                try:
                    home_name = match.get('homeTeam', {}).get('name', '')
                    away_name = match.get('awayTeam', {}).get('name', '')
                    
                    # Improved fuzzy matching
                    def name_similarity(name1: str, name2: str) -> float:
                        name1_lower = name1.lower().strip()
                        name2_lower = name2.lower().strip()
                        
                        # Exact match
                        if name1_lower == name2_lower:
                            return 1.0
                        
                        # Contains match
                        if name1_lower in name2_lower or name2_lower in name1_lower:
                            return 0.8
                        
                        # Last name match (common for tennis)
                        name1_parts = name1_lower.split()
                        name2_parts = name2_lower.split()
                        if len(name1_parts) > 1 and len(name2_parts) > 1:
                            if name1_parts[-1] == name2_parts[-1]:  # Last names match
                                return 0.7
                        
                        return 0.0
                    
                    # Check all possible mappings
                    p1_home_sim = name_similarity(p1_name, home_name)
                    p1_away_sim = name_similarity(p1_name, away_name)
                    p2_home_sim = name_similarity(p2_name, home_name)
                    p2_away_sim = name_similarity(p2_name, away_name)
                    
                    # P1 is home, P2 is away
                    if p1_home_sim >= 0.7 and p2_away_sim >= 0.7:
                        event_id = match.get('id')
                        if event_id:
                            print(f"   ✅ Found event ID: {event_id}")
                            print(f"   🏠 Player mapping: {p1_name} = home, {p2_name} = away")
                            
                            return {
                                'event_id': event_id,
                                'p1_is_home': True,
                                'p2_is_home': False,
                                'home_name': home_name,
                                'away_name': away_name,
                                'match_info': match
                            }
                    
                    # P1 is away, P2 is home
                    elif p1_away_sim >= 0.7 and p2_home_sim >= 0.7:
                        event_id = match.get('id')
                        if event_id:
                            print(f"   ✅ Found event ID: {event_id}")
                            print(f"   🏠 Player mapping: {p1_name} = away, {p2_name} = home")
                            
                            return {
                                'event_id': event_id,
                                'p1_is_home': False,
                                'p2_is_home': True,
                                'home_name': home_name,
                                'away_name': away_name,
                                'match_info': match
                            }
                            
                except Exception as e:
                    continue
                    
            print(f"   ❌ No matching event found")
            return None
            
        except Exception as e:
            print(f"   ❌ Error finding event: {e}")
            return None
    
    async def get_match_result(self, event_id: int) -> Optional[Dict]:
        """Get match result using MatchDataProvider API"""
        try:
            print(f"   📊 Fetching results for event {event_id}...")
            
            # Use the existing MatchDataProvider integration from the player service
            url = f"{self.base_url}/event/{event_id}"
            
            response = await self.session.get(url)
            
            if response.status_code == 200:
                event_data = response.json()
                event = event_data.get('event', {})
                
                # Check if match is finished
                status = event.get('status', {})
                status_type = status.get('type', '')
                
                if status_type != 'finished':
                    print(f"   ⏳ Match not finished (status: {status_type})")
                    return {"finished": False, "status": status_type}
                
                # Get set scores
                home_score = event.get('homeScore', {})
                away_score = event.get('awayScore', {})
                
                home_sets = home_score.get('display', 0)
                away_sets = away_score.get('display', 0)
                
                # Try to get detailed game scores if available
                home_games = 0
                away_games = 0
                
                # Look for period scores (set-by-set games)
                home_periods = home_score.get('periods', [])
                away_periods = away_score.get('periods', [])
                
                if home_periods and away_periods and len(home_periods) == len(away_periods):
                    for i in range(len(home_periods)):
                        home_games += int(home_periods[i]) if isinstance(home_periods[i], (int, str)) and str(home_periods[i]).isdigit() else 0
                        away_games += int(away_periods[i]) if isinstance(away_periods[i], (int, str)) and str(away_periods[i]).isdigit() else 0
                
                # Handle string scores (sometimes MatchDataProvider returns them as strings)
                if isinstance(home_sets, str):
                    home_sets = int(home_sets) if home_sets.isdigit() else 0
                if isinstance(away_sets, str):
                    away_sets = int(away_sets) if away_sets.isdigit() else 0
                
                total_sets = home_sets + away_sets
                
                if total_sets == 0:
                    print(f"   ⏳ No sets played yet")
                    return {"finished": False}
                
                if home_games > 0 or away_games > 0:
                    print(f"   ✅ FINAL Result: {home_sets}-{away_sets} sets ({home_games}-{away_games} games)")
                else:
                    print(f"   ✅ FINAL Result: {home_sets}-{away_sets} sets")
                
                return {
                    "finished": True,
                    "home_sets": home_sets,
                    "away_sets": away_sets,
                    "home_games": home_games,
                    "away_games": away_games,
                    "winner": "home" if home_sets > away_sets else "away",
                    "status": status
                }
            else:
                print(f"   ❌ Failed to fetch result: {response.status_code}")
                return None
                        
        except Exception as e:
            print(f"   ❌ Error fetching result: {e}")
            return None
    
    async def validate_prediction(self, prediction: Dict) -> Dict:
        """Validate a single prediction"""
        result = {
            "match": prediction['Match'],
            "date": prediction['Date'],
            "finished": False,
            "prediction_correct": None,
            "set_bet_correct": None,
            "voided": False,
            "error": None
        }
        
        try:
            # Check betting recommendation first
            betting_rec = prediction.get('recommended_bet', prediction.get('Betting Recommendation', ''))
            
            # Skip matches that are flagged to skip
            if 'SKIP' in betting_rec.upper() or 'NO BET' in betting_rec.upper():
                result["error"] = f"Skipped per recommendation: {betting_rec}"
                print(f"   🚫 SKIPPED: {betting_rec}")
                return result
            
            # Find event and player mapping
            event_info = await self.find_event_id(prediction)
            if not event_info:
                result["error"] = "Event not found"
                return result
            
            event_id = event_info['event_id']
            p1_is_home = event_info['p1_is_home']
            p2_is_home = event_info['p2_is_home']
            
            # Get result
            match_result = await self.get_match_result(event_id)
            if not match_result:
                result["error"] = "Result not available"
                return result
            
            if not match_result.get("finished"):
                result["error"] = "Match not finished"
                return result
            
            result["finished"] = True
            
            # Analyze set betting (our strategy) - use actual column names
            p1_prob = float(prediction.get('player1_set_probability', '0'))
            p2_prob = float(prediction.get('player2_set_probability', '0'))
            
            # Convert to percentages if needed (they appear to be decimals 0-1)
            if p1_prob <= 1.0:
                p1_prob *= 100
            if p2_prob <= 1.0:
                p2_prob *= 100
            
            # Parse match to get player names
            match_parts = prediction['Match'].split(' vs ')
            p1_name, p2_name = match_parts[0].strip(), match_parts[1].strip()
            
            # Who did we bet on? (highest probability)
            if p1_prob > p2_prob:
                bet_player = p1_name
                bet_prob = p1_prob
                bet_player_is_home = p1_is_home
                print(f"   💰 We bet on {p1_name} ≥1 set ({p1_prob:.1f}% vs {p2_name} {p2_prob:.1f}%)")
            else:
                bet_player = p2_name  
                bet_prob = p2_prob
                bet_player_is_home = p2_is_home
                print(f"   💰 We bet on {p2_name} ≥1 set ({p2_prob:.1f}% vs {p1_name} {p1_prob:.1f}%)")
            
            # Get the actual result
            home_sets = match_result["home_sets"] 
            away_sets = match_result["away_sets"]
            home_games = match_result.get("home_games", 0)
            away_games = match_result.get("away_games", 0)
            winner = match_result.get("winner", "")
            
            print(f"   📊 MatchDataProvider result: home {home_sets} - {away_sets} away")
            if home_games > 0 or away_games > 0:
                print(f"   📊 Game score: home {home_games} - {away_games} away")
            print(f"   🏆 Match winner: {winner}")
            
            # Check if match was retired (1-0 or 0-1)
            total_sets = home_sets + away_sets
            is_voided = total_sets == 1
            
            if is_voided:
                print(f"   🚫 BET VOIDED - Match retired/walkover ({home_sets}-{away_sets})")
                result["set_bet_correct"] = None
                result["voided"] = True
                result["bet_on"] = bet_player
                result["bet_prob"] = bet_prob
                result["actual_sets"] = f"{home_sets}-{away_sets}"
                result["actual_games"] = f"{home_games}-{away_games}" if home_games > 0 or away_games > 0 else ""
                result["bet_player_sets"] = None
                result["bet_player_games"] = None
                return result
            
            # Determine if our bet player won at least 1 set
            if bet_player_is_home:
                bet_player_sets = home_sets
                bet_player_games = home_games
                print(f"   🎯 {bet_player} (home) won {home_sets} sets")
            else:
                bet_player_sets = away_sets
                bet_player_games = away_games
                print(f"   🎯 {bet_player} (away) won {away_sets} sets")
            
            # Check if bet won (≥1 set)
            bet_won = bet_player_sets > 0
            
            if bet_won:
                print(f"   ✅ BET WINS! {bet_player} won {bet_player_sets} sets")
            else:
                print(f"   ❌ BET LOSES! {bet_player} won {bet_player_sets} sets")
            
            result["set_bet_correct"] = bet_won
            result["voided"] = False
            result["bet_on"] = bet_player
            result["bet_prob"] = bet_prob
            result["actual_sets"] = f"{home_sets}-{away_sets}"
            result["actual_games"] = f"{home_games}-{away_games}" if home_games > 0 or away_games > 0 else ""
            result["bet_player_sets"] = bet_player_sets
            result["bet_player_games"] = bet_player_games
            
            # Validate Over 2.5 Sets prediction if available
            over_2_5_prob_str = prediction.get('over_2_5_sets_probability', '')
            if over_2_5_prob_str:
                try:
                    over_2_5_prob = float(over_2_5_prob_str)
                    # Convert to percentage if needed
                    if over_2_5_prob <= 1.0:
                        over_2_5_prob *= 100
                    
                    # Determine if match went Over 2.5 sets (3+ sets)
                    total_sets_played = home_sets + away_sets
                    went_over_2_5 = total_sets_played >= 3
                    
                    # Determine recommended bet (≥60% = Over, ≤40% = Under)
                    recommended_bet = None
                    if over_2_5_prob >= 60:
                        recommended_bet = "Over"
                    elif over_2_5_prob <= 40:
                        recommended_bet = "Under"
                    
                    # Check if prediction was correct
                    over_2_5_correct = None
                    if recommended_bet:
                        if recommended_bet == "Over":
                            over_2_5_correct = went_over_2_5
                        else:  # Under
                            over_2_5_correct = not went_over_2_5
                        
                        if over_2_5_correct:
                            print(f"   ✅ Over 2.5 Sets BET CORRECT! Predicted {recommended_bet} ({over_2_5_prob:.1f}%), Match went {'3 sets' if went_over_2_5 else '2 sets'}")
                        else:
                            print(f"   ❌ Over 2.5 Sets BET INCORRECT! Predicted {recommended_bet} ({over_2_5_prob:.1f}%), Match went {'3 sets' if went_over_2_5 else '2 sets'}")
                    else:
                        print(f"   ⚠️  Over 2.5 Sets probability inconclusive ({over_2_5_prob:.1f}%) - no bet recommended")
                    
                    result["over_2_5_prob"] = over_2_5_prob
                    result["over_2_5_recommended"] = recommended_bet
                    result["over_2_5_actual"] = "Over" if went_over_2_5 else "Under"
                    result["over_2_5_correct"] = over_2_5_correct
                    result["total_sets_played"] = total_sets_played
                    
                except (ValueError, TypeError) as e:
                    print(f"   ⚠️  Could not parse Over 2.5 Sets probability: {over_2_5_prob_str}")
                    result["over_2_5_prob"] = None
                    result["over_2_5_recommended"] = None
                    result["over_2_5_actual"] = None
                    result["over_2_5_correct"] = None
                    result["total_sets_played"] = total_sets
            else:
                result["over_2_5_prob"] = None
                result["over_2_5_recommended"] = None
                result["over_2_5_actual"] = None
                result["over_2_5_correct"] = None
                result["total_sets_played"] = total_sets
            
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Error: {e}")
            
        return result
    
    async def validate_all(self, predictions: List[Dict], max_predictions: int = None, batch_size: int = 5) -> List[Dict]:
        """Validate predictions with concurrent batching for better performance"""
        total = min(len(predictions), max_predictions) if max_predictions else len(predictions)
        predictions_to_process = predictions[:total]
        
        print(f"🔍 Validating {total} predictions in batches of {batch_size}...")
        
        results = []
        
        # Process in batches for better concurrency
        for i in range(0, len(predictions_to_process), batch_size):
            batch = predictions_to_process[i:i + batch_size]
            batch_results = []
            
            print(f"\n🚀 Processing batch {i//batch_size + 1} ({len(batch)} predictions)")
            
            # Create tasks for concurrent execution
            tasks = []
            for j, prediction in enumerate(batch):
                print(f"⏳ [{i+j+1}/{total}] Queuing: {prediction['Match']}")
                task = asyncio.create_task(self.validate_prediction(prediction))
                tasks.append((prediction, task))
            
            # Wait for all tasks in batch to complete
            try:
                for prediction, task in tasks:
                    try:
                        result = await task
                        batch_results.append(result)
                    except Exception as e:
                        print(f"   ❌ Error validating {prediction.get('Match', 'Unknown')}: {e}")
                        batch_results.append({
                            "match": prediction.get('Match', 'Unknown'),
                            "error": str(e),
                            "finished": False
                        })
                
                results.extend(batch_results)
                
                # Rate limiting between batches
                if i + batch_size < len(predictions_to_process):
                    print(f"⏸️  Waiting 2s between batches...")
                    await asyncio.sleep(2)
                    
            except KeyboardInterrupt:
                print(f"\n🛑 Interrupted by user at batch {i//batch_size + 1}")
                break
        
        return results
    
    def save_results(self, results: List[Dict], output_file: str):
        """Save validation results to CSV"""
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Validation_Timestamp', 'Match_Date', 'Match', 
                    'Predicted_Winner', 'Predicted_Prob', 'Actual_Sets',
                    'Bet_Player_Sets', 'Match_Finished', 'Prediction_Correct',
                    'Over_2_5_Prob', 'Over_2_5_Recommended', 'Over_2_5_Actual',
                    'Total_Sets_Played', 'Over_2_5_Correct',
                    'Error_Message'
                ])
                
                # Write results
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for result in results:
                    writer.writerow([
                        timestamp,
                        result.get('date', ''),
                        result.get('match', ''),
                        result.get('bet_on', ''),
                        f"{result.get('bet_prob', 0):.1f}%" if result.get('bet_prob') else '',
                        result.get('actual_sets', ''),
                        result.get('bet_player_sets', ''),
                        'True' if result.get('finished') else 'False',
                        'True' if result.get('set_bet_correct') else 'False',
                        f"{result.get('over_2_5_prob', 0):.1f}%" if result.get('over_2_5_prob') is not None else '',
                        result.get('over_2_5_recommended', ''),
                        result.get('over_2_5_actual', ''),
                        result.get('total_sets_played', ''),
                        'True' if result.get('over_2_5_correct') else ('False' if result.get('over_2_5_correct') is False else ''),
                        result.get('error', '')
                    ])
            
            print(f"💾 Validation results saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
    
    def print_summary(self, results: List[Dict]):
        """Print validation summary"""
        finished = [r for r in results if r.get("finished")]
        voided = [r for r in finished if r.get("voided")]
        set_bets = [r for r in finished if r.get("set_bet_correct") is not None]
        wins = [r for r in set_bets if r.get("set_bet_correct")]
        losses = [r for r in set_bets if not r.get("set_bet_correct")]
        
        print(f"\n{'='*60}")
        print(f"🎯 TENNIS PREDICTION VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"📊 Total Predictions: {len(results)}")
        print(f"🏁 Finished Matches: {len(finished)}")
        
        if voided:
            print(f"🚫 Voided Bets (Retirements): {len(voided)}")
        
        print(f"🎾 Set Betting Results: {len(wins)}/{len(set_bets)} = {(len(wins)/len(set_bets)*100):.1f}%" if set_bets else "No analyzable bets")
        
        # Analyze set score breakdowns for wins
        if wins:
            straight_sets_wins = []  # 2-0 wins
            three_set_wins = []      # 2-1 wins
            total_completed_wins = []  # All 2-0 or 2-1 wins
            total_games_won = 0  # Total games won across all winning bets
            wins_with_game_data = 0  # Count of wins that have game data
            
            for result in wins:
                actual_sets = result.get('actual_sets', '')
                bet_player_games = result.get('bet_player_games', 0)
                
                # Add games won to total
                if bet_player_games > 0:
                    total_games_won += bet_player_games
                    wins_with_game_data += 1
                
                if actual_sets:
                    # Parse set scores
                    try:
                        home_sets, away_sets = map(int, actual_sets.split('-'))
                        total_sets = home_sets + away_sets
                        
                        if total_sets == 2:
                            straight_sets_wins.append(result)
                            total_completed_wins.append(result)
                        elif total_sets == 3:
                            three_set_wins.append(result)
                            total_completed_wins.append(result)
                    except ValueError:
                        # Handle edge cases
                        pass
            
            print(f"\n📊 SET SCORE BREAKDOWN FOR WINS:")
            print(f"   🎾 Total Wins (2-0 or 2-1): {len(total_completed_wins)}")
            print(f"      - Straight Sets (2-0): {len(straight_sets_wins)}")
            print(f"      - Three Sets (2-1): {len(three_set_wins)}")
            
            if total_games_won > 0:
                avg_games_per_win = total_games_won / wins_with_game_data if wins_with_game_data > 0 else 0
                print(f"   🎯 Total Games Won: {total_games_won} games ({wins_with_game_data} matches with game data)")
                print(f"   📊 Average Games per Win: {avg_games_per_win:.1f} games")
            
            if len(wins) > 0:
                total_pct = len(total_completed_wins) / len(wins) * 100
                straight_pct = len(straight_sets_wins) / len(wins) * 100
                three_pct = len(three_set_wins) / len(wins) * 100
                print(f"   📈 Complete Match Wins: {total_pct:.1f}%")
                print(f"   📈 Straight Sets: {straight_pct:.1f}%")
                print(f"   📈 Three Sets: {three_pct:.1f}%")
        
        if wins:
            print(f"\n🏆 WINNING BETS ({len(wins)}):")
            for result in wins:
                print(f"✅ {result['match']} - Bet on {result['bet_on']} ≥1 set ({result['bet_prob']:.1f}%) - Won {result['bet_player_sets']} sets")
        
        if losses:
            print(f"\n❌ LOSING BETS ({len(losses)}):")
            for result in losses:
                print(f"❌ {result['match']} - Bet on {result['bet_on']} ≥1 set ({result['bet_prob']:.1f}%) - Won {result['bet_player_sets']} sets")
        
        if voided:
            print(f"\n🚫 VOIDED BETS ({len(voided)}):")
            for result in voided:
                print(f"🚫 {result['match']} - Bet on {result['bet_on']} ≥1 set ({result['bet_prob']:.1f}%) - RETIRED ({result['actual_sets']})")
        
        # Analyze Over 2.5 Sets predictions
        over_2_5_bets = [r for r in finished if r.get("over_2_5_recommended") and r.get("over_2_5_correct") is not None]
        over_2_5_wins = [r for r in over_2_5_bets if r.get("over_2_5_correct")]
        over_2_5_losses = [r for r in over_2_5_bets if not r.get("over_2_5_correct")]
        
        if over_2_5_bets:
            print(f"\n{'='*60}")
            print(f"📊 OVER 2.5 SETS PREDICTION VALIDATION")
            print(f"{'='*60}")
            print(f"🎯 Total Over 2.5 Sets Bets: {len(over_2_5_bets)}")
            print(f"✅ Correct Predictions: {len(over_2_5_wins)}")
            print(f"❌ Incorrect Predictions: {len(over_2_5_losses)}")
            
            if over_2_5_bets:
                over_2_5_win_rate = len(over_2_5_wins) / len(over_2_5_bets) * 100
                print(f"📈 Win Rate: {over_2_5_win_rate:.1f}%")
                
                # Analyze by bet type
                over_bets = [r for r in over_2_5_bets if r.get("over_2_5_recommended") == "Over"]
                under_bets = [r for r in over_2_5_bets if r.get("over_2_5_recommended") == "Under"]
                
                if over_bets:
                    over_wins = [r for r in over_bets if r.get("over_2_5_correct")]
                    print(f"\n   📊 'Over 2.5 Sets' Bets: {len(over_wins)}/{len(over_bets)} = {len(over_wins)/len(over_bets)*100:.1f}%")
                    avg_over_prob = sum(r.get('over_2_5_prob', 0) for r in over_bets) / len(over_bets) if over_bets else 0
                    print(f"   📊 Avg Probability: {avg_over_prob:.1f}%")
                
                if under_bets:
                    under_wins = [r for r in under_bets if r.get("over_2_5_correct")]
                    print(f"\n   📊 'Under 2.5 Sets' Bets: {len(under_wins)}/{len(under_bets)} = {len(under_wins)/len(under_bets)*100:.1f}%")
                    avg_under_prob = sum(r.get('over_2_5_prob', 0) for r in under_bets) / len(under_bets) if under_bets else 0
                    print(f"   📊 Avg Probability: {avg_under_prob:.1f}%")
                
                # Show breakdown by actual outcome
                matches_went_3_sets = [r for r in over_2_5_bets if r.get("total_sets_played", 0) >= 3]
                matches_went_2_sets = [r for r in over_2_5_bets if r.get("total_sets_played", 0) == 2]
                print(f"\n   📊 Actual Outcomes:")
                print(f"      - 3 Sets: {len(matches_went_3_sets)} matches ({len(matches_went_3_sets)/len(over_2_5_bets)*100:.1f}%)")
                print(f"      - 2 Sets: {len(matches_went_2_sets)} matches ({len(matches_went_2_sets)/len(over_2_5_bets)*100:.1f}%)")
        
        # Calculate some stats
        if set_bets:
            win_rate = len(wins) / len(set_bets) * 100
            avg_win_prob = sum(r['bet_prob'] for r in wins) / len(wins) if wins else 0
            avg_loss_prob = sum(r['bet_prob'] for r in losses) / len(losses) if losses else 0
            
            print(f"\n📈 PERFORMANCE METRICS (+1.5 Sets):")
            print(f"   🎯 Win Rate: {win_rate:.1f}% ({len(wins)} wins / {len(set_bets)} completed bets)")
            if voided:
                print(f"   🚫 Voided bets excluded from win rate: {len(voided)}")
            print(f"   📊 Avg Win Confidence: {avg_win_prob:.1f}%")
            print(f"   📊 Avg Loss Confidence: {avg_loss_prob:.1f}%")


async def main():
    """Main async function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tennis prediction validator')
    parser.add_argument('--input-file', default='tennis_predictions.csv', help='Prediction CSV file')
    parser.add_argument('--output-file', help='Output validation file (default: auto-generated)')
    parser.add_argument('--max-predictions', type=int, help='Limit number of predictions to validate')
    parser.add_argument('--prediction-date', help='Specific date to validate (YYYY-MM-DD)')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of concurrent requests per batch (default: 5)')
    
    args = parser.parse_args()
    
    print("🎾 Tennis Prediction Validator")
    print("="*40)
    
    # Determine input file
    if args.prediction_date:
        # Look for date-specific prediction file
        date_timestamp = datetime.strptime(args.prediction_date, '%Y-%m-%d').strftime('%Y%m%d')
        possible_files = [
            f"prediction_archive/set_predictions_{date_timestamp}.csv",
            f"tennis_predictions_{date_timestamp}.csv",
            args.input_file
        ]
        
        input_file = None
        for file_path in possible_files:
            if os.path.exists(file_path):
                input_file = file_path
                break
        
        if not input_file:
            print(f"❌ No prediction file found for {args.prediction_date}")
            return
    else:
        input_file = args.input_file
    
    # Determine output file
    if args.output_file:
        output_file = args.output_file
    else:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"logs/validation_{base_name}_{timestamp}.csv"
    
    print(f"📁 Input: {input_file}")
    print(f"📁 Output: {output_file}")
    
    # Validate predictions
    async with TennisPredictionValidator() as validator:
        predictions = validator.load_predictions(input_file)
        
        if not predictions:
            print("❌ No predictions found")
            return
        
        # Run validation
        results = await validator.validate_all(predictions, max_predictions=args.max_predictions, batch_size=args.batch_size)
        
        # Save and summarize results
        validator.save_results(results, output_file)
        validator.print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
