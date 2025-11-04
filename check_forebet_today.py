#!/usr/bin/env python3
"""
Quick Forebet check - scrape today's predictions and see what they think
"""

from curl_cffi import requests
from bs4 import BeautifulSoup

def scrape_forebet_today():
    """Scrape Forebet predictions for today"""
    url = "https://www.forebet.com/en/tennis/predictions-today"
    
    print("📥 Scraping Forebet today...")
    print(f"   URL: {url}")
    print()
    
    try:
        response = requests.get(
            url,
            impersonate="chrome110",
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all match rows
        matches = soup.find_all('div', class_='rcnt')
        
        print(f"✅ Found {len(matches)} matches")
        print()
        print("="*80)
        print("FOREBET PREDICTIONS TODAY:")
        print("="*80)
        print()
        
        for i, match in enumerate(matches[:20], 1):  # Show first 20
            try:
                # Extract team names
                team_spans = match.find_all('span', class_='homeTeam') + match.find_all('span', class_='awayTeam')
                if len(team_spans) < 2:
                    continue
                
                player1 = team_spans[0].get_text(strip=True)
                player2 = team_spans[1].get_text(strip=True)
                
                # Extract prediction
                predict_div = match.find('div', class_='predict')
                prediction = predict_div.get_text(strip=True) if predict_div else "N/A"
                
                # Extract probabilities if available
                prob_spans = match.find_all('span', class_='fprc')
                probs = [p.get_text(strip=True) for p in prob_spans] if prob_spans else []
                
                print(f"{i}. {player1} vs {player2}")
                print(f"   Forebet predicts: {prediction}")
                if probs:
                    print(f"   Probabilities: {', '.join(probs)}")
                print()
            
            except Exception as e:
                continue
        
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    scrape_forebet_today()

