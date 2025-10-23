#!/usr/bin/env python3
"""
Simple Loss Analysis - No Dependencies
=====================================

Analyzes losing predictions to find patterns in what actual winners had
that our HOT_STREAK_74PCT_BACKUP model undervalued.
"""

import csv
import json
import re
from collections import defaultdict

def load_csv_as_dict(filename):
    """Load CSV file as list of dictionaries"""
    data = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    return data

def parse_match_name(match_str):
    """Parse 'Player1 vs Player2' format"""
    if ' vs ' in match_str:
        return match_str.split(' vs ')
    return None, None

def find_matching_prediction(validation_row, predictions_data):
    """Find the matching prediction row for a validation result"""
    match_name = validation_row['Match']
    p1, p2 = parse_match_name(match_name)
    
    if not p1 or not p2:
        return None
    
    # Search for matching prediction
    for pred_row in predictions_data:
        pred_p1 = pred_row.get('player1_name', '')
        pred_p2 = pred_row.get('player2_name', '')
        
        # Check if names match (allowing partial matches)
        if ((p1.strip() in pred_p1 or pred_p1 in p1.strip()) and 
            (p2.strip() in pred_p2 or pred_p2 in p2.strip())):
            return pred_row
        
        # Check reverse order
        if ((p1.strip() in pred_p2 or pred_p2 in p1.strip()) and 
            (p2.strip() in pred_p1 or pred_p1 in p2.strip())):
            return pred_row
    
    return None

def extract_percentage(text, pattern_prefix):
    """Extract percentage value from text"""
    try:
        if pattern_prefix in text:
            # Look for pattern like "P1: 65.4%" or "P2: 32.1%"
            match = re.search(rf'{pattern_prefix} (\d+\.?\d*)%', text)
            if match:
                return float(match.group(1))
    except:
        pass
    return None

def extract_numeric_value(text, pattern_prefix):
    """Extract numeric value from text"""
    try:
        if pattern_prefix in text:
            # Look for pattern like "P1: 25.4" or "P2: 18.3"
            match = re.search(rf'{pattern_prefix} (\d+\.?\d*)', text)
            if match:
                return float(match.group(1))
    except:
        pass
    return None

def parse_player_metrics(metrics_str, player_prefix):
    """Parse metrics for a specific player (P1 or P2)"""
    metrics = {}
    
    try:
        # Remove quotes and parse as dict
        metrics_str = metrics_str.replace("'", '"')
        data = json.loads(metrics_str)
        
        # Extract set performance
        set_perf = data.get('set_performance', '')
        val = extract_percentage(set_perf, player_prefix)
        if val: metrics['set_performance'] = val
        
        # Extract recent form
        form = data.get('form', '')
        val = extract_numeric_value(form, player_prefix)
        if val: metrics['recent_form'] = val
        
        # Extract surface performance
        surface = data.get('surface', '')
        val = extract_percentage(surface, player_prefix)
        if val: metrics['surface_performance'] = val
        
        # Extract mental toughness
        mental = data.get('mental_toughness', '')
        val = extract_percentage(mental, player_prefix)
        if val: metrics['mental_toughness'] = val
        
        # Extract clutch performance
        clutch = data.get('clutch', '')
        val = extract_percentage(clutch, player_prefix)
        if val: metrics['clutch_performance'] = val
        
        # Extract return of serve
        return_serve = data.get('return_serve', '')
        val = extract_percentage(return_serve, player_prefix)
        if val: metrics['return_of_serve'] = val
        
        # Extract momentum
        momentum = data.get('momentum', '')
        val = extract_numeric_value(momentum, player_prefix)
        if val: metrics['momentum'] = val
        
    except Exception as e:
        print(f"Error parsing metrics: {e}")
    
    return metrics

def analyze_single_loss(validation_row, prediction_row):
    """Analyze a single prediction failure"""
    
    try:
        # Get actual match result
        actual_sets = validation_row['Actual_Sets']
        if not actual_sets or '-' not in actual_sets:
            return None
        
        p1_sets, p2_sets = map(int, actual_sets.split('-'))
        actual_winner_is_p1 = p1_sets > p2_sets
        
        # Get predicted winner
        predicted_winner = validation_row['Predicted_Winner']
        player1_name = prediction_row['player1_name']
        player2_name = prediction_row['player2_name']
        
        # Determine if predicted winner was P1 or P2
        predicted_is_p1 = predicted_winner in player1_name or player1_name in predicted_winner
        
        # If prediction and actual match, this isn't a reversal error
        if predicted_is_p1 == actual_winner_is_p1:
            return None
        
        # Parse metrics for both players
        metrics_str = prediction_row.get('weight_breakdown', '{}')
        p1_metrics = parse_player_metrics(metrics_str, 'P1:')
        p2_metrics = parse_player_metrics(metrics_str, 'P2:')
        
        # Determine winner vs predicted winner metrics
        if actual_winner_is_p1:
            winner_metrics = p1_metrics
            loser_metrics = p2_metrics
            winner_name = player1_name
            predicted_name = player2_name
        else:
            winner_metrics = p2_metrics
            loser_metrics = p1_metrics
            winner_name = player2_name
            predicted_name = player1_name
        
        # Calculate advantages the actual winner had
        advantages = {}
        
        for metric in ['set_performance', 'recent_form', 'surface_performance', 
                      'mental_toughness', 'clutch_performance', 'return_of_serve', 'momentum']:
            winner_val = winner_metrics.get(metric, 0)
            loser_val = loser_metrics.get(metric, 0)
            
            if winner_val > loser_val:
                advantages[metric] = winner_val - loser_val
        
        return {
            'match': f"{player1_name} vs {player2_name}",
            'predicted': predicted_name,
            'actual_winner': winner_name,
            'confidence': validation_row.get('Predicted_Prob', 'N/A'),
            'advantages': advantages,
            'winner_metrics': winner_metrics,
            'predicted_metrics': loser_metrics
        }
        
    except Exception as e:
        print(f"Error analyzing loss: {e}")
        return None

def main():
    print("🔍 SIMPLE LOSS ANALYSIS - HOT_STREAK_74PCT_BACKUP")
    print("="*60)
    
    # Load data
    print("📊 Loading validation results...")
    validation_data = load_csv_as_dict('logs/validation_all_HOT_STREAK_74PCT_BACKUP_20250929_090501.csv')
    
    print("📊 Loading prediction data...")
    prediction_data = load_csv_as_dict('all_HOT_STREAK_74PCT_BACKUP.csv')
    
    if not validation_data or not prediction_data:
        print("❌ Could not load data files!")
        return
    
    # Find all losses
    losses = [row for row in validation_data if row.get('Prediction_Correct') == 'False']
    print(f"🎯 Found {len(losses)} losing predictions")
    
    # Analyze each loss
    analyzed_losses = []
    successful_analyses = 0
    
    for loss_row in losses:
        prediction_row = find_matching_prediction(loss_row, prediction_data)
        if prediction_row:
            analysis = analyze_single_loss(loss_row, prediction_row)
            if analysis:
                analyzed_losses.append(analysis)
                successful_analyses += 1
    
    print(f"✅ Successfully analyzed {successful_analyses} losses")
    
    # Aggregate patterns
    print("\n🏆 WHAT ACTUAL WINNERS HAD THAT WE UNDERVALUED:")
    print("="*60)
    
    factor_advantages = defaultdict(list)
    
    for analysis in analyzed_losses:
        for factor, advantage in analysis['advantages'].items():
            if advantage > 5:  # Only significant advantages (>5%)
                factor_advantages[factor].append(advantage)
    
    # Sort by frequency and impact
    for factor in sorted(factor_advantages.keys(), 
                        key=lambda x: len(factor_advantages[x]), reverse=True):
        values = factor_advantages[factor]
        if len(values) >= 3:  # At least 3 cases
            avg_advantage = sum(values) / len(values)
            print(f"   📈 {factor.replace('_', ' ').title()}: "
                  f"{avg_advantage:.1f}% avg advantage ({len(values)} cases)")
    
    # Show specific examples
    print("\n🔍 NOTABLE FAILURE EXAMPLES:")
    print("="*60)
    
    for i, analysis in enumerate(analyzed_losses[:8]):  # Show first 8
        print(f"\n   {i+1}. {analysis['match']}")
        print(f"      ❌ Predicted: {analysis['predicted']} ({analysis['confidence']})")
        print(f"      ✅ Actual: {analysis['actual_winner']}")
        
        # Show top advantages
        top_advantages = sorted(analysis['advantages'].items(), 
                              key=lambda x: x[1], reverse=True)[:2]
        if top_advantages:
            advantages_str = ", ".join([f"{factor.replace('_', ' ')} (+{val:.1f}%)" 
                                      for factor, val in top_advantages])
            print(f"      🎯 Winner had: {advantages_str}")
    
    print(f"\n💡 SUMMARY: {successful_analyses} losses analyzed")
    print("🔧 Consider increasing weights for factors where winners consistently had advantages!")

if __name__ == "__main__":
    main()
