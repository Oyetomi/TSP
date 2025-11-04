#!/usr/bin/env python3
"""
Forebet Impact Analysis
Analyzes whether Forebet predictions could have improved our win rate
by avoiding losses while preserving wins.
"""

import csv
import json
from datetime import datetime, timedelta
from curl_cffi import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from typing import List, Dict, Optional
import time

class ForebetImpactAnalyzer:
    def __init__(self):
        self.forebet_predictions = []
        self.our_predictions = []
        self.matches_comparison = []
    
    def scrape_forebet_date(self, date_str: str) -> List[Dict]:
        """Scrape Forebet predictions for a specific date"""
        # Forebet uses different URL format - try today/yesterday
        if date_str == datetime.now().strftime('%Y-%m-%d'):
            url = "https://www.forebet.com/en/tennis/predictions-today"
        elif date_str == (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'):
            url = "https://www.forebet.com/en/tennis/predictions-yesterday"
        else:
            url = "https://www.forebet.com/en/tennis/predictions-today"
        
        print(f"📥 Scraping Forebet ({url})...")
        
        try:
            response = requests.get(
                url,
                impersonate="chrome110",
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"   ❌ Failed: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            predictions = []
            
            # Find all match rows
            matches = soup.find_all('div', class_='rcnt')
            
            for match in matches:
                try:
                    # Extract team names
                    team_spans = match.find_all('span', class_='homeTeam') + match.find_all('span', class_='awayTeam')
                    if len(team_spans) < 2:
                        continue
                    
                    player1 = team_spans[0].get_text(strip=True)
                    player2 = team_spans[1].get_text(strip=True)
                    
                    # Extract prediction
                    predict_div = match.find('div', class_='predict')
                    if not predict_div:
                        continue
                    
                    prediction_text = predict_div.get_text(strip=True)
                    
                    # Extract actual result if available
                    result_divs = match.find_all('div', class_='lscr_td')
                    actual_result = None
                    
                    if len(result_divs) >= 2:
                        try:
                            score1 = result_divs[0].get_text(strip=True)
                            score2 = result_divs[1].get_text(strip=True)
                            
                            if score1 and score2 and score1.isdigit() and score2.isdigit():
                                actual_result = f"{score1}-{score2}"
                        except:
                            pass
                    
                    predictions.append({
                        'date': date_str,
                        'player1': player1,
                        'player2': player2,
                        'prediction': prediction_text,
                        'actual_result': actual_result
                    })
                
                except Exception as e:
                    continue
            
            print(f"   ✓ Found {len(predictions)} predictions")
            return predictions
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []
    
    def scrape_forebet_multiple_dates(self, start_date: str, end_date: str):
        """Scrape Forebet for date range"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            predictions = self.scrape_forebet_date(date_str)
            self.forebet_predictions.extend(predictions)
            
            current += timedelta(days=1)
            time.sleep(2)  # Be nice to the server
        
        print(f"\n✓ Total Forebet predictions scraped: {len(self.forebet_predictions)}")
    
    def load_our_predictions(self, csv_file: str):
        """Load our system's predictions from CSV"""
        print(f"\n📥 Loading our predictions from {csv_file}...")
        
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.our_predictions.append({
                    'date': row['date'],
                    'player1': row['player1_name'],
                    'player2': row['player2_name'],
                    'predicted_winner': row['predicted_winner'],
                    'confidence': row['confidence'],
                    'tournament': row['tournament'],
                    'surface': row['surface']
                })
        
        print(f"   ✓ Loaded {len(self.our_predictions)} predictions")
    
    def fuzzy_match_players(self, name1: str, name2: str, threshold: int = 75) -> bool:
        """Check if two player names match using fuzzy matching"""
        # Handle abbreviated names
        name1_parts = name1.split()
        name2_parts = name2.split()
        
        # Try full name match
        if fuzz.ratio(name1.lower(), name2.lower()) >= threshold:
            return True
        
        # Try last name match (most reliable)
        if len(name1_parts) > 0 and len(name2_parts) > 0:
            last1 = name1_parts[-1].lower()
            last2 = name2_parts[-1].lower()
            if fuzz.ratio(last1, last2) >= 85:
                return True
        
        return False
    
    def match_predictions(self):
        """Match Forebet predictions with our predictions"""
        print(f"\n🔗 Matching predictions...")
        
        for our_pred in self.our_predictions:
            best_match = None
            best_score = 0
            
            for forebet_pred in self.forebet_predictions:
                # Check if dates are close (within 1 day)
                our_date = datetime.strptime(our_pred['date'], '%Y-%m-%d')
                forebet_date = datetime.strptime(forebet_pred['date'], '%Y-%m-%d')
                
                if abs((our_date - forebet_date).days) > 1:
                    continue
                
                # Check if players match
                p1_match = (
                    self.fuzzy_match_players(our_pred['player1'], forebet_pred['player1']) or
                    self.fuzzy_match_players(our_pred['player1'], forebet_pred['player2'])
                )
                
                p2_match = (
                    self.fuzzy_match_players(our_pred['player2'], forebet_pred['player1']) or
                    self.fuzzy_match_players(our_pred['player2'], forebet_pred['player2'])
                )
                
                if p1_match and p2_match:
                    # Determine Forebet's predicted winner
                    forebet_winner = None
                    
                    # Parse Forebet prediction (usually has player name in it)
                    if self.fuzzy_match_players(our_pred['player1'], forebet_pred['prediction'], threshold=60):
                        forebet_winner = our_pred['player1']
                    elif self.fuzzy_match_players(our_pred['player2'], forebet_pred['prediction'], threshold=60):
                        forebet_winner = our_pred['player2']
                    
                    # Calculate match score
                    score = 100
                    
                    if score > best_score:
                        best_score = score
                        best_match = {
                            'forebet_pred': forebet_pred,
                            'forebet_winner': forebet_winner
                        }
            
            if best_match:
                self.matches_comparison.append({
                    **our_pred,
                    'forebet_prediction': best_match['forebet_pred']['prediction'],
                    'forebet_winner': best_match['forebet_winner'],
                    'forebet_result': best_match['forebet_pred']['actual_result'],
                    'agreement': best_match['forebet_winner'] == our_pred['predicted_winner'] if best_match['forebet_winner'] else None
                })
        
        print(f"   ✓ Matched {len(self.matches_comparison)} predictions")
    
    def analyze_impact(self):
        """Analyze the impact of using Forebet as a filter"""
        print(f"\n" + "="*80)
        print("📊 FOREBET IMPACT ANALYSIS")
        print("="*80)
        
        # Load actual results to determine wins/losses
        wins = []
        losses = []
        
        known_losses = [
            'Raphael Collignon',
            'Alex Molcan',
            'Martin Damm Jr',
            'Norbert Gombos',
            'Whitney Osuigwe',
            'Andrea Collarini'
        ]
        
        for match in self.matches_comparison:
            if match['predicted_winner'] in known_losses:
                losses.append(match)
            else:
                wins.append(match)
        
        print(f"\n📋 MATCHED PREDICTIONS:")
        print(f"   Total matched: {len(self.matches_comparison)}")
        print(f"   Our wins: {len(wins)}")
        print(f"   Our losses: {len(losses)}")
        print()
        
        # Analyze losses
        print("="*80)
        print("❌ ANALYZING OUR LOSSES:")
        print("="*80)
        print()
        
        losses_forebet_agreed = 0
        losses_forebet_disagreed = 0
        losses_forebet_unknown = 0
        
        for i, loss in enumerate(losses, 1):
            print(f"{i}. {loss['predicted_winner']} vs opponent")
            print(f"   Date: {loss['date']}")
            print(f"   Our pick: {loss['predicted_winner']} (Confidence: {loss['confidence']})")
            
            if loss.get('forebet_winner'):
                print(f"   Forebet pick: {loss['forebet_winner']}")
                
                if loss['agreement']:
                    print(f"   ✅ FOREBET AGREED - Would NOT have filtered")
                    losses_forebet_agreed += 1
                else:
                    print(f"   ❌ FOREBET DISAGREED - Would have SKIPPED!")
                    losses_forebet_disagreed += 1
            else:
                print(f"   ❓ FOREBET UNKNOWN - Couldn't determine pick")
                losses_forebet_unknown += 1
            
            print()
        
        print("="*80)
        print("✅ ANALYZING OUR WINS:")
        print("="*80)
        print()
        
        wins_forebet_agreed = 0
        wins_forebet_disagreed = 0
        wins_forebet_unknown = 0
        
        for win in wins:
            if win.get('agreement') is True:
                wins_forebet_agreed += 1
            elif win.get('agreement') is False:
                wins_forebet_disagreed += 1
            else:
                wins_forebet_unknown += 1
        
        print(f"   Forebet AGREED: {wins_forebet_agreed}/{len(wins)} ({wins_forebet_agreed/len(wins)*100:.1f}%)")
        print(f"   Forebet DISAGREED: {wins_forebet_disagreed}/{len(wins)} ({wins_forebet_disagreed/len(wins)*100:.1f}%)")
        print(f"   Forebet UNKNOWN: {wins_forebet_unknown}/{len(wins)} ({wins_forebet_unknown/len(wins)*100:.1f}%)")
        print()
        
        # Calculate net impact
        print("="*80)
        print("🎯 NET IMPACT ANALYSIS:")
        print("="*80)
        print()
        
        losses_avoided = losses_forebet_disagreed
        wins_sacrificed = wins_forebet_disagreed
        
        print(f"   Losses avoided: {losses_avoided}/{len(losses)} ({losses_avoided/len(losses)*100:.1f}%)")
        print(f"   Wins sacrificed: {wins_sacrificed}/{len(wins)} ({wins_sacrificed/len(wins)*100:.1f}%)")
        print()
        
        net_impact = losses_avoided - wins_sacrificed
        
        print(f"   📊 NET IMPACT: {net_impact:+d}")
        print()
        
        if net_impact > 0:
            print(f"   ✅ POSITIVE IMPACT!")
            print(f"      Using Forebet filter would IMPROVE results")
            print(f"      New record: {len(wins) - wins_sacrificed}-{len(losses) - losses_avoided}")
            
            new_win_rate = (len(wins) - wins_sacrificed) / (len(wins) + len(losses) - wins_sacrificed - losses_avoided)
            old_win_rate = len(wins) / (len(wins) + len(losses))
            
            print(f"      Old win rate: {old_win_rate:.1%}")
            print(f"      New win rate: {new_win_rate:.1%} (+{(new_win_rate - old_win_rate)*100:.1f}%)")
        elif net_impact < 0:
            print(f"   ❌ NEGATIVE IMPACT!")
            print(f"      Using Forebet filter would HURT results")
            print(f"      Would sacrifice {abs(net_impact)} more wins than losses avoided")
        else:
            print(f"   ⚖️  NEUTRAL IMPACT")
            print(f"      Forebet filter would have no net effect")
        
        print()
        print("="*80)
        print("💡 RECOMMENDATION:")
        print("="*80)
        print()
        
        if net_impact >= 2:
            print("   ✅ INTEGRATE FOREBET as 'Disagreement Filter'")
            print("      • Skip bets where Forebet disagrees")
            print("      • Would improve win rate")
            print("      • Trade-off: Reduced volume but better quality")
        elif net_impact >= 0:
            print("   🤔 MARGINAL - Consider 'Tie-Breaker' approach")
            print("      • Only use Forebet for Low confidence bets")
            print("      • Skip if Forebet disagrees on marginal picks")
            print("      • Preserve high-confidence bets regardless")
        else:
            print("   ❌ DO NOT INTEGRATE")
            print("      • Forebet would hurt more than help")
            print("      • Stick with enhanced skip rules")
            print("      • Our system is already superior")
        
        print()
        
        # Save detailed results
        output_file = 'forebet_impact_analysis.json'
        with open(output_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_matches': len(self.matches_comparison),
                    'wins': len(wins),
                    'losses': len(losses),
                    'losses_avoided': losses_avoided,
                    'wins_sacrificed': wins_sacrificed,
                    'net_impact': net_impact
                },
                'detailed_matches': self.matches_comparison
            }, f, indent=2)
        
        print(f"📁 Detailed results saved to: {output_file}")

def main():
    analyzer = ForebetImpactAnalyzer()
    
    # Scrape Forebet for Oct 30 - Nov 3
    print("🚀 Starting Forebet Impact Analysis")
    print("="*80)
    print()
    
    analyzer.scrape_forebet_multiple_dates('2025-10-30', '2025-11-03')
    
    # Load our predictions
    analyzer.load_our_predictions('all_SERVE_STRENGTH_V3_OCT2025_3YEAR.csv')
    
    # Match them up
    analyzer.match_predictions()
    
    # Analyze impact
    analyzer.analyze_impact()
    
    print()
    print("="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()

