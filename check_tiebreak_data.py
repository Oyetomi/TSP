#!/usr/bin/env python3
"""
Script to check tiebreak data availability for players
Before modifying main code, verify that players actually have tiebreak data
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_secrets import MATCH_DATA_CONFIG
from app.services.player_analysis_service import PlayerAnalysisService
from enhanced_statistics_handler import EnhancedStatisticsHandler
from prediction_config import PredictionConfig

def check_player_tiebreak_data(player_id: int, player_name: str, surface: str = None):
    """Check if a player has tiebreak data available"""
    print(f"\n{'='*80}")
    print(f"CHECKING TIEBREAK DATA FOR: {player_name} (ID: {player_id})")
    print(f"{'='*80}")
    
    # Initialize services
    player_service = PlayerAnalysisService()
    config = PredictionConfig()
    stats_handler = EnhancedStatisticsHandler(player_service, config)
    
    try:
        # Get enhanced statistics WITH surface
        print(f"\n📍 Surface-specific stats ({surface or 'Overall'}):")
        enhanced_stats = stats_handler.get_enhanced_player_statistics(player_id, surface)
        
        # Also check OVERALL stats (no surface filter)
        print(f"\n📍 Overall stats (all surfaces):")
        enhanced_stats_overall = stats_handler.get_enhanced_player_statistics(player_id, None)
        
        # Check for 404 errors
        has_404 = enhanced_stats.get('has_404_error', False)
        print(f"\n📊 404 Status: {'❌ HAS 404 ERRORS' if has_404 else '✅ NO 404 ERRORS'}")
        
        # Get statistics
        stats = enhanced_stats.get('statistics', {})
        reliability = enhanced_stats.get('reliability_score', 0.0)
        
        # Check tiebreak data
        tb_won = stats.get('tiebreaksWon', 0)
        tb_lost = stats.get('tiebreakLosses', 0)
        tb_total = tb_won + tb_lost
        tb_rate = (tb_won / tb_total * 100) if tb_total > 0 else 0
        
        print(f"\n🎾 Tiebreak Statistics:")
        print(f"   Won: {tb_won}")
        print(f"   Lost: {tb_lost}")
        print(f"   Total: {tb_total}")
        print(f"   Win Rate: {tb_rate:.1f}%")
        
        # Check sample sizes
        sample_sizes = enhanced_stats.get('sample_sizes', {})
        print(f"\n📈 Sample Sizes:")
        print(f"   Matches: {sample_sizes.get('matches', 0)}")
        print(f"   Tiebreaks: {sample_sizes.get('tiebreaks', 0)}")
        
        # Check current year only stats
        current_year_only = enhanced_stats.get('current_year_only', {})
        print(f"\n📅 Current Year (2025) Only:")
        curr_tb_won = current_year_only.get('tiebreaksWon', 0)
        curr_tb_lost = current_year_only.get('tiebreakLosses', 0)
        curr_tb_total = curr_tb_won + curr_tb_lost
        print(f"   Tiebreaks: {curr_tb_won}W / {curr_tb_lost}L = {curr_tb_total} total")
        
        # Check previous year stats
        print(f"\n📅 Previous Year (2024):")
        try:
            prev_stats = player_service.get_player_year_statistics(player_id, 2024)
            if prev_stats and prev_stats.get('statistics'):
                prev_surface_stats = None
                for stat in prev_stats.get('statistics', []):
                    if surface and stat.get('groundType') == surface:
                        prev_surface_stats = stat
                        break
                    elif not surface and not stat.get('groundType'):
                        prev_surface_stats = stat
                        break
                
                if prev_surface_stats:
                    prev_tb_won = prev_surface_stats.get('tiebreaksWon', 0)
                    prev_tb_lost = prev_surface_stats.get('tiebreakLosses', 0)
                    prev_tb_total = prev_tb_won + prev_tb_lost
                    print(f"   Tiebreaks: {prev_tb_won}W / {prev_tb_lost}L = {prev_tb_total} total")
                else:
                    print(f"   ⚠️  No matching surface stats found")
            else:
                print(f"   ❌ No statistics available")
        except Exception as e:
            print(f"   ❌ Error fetching 2024 stats: {e}")
        
        # Check 2023 stats
        print(f"\n📅 Old Year (2023):")
        try:
            old_stats = player_service.get_player_year_statistics(player_id, 2023)
            if old_stats and old_stats.get('statistics'):
                old_surface_stats = None
                for stat in old_stats.get('statistics', []):
                    if surface and stat.get('groundType') == surface:
                        old_surface_stats = stat
                        break
                    elif not surface and not stat.get('groundType'):
                        old_surface_stats = stat
                        break
                
                if old_surface_stats:
                    old_tb_won = old_surface_stats.get('tiebreaksWon', 0)
                    old_tb_lost = old_surface_stats.get('tiebreakLosses', 0)
                    old_tb_total = old_tb_won + old_tb_lost
                    print(f"   Tiebreaks: {old_tb_won}W / {old_tb_lost}L = {old_tb_total} total")
                else:
                    print(f"   ⚠️  No matching surface stats found")
            else:
                print(f"   ❌ No statistics available (likely 404)")
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "HTTP Error 404" in error_msg:
                print(f"   ❌ 404 Error (expected for newer players)")
            else:
                print(f"   ❌ Error fetching 2023 stats: {e}")
        
        # Check overall stats too
        stats_overall = enhanced_stats_overall.get('statistics', {})
        tb_won_overall = stats_overall.get('tiebreaksWon', 0)
        tb_lost_overall = stats_overall.get('tiebreakLosses', 0)
        tb_total_overall = tb_won_overall + tb_lost_overall
        
        print(f"\n🎾 Overall Tiebreak Statistics (all surfaces):")
        print(f"   Won: {tb_won_overall}")
        print(f"   Lost: {tb_lost_overall}")
        print(f"   Total: {tb_total_overall}")
        
        # Final assessment
        print(f"\n{'='*80}")
        print(f"ASSESSMENT:")
        print(f"{'='*80}")
        
        # Check both surface-specific and overall
        has_data = tb_total > 0 or tb_total_overall > 0
        
        if tb_total > 0:
            print(f"✅ HAS SURFACE-SPECIFIC TIEBREAK DATA: {tb_total} tiebreaks ({tb_won}W/{tb_lost}L)")
        elif tb_total_overall > 0:
            print(f"⚠️  NO SURFACE-SPECIFIC DATA, BUT HAS OVERALL DATA: {tb_total_overall} tiebreaks")
            print(f"   (Could use overall data as fallback)")
        
        if has_data:
            if has_404:
                print(f"⚠️  BUT: Has 404 errors (some years missing)")
                print(f"✅ SHOULD PROCEED: Data available from other years")
            else:
                print(f"✅ NO ISSUES: All years available")
        else:
            print(f"❌ NO TIEBREAK DATA: Cannot calculate tiebreak performance")
            if has_404:
                print(f"❌ REASON: 404 errors AND no tiebreak data")
            else:
                print(f"❌ REASON: No tiebreak data in any year")
        
        return {
            'has_tiebreak_data': has_data,
            'has_surface_data': tb_total > 0,
            'has_overall_data': tb_total_overall > 0,
            'has_404': has_404,
            'tb_total': tb_total,
            'tb_won': tb_won,
            'tb_lost': tb_lost,
            'tb_total_overall': tb_total_overall,
            'should_proceed': has_data  # Proceed if we have any tiebreak data
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'has_tiebreak_data': False,
            'has_404': False,
            'tb_total': 0,
            'tb_won': 0,
            'tb_lost': 0,
            'should_proceed': False,
            'error': str(e)
        }

def main():
    """Check both players from the match"""
    # Sho Shimabukuro vs Coleman Wong
    player1_id = 216154  # Sho Shimabukuro (correct ID from SofaScore)
    player1_name = "Sho Shimabukuro"
    
    player2_id = 289106  # Coleman Wong
    player2_name = "Coleman Wong"
    
    surface = "Hardcourt outdoor"
    
    print(f"\n{'#'*80}")
    print(f"# TIEBREAK DATA VERIFICATION")
    print(f"# Match: {player1_name} vs {player2_name}")
    print(f"# Surface: {surface}")
    print(f"{'#'*80}")
    
    # Check player 1
    p1_result = check_player_tiebreak_data(player1_id, player1_name, surface)
    
    # Check player 2
    p2_result = check_player_tiebreak_data(player2_id, player2_name, surface)
    
    # Final verdict
    print(f"\n{'#'*80}")
    print(f"# FINAL VERDICT")
    print(f"{'#'*80}")
    
    p1_ok = p1_result.get('should_proceed', False)
    p2_ok = p2_result.get('should_proceed', False)
    
    print(f"\n{player1_name}: {'✅ HAS DATA' if p1_ok else '❌ NO DATA'}")
    print(f"{player2_name}: {'✅ HAS DATA' if p2_ok else '❌ NO DATA'}")
    
    if p1_ok and p2_ok:
        print(f"\n✅ BOTH PLAYERS HAVE TIEBREAK DATA")
        print(f"✅ CODE CHANGE IS JUSTIFIED: Should allow 404s if tiebreak data exists")
        print(f"✅ Match should NOT be skipped")
    elif p1_ok or p2_ok:
        print(f"\n⚠️  ONE PLAYER HAS DATA, ONE DOESN'T")
        print(f"⚠️  May need to handle this case differently")
    else:
        print(f"\n❌ NEITHER PLAYER HAS TIEBREAK DATA")
        print(f"❌ Current skip logic is CORRECT")
        print(f"❌ Code change may not be needed")

if __name__ == "__main__":
    main()

