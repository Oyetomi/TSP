#!/usr/bin/env python3
"""
Analysis of Prediction Failures
===============================

Analyzes losing bets to identify what characteristics the actual winners 
had in common that our HOT_STREAK_74PCT_BACKUP model missed.
"""

import pandas as pd
import json
import re
from collections import defaultdict, Counter

def parse_player_stats(stats_str):
    """Parse the player statistics JSON string"""
    try:
        return json.loads(stats_str.replace("'", '"'))
    except:
        return {}

def extract_losses_with_details():
    """Extract losing predictions with detailed player analysis"""
    
    # Load validation results
    validation_df = pd.read_csv('logs/validation_all_HOT_STREAK_74PCT_BACKUP_20250929_090501.csv')
    
    # Load original predictions with full player data
    predictions_df = pd.read_csv('all_HOT_STREAK_74PCT_BACKUP.csv')
    
    # Get only the losing bets
    losses = validation_df[validation_df['Prediction_Correct'] == False].copy()
    
    print(f"🔍 ANALYZING {len(losses)} LOSING PREDICTIONS")
    print("="*60)
    
    analysis_results = {
        'winner_advantages': defaultdict(list),
        'loser_weaknesses': defaultdict(list),
        'pattern_analysis': defaultdict(int),
        'detailed_failures': []
    }
    
    for _, loss in losses.iterrows():
        match_name = loss['Match']
        predicted_winner = loss['Predicted_Winner']
        
        # Find corresponding match in predictions
        match_row = predictions_df[
            (predictions_df['Player 1'].str.contains(match_name.split(' vs ')[0], na=False) |
             predictions_df['Player 2'].str.contains(match_name.split(' vs ')[0], na=False)) &
            (predictions_df['Player 1'].str.contains(match_name.split(' vs ')[1], na=False) |
             predictions_df['Player 2'].str.contains(match_name.split(' vs ')[1], na=False))
        ]
        
        if match_row.empty:
            continue
            
        match_data = match_row.iloc[0]
        
        # Determine who actually won based on sets
        actual_sets = loss['Actual_Sets']
        if pd.isna(actual_sets):
            continue
            
        p1_sets, p2_sets = map(int, actual_sets.split('-'))
        actual_winner = match_data['Player 1'] if p1_sets > p2_sets else match_data['Player 2']
        
        # Parse player statistics
        try:
            player_stats = parse_player_stats(match_data['Performance Metrics'])
        except:
            continue
            
        # Analyze what the actual winner had that we missed
        failure_analysis = analyze_individual_failure(
            match_data, predicted_winner, actual_winner, player_stats, loss
        )
        
        if failure_analysis:
            analysis_results['detailed_failures'].append(failure_analysis)
            
            # Aggregate patterns
            for advantage in failure_analysis['winner_advantages']:
                analysis_results['winner_advantages'][advantage['factor']].append(advantage['value'])
                
            for weakness in failure_analysis['predicted_winner_weaknesses']:
                analysis_results['loser_weaknesses'][weakness['factor']].append(weakness['value'])
                
            analysis_results['pattern_analysis'][failure_analysis['primary_miss']] += 1
    
    return analysis_results

def analyze_individual_failure(match_data, predicted_winner, actual_winner, player_stats, loss_info):
    """Analyze a single prediction failure in detail"""
    
    try:
        # Determine if P1 or P2 was predicted vs actual winner
        p1_name = match_data['Player 1']
        p2_name = match_data['Player 2']
        
        predicted_is_p1 = predicted_winner in p1_name or p1_name in predicted_winner
        actual_is_p1 = actual_winner in p1_name or p1_name in actual_winner
        
        if predicted_is_p1 == actual_is_p1:
            return None  # Not a clear reversal
            
        # Extract key metrics for both players
        p1_metrics = extract_player_metrics(player_stats, 'P1:', match_data)
        p2_metrics = extract_player_metrics(player_stats, 'P2:', match_data)
        
        # Determine winner/loser metrics
        if actual_is_p1:
            winner_metrics = p1_metrics
            loser_metrics = p2_metrics
            winner_name = p1_name
            predicted_name = p2_name
        else:
            winner_metrics = p2_metrics
            loser_metrics = p1_metrics
            winner_name = p2_name
            predicted_name = p1_name
            
        # Identify what the actual winner had that we undervalued
        winner_advantages = []
        predicted_weaknesses = []
        
        # Compare key factors
        factors_to_check = [
            ('set_performance', 'Set Performance'),
            ('form', 'Recent Form'),
            ('surface', 'Surface Performance'),
            ('mental_toughness', 'Mental Toughness'),
            ('return_serve', 'Return of Serve'),
            ('clutch', 'Clutch Performance'),
            ('momentum', 'Momentum')
        ]
        
        primary_miss = "unknown"
        
        for factor_key, factor_name in factors_to_check:
            winner_val = winner_metrics.get(factor_key, 0)
            loser_val = loser_metrics.get(factor_key, 0)
            
            if winner_val > loser_val:
                advantage_size = winner_val - loser_val
                winner_advantages.append({
                    'factor': factor_name,
                    'value': advantage_size,
                    'winner_score': winner_val,
                    'predicted_score': loser_val
                })
                
                # Identify primary miss (largest advantage we ignored)
                if advantage_size > 15 and primary_miss == "unknown":  # 15% threshold
                    primary_miss = f"undervalued_{factor_name.lower().replace(' ', '_')}"
            
            elif loser_val > winner_val:
                weakness_size = loser_val - winner_val
                predicted_weaknesses.append({
                    'factor': factor_name,
                    'value': weakness_size,
                    'predicted_score': loser_val,
                    'winner_score': winner_val
                })
        
        return {
            'match': f"{p1_name} vs {p2_name}",
            'predicted_winner': predicted_name,
            'actual_winner': winner_name,
            'confidence': loss_info.get('Predicted_Prob', 'N/A'),
            'winner_advantages': winner_advantages,
            'predicted_winner_weaknesses': predicted_weaknesses,
            'primary_miss': primary_miss,
            'winner_metrics': winner_metrics,
            'predicted_metrics': loser_metrics
        }
        
    except Exception as e:
        print(f"Error analyzing {match_data['Player 1']} vs {match_data['Player 2']}: {e}")
        return None

def extract_player_metrics(player_stats, prefix, match_data):
    """Extract numerical metrics for a player"""
    metrics = {}
    
    try:
        # Set Performance
        set_perf = player_stats.get('set_performance', '')
        if prefix in set_perf:
            set_match = re.search(rf'{prefix} (\d+\.?\d*)%', set_perf)
            if set_match:
                metrics['set_performance'] = float(set_match.group(1))
        
        # Recent Form
        form = player_stats.get('form', '')
        if prefix in form:
            form_match = re.search(rf'{prefix} (\d+\.?\d*)', form)
            if form_match:
                metrics['form'] = float(form_match.group(1))
        
        # Surface Performance  
        surface = player_stats.get('surface', '')
        if prefix in surface:
            surf_match = re.search(rf'{prefix} (\d+\.?\d*)%', surface)
            if surf_match:
                metrics['surface'] = float(surf_match.group(1))
        
        # Mental Toughness
        mental = player_stats.get('mental_toughness', '')
        if prefix in mental:
            mental_match = re.search(rf'{prefix} (\d+\.?\d*)%', mental)
            if mental_match:
                metrics['mental_toughness'] = float(mental_match.group(1))
        
        # Return of Serve
        return_serve = player_stats.get('return_serve', '')
        if prefix in return_serve:
            return_match = re.search(rf'{prefix} (\d+\.?\d*)%', return_serve)
            if return_match:
                metrics['return_serve'] = float(return_match.group(1))
        
        # Clutch Performance
        clutch = player_stats.get('clutch', '')
        if prefix in clutch:
            clutch_match = re.search(rf'{prefix} (\d+\.?\d*)%', clutch)
            if clutch_match:
                metrics['clutch'] = float(clutch_match.group(1))
        
        # Momentum
        momentum = player_stats.get('momentum', '')
        if prefix in momentum:
            mom_match = re.search(rf'{prefix} (\d+\.?\d*)', momentum)
            if mom_match:
                metrics['momentum'] = float(mom_match.group(1))
        
    except Exception as e:
        print(f"Error extracting metrics for {prefix}: {e}")
    
    return metrics

def print_analysis_summary(results):
    """Print comprehensive analysis summary"""
    
    print("\n🏆 ACTUAL WINNERS' COMMON ADVANTAGES")
    print("="*50)
    
    for factor, values in results['winner_advantages'].items():
        if len(values) >= 3:  # Only factors that appeared in 3+ losses
            avg_advantage = sum(values) / len(values)
            print(f"   📈 {factor}: {avg_advantage:.1f}% average advantage ({len(values)} cases)")
    
    print("\n❌ PREDICTED WINNERS' COMMON WEAKNESSES")
    print("="*50)
    
    for factor, values in results['loser_weaknesses'].items():
        if len(values) >= 3:
            avg_weakness = sum(values) / len(values)
            print(f"   📉 {factor}: {avg_weakness:.1f}% average weakness ({len(values)} cases)")
    
    print("\n🎯 PRIMARY FAILURE PATTERNS")
    print("="*50)
    
    for pattern, count in sorted(results['pattern_analysis'].items(), key=lambda x: x[1], reverse=True):
        if count >= 2:
            print(f"   🔍 {pattern.replace('_', ' ').title()}: {count} cases")
    
    print("\n📊 DETAILED FAILURE EXAMPLES")
    print("="*50)
    
    # Show top 5 most instructive failures
    for i, failure in enumerate(results['detailed_failures'][:5]):
        print(f"\n   {i+1}. {failure['match']}")
        print(f"      ❌ Predicted: {failure['predicted_winner']} ({failure['confidence']})")
        print(f"      ✅ Actual: {failure['actual_winner']}")
        
        if failure['winner_advantages']:
            print(f"      🏆 Winner had: ", end="")
            advantages = [f"{adv['factor']} (+{adv['value']:.1f}%)" 
                         for adv in failure['winner_advantages'][:2]]
            print(", ".join(advantages))

if __name__ == "__main__":
    print("🔍 TENNIS PREDICTION FAILURE ANALYSIS")
    print("="*60)
    print("📊 Analyzing what the actual winners had that we missed...")
    
    results = extract_losses_with_details()
    print_analysis_summary(results)
    
    print(f"\n✅ Analysis complete! Examined {len(results['detailed_failures'])} prediction failures.")
    print("💡 Use these insights to adjust the weight configuration!")
