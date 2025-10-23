#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from curl_cffi import requests
import json
from datetime import datetime

class LossAnalyzer:
    """Analyze losing bets to identify system weaknesses"""
    
    def __init__(self):
        self.losses = [
            {
                "match": "Jazmin Ortenzi vs Berfu Cengiz",
                "predicted_winner": "Jazmin Ortenzi", 
                "predicted_prob": "76.3%",
                "actual_result": "0-2 (lost to Berfu)",
                "player_id": None  # Need to find
            },
            {
                "match": "Maxime Janvier vs Egor Gerasimov",
                "predicted_winner": "Egor Gerasimov",
                "predicted_prob": "84.3%", 
                "actual_result": "0-2 (lost to Maxime)",
                "player_id": 57021  # From previous analysis
            },
            {
                "match": "Stefan Palosi vs Mathys Erhard", 
                "predicted_winner": "Mathys Erhard",
                "predicted_prob": "84.7%",
                "actual_result": "0-2 (lost to Stefan)",
                "player_id": None  # Need to find
            },
            {
                "match": "Quinn Vandecasteele vs James Trotter",
                "predicted_winner": "James Trotter", 
                "predicted_prob": "84.5%",
                "actual_result": "0-2 (lost to Quinn)",
                "player_id": None  # Need to find
            }
        ]
        
    def get_player_stats(self, player_id):
        """Fetch player statistics using curl_cffi"""
        try:
            url = f"https://www.matchdata-api.example.com/api/v1/team/{player_id}/year-statistics/2025"
            
            response = requests.get(
                url,
                headers={
                    'accept': '*/*',
                    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
                    'cache-control': 'no-cache',
                    'pragma': 'no-cache',
                    'priority': 'u=1, i',
                    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"macOS"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'sec-gpc': '1',
                    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
                },
                impersonate="chrome"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error {response.status_code} for player {player_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching stats for {player_id}: {e}")
            return None
    
    def analyze_surface_performance(self, stats, surface="Red clay"):
        """Analyze surface-specific performance"""
        if not stats or 'statistics' not in stats:
            return "No data"
            
        statistics = stats['statistics']
        
        for stat_group in statistics:
            if not isinstance(stat_group, dict):
                continue
                
            ground_type = stat_group.get('groundType', '')
            if ground_type == surface:
                matches = stat_group.get('matches', 0)
                wins = stat_group.get('wins', 0)
                
                if matches > 0:
                    win_rate = wins / matches
                    return f"{wins}/{matches} = {win_rate:.1%} ({matches} matches)"
                    
        return f"No {surface} data"
    
    def analyze_tiebreak_performance(self, stats):
        """Analyze tiebreak performance"""
        if not stats or 'statistics' not in stats:
            return "No data"
            
        # Look for overall tiebreak stats (not surface-specific)
        statistics = stats['statistics']
        
        for stat_group in statistics:
            if not isinstance(stat_group, dict):
                continue
                
            # Overall stats usually don't have groundType
            if 'groundType' not in stat_group or not stat_group.get('groundType'):
                tb_won = stat_group.get('tiebreaksWon', 0)
                tb_lost = stat_group.get('tiebreakLosses', 0)
                tb_total = tb_won + tb_lost
                
                if tb_total > 0:
                    tb_rate = tb_won / tb_total
                    return f"{tb_won}/{tb_total} = {tb_rate:.1%} ({tb_total} tiebreaks)"
                    
        return "No tiebreak data"
    
    def analyze_loss(self, loss_info):
        """Analyze a single loss"""
        print(f"\n🔍 ANALYZING: {loss_info['match']}")
        print(f"   Predicted: {loss_info['predicted_winner']} ({loss_info['predicted_prob']})")
        print(f"   Actual: {loss_info['actual_result']}")
        print(f"   " + "="*60)
        
        if not loss_info['player_id']:
            print(f"   ❌ Player ID not found - need manual lookup")
            return
            
        # Get player statistics
        stats = self.get_player_stats(loss_info['player_id'])
        
        if not stats:
            print(f"   ❌ No statistics available")
            return
            
        # Analyze different aspects
        surface_perf = self.analyze_surface_performance(stats, "Red clay")
        tiebreak_perf = self.analyze_tiebreak_performance(stats)
        
        print(f"   🏟️ Red Clay Performance: {surface_perf}")
        print(f"   🏆 Tiebreak Performance: {tiebreak_perf}")
        
        # Analyze sample sizes
        if "matches)" in surface_perf:
            matches_str = surface_perf.split("(")[1].split(" matches")[0]
            try:
                matches = int(matches_str)
                if matches < 10:
                    print(f"   ⚠️ LOW SAMPLE SIZE: Only {matches} clay matches!")
                elif matches < 20:
                    print(f"   ⚠️ MODERATE SAMPLE: {matches} clay matches")
                else:
                    print(f"   ✅ GOOD SAMPLE: {matches} clay matches")
            except:
                pass
                
        if "tiebreaks)" in tiebreak_perf:
            tb_str = tiebreak_perf.split("(")[1].split(" tiebreaks")[0]
            try:
                tb_count = int(tb_str)
                if tb_count <= 2:
                    print(f"   ⚠️ EXTREME TIEBREAK UNCERTAINTY: Only {tb_count} tiebreaks!")
                elif tb_count < 5:
                    print(f"   ⚠️ LOW TIEBREAK SAMPLE: {tb_count} tiebreaks")
                else:
                    print(f"   ✅ REASONABLE TIEBREAK SAMPLE: {tb_count} tiebreaks")
            except:
                pass
    
    def analyze_all_losses(self):
        """Analyze all current losses"""
        print("🎾 COMPREHENSIVE LOSS ANALYSIS")
        print("="*70)
        print(f"Analyzing {len(self.losses)} losing bets from recent validation...")
        
        for loss in self.losses:
            self.analyze_loss(loss)
            
        print(f"\n💡 PATTERN ANALYSIS:")
        print(f"   - All losses were high-confidence predictions (76-85%)")
        print(f"   - All predicted winners lost 0-2 (straight sets)")
        print(f"   - Need to check for sample size and data quality issues")

if __name__ == "__main__":
    analyzer = LossAnalyzer()
    analyzer.analyze_all_losses()
