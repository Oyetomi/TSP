#!/usr/bin/env python3
"""
Compare Forebet's predictions today with our predictions today
to estimate agreement rate
"""

import csv
from curl_cffi import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

def scrape_forebet():
    """Scrape Forebet predictions"""
    url = "https://www.forebet.com/en/tennis/predictions-today"
    
    print("📥 Scraping Forebet...")
    
    response = requests.get(url, impersonate="chrome110", timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    predictions = []
    matches = soup.find_all('div', class_='rcnt')
    
    for match in matches:
        try:
            team_spans = match.find_all('span', class_='homeTeam') + match.find_all('span', class_='awayTeam')
            if len(team_spans) < 2:
                continue
            
            player1 = team_spans[0].get_text(strip=True)
            player2 = team_spans[1].get_text(strip=True)
            
            predict_div = match.find('div', class_='predict')
            if not predict_div:
                continue
            
            prediction = predict_div.get_text(strip=True)
            
            # Determine winner (1 or 2)
            if prediction == "1":
                winner = player1
            elif prediction == "2":
                winner = player2
            else:
                winner = None
            
            predictions.append({
                'player1': player1,
                'player2': player2,
                'prediction': prediction,
                'winner': winner
            })
        except:
            continue
    
    print(f"   ✓ Found {len(predictions)} Forebet predictions")
    return predictions

def load_our_predictions():
    """Load our predictions from tennis_predictions.csv"""
    print("📥 Loading our predictions...")
    
    predictions = []
    with open('tennis_predictions.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['date'] == '2025-11-03':  # Today only
                predictions.append({
                    'player1': row['player1_name'],
                    'player2': row['player2_name'],
                    'predicted_winner': row['predicted_winner'],
                    'confidence': row['confidence']
                })
    
    print(f"   ✓ Loaded {len(predictions)} of our predictions")
    return predictions

def fuzzy_match(name1, name2, threshold=75):
    """Check if names match"""
    name1_parts = name1.split()
    name2_parts = name2.split()
    
    if fuzz.ratio(name1.lower(), name2.lower()) >= threshold:
        return True
    
    if len(name1_parts) > 0 and len(name2_parts) > 0:
        last1 = name1_parts[-1].lower()
        last2 = name2_parts[-1].lower()
        if fuzz.ratio(last1, last2) >= 85:
            return True
    
    return False

def compare_predictions(forebet_preds, our_preds):
    """Compare predictions"""
    print()
    print("="*80)
    print("🔍 COMPARING PREDICTIONS:")
    print("="*80)
    print()
    
    matched = 0
    agreed = 0
    disagreed = 0
    
    comparisons = []
    
    for our in our_preds:
        for forebet in forebet_preds:
            # Check if same match
            p1_match = (
                fuzzy_match(our['player1'], forebet['player1']) or
                fuzzy_match(our['player1'], forebet['player2'])
            )
            p2_match = (
                fuzzy_match(our['player2'], forebet['player1']) or
                fuzzy_match(our['player2'], forebet['player2'])
            )
            
            if p1_match and p2_match and forebet['winner']:
                matched += 1
                
                # Determine agreement
                forebet_winner_normalized = None
                if fuzzy_match(forebet['winner'], our['player1']):
                    forebet_winner_normalized = our['player1']
                elif fuzzy_match(forebet['winner'], our['player2']):
                    forebet_winner_normalized = our['player2']
                
                agreement = (forebet_winner_normalized == our['predicted_winner'])
                
                if agreement:
                    agreed += 1
                else:
                    disagreed += 1
                
                comparisons.append({
                    'our_p1': our['player1'],
                    'our_p2': our['player2'],
                    'our_pick': our['predicted_winner'],
                    'our_confidence': our['confidence'],
                    'forebet_pick': forebet_winner_normalized,
                    'agreement': agreement
                })
                
                break
    
    # Display results
    print(f"Matched predictions: {matched}")
    print(f"   ✅ Agreed: {agreed}")
    print(f"   ❌ Disagreed: {disagreed}")
    print()
    
    if matched > 0:
        agreement_rate = agreed / matched
        print(f"Agreement rate: {agreement_rate:.1%}")
    else:
        agreement_rate = 0
        print("No matches found for comparison")
    
    print()
    print("="*80)
    print("DETAILED COMPARISONS:")
    print("="*80)
    print()
    
    for i, comp in enumerate(comparisons, 1):
        symbol = "✅" if comp['agreement'] else "❌"
        print(f"{i}. {comp['our_p1']} vs {comp['our_p2']}")
        print(f"   Our pick: {comp['our_pick']} ({comp['our_confidence']})")
        print(f"   Forebet pick: {comp['forebet_pick']}")
        print(f"   {symbol} {'AGREE' if comp['agreement'] else 'DISAGREE'}")
        print()
    
    print("="*80)
    print()
    
    # Extrapolate to past 48 matches
    if matched > 0:
        print("📊 EXTRAPOLATION TO PAST 48 MATCHES:")
        print()
        print(f"   Agreement rate (today): {agreement_rate:.1%}")
        print()
        print(f"   If this rate held for our 48 matches:")
        print(f"   • Agreed: {48 * agreement_rate:.0f} matches")
        print(f"   • Disagreed: {48 * (1-agreement_rate):.0f} matches")
        print()
        print(f"   Assuming Forebet disagreed with all 7 losses:")
        print(f"   • Wins Forebet agreed with: {41 * agreement_rate:.0f}")
        print(f"   • Wins Forebet disagreed with: {41 * (1-agreement_rate):.0f}")
        print()
        
        wins_disagreed = 41 * (1 - agreement_rate)
        net_impact = 7 - wins_disagreed
        
        print(f"   NET IMPACT: {net_impact:+.0f}")
        print(f"   • Losses avoided: 7")
        print(f"   • Wins sacrificed: {wins_disagreed:.0f}")
        print()
        
        if net_impact > 0:
            print(f"   ✅ POSITIVE IMPACT!")
            print(f"      Using Forebet would improve results")
        elif abs(net_impact) < 1:
            print(f"   ⚖️  NEUTRAL IMPACT")
            print(f"      Using Forebet would have minimal effect")
        else:
            print(f"   ❌ NEGATIVE IMPACT!")
            print(f"      Using Forebet would hurt results")
        print()
        print("="*80)

if __name__ == "__main__":
    forebet_preds = scrape_forebet()
    our_preds = load_our_predictions()
    compare_predictions(forebet_preds, our_preds)

