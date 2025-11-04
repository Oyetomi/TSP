#!/usr/bin/env python3
"""
Analyze skip reasons from skipped_matches.log
"""
import re
from collections import Counter, defaultdict
from pathlib import Path

def analyze_skip_log(log_file: str = "logs/skipped_matches.log"):
    """Analyze skip reasons from log file"""
    
    if not Path(log_file).exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    skip_entries = []
    current_entry = {}
    
    for i, line in enumerate(lines):
        # Match skip header
        if 'SKIP #' in line and '-' in line:
            if current_entry:
                skip_entries.append(current_entry)
            skip_num_match = re.search(r'SKIP #(\d+)', line)
            skip_type_match = re.search(r'-\s+(\w+)', line)
            if skip_num_match and skip_type_match:
                current_entry = {
                    'num': skip_num_match.group(1),
                    'type': skip_type_match.group(1),
                    'reason': '',
                    'match': ''
                }
        
        # Match skip reason
        elif '❌ SKIP REASON:' in line:
            # Get next line which contains the reason
            if i + 1 < len(lines):
                reason_line = lines[i + 1].strip()
                # Remove timestamp if present
                reason_line = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - ', '', reason_line)
                if reason_line:
                    current_entry['reason'] = reason_line
        
        # Match player names
        elif '🎾 MATCH:' in line:
            match_text = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - 🎾 MATCH: ', '', line.strip())
            current_entry['match'] = match_text
    
    # Add last entry
    if current_entry:
        skip_entries.append(current_entry)
    
    # Analyze
    skip_counts = Counter([e['type'] for e in skip_entries])
    
    # Categorize reasons
    reason_categories = defaultdict(int)
    detailed_reasons = defaultdict(list)
    
    for entry in skip_entries:
        reason = entry['reason'].lower()
        skip_type = entry['type']
        
        # Categorize
        if 'tiebreak' in reason:
            reason_categories['TIEBREAK_DATA'] += 1
            detailed_reasons['TIEBREAK_DATA'].append(entry['reason'])
        elif 'insufficient years' in reason or 'missing year data' in reason or 'multi-year' in reason:
            reason_categories['MULTI_YEAR_REQUIREMENT'] += 1
            detailed_reasons['MULTI_YEAR_REQUIREMENT'].append(entry['reason'])
        elif 'insufficient data' in reason or 'insufficient statistics' in reason:
            reason_categories['INSUFFICIENT_DATA'] += 1
            detailed_reasons['INSUFFICIENT_DATA'].append(entry['reason'])
        elif 'quality opposition' in reason or 'quality data' in reason or 'inflated win rate' in reason:
            reason_categories['QUALITY_OPPOSITION_DATA'] += 1
            detailed_reasons['QUALITY_OPPOSITION_DATA'].append(entry['reason'])
        elif 'poor form' in reason or 'poor performance' in reason:
            reason_categories['POOR_FORM'] += 1
            detailed_reasons['POOR_FORM'].append(entry['reason'])
        elif '404' in reason or 'not found' in reason or 'has_404_error' in reason:
            reason_categories['404_ERROR'] += 1
            detailed_reasons['404_ERROR'].append(entry['reason'])
        elif 'no 2025 data' in reason or 'no 2024 data' in reason or 'zero current-year' in reason:
            reason_categories['NO_CURRENT_YEAR_DATA'] += 1
            detailed_reasons['NO_CURRENT_YEAR_DATA'].append(entry['reason'])
        elif 'unable to verify' in reason or 'verification' in reason:
            reason_categories['VERIFICATION_FAILURE'] += 1
            detailed_reasons['VERIFICATION_FAILURE'].append(entry['reason'])
        elif 'crowd' in reason or 'circuit breaker' in reason:
            reason_categories['CROWD_DISAGREEMENT'] += 1
            detailed_reasons['CROWD_DISAGREEMENT'].append(entry['reason'])
        else:
            reason_categories['OTHER'] += 1
            detailed_reasons['OTHER'].append(entry['reason'])
    
    # Print summary
    print("=" * 80)
    print("SKIP REASON ANALYSIS")
    print("=" * 80)
    print(f"\n📊 Total Skipped Matches: {len(skip_entries)}")
    
    print("\n" + "=" * 80)
    print("BREAKDOWN BY SKIP TYPE:")
    print("=" * 80)
    
    for skip_type, count in skip_counts.most_common():
        percentage = (count / len(skip_entries) * 100) if skip_entries else 0
        print(f"{skip_type:30s}: {count:4d} ({percentage:5.1f}%)")
    
    print("\n" + "=" * 80)
    print("BREAKDOWN BY REASON CATEGORY:")
    print("=" * 80)
    
    for category, count in sorted(reason_categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(skip_entries) * 100) if skip_entries else 0
        print(f"{category:30s}: {count:4d} ({percentage:5.1f}%)")
    
    # Show top reasons by category
    print("\n" + "=" * 80)
    print("TOP REASONS BY CATEGORY (showing first 3 examples each):")
    print("=" * 80)
    
    for category in sorted(reason_categories.keys(), key=lambda x: reason_categories[x], reverse=True):
        examples = detailed_reasons[category]
        if examples:
            print(f"\n📋 {category} ({len(examples)} occurrences):")
            # Get unique reasons
            unique_reasons = Counter(examples)
            for i, (reason, count) in enumerate(unique_reasons.most_common(3), 1):
                print(f"\n  {i}. ({count} times)")
                print(f"     {reason[:150]}")

if __name__ == "__main__":
    analyze_skip_log()
