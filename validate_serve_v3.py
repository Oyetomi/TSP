#!/usr/bin/env python3
"""
Quick validation of SERVE_STRENGTH_V3_OCT2025_3YEAR predictions
"""
import csv
from collections import defaultdict
from datetime import datetime

def parse_csv():
    """Parse CSV and categorize results"""
    wins = []
    losses = []
    pending = []
    
    seen_matches = set()  # Deduplication
    
    with open('all_SERVE_STRENGTH_V3_OCT2025_3YEAR.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                date = row.get('date', 'Unknown')
                p1 = row.get('player1_name', '')
                p2 = row.get('player2_name', '')
                
                # Deduplication key
                players_sorted = tuple(sorted([p1, p2]))
                match_key = f"{date}_{players_sorted[0]}_{players_sorted[1]}"
                
                if match_key in seen_matches:
                    continue
                seen_matches.add(match_key)
                
                actual_result = row.get('actual_result', '')
                
                if not actual_result or actual_result == 'pending':
                    pending.append({
                        'date': date,
                        'match': f"{p1} vs {p2}",
                        'predicted_winner': row.get('predicted_winner', ''),
                        'confidence': row.get('confidence', ''),
                    })
                    continue
                
                result_data = {
                    'date': date,
                    'player1': p1,
                    'player2': p2,
                    'match': f"{p1} vs {p2}",
                    'predicted_winner': row.get('predicted_winner', ''),
                    'confidence': row.get('confidence', ''),
                    'actual_result': actual_result,
                    'surface': row.get('surface', 'Unknown'),
                    'tournament': row.get('tournament', 'Unknown'),
                }
                
                if actual_result.startswith('won'):
                    wins.append(result_data)
                elif actual_result.startswith('lost'):
                    losses.append(result_data)
                    
            except (ValueError, KeyError) as e:
                continue
    
    return wins, losses, pending

def analyze_by_confidence(wins, losses):
    """Analyze performance by confidence level"""
    confidence_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    for win in wins:
        conf = win['confidence']
        confidence_stats[conf]['wins'] += 1
    
    for loss in losses:
        conf = loss['confidence']
        confidence_stats[conf]['losses'] += 1
    
    return confidence_stats

def analyze_by_surface(wins, losses):
    """Analyze performance by surface"""
    surface_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    for win in wins:
        surf = win['surface']
        surface_stats[surf]['wins'] += 1
    
    for loss in losses:
        surf = loss['surface']
        surface_stats[surf]['losses'] += 1
    
    return surface_stats

def main():
    print("=" * 80)
    print("🎾 SERVE_STRENGTH_V3_OCT2025_3YEAR VALIDATION")
    print("=" * 80)
    print()
    
    wins, losses, pending = parse_csv()
    
    total_completed = len(wins) + len(losses)
    total_pending = len(pending)
    
    if total_completed == 0:
        print("❌ No completed matches found!")
        return
    
    win_rate = (len(wins) / total_completed) * 100
    
    print("📊 OVERALL PERFORMANCE")
    print("-" * 80)
    print(f"✅ Wins: {len(wins)}")
    print(f"❌ Losses: {len(losses)}")
    print(f"⏳ Pending: {total_pending}")
    print(f"📈 Win Rate: {win_rate:.1f}% ({len(wins)}/{total_completed})")
    print()
    
    # By confidence
    print("🎯 PERFORMANCE BY CONFIDENCE")
    print("-" * 80)
    conf_stats = analyze_by_confidence(wins, losses)
    
    for conf in sorted(conf_stats.keys()):
        stats = conf_stats[conf]
        total = stats['wins'] + stats['losses']
        wr = (stats['wins'] / total * 100) if total > 0 else 0
        print(f"{conf:8s}: {stats['wins']:3d}W - {stats['losses']:2d}L = {wr:5.1f}% ({total} bets)")
    
    print()
    
    # By surface
    print("🏟️  PERFORMANCE BY SURFACE")
    print("-" * 80)
    surf_stats = analyze_by_surface(wins, losses)
    
    for surf in sorted(surf_stats.keys(), key=lambda x: surf_stats[x]['wins'] + surf_stats[x]['losses'], reverse=True):
        stats = surf_stats[surf]
        total = stats['wins'] + stats['losses']
        wr = (stats['wins'] / total * 100) if total > 0 else 0
        print(f"{surf:20s}: {stats['wins']:3d}W - {stats['losses']:2d}L = {wr:5.1f}% ({total} bets)")
    
    print()
    
    # Recent losses
    print("🔍 MOST RECENT LOSSES (Last 10)")
    print("-" * 80)
    recent_losses = sorted(losses, key=lambda x: x['date'], reverse=True)[:10]
    
    for i, loss in enumerate(recent_losses, 1):
        print(f"{i:2d}. {loss['date']} | {loss['match']}")
        print(f"    Predicted: {loss['predicted_winner']} ({loss['confidence']})")
        print(f"    Surface: {loss['surface']} | Tournament: {loss['tournament']}")
        print()
    
    print("=" * 80)

if __name__ == "__main__":
    main()

