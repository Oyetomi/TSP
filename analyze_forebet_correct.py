#!/usr/bin/env python3
"""
Analyze Forebet's predictions (CORRECTLY parsed)
Compare with our system's predictions to see impact
"""

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from datetime import datetime, timedelta
import csv

def parse_forebet_predictions(html_file):
    """Parse Forebet predictions from saved HTML"""
    
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    predictions = []
    
    # Find all match rows
    match_rows = soup.find_all('div', class_='rcnt')
    
    print(f"📊 Found {len(match_rows)} match rows\n")
    
    for row in match_rows:
        try:
            # Get player names
            tnms = row.find('div', class_='tnms')
            if not tnms:
                continue
                
            home_team = tnms.find('span', class_='homeTeam')
            away_team = tnms.find('span', class_='awayTeam')
            
            if not home_team or not away_team:
                continue
            
            player1 = home_team.get_text(strip=True)
            player2 = away_team.get_text(strip=True)
            
            # Get probabilities
            fprc = row.find('div', class_='fprc')
            if fprc:
                probs = fprc.find_all('span')
                if len(probs) >= 2:
                    # Check which has 'fpr' class (the predicted winner)
                    if 'fpr' in probs[0].get('class', []):
                        prob1 = probs[0].get_text(strip=True)
                        prob2 = probs[1].get_text(strip=True)
                        forebet_predicted = player1
                    else:
                        prob1 = probs[1].get_text(strip=True)
                        prob2 = probs[0].get_text(strip=True)
                        forebet_predicted = player2
                else:
                    prob1 = prob2 = "N/A"
                    forebet_predicted = None
            else:
                prob1 = prob2 = "N/A"
                forebet_predicted = None
            
            # Get prediction div (predict_y, predict_no, or predict)
            predict_div = row.find('div', class_=['predict_y', 'predict_no', 'predict'])
            
            if not predict_div:
                continue
            
            # Determine status
            if 'predict_y' in predict_div.get('class', []):
                status = 'CORRECT'
            elif 'predict_no' in predict_div.get('class', []):
                status = 'WRONG'
            else:
                status = 'UNFINISHED'
                continue  # Skip unfinished matches
            
            # Get actual result
            ex_sc = row.find('div', class_='ex_sc')
            if ex_sc:
                result_text = ex_sc.get_text(strip=True)
                result = result_text.replace('\n', '-')
            else:
                result = "N/A"
            
            predictions.append({
                'player1': player1,
                'player2': player2,
                'forebet_predicted': forebet_predicted,
                'prob1': prob1,
                'prob2': prob2,
                'status': status,
                'result': result
            })
            
        except Exception as e:
            print(f"⚠️ Error parsing row: {e}")
            continue
    
    return predictions

def load_our_predictions(csv_file):
    """Load our system's predictions"""
    predictions = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            predictions.append(row)
    
    return predictions

def fuzzy_match_players(fb_p1, fb_p2, our_p1, our_p2, threshold=70):
    """
    Match players between Forebet and our system using fuzzy matching
    Returns True if match found, False otherwise
    """
    # Try direct match (p1 vs p1, p2 vs p2)
    score1 = max(
        fuzz.ratio(fb_p1.lower(), our_p1.lower()),
        fuzz.partial_ratio(fb_p1.lower(), our_p1.lower()),
        fuzz.token_sort_ratio(fb_p1.lower(), our_p1.lower())
    )
    score2 = max(
        fuzz.ratio(fb_p2.lower(), our_p2.lower()),
        fuzz.partial_ratio(fb_p2.lower(), our_p2.lower()),
        fuzz.token_sort_ratio(fb_p2.lower(), our_p2.lower())
    )
    
    if score1 >= threshold and score2 >= threshold:
        return True
    
    # Try reversed match (p1 vs p2, p2 vs p1)
    score1_rev = max(
        fuzz.ratio(fb_p1.lower(), our_p2.lower()),
        fuzz.partial_ratio(fb_p1.lower(), our_p2.lower()),
        fuzz.token_sort_ratio(fb_p1.lower(), our_p2.lower())
    )
    score2_rev = max(
        fuzz.ratio(fb_p2.lower(), our_p1.lower()),
        fuzz.partial_ratio(fb_p2.lower(), our_p1.lower()),
        fuzz.token_sort_ratio(fb_p2.lower(), our_p1.lower())
    )
    
    if score1_rev >= threshold and score2_rev >= threshold:
        return True
    
    return False

def compare_predictions():
    """Compare Forebet with our system"""
    
    print("=" * 80)
    print("🎯 FOREBET ACCURACY ANALYSIS (CORRECT PARSING)")
    print("=" * 80)
    print()
    
    # Parse Forebet predictions
    forebet_preds = parse_forebet_predictions('forebet_predictions_today.html')
    
    print(f"✅ Parsed {len(forebet_preds)} finished Forebet predictions\n")
    
    # Calculate Forebet accuracy
    correct = sum(1 for p in forebet_preds if p['status'] == 'CORRECT')
    wrong = sum(1 for p in forebet_preds if p['status'] == 'WRONG')
    accuracy = (correct / (correct + wrong)) * 100 if (correct + wrong) > 0 else 0
    
    print(f"📊 FOREBET PERFORMANCE:")
    print(f"   ✅ Correct: {correct}")
    print(f"   ❌ Wrong: {wrong}")
    print(f"   📈 Accuracy: {accuracy:.1f}%")
    print()
    
    # Load our predictions
    our_preds = load_our_predictions('tennis_predictions.csv')
    print(f"📋 Loaded {len(our_preds)} of our predictions\n")
    
    # Find matches
    matches = []
    for fb in forebet_preds:
        for ours in our_preds:
            if fuzzy_match_players(
                fb['player1'], fb['player2'],
                ours['player1_name'], ours['player2_name']
            ):
                matches.append({
                    'forebet': fb,
                    'ours': ours
                })
                break
    
    print(f"🔗 Matched {len(matches)} predictions between systems\n")
    print("=" * 80)
    print()
    
    if len(matches) == 0:
        print("❌ No matches found between systems")
        return
    
    # Analyze matches
    print("📋 DETAILED COMPARISON:")
    print()
    
    agreement_count = 0
    disagreement_count = 0
    
    for i, match in enumerate(matches, 1):
        fb = match['forebet']
        ours = match['ours']
        
        # Determine our predicted winner
        our_predicted = ours['predicted_winner']
        
        # Check if predictions agree (fuzzy match on names)
        fb_predicted_lower = fb['forebet_predicted'].lower() if fb['forebet_predicted'] else ""
        our_predicted_lower = our_predicted.lower()
        
        agreement_score = max(
            fuzz.ratio(fb_predicted_lower, our_predicted_lower),
            fuzz.partial_ratio(fb_predicted_lower, our_predicted_lower),
            fuzz.token_sort_ratio(fb_predicted_lower, our_predicted_lower)
        )
        
        agree = agreement_score >= 70
        
        if agree:
            agreement_count += 1
            status_emoji = "✅"
        else:
            disagreement_count += 1
            status_emoji = "❌"
        
        print(f"{i}. {fb['player1']} vs {fb['player2']}")
        print(f"   Forebet predicted: {fb['forebet_predicted']} ({fb['status']})")
        print(f"   We predicted: {our_predicted} ({ours.get('confidence', 'N/A')} conf)")
        print(f"   {status_emoji} {'AGREE' if agree else 'DISAGREE'}")
        print()
    
    print("=" * 80)
    print()
    print("📊 AGREEMENT ANALYSIS:")
    print(f"   ✅ Agreements: {agreement_count}")
    print(f"   ❌ Disagreements: {disagreement_count}")
    if len(matches) > 0:
        agreement_rate = (agreement_count / len(matches)) * 100
        print(f"   📈 Agreement rate: {agreement_rate:.1f}%")
    print()
    
    # Impact analysis
    print("=" * 80)
    print("💡 WHAT THIS MEANS:")
    print()
    print(f"   Forebet accuracy: {accuracy:.1f}%")
    print(f"   Agreement rate: {agreement_rate:.1f}%")
    print()
    
    if agreement_rate >= 70:
        print("   ✅ HIGH AGREEMENT: Forebet could reinforce our picks")
    elif agreement_rate >= 50:
        print("   ⚠️ MODERATE AGREEMENT: Use with caution")
    else:
        print("   ❌ LOW AGREEMENT: Systems have different approaches")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    compare_predictions()

