#!/usr/bin/env python3
"""
Prediction Risk Analyzer
========================

Analyzes tennis prediction CSV files to identify high-risk bets based on
the patterns discovered from our failed predictions.
"""

import csv
import json
import re
from typing import List, Dict, Tuple

class PredictionRiskAnalyzer:
    def __init__(self):
        self.risk_factors = {
            'massive_ranking_gap': {'threshold': 75, 'weight': 0.4},
            'crowd_disagreement': {'threshold': 0.80, 'weight': 0.3}, 
            'high_confidence_upset': {'threshold': 0.70, 'weight': 0.2},
            'small_sample_size': {'threshold': 15, 'weight': 0.1}
        }
    
    def analyze_csv(self, csv_file: str) -> Dict:
        """Analyze a prediction CSV for risk factors"""
        print(f"🔍 Analyzing prediction risk in: {csv_file}")
        
        results = {
            'total_predictions': 0,
            'high_risk_predictions': [],
            'medium_risk_predictions': [],
            'risk_summary': {},
            'recommendations': []
        }
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                # Skip comment lines
                lines = [line for line in f if not line.strip().startswith('#')]
            
            if not lines:
                return results
                
            reader = csv.DictReader(lines)
            
            for row in reader:
                results['total_predictions'] += 1
                risk_analysis = self._analyze_prediction_risk(row)
                
                if risk_analysis['total_risk_score'] >= 0.7:
                    results['high_risk_predictions'].append(risk_analysis)
                elif risk_analysis['total_risk_score'] >= 0.4:
                    results['medium_risk_predictions'].append(risk_analysis)
            
            # Generate summary
            results['risk_summary'] = self._generate_risk_summary(results)
            results['recommendations'] = self._generate_recommendations(results)
            
        except Exception as e:
            print(f"❌ Error analyzing CSV: {e}")
            results['error'] = str(e)
        
        return results
    
    def _analyze_prediction_risk(self, prediction: Dict) -> Dict:
        """Analyze risk factors for a single prediction"""
        risk_analysis = {
            'match': prediction.get('Match', prediction.get('player1_name', '') + ' vs ' + prediction.get('player2_name', '')),
            'predicted_winner': prediction.get('predicted_winner', ''),
            'confidence': prediction.get('confidence', ''),
            'risk_factors': {},
            'total_risk_score': 0.0,
            'risk_level': 'LOW'
        }
        
        try:
            # Extract rankings
            p1_ranking = int(prediction.get('player1_ranking', 999))
            p2_ranking = int(prediction.get('player2_ranking', 999))
            ranking_gap = abs(p1_ranking - p2_ranking)
            
            # Check for massive ranking gap
            if ranking_gap >= self.risk_factors['massive_ranking_gap']['threshold']:
                risk_analysis['risk_factors']['massive_ranking_gap'] = {
                    'value': ranking_gap,
                    'description': f"Ranking gap: {ranking_gap} positions (#${p1_ranking} vs #{p2_ranking})",
                    'risk_score': self.risk_factors['massive_ranking_gap']['weight']
                }
                risk_analysis['total_risk_score'] += self.risk_factors['massive_ranking_gap']['weight']
            
            # Check for crowd disagreement
            crowd_data = prediction.get('weight_breakdown', '')
            if 'crowd_sentiment' in crowd_data:
                crowd_match = re.search(r'(\d+\.?\d*)% of \d+.*favor', crowd_data)
                if crowd_match:
                    crowd_pct = float(crowd_match.group(1)) / 100
                    predicted_winner = prediction.get('predicted_winner', '')
                    
                    # Check if crowd heavily favors opposite player
                    if crowd_pct >= self.risk_factors['crowd_disagreement']['threshold']:
                        # Determine if crowd disagrees with our prediction
                        match_name = risk_analysis['match']
                        if predicted_winner not in crowd_data or 'disagreement' in crowd_data.lower():
                            risk_analysis['risk_factors']['crowd_disagreement'] = {
                                'value': crowd_pct,
                                'description': f"Crowd disagreement: {crowd_pct:.1%} favor opponent",
                                'risk_score': self.risk_factors['crowd_disagreement']['weight']
                            }
                            risk_analysis['total_risk_score'] += self.risk_factors['crowd_disagreement']['weight']
            
            # Check for high confidence upset prediction
            confidence_str = prediction.get('confidence', '0%')
            if isinstance(confidence_str, str) and '%' in confidence_str:
                confidence = float(confidence_str.replace('%', '')) / 100
            else:
                confidence = float(confidence_str) if confidence_str else 0
            
            predicted_winner = prediction.get('predicted_winner', '')
            match_name = risk_analysis['match']
            
            # Determine if this is an upset (betting on lower-ranked player)
            is_upset = False
            if predicted_winner and ' vs ' in match_name:
                players = match_name.split(' vs ')
                if len(players) == 2:
                    p1_name, p2_name = players[0].strip(), players[1].strip()
                    if predicted_winner == p1_name and p1_ranking > p2_ranking:
                        is_upset = True
                    elif predicted_winner == p2_name and p2_ranking > p1_ranking:
                        is_upset = True
            
            if is_upset and confidence >= self.risk_factors['high_confidence_upset']['threshold']:
                risk_analysis['risk_factors']['high_confidence_upset'] = {
                    'value': confidence,
                    'description': f"High confidence upset: {confidence:.1%} on lower-ranked player",
                    'risk_score': self.risk_factors['high_confidence_upset']['weight']
                }
                risk_analysis['total_risk_score'] += self.risk_factors['high_confidence_upset']['weight']
            
            # Check for small sample sizes
            weight_breakdown = prediction.get('weight_breakdown', '')
            if 'sets)' in weight_breakdown:
                # Extract set counts from weight breakdown
                set_matches = re.findall(r'(\d+) sets\)', weight_breakdown)
                if set_matches:
                    min_sets = min(int(sets) for sets in set_matches)
                    if min_sets < self.risk_factors['small_sample_size']['threshold']:
                        risk_analysis['risk_factors']['small_sample_size'] = {
                            'value': min_sets,
                            'description': f"Small sample size: {min_sets} sets for performance analysis",
                            'risk_score': self.risk_factors['small_sample_size']['weight']
                        }
                        risk_analysis['total_risk_score'] += self.risk_factors['small_sample_size']['weight']
            
            # Determine risk level
            if risk_analysis['total_risk_score'] >= 0.7:
                risk_analysis['risk_level'] = 'HIGH'
            elif risk_analysis['total_risk_score'] >= 0.4:
                risk_analysis['risk_level'] = 'MEDIUM'
            else:
                risk_analysis['risk_level'] = 'LOW'
                
        except Exception as e:
            risk_analysis['error'] = str(e)
        
        return risk_analysis
    
    def _generate_risk_summary(self, results: Dict) -> Dict:
        """Generate summary of risk analysis"""
        total = results['total_predictions']
        high_risk = len(results['high_risk_predictions'])
        medium_risk = len(results['medium_risk_predictions'])
        low_risk = total - high_risk - medium_risk
        
        return {
            'total_predictions': total,
            'high_risk_count': high_risk,
            'medium_risk_count': medium_risk,
            'low_risk_count': low_risk,
            'high_risk_percentage': (high_risk / total * 100) if total > 0 else 0,
            'medium_risk_percentage': (medium_risk / total * 100) if total > 0 else 0,
            'low_risk_percentage': (low_risk / total * 100) if total > 0 else 0
        }
    
    def _generate_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on risk analysis"""
        recommendations = []
        
        high_risk = len(results['high_risk_predictions'])
        medium_risk = len(results['medium_risk_predictions'])
        total = results['total_predictions']
        
        if high_risk > 0:
            recommendations.append(f"🚨 CRITICAL: {high_risk} high-risk predictions identified - consider skipping these bets")
        
        if medium_risk > 0:
            recommendations.append(f"⚠️ WARNING: {medium_risk} medium-risk predictions - reduce stake or confidence")
        
        if high_risk + medium_risk > total * 0.3:
            recommendations.append("📊 SYSTEM ISSUE: >30% of predictions are high/medium risk - review weighting logic")
        
        # Specific pattern recommendations
        ranking_gap_risks = sum(1 for pred in results['high_risk_predictions'] 
                               if 'massive_ranking_gap' in pred['risk_factors'])
        if ranking_gap_risks > 0:
            recommendations.append(f"🎯 RANKING: {ranking_gap_risks} predictions ignore massive ranking gaps - increase ranking weight")
        
        crowd_risks = sum(1 for pred in results['high_risk_predictions'] 
                         if 'crowd_disagreement' in pred['risk_factors'])
        if crowd_risks > 0:
            recommendations.append(f"👥 CROWD: {crowd_risks} predictions against crowd consensus - add circuit breaker")
        
        return recommendations
    
    def print_analysis(self, results: Dict):
        """Print formatted risk analysis"""
        print(f"\n🎯 PREDICTION RISK ANALYSIS RESULTS")
        print("="*50)
        
        summary = results['risk_summary']
        print(f"📊 Total Predictions: {summary['total_predictions']}")
        print(f"🚨 High Risk: {summary['high_risk_count']} ({summary['high_risk_percentage']:.1f}%)")
        print(f"⚠️ Medium Risk: {summary['medium_risk_count']} ({summary['medium_risk_percentage']:.1f}%)")
        print(f"✅ Low Risk: {summary['low_risk_count']} ({summary['low_risk_percentage']:.1f}%)")
        
        if results['high_risk_predictions']:
            print(f"\n🚨 HIGH RISK PREDICTIONS:")
            for pred in results['high_risk_predictions']:
                print(f"   {pred['match']} (Risk Score: {pred['total_risk_score']:.2f})")
                for factor, details in pred['risk_factors'].items():
                    print(f"      • {details['description']}")
        
        if results['medium_risk_predictions']:
            print(f"\n⚠️ MEDIUM RISK PREDICTIONS:")
            for pred in results['medium_risk_predictions'][:5]:  # Show first 5
                print(f"   {pred['match']} (Risk Score: {pred['total_risk_score']:.2f})")
        
        if results['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in results['recommendations']:
                print(f"   {rec}")

def main():
    """Analyze prediction risk for latest CSV"""
    import glob
    import os
    
    # Find the most recent prediction file
    csv_files = glob.glob("tennis_predictions*.csv") + glob.glob("prediction_archive/tennis_predictions*.csv")
    if not csv_files:
        print("❌ No prediction CSV files found")
        return
    
    # Use the most recent file
    latest_file = max(csv_files, key=os.path.getmtime)
    
    analyzer = PredictionRiskAnalyzer()
    results = analyzer.analyze_csv(latest_file)
    analyzer.print_analysis(results)
    
    # Save results
    timestamp = latest_file.split('_')[-1].replace('.csv', '') if '_' in latest_file else 'latest'
    output_file = f"logs/risk_analysis_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed analysis saved to: {output_file}")

if __name__ == "__main__":
    main()
