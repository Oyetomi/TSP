#!/usr/bin/env python3
"""
Careful Validation Verification
==============================

Double-checking the validation logic with careful debugging
to make sure we're testing correctly.
"""

import csv
import json
import re

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

def debug_first_few_matches():
    """Debug the first few matches to verify logic"""
    
    print("🔍 DEBUGGING VALIDATION LOGIC")
    print("="*80)
    
    # Load data
    validation_data = load_csv_as_dict('logs/validation_all_HOT_STREAK_74PCT_BACKUP_20250929_090501.csv')
    prediction_data = load_csv_as_dict('all_HOT_STREAK_74PCT_BACKUP.csv')
    
    # Debug first 3 matches
    for i, val_row in enumerate(validation_data[:3]):
        match_name = val_row['Match']
        predicted_winner = val_row['Predicted_Winner']
        actual_sets = val_row['Actual_Sets']
        was_correct = val_row['Prediction_Correct']
        
        print(f"\n🔍 MATCH {i+1}: {match_name}")
        print(f"   Original Prediction: {predicted_winner}")
        print(f"   Actual Sets: {actual_sets}")
        print(f"   Was Original Correct: {was_correct}")
        
        # Parse actual winner
        if '-' in actual_sets:
            p1_sets, p2_sets = map(int, actual_sets.split('-'))
            p1_name, p2_name = match_name.split(' vs ')
            
            if p1_sets > p2_sets:
                actual_winner = p1_name.strip()
                print(f"   Actual Winner: {actual_winner} (P1)")
            else:
                actual_winner = p2_name.strip()
                print(f"   Actual Winner: {actual_winner} (P2)")
            
            # Verify the original prediction correctness
            predicted_name = predicted_winner.strip()
            actual_name = actual_winner.strip()
            
            print(f"   Predicted: '{predicted_name}'")
            print(f"   Actual: '{actual_name}'")
            print(f"   Names Match: {predicted_name == actual_name}")
            
            should_be_correct = predicted_name == actual_name
            print(f"   Should be correct: {should_be_correct}")
            print(f"   Validation says: {was_correct}")
            
            if str(should_be_correct) != was_correct:
                print(f"   ⚠️ VALIDATION MISMATCH!")
            else:
                print(f"   ✅ Validation matches our calculation")
        
        # Find matching prediction row for weight analysis
        pred_row = None
        for pred in prediction_data:
            pred_p1 = pred.get('player1_name', '')
            pred_p2 = pred.get('player2_name', '')
            
            if ((p1_name.strip() in pred_p1 or pred_p1 in p1_name.strip()) and 
                (p2_name.strip() in pred_p2 or pred_p2 in p2_name.strip())):
                pred_row = pred
                break
        
        if pred_row:
            pred_winner = pred_row.get('predicted_winner', '')
            print(f"   Prediction CSV winner: {pred_winner}")
            print(f"   Validation CSV winner: {predicted_winner}")
            print(f"   Winners match: {pred_winner.strip() == predicted_winner.strip()}")
        else:
            print(f"   ❌ Could not find matching prediction row")

def simple_retention_test():
    """Simple test of just a few known correct predictions"""
    
    print(f"\n\n🧪 SIMPLE RETENTION TEST")
    print("="*80)
    
    # Original weights (HOT_STREAK_74PCT_BACKUP)
    original_weights = {
        'recent_form': 0.12,
        'utr_rating': 0.18,
        'atp_ranking': 0.15,
        'set_performance': 0.22,
        'surface_performance': 0.10,
        'mental_toughness': 0.08,
        'sets_in_losses': 0.15,
        'clutch_factor': 0.0,
        'return_of_serve': 0.0,
    }
    
    # New weights (BALANCED_AGGRESSIVE_FIX)
    new_weights = {
        'recent_form': 0.20,
        'set_performance': 0.16,
        'surface_performance': 0.15,
        'mental_toughness': 0.15,
        'clutch_factor': 0.12,
        'utr_rating': 0.10,
        'return_of_serve': 0.07,
        'atp_ranking': 0.05,
        'sets_in_losses': 0.0,
    }
    
    # Load data
    validation_data = load_csv_as_dict('logs/validation_all_HOT_STREAK_74PCT_BACKUP_20250929_090501.csv')
    
    # Get just the first 5 CORRECT predictions
    correct_predictions = [row for row in validation_data if row.get('Prediction_Correct') == 'True'][:5]
    
    print(f"Testing {len(correct_predictions)} known correct predictions...")
    
    for val_row in correct_predictions:
        match_name = val_row['Match']
        predicted_winner = val_row['Predicted_Winner'] 
        actual_sets = val_row['Actual_Sets']
        
        print(f"\n✅ CORRECT PREDICTION: {match_name}")
        print(f"   Original predicted: {predicted_winner}")
        print(f"   Actual result: {actual_sets}")
        
        # For now, let's just count these as a sanity check
        # Real test would need the weight breakdown parsing

if __name__ == "__main__":
    debug_first_few_matches()
    simple_retention_test()
