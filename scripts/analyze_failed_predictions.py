#!/usr/bin/env python3
"""
Failed Prediction Analysis Script
================================

Deep dive analysis of betting predictions that failed to understand
what went wrong in our prediction logic.
"""

import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from curl_cffi import requests
import time

class FailedPredictionAnalyzer:
    def __init__(self):
        self.analysis_results = []
        self.session = None
        
    def get_player_form_data(self, player_id: int, player_name: str) -> Dict:
        """Get the same form data our prediction system used"""
        try:
            print(f"📊 Fetching form data for {player_name} (ID: {player_id})...")
            
            # Headers to impersonate a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.matchdata-api.example.com/',
                'Origin': 'https://www.matchdata-api.example.com',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
            
            # Get player details using team endpoint (tennis players are teams in MatchDataProvider)
            player_url = f"https://www.matchdata-api.example.com/api/v1/team/{player_id}"
            response = requests.get(player_url, headers=headers, impersonate="chrome120")
            if response.status_code != 200:
                print(f"   ❌ Failed to get player data: {response.status_code}")
                return {}
            player_data = response.json()
            
            time.sleep(0.5)  # Rate limiting
            
            # Get recent matches (last 20 for good sample)
            recent_url = f"https://www.matchdata-api.example.com/api/v1/team/{player_id}/events/last/0"
            recent_matches = []
            try:
                response = requests.get(recent_url, headers=headers, impersonate="chrome120")
                if response.status_code == 200:
                    recent_data = response.json()
                    recent_matches = recent_data.get('events', [])[:20]  # Last 20 matches
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"   ⚠️ Could not get recent matches for {player_name}: {e}")
            
            # Get statistics/ranking info using team endpoint
            stats_data = {}
            try:
                stats_url = f"https://www.matchdata-api.example.com/api/v1/team/{player_id}/statistics"
                response = requests.get(stats_url, headers=headers, impersonate="chrome120")
                if response.status_code == 200:
                    stats_data = response.json()
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"   ⚠️ Could not get stats for {player_name}: {e}")
            
            # Analyze form from recent matches
            form_analysis = self._analyze_player_form(recent_matches, player_name)
            
            return {
                'player_info': player_data.get('team', {}),  # Use 'team' key for tennis players
                'recent_matches': recent_matches,
                'statistics': stats_data,
                'form_analysis': form_analysis
            }
                
        except Exception as e:
            print(f"   ❌ Error fetching form data for {player_name}: {e}")
            return {}
    
    def _analyze_player_form(self, matches: List[Dict], player_name: str) -> Dict:
        """Analyze player form from recent matches (similar to our prediction system)"""
        if not matches:
            return {}
        
        analysis = {
            'total_matches': len(matches),
            'wins': 0,
            'losses': 0,
            'sets_won': 0,
            'sets_lost': 0,
            'surface_breakdown': {},
            'opponent_rankings': [],
            'recent_form_score': 0,
            'match_details': []
        }
        
        for match in matches:
            try:
                # Get match result
                status = match.get('status', {})
                if status.get('type') != 'finished':
                    continue
                
                # Determine if player won
                home_team = match.get('homeTeam', {}).get('name', '')
                away_team = match.get('awayTeam', {}).get('name', '')
                
                player_is_home = player_name.lower() in home_team.lower() or home_team.lower() in player_name.lower()
                player_is_away = player_name.lower() in away_team.lower() or away_team.lower() in player_name.lower()
                
                if not (player_is_home or player_is_away):
                    continue  # Can't determine player position
                
                home_score = match.get('homeScore', {}).get('display', 0)
                away_score = match.get('awayScore', {}).get('display', 0)
                
                if player_is_home:
                    player_sets = home_score
                    opponent_sets = away_score
                    opponent_name = away_team
                else:
                    player_sets = away_score
                    opponent_sets = home_score
                    opponent_name = home_team
                
                # Record result
                player_won = player_sets > opponent_sets
                if player_won:
                    analysis['wins'] += 1
                else:
                    analysis['losses'] += 1
                
                analysis['sets_won'] += player_sets
                analysis['sets_lost'] += opponent_sets
                
                # Surface analysis
                tournament = match.get('tournament', {})
                surface = tournament.get('category', {}).get('name', 'Unknown')
                if surface not in analysis['surface_breakdown']:
                    analysis['surface_breakdown'][surface] = {'wins': 0, 'losses': 0, 'sets_won': 0, 'sets_lost': 0}
                
                if player_won:
                    analysis['surface_breakdown'][surface]['wins'] += 1
                else:
                    analysis['surface_breakdown'][surface]['losses'] += 1
                analysis['surface_breakdown'][surface]['sets_won'] += player_sets
                analysis['surface_breakdown'][surface]['sets_lost'] += opponent_sets
                
                # Store match details
                match_detail = {
                    'date': match.get('startTimestamp'),
                    'tournament': tournament.get('name', 'Unknown'),
                    'surface': surface,
                    'opponent': opponent_name,
                    'score': f"{player_sets}-{opponent_sets}",
                    'won': player_won,
                    'sets_won': player_sets,
                    'sets_lost': opponent_sets
                }
                analysis['match_details'].append(match_detail)
                
            except Exception as e:
                print(f"   ⚠️ Error analyzing match: {e}")
                continue
        
        # Calculate form score (similar to our system)
        total_matches = analysis['wins'] + analysis['losses']
        if total_matches > 0:
            win_rate = analysis['wins'] / total_matches
            set_rate = analysis['sets_won'] / (analysis['sets_won'] + analysis['sets_lost']) if (analysis['sets_won'] + analysis['sets_lost']) > 0 else 0
            analysis['win_rate'] = win_rate
            analysis['set_rate'] = set_rate
            analysis['recent_form_score'] = (win_rate * 0.6 + set_rate * 0.4) * 100  # Similar to our weighting
        
        return analysis

    def get_detailed_match_data(self, event_id: int) -> Optional[Dict]:
        """Get comprehensive match data from MatchDataProvider"""
        try:
            print(f"🔍 Fetching detailed data for event {event_id}...")
            
            # Headers to impersonate a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.matchdata-api.example.com/',
                'Origin': 'https://www.matchdata-api.example.com',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
            
            # Get main event data
            event_url = f"https://www.matchdata-api.example.com/api/v1/event/{event_id}"
            response = requests.get(event_url, headers=headers, impersonate="chrome120")
            if response.status_code != 200:
                print(f"   ❌ Failed to get event data: {response.status_code}")
                return None
            event_data = response.json()
            
            time.sleep(0.5)  # Rate limiting
            
            # Get detailed statistics
            stats_data = None
            try:
                stats_url = f"https://www.matchdata-api.example.com/api/v1/event/{event_id}/statistics"
                response = requests.get(stats_url, headers=headers, impersonate="chrome120")
                if response.status_code == 200:
                    stats_data = response.json()
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"   ⚠️ Could not get statistics for event {event_id}: {e}")
            
            # Get set scores if available
            sets_data = None
            try:
                sets_url = f"https://www.matchdata-api.example.com/api/v1/event/{event_id}/sets"
                response = requests.get(sets_url, headers=headers, impersonate="chrome120")
                if response.status_code == 200:
                    sets_data = response.json()
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"   ⚠️ Could not get set scores for event {event_id}: {e}")
            
            return {
                'event': event_data,
                'statistics': stats_data,
                'sets': sets_data
                }
                
        except Exception as e:
            print(f"   ❌ Error fetching match data: {e}")
            return None
    
    def extract_match_insights(self, match_data: Dict, prediction_data: Dict) -> Dict:
        """Extract key insights from the match that explain the prediction failure"""
        insights = {
            'event_id': prediction_data.get('event_id'),
            'match_name': prediction_data.get('match_name'),
            'predicted_winner': prediction_data.get('predicted_winner'),
            'actual_winner': None,
            'predicted_confidence': prediction_data.get('confidence'),
            'prediction_factors': prediction_data.get('factors', {}),
            'actual_stats': {},
            'failure_reasons': [],
            'set_scores': [],
            'key_stats_comparison': {}
        }
        
        try:
            event = match_data['event']['event']
            
            # Basic match info
            home_player = event.get('homeTeam', {}).get('name', 'Unknown')
            away_player = event.get('awayTeam', {}).get('name', 'Unknown')
            
            # Final score
            home_score = event.get('homeScore', {})
            away_score = event.get('awayScore', {})
            
            home_sets = home_score.get('display', 0)
            away_sets = away_score.get('display', 0)
            
            insights['actual_winner'] = home_player if home_sets > away_sets else away_player
            insights['final_score'] = f"{home_sets}-{away_sets}"
            
            # Set scores breakdown
            if match_data.get('sets'):
                try:
                    sets_info = match_data['sets']
                    if 'periods' in sets_info:
                        for period in sets_info['periods']:
                            set_num = period.get('number', 0)
                            home_games = period.get('homeScore', 0)
                            away_games = period.get('awayScore', 0)
                            insights['set_scores'].append({
                                'set': set_num,
                                'home_games': home_games,
                                'away_games': away_games,
                                'winner': home_player if home_games > away_games else away_player
                            })
                except Exception as e:
                    print(f"   ⚠️ Error parsing set scores: {e}")
            
            # Match statistics analysis
            if match_data.get('statistics'):
                try:
                    stats = match_data['statistics']
                    if 'statistics' in stats:
                        for stat_group in stats['statistics']:
                            if 'statisticsItems' in stat_group:
                                for stat in stat_group['statisticsItems']:
                                    stat_name = stat.get('name', '')
                                    home_value = stat.get('homeValue', 0)
                                    away_value = stat.get('awayValue', 0)
                                    
                                    insights['actual_stats'][stat_name] = {
                                        'home': home_value,
                                        'away': away_value
                                    }
                except Exception as e:
                    print(f"   ⚠️ Error parsing statistics: {e}")
            
            # Analyze why prediction failed
            insights['failure_reasons'] = self._analyze_failure_reasons(insights, prediction_data)
            
        except Exception as e:
            print(f"   ❌ Error extracting insights: {e}")
            insights['error'] = str(e)
        
        return insights
    
    def _analyze_failure_reasons(self, insights: Dict, prediction_data: Dict) -> List[str]:
        """Analyze specific reasons why the prediction failed"""
        reasons = []
        
        # Check if predicted player won any sets
        predicted_winner = prediction_data.get('predicted_winner', '')
        set_scores = insights.get('set_scores', [])
        
        sets_won_by_predicted = 0
        for set_info in set_scores:
            if set_info.get('winner') == predicted_winner:
                sets_won_by_predicted += 1
        
        if sets_won_by_predicted == 0:
            reasons.append("BAGEL: Predicted player won 0 sets (complete failure)")
        elif sets_won_by_predicted == 1:
            reasons.append("PARTIAL: Predicted player won only 1 set")
        
        # Analyze key stats that contradicted our prediction
        actual_stats = insights.get('actual_stats', {})
        
        # Check serve performance
        if 'First serve percentage' in actual_stats:
            first_serve = actual_stats['First serve percentage']
            home_serve = first_serve.get('home', 0)
            away_serve = first_serve.get('away', 0)
            
            if abs(home_serve - away_serve) > 15:  # Significant difference
                if home_serve > away_serve:
                    reasons.append(f"Serve dominance: Home player much better first serve ({home_serve}% vs {away_serve}%)")
                else:
                    reasons.append(f"Serve dominance: Away player much better first serve ({away_serve}% vs {home_serve}%)")
        
        # Check break points
        if 'Break points won' in actual_stats:
            break_points = actual_stats['Break points won']
            home_bp = break_points.get('home', 0)
            away_bp = break_points.get('away', 0)
            
            if home_bp != away_bp:
                if home_bp > away_bp:
                    reasons.append(f"Break point efficiency: Home player converted {home_bp} vs {away_bp}")
                else:
                    reasons.append(f"Break point efficiency: Away player converted {away_bp} vs {home_bp}")
        
        # Check total points
        if 'Total points won' in actual_stats:
            total_points = actual_stats['Total points won']
            home_points = total_points.get('home', 0)
            away_points = total_points.get('away', 0)
            
            total = home_points + away_points
            if total > 0:
                home_pct = (home_points / total) * 100
                away_pct = (away_points / total) * 100
                
                if abs(home_pct - away_pct) > 10:  # Significant difference
                    if home_pct > away_pct:
                        reasons.append(f"Points dominance: Home player won {home_pct:.1f}% of total points")
                    else:
                        reasons.append(f"Points dominance: Away player won {away_pct:.1f}% of total points")
        
        # Check aces
        if 'Aces' in actual_stats:
            aces = actual_stats['Aces']
            home_aces = aces.get('home', 0)
            away_aces = aces.get('away', 0)
            
            if abs(home_aces - away_aces) > 5:  # Significant difference
                if home_aces > away_aces:
                    reasons.append(f"Serve power: Home player hit {home_aces} aces vs {away_aces}")
                else:
                    reasons.append(f"Serve power: Away player hit {away_aces} aces vs {home_aces}")
        
        # If no specific reasons found, add general failure reason
        if not reasons:
            reasons.append("Unexpected outcome: No clear statistical explanation")
        
        return reasons
    
    def analyze_failed_prediction(self, event_id: int, prediction_data: Dict) -> Dict:
        """ENHANCED: Comprehensive analysis showing EXACT weight factors that led to failed prediction"""
        print(f"\n🔍 ANALYZING FAILED PREDICTION: {prediction_data.get('match_name', 'Unknown')}")
        print("="*70)
        
        # Get detailed match data
        match_data = self.get_detailed_match_data(event_id)
        if not match_data:
            return {
                'event_id': event_id,
                'error': 'Could not fetch match data',
                'match_name': prediction_data.get('match_name')
            }
        
        # Extract player IDs from match data
        event = match_data['event']['event']
        home_player_id = event.get('homeTeam', {}).get('id')
        away_player_id = event.get('awayTeam', {}).get('id')
        home_player_name = event.get('homeTeam', {}).get('name', 'Unknown')
        away_player_name = event.get('awayTeam', {}).get('name', 'Unknown')
        
        print(f"\n🔧 RECREATING THE EXACT PREDICTION THAT FAILED...")
        
        # ENHANCED: Recreate the actual prediction using our betting analyzer
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from betting_analysis_script import TennisBettingAnalyzer
            
            # Initialize analyzer with current weights
            analyzer = TennisBettingAnalyzer()
            
            print(f"📊 Getting enhanced player profiles (same as prediction system)...")
            
            # Get full player profiles exactly like the prediction system
            try:
                home_profile = analyzer.get_enhanced_player_profile(home_player_id, surface="Unknown")
                away_profile = analyzer.get_enhanced_player_profile(away_player_id, surface="Unknown")
                
                print(f"✅ Successfully loaded player profiles")
                
                # RECREATE THE EXACT WEIGHTED PREDICTION
                print(f"\n⚖️ RECREATING WEIGHTED PREDICTION WITH CURRENT CONFIG...")
                prediction_result = analyzer.calculate_weighted_prediction(
                    home_profile, away_profile, surface="Unknown", event_id=event_id
                )
                
                print(f"\n🎯 RECREATED PREDICTION:")
                print(f"   🏆 Predicted Winner: {prediction_result.predicted_winner}")
                print(f"   📊 Win Probability: {prediction_result.win_probability:.1%}")
                print(f"   ⭐ Confidence Level: {prediction_result.confidence_level}")
                
                print(f"\n📊 COMPLETE WEIGHT FACTOR BREAKDOWN:")
                print(f"   🏠 HOME: {home_player_name}")
                print(f"   ✈️  AWAY: {away_player_name}")
                print(f"")
                
                # Show all factors with exact values
                print(f"🔍 DETAILED FACTOR COMPARISON:")
                
                print(f"\n   📈 RECENT FORM (Weight: {analyzer.WEIGHTS.get('recent_form', 0):.0%}):")
                print(f"      🏠 {home_player_name}: {home_profile.recent_form_score:.1f}")
                print(f"      ✈️  {away_player_name}: {away_profile.recent_form_score:.1f}")
                form_advantage = home_profile.recent_form_score - away_profile.recent_form_score
                winner_icon = "🏠" if form_advantage > 0 else "✈️"
                print(f"      🎯 Form Advantage: {winner_icon} {abs(form_advantage):.1f} points")
                
                print(f"\n   🏆 RANKING FACTORS (Combined Weight: {analyzer.WEIGHTS.get('atp_ranking', 0) + analyzer.WEIGHTS.get('utr_rating', 0):.0%}):")
                home_ranking = home_profile.atp_ranking or home_profile.wta_ranking or 9999
                away_ranking = away_profile.atp_ranking or away_profile.wta_ranking or 9999
                print(f"      🏠 {home_player_name} ATP/WTA: #{home_ranking}")
                print(f"      ✈️  {away_player_name} ATP/WTA: #{away_ranking}")
                ranking_advantage = "🏠 HOME" if home_ranking < away_ranking else "✈️ AWAY"
                print(f"      🎯 Ranking Advantage: {ranking_advantage} (gap: {abs(home_ranking - away_ranking)} positions)")
                
                home_utr = home_profile.utr_rating or 0
                away_utr = away_profile.utr_rating or 0
                if home_utr > 0 or away_utr > 0:
                    print(f"      🏠 {home_player_name} UTR: {home_utr:.2f}")
                    print(f"      ✈️  {away_player_name} UTR: {away_utr:.2f}")
                    utr_advantage = "🏠" if home_utr > away_utr else "✈️"
                    print(f"      🎯 UTR Advantage: {utr_advantage} {abs(home_utr - away_utr):.2f} points")
                
                print(f"\n   🎾 SET PERFORMANCE (Weight: {analyzer.WEIGHTS.get('set_performance', 0):.0%}):")
                home_set_rate = getattr(home_profile, 'set_win_rate', 0)
                away_set_rate = getattr(away_profile, 'set_win_rate', 0)
                print(f"      🏠 {home_player_name}: {home_set_rate:.1%}")
                print(f"      ✈️  {away_player_name}: {away_set_rate:.1%}")
                set_advantage = "🏠" if home_set_rate > away_set_rate else "✈️"
                print(f"      🎯 Set Performance Advantage: {set_advantage} {abs(home_set_rate - away_set_rate):.1%}")
                
                print(f"\n   🌍 SURFACE PERFORMANCE (Weight: {analyzer.WEIGHTS.get('surface_performance', 0):.0%}):")
                print(f"      🏠 {home_player_name}: {home_profile.surface_win_rate:.1%}")
                print(f"      ✈️  {away_player_name}: {away_profile.surface_win_rate:.1%}")
                surface_advantage = "🏠" if home_profile.surface_win_rate > away_profile.surface_win_rate else "✈️"
                print(f"      🎯 Surface Advantage: {surface_advantage} {abs(home_profile.surface_win_rate - away_profile.surface_win_rate):.1%}")
                
                # Show the key factors that drove the prediction
                print(f"\n🔑 KEY FACTORS THAT DROVE OUR PREDICTION:")
                for i, factor in enumerate(prediction_result.key_factors, 1):
                    print(f"   {i:2d}. {factor}")
                
                # Show weight breakdown
                if prediction_result.weight_breakdown:
                    print(f"\n⚖️ WEIGHT BREAKDOWN:")
                    for factor, value in prediction_result.weight_breakdown.items():
                        print(f"   • {factor}: {value}")
                
            except Exception as profile_error:
                print(f"❌ Could not load player profiles: {profile_error}")
                # Fallback to original analysis
                home_form_data = {}
                away_form_data = {}
                
                if home_player_id:
                    print(f"\n📊 FETCHING BASIC FORM DATA FOR HOME PLAYER...")
                    home_form_data = self.get_player_form_data(home_player_id, home_player_name)
                
                if away_player_id:
                    print(f"\n📊 FETCHING BASIC FORM DATA FOR AWAY PLAYER...")
                    away_form_data = self.get_player_form_data(away_player_id, away_player_name)
                
                prediction_result = None
                home_profile = None
                away_profile = None
        
        except Exception as analyzer_error:
            print(f"❌ Could not recreate prediction analysis: {analyzer_error}")
            prediction_result = None
            home_profile = None
            away_profile = None
        
        # Extract insights including form analysis
        insights = self.extract_match_insights(match_data, prediction_data)
        
        # Add enhanced data if available
        if prediction_result and home_profile and away_profile:
            insights.update({
                'recreated_prediction': {
                    'winner': prediction_result.predicted_winner,
                    'confidence': prediction_result.win_probability,
                    'level': prediction_result.confidence_level,
                    'factors': prediction_result.key_factors,
                    'weight_breakdown': prediction_result.weight_breakdown
                },
                'complete_player_analysis': {
                    'home': {
                        'name': home_player_name,
                        'recent_form': home_profile.recent_form_score,
                        'ranking': home_profile.atp_ranking or home_profile.wta_ranking,
                        'utr': home_profile.utr_rating,
                        'surface_win_rate': home_profile.surface_win_rate,
                        'set_win_rate': getattr(home_profile, 'set_win_rate', 0)
                    },
                    'away': {
                        'name': away_player_name,
                        'recent_form': away_profile.recent_form_score,
                        'ranking': away_profile.atp_ranking or away_profile.wta_ranking,
                        'utr': away_profile.utr_rating,
                        'surface_win_rate': away_profile.surface_win_rate,
                        'set_win_rate': getattr(away_profile, 'set_win_rate', 0)
                    }
                }
            })
        
        # Display final summary
        print(f"\n🎯 PREDICTION FAILURE SUMMARY:")
        print(f"   🏆 We Predicted: {insights.get('predicted_winner', 'Unknown')}")
        print(f"   ❌ Reality: {insights.get('actual_winner', 'Unknown')} won")
        print(f"   📊 Final Score: {insights.get('final_score', 'Unknown')}")
        
        # Enhanced failure analysis
        if prediction_result and home_profile and away_profile:
            print(f"\n❓ WHY DID OUR PREDICTION FAIL?")
            
            predicted_winner = prediction_result.predicted_winner
            actual_winner = insights.get('actual_winner')
            
            misleading_factors = []
            
            # Check each factor
            if predicted_winner == home_player_name:
                if home_profile.recent_form_score > away_profile.recent_form_score:
                    misleading_factors.append(f"Form supported our pick: {home_profile.recent_form_score:.1f} vs {away_profile.recent_form_score:.1f}")
                
                home_ranking = home_profile.atp_ranking or home_profile.wta_ranking or 9999
                away_ranking = away_profile.atp_ranking or away_profile.wta_ranking or 9999
                if home_ranking < away_ranking:
                    misleading_factors.append(f"Ranking supported our pick: #{home_ranking} vs #{away_ranking}")
            else:
                if away_profile.recent_form_score > home_profile.recent_form_score:
                    misleading_factors.append(f"Form supported our pick: {away_profile.recent_form_score:.1f} vs {home_profile.recent_form_score:.1f}")
                
                home_ranking = home_profile.atp_ranking or home_profile.wta_ranking or 9999
                away_ranking = away_profile.atp_ranking or away_profile.wta_ranking or 9999
                if away_ranking < home_ranking:
                    misleading_factors.append(f"Ranking supported our pick: #{away_ranking} vs #{home_ranking}")
            
            if misleading_factors:
                for factor in misleading_factors:
                    print(f"   • {factor}")
            
            # Check for bagel failure
            if self.is_bagel_loss_from_insights(insights, predicted_winner):
                print(f"   🚨 BAGEL FAILURE: {predicted_winner} won 0 sets!")
        
        return insights
    
    def is_bagel_loss_from_insights(self, insights: Dict, predicted_winner: str) -> bool:
        """Check if this was a bagel loss (predicted player won 0 sets)"""
        try:
            final_score = insights.get('final_score', '')
            if '-' in final_score:
                parts = final_score.split('-')
                if len(parts) == 2:
                    home_sets = int(parts[0])
                    away_sets = int(parts[1])
                    
                    home_name = insights.get('match_name', '').split(' vs ')[0]
                    
                    # Check if predicted winner won 0 sets
                    if predicted_winner == home_name:
                        return home_sets == 0
                    else:
                        return away_sets == 0
        except:
            pass
        return False
    
    def _analyze_form_prediction_failure(self, prediction_data: Dict, home_form: Dict, away_form: Dict, 
                                       home_name: str, away_name: str) -> List[str]:
        """Analyze why our form-based prediction failed"""
        reasons = []
        
        if not home_form.get('form_analysis') or not away_form.get('form_analysis'):
            reasons.append("Could not analyze form data - insufficient data retrieved")
            return reasons
        
        home_analysis = home_form['form_analysis']
        away_analysis = away_form['form_analysis']
        
        predicted_winner = prediction_data.get('predicted_winner', '')
        
        # Check if predicted winner had better form scores
        home_form_score = home_analysis.get('recent_form_score', 0)
        away_form_score = away_analysis.get('recent_form_score', 0)
        
        if predicted_winner == home_name and home_form_score > away_form_score:
            reasons.append(f"Form score supported prediction: {home_name} {home_form_score:.1f} vs {away_name} {away_form_score:.1f}")
        elif predicted_winner == away_name and away_form_score > home_form_score:
            reasons.append(f"Form score supported prediction: {away_name} {away_form_score:.1f} vs {home_name} {home_form_score:.1f}")
        else:
            reasons.append(f"Form scores were misleading: {home_name} {home_form_score:.1f} vs {away_name} {away_form_score:.1f}")
        
        # Check sample sizes
        home_matches = home_analysis.get('total_matches', 0)
        away_matches = away_analysis.get('total_matches', 0)
        
        if home_matches < 10:
            reasons.append(f"Small sample size for {home_name}: only {home_matches} recent matches")
        if away_matches < 10:
            reasons.append(f"Small sample size for {away_name}: only {away_matches} recent matches")
        
        # Check set rates vs win rates
        if predicted_winner == home_name:
            home_set_rate = home_analysis.get('set_rate', 0)
            if home_set_rate < 0.4:  # Less than 40% set rate
                reasons.append(f"Low set rate for predicted winner {home_name}: {home_set_rate:.1%}")
        elif predicted_winner == away_name:
            away_set_rate = away_analysis.get('set_rate', 0)
            if away_set_rate < 0.4:
                reasons.append(f"Low set rate for predicted winner {away_name}: {away_set_rate:.1%}")
        
        # Check recent match quality
        if predicted_winner == home_name:
            recent_details = home_analysis.get('match_details', [])[:5]  # Last 5 matches
            wins_in_last_5 = sum(1 for match in recent_details if match.get('won', False))
            if wins_in_last_5 <= 1:
                reasons.append(f"Poor recent form for {home_name}: only {wins_in_last_5}/5 wins in last 5 matches")
        elif predicted_winner == away_name:
            recent_details = away_analysis.get('match_details', [])[:5]
            wins_in_last_5 = sum(1 for match in recent_details if match.get('won', False))
            if wins_in_last_5 <= 1:
                reasons.append(f"Poor recent form for {away_name}: only {wins_in_last_5}/5 wins in last 5 matches")
        
        return reasons
    
    def save_analysis_results(self, results: List[Dict], output_dir: str = "logs"):
        """Save analysis results to CSV and JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save detailed JSON
        json_file = f"{output_dir}/failed_predictions_analysis_{timestamp}.json"
        os.makedirs(output_dir, exist_ok=True)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save summary CSV
        csv_file = f"{output_dir}/failed_predictions_summary_{timestamp}.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Event_ID', 'Match_Name', 'Predicted_Winner', 'Actual_Winner',
                'Final_Score', 'Predicted_Confidence', 'Sets_Won_By_Predicted',
                'Primary_Failure_Reason', 'All_Failure_Reasons', 'Key_Stats',
                'Home_Form_Score', 'Away_Form_Score', 'Home_Win_Rate', 'Away_Win_Rate',
                'Home_Set_Rate', 'Away_Set_Rate', 'Home_Recent_Record', 'Away_Recent_Record',
                'Form_Failure_Analysis'
            ])
            
                            # Data rows
            for result in results:
                if 'error' in result:
                    writer.writerow([
                        result.get('event_id', ''),
                        result.get('match_name', ''),
                        'ERROR',
                        'ERROR',
                        result.get('error', ''),
                        '', '', '', '', '', '', '', '', '', '', '', '', '', ''
                    ])
                    continue
                
                # Count sets won by predicted player
                sets_won = 0
                for set_info in result.get('set_scores', []):
                    if set_info.get('winner') == result.get('predicted_winner'):
                        sets_won += 1
                
                failure_reasons = result.get('failure_reasons', [])
                primary_reason = failure_reasons[0] if failure_reasons else 'Unknown'
                all_reasons = '; '.join(failure_reasons)
                
                # Key stats summary
                stats = result.get('actual_stats', {})
                key_stats = []
                if 'First serve percentage' in stats:
                    fs = stats['First serve percentage']
                    key_stats.append(f"1st serve: {fs.get('home', 0)}%/{fs.get('away', 0)}%")
                if 'Aces' in stats:
                    aces = stats['Aces']
                    key_stats.append(f"Aces: {aces.get('home', 0)}/{aces.get('away', 0)}")
                
                # Extract form data
                home_form = result.get('home_player_form', {}).get('form_analysis', {})
                away_form = result.get('away_player_form', {}).get('form_analysis', {})
                
                home_form_score = home_form.get('recent_form_score', 0)
                away_form_score = away_form.get('recent_form_score', 0)
                home_win_rate = home_form.get('win_rate', 0)
                away_win_rate = away_form.get('win_rate', 0)
                home_set_rate = home_form.get('set_rate', 0)
                away_set_rate = away_form.get('set_rate', 0)
                
                home_record = f"{home_form.get('wins', 0)}-{home_form.get('losses', 0)}"
                away_record = f"{away_form.get('wins', 0)}-{away_form.get('losses', 0)}"
                
                form_failure_analysis = '; '.join(result.get('form_failure_analysis', []))
                
                writer.writerow([
                    result.get('event_id', ''),
                    result.get('match_name', ''),
                    result.get('predicted_winner', ''),
                    result.get('actual_winner', ''),
                    result.get('final_score', ''),
                    result.get('predicted_confidence', ''),
                    sets_won,
                    primary_reason,
                    all_reasons,
                    '; '.join(key_stats),
                    f"{home_form_score:.1f}",
                    f"{away_form_score:.1f}",
                    f"{home_win_rate:.1%}",
                    f"{away_win_rate:.1%}",
                    f"{home_set_rate:.1%}",
                    f"{away_set_rate:.1%}",
                    home_record,
                    away_record,
                    form_failure_analysis
                ])
        
        print(f"\n💾 ANALYSIS SAVED:")
        print(f"   📄 Detailed: {json_file}")
        print(f"   📊 Summary: {csv_file}")

def main():
    """Analyze the failed predictions from today's betting"""
    
    # Current BAGEL LOSSES from BALANCED_PERFORMANCE_V1 to analyze
    failed_predictions = [
        {
            'event_id': 14717278,
            'match_name': 'Nicolas Kicker vs Gonzalo Bueno',
            'predicted_winner': 'Gonzalo Bueno',
            'confidence': '70.0%',
            'factors': {
                'outcome': 'BAGEL LOSS: Gonzalo Bueno won 0 sets',
                'actual_winner': 'Nicolas Kicker',
                'actual_score': '2-0'
            },
            'players': {
                'home': 'Nicolas Kicker',
                'away': 'Gonzalo Bueno'
            }
        },
        {
            'event_id': 14708961,
            'match_name': 'Bernard Tomic vs Mackenzie McDonald',
            'predicted_winner': 'Bernard Tomic',
            'confidence': '65.6%',
            'factors': {
                'outcome': 'BAGEL LOSS: Bernard Tomic won 0 sets',
                'actual_winner': 'Mackenzie McDonald',
                'actual_score': '0-2'
            },
            'players': {
                'home': 'Bernard Tomic',
                'away': 'Mackenzie McDonald'
            }
        },
        {
            'event_id': 14708956,
            'match_name': 'Eliot Spizzirri vs Lloyd Harris',
            'predicted_winner': 'Lloyd Harris',
            'confidence': '66.2%',
            'factors': {
                'outcome': 'BAGEL LOSS: Lloyd Harris won 0 sets',
                'actual_winner': 'Eliot Spizzirri',
                'actual_score': '1-0'
            },
            'players': {
                'home': 'Eliot Spizzirri',
                'away': 'Lloyd Harris'
            }
        }
    ]
    
    print("🔍 FAILED PREDICTION DEEP ANALYSIS")
    print("="*50)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Analyzing {len(failed_predictions)} failed predictions...")
    
    analyzer = FailedPredictionAnalyzer()
    results = []
    
    for prediction in failed_predictions:
        try:
            result = analyzer.analyze_failed_prediction(
                prediction['event_id'], 
                prediction
            )
            results.append(result)
            
            # Rate limiting
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error analyzing {prediction['match_name']}: {e}")
            results.append({
                'event_id': prediction['event_id'],
                'match_name': prediction['match_name'],
                'error': str(e)
            })
    
    # Save results
    analyzer.save_analysis_results(results)
    
    print(f"\n🎯 ANALYSIS COMPLETE!")
    print(f"📊 {len(results)} predictions analyzed")
    print(f"💾 Results saved to logs/ directory")

if __name__ == "__main__":
    main()
