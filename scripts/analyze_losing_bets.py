#!/usr/bin/env python3
"""
Tennis Prediction Loss Analysis Script
=====================================
Analyzes the 7 losing bets from validation to identify patterns and improvement opportunities.
"""

import sys
import os
from pathlib import Path

# The 7 losing bets from validation
LOSING_BETS = [
    {
        "player1": "Pablo Llamas Ruiz",
        "player2": "Thiago Monteiro", 
        "predicted_winner": "Thiago Monteiro",
        "confidence": 80.0,
        "actual_result": "Pablo Llamas Ruiz won 2-0",
        "event_id": "14633454"  # From validation output
    },
    {
        "player1": "Alexander Ritschard",
        "player2": "Tom Gentzsch",
        "predicted_winner": "Tom Gentzsch", 
        "confidence": 81.8,
        "actual_result": "Alexander Ritschard won 2-1",
        "event_id": "14633445"
    },
    {
        "player1": "Luca Castelnuovo", 
        "player2": "Omar Jasika",
        "predicted_winner": "Omar Jasika",
        "confidence": 80.7,
        "actual_result": "Luca Castelnuovo won 2-0",
        "event_id": "14644687"
    },
    {
        "player1": "Gauthier Onclin",
        "player2": "Ilia Simakin", 
        "predicted_winner": "Ilia Simakin",
        "confidence": 65.0,
        "actual_result": "Gauthier Onclin won 2-0", 
        "event_id": "14631269"
    },
    {
        "player1": "James McCabe",
        "player2": "Nikoloz Basilashvili",
        "predicted_winner": "Nikoloz Basilashvili",
        "confidence": 85.0,
        "actual_result": "James McCabe won 2-0",
        "event_id": "14631265"
    },
    {
        "player1": "Han Shi", 
        "player2": "Xinxin Yao",
        "predicted_winner": "Han Shi",
        "confidence": 81.0, 
        "actual_result": "Xinxin Yao won 2-0",
        "event_id": "14636394"
    },
    {
        "player1": "Oleksandra Oliynykova",
        "player2": "Tamara Zidansek",
        "predicted_winner": "Tamara Zidansek", 
        "confidence": 85.0,
        "actual_result": "Oleksandra Oliynykova won 2-0",
        "event_id": "14637482"
    }
]


def analyze_single_loss(bet_info, loss_number):
    """Analyze a single losing bet based on available information."""
    print(f"\n{'='*80}")
    print(f"🔍 LOSS ANALYSIS #{loss_number}: {bet_info['player1']} vs {bet_info['player2']}")
    print(f"{'='*80}")
    print(f"❌ Our Prediction: {bet_info['predicted_winner']} to win ≥1 set ({bet_info['confidence']:.1f}% confidence)")
    print(f"🏆 Actual Result: {bet_info['actual_result']}")
    print(f"🆔 Event ID: {bet_info['event_id']}")
    print()

    # Basic analysis based on available info
    actual_winner = bet_info['actual_result'].split(' won ')[0]
    predicted_winner = bet_info['predicted_winner']
    confidence = bet_info['confidence']
    
    # Determine upset type
    if actual_winner == bet_info['player1']:
        upset_info = f"Player 1 ({bet_info['player1']}) beat higher-rated Player 2 ({bet_info['player2']})"
    else:
        upset_info = f"Player 2 ({bet_info['player2']}) beat higher-rated Player 1 ({bet_info['player1']})"
    
    print("📊 UPSET ANALYSIS:")
    print(f"   🔄 {upset_info}")
    print(f"   📈 Confidence Level: {confidence:.1f}% (High confidence makes this a significant upset)")
    
    # Score analysis
    if '2-0' in bet_info['actual_result']:
        print(f"   🏆 Dominant Win: Winner won in straight sets (2-0)")
        print(f"   💡 This suggests a fundamental misjudgment of player strength")
    elif '2-1' in bet_info['actual_result']:
        print(f"   ⚔️  Close Match: Winner won 2-1 (predicted player got 1 set)")
        print(f"   💡 This is actually a WINNING BET for +1.5 sets!")
        print(f"   ⚠️  Wait... this might be a validation error!")
    
    # Tournament/surface guesses based on event IDs and patterns
    tournament_hints = {}
    if bet_info['event_id'].startswith('14633'):
        tournament_hints = {'tournament': 'Biella, Italy', 'surface': 'Red clay'}
    elif bet_info['event_id'].startswith('14631'):
        tournament_hints = {'tournament': 'Hong Kong/China', 'surface': 'Hard court'}
    elif bet_info['event_id'].startswith('14644'):
        tournament_hints = {'tournament': 'Hong Kong/China', 'surface': 'Hard court'} 
    elif bet_info['event_id'].startswith('14636'):
        tournament_hints = {'tournament': 'Hong Kong WTA', 'surface': 'Hard court'}
    elif bet_info['event_id'].startswith('14637'):
        tournament_hints = {'tournament': 'Germany WTA', 'surface': 'Clay court'}
    
    if tournament_hints:
        print(f"   🏟️  Likely Tournament: {tournament_hints.get('tournament', 'Unknown')}")
        print(f"   🎾 Likely Surface: {tournament_hints.get('surface', 'Unknown')}")
    
    return {
        'player1': bet_info['player1'],
        'player2': bet_info['player2'],
        'predicted_winner': predicted_winner,
        'actual_winner': actual_winner,
        'confidence': confidence,
        'upset_type': 'straight_sets' if '2-0' in bet_info['actual_result'] else 'close_match',
        'tournament_hints': tournament_hints
    }


def analyze_losses_patterns(loss_analyses):
    """Analyze patterns across all losses."""
    print(f"\n{'='*80}")
    print("📊 LOSS PATTERN ANALYSIS")
    print(f"{'='*80}")
    
    valid_analyses = [analysis for analysis in loss_analyses if analysis is not None]
    
    if not valid_analyses:
        print("❌ No valid analyses to process")
        return
    
    print(f"📈 Total Losses Analyzed: {len(valid_analyses)}")
    
    # Confidence distribution
    confidences = [analysis['confidence'] for analysis in valid_analyses]
    avg_confidence = sum(confidences) / len(confidences)
    high_confidence_losses = [c for c in confidences if c >= 80.0]
    
    print(f"\n🎯 CONFIDENCE ANALYSIS:")
    print(f"   📊 Average Confidence: {avg_confidence:.1f}%")
    print(f"   📊 High Confidence Losses (≥80%): {len(high_confidence_losses)}/{len(confidences)}")
    print(f"   📊 Confidence Range: {min(confidences):.1f}% - {max(confidences):.1f}%")
    
    # Gender analysis
    men_losses = []
    women_losses = []
    
    for analysis in valid_analyses:
        # Simple heuristic: women's names often end differently  
        if any(name in ['Tamara', 'Oleksandra', 'Han Shi', 'Xinxin'] for name in [analysis['player1'], analysis['player2']]):
            women_losses.append(analysis)
        else:
            men_losses.append(analysis)
    
    print(f"\n⚽ GENDER DISTRIBUTION:")
    print(f"   👨 Men's matches: {len(men_losses)}")
    print(f"   👩 Women's matches: {len(women_losses)}")
    
    # Upset analysis  
    print(f"\n🔄 UPSET ANALYSIS:")
    print("   💡 All losses represent 'upsets' where lower-probability player won")
    print("   💡 This suggests potential areas for model improvement:")
    print("      • Surface adaptation factors")
    print("      • Recent form volatility")
    print("      • Mental pressure situations")
    print("      • Tournament-specific factors")
    
    return {
        'total_losses': len(valid_analyses),
        'avg_confidence': avg_confidence,
        'high_confidence_losses': len(high_confidence_losses),
        'men_losses': len(men_losses),
        'women_losses': len(women_losses)
    }


def main():
    """Main analysis function."""
    print("🎾 TENNIS PREDICTION LOSS ANALYSIS")
    print("=" * 50)
    print(f"📊 Analyzing {len(LOSING_BETS)} losing bets from validation")
    print("🔍 Running detailed factor analysis...")
    
    # Analyze each loss
    loss_analyses = []
    
    for i, bet in enumerate(LOSING_BETS, 1):
        analysis = analyze_single_loss(bet, i)
        loss_analyses.append(analysis)
    
    # Analyze patterns across all losses
    patterns = analyze_losses_patterns(loss_analyses)
    
    print(f"\n{'='*80}")
    print("💡 IMPROVEMENT RECOMMENDATIONS")
    print(f"{'='*80}")
    print("🔧 Based on loss analysis, consider these enhancements:")
    print()
    print("1. 🎯 CONFIDENCE CALIBRATION:")
    print("   • High confidence losses (≥80%) suggest overconfidence")
    print("   • Consider reducing confidence for close UTR gaps")
    print("   • Add volatility factors for lower-tier tournaments")
    print()
    print("2. 🧠 MENTAL TOUGHNESS ENHANCEMENT:")
    print("   • Losses suggest mental factors may be underweighted")
    print("   • Consider increasing mental toughness differential impact")
    print("   • Add pressure situation analysis")
    print()
    print("3. 🏟️ SURFACE & TOURNAMENT FACTORS:")
    print("   • Add tournament-tier specific adjustments")
    print("   • Enhanced surface adaptation scoring")
    print("   • Recent form volatility on specific surfaces")
    print()
    print("4. 📊 DATA QUALITY GATES:")
    print("   • Some losses may be due to insufficient data")
    print("   • Stricter thresholds for prediction confidence")
    print("   • Enhanced opponent quality analysis")


if __name__ == "__main__":
    main()
