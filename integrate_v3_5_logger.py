#!/usr/bin/env python3
"""
V3.5 Logger Integration Helper
==============================

Simple script to integrate V3.5 logger into betting_analysis_script.py
Keeps components decoupled while providing easy integration.

Run this to automatically add V3.5 logging to your system.
"""

import os
import re


def integrate_v3_5_logger():
    """Integrate V3.5 logger into betting_analysis_script.py"""
    
    script_path = "betting_analysis_script.py"
    
    if not os.path.exists(script_path):
        print(f"❌ Error: {script_path} not found")
        return False
    
    print("🔧 Integrating V3.5 Logger into betting_analysis_script.py")
    print("=" * 80)
    
    # Read the file
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Check if already integrated
    if 'v3_5_logger' in content.lower():
        print("⚠️  V3.5 logger already integrated!")
        print("   Skipping integration to avoid duplicates")
        return True
    
    # Step 1: Add import at top of class __init__
    import_code = """
        # Initialize V3.5 logger (if V3.5 is active)
        self.v3_5_logger = None
        try:
            from weight_configs import get_current_config_name
            if get_current_config_name() == 'SERVE_STRENGTH_V3_5_NOV2025':
                from v3_5_logger import V35Logger
                self.v3_5_logger = V35Logger()
                print("✅ V3.5 Logger ENABLED - Logging to logs/v3_5_predictions.log")
                
                # Log weight configuration
                from weight_configs import get_current_config
                self.v3_5_logger.log_weight_config(get_current_config())
            else:
                print("ℹ️  V3.5 Logger DISABLED (V3.5 config not active)")
        except Exception as e:
            print(f"⚠️  V3.5 Logger initialization failed: {e}")
"""
    
    # Find the __init__ method and add after elo_service initialization
    pattern = r"(if elo_enabled:.*?print\(f\"   Auto-update: ON.*?\"\))"
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(
            pattern,
            r"\1" + import_code,
            content,
            flags=re.DOTALL
        )
        print("✅ Step 1: Added V3.5 logger initialization")
    else:
        print("⚠️  Warning: Could not find elo_service initialization")
        print("   You may need to manually add V3.5 logger initialization")
    
    # Step 2: Add logging call in analyze_single_match (before return result)
    logging_code = """
                    # Log to V3.5 logger (if enabled)
                    if self.v3_5_logger:
                        try:
                            # Collect factor scores for both players
                            player1_factors = {
                                'set_performance': player1_profile.set_win_rate or 0.0,
                                'serve_dominance': getattr(player1_profile, 'serve_dominance', 0.0),
                                'return_of_serve': getattr(player1_profile, 'return_strength', 0.0),
                                'recent_form': player1_profile.recent_form_score / 100.0 if player1_profile.recent_form_score else 0.0,
                                'surface_performance': getattr(player1_profile, 'surface_win_rate', 0.0),
                                'pressure_performance': getattr(player1_profile, 'pressure_performance', 0.0),
                            }
                            
                            player2_factors = {
                                'set_performance': player2_profile.set_win_rate or 0.0,
                                'serve_dominance': getattr(player2_profile, 'serve_dominance', 0.0),
                                'return_of_serve': getattr(player2_profile, 'return_strength', 0.0),
                                'recent_form': player2_profile.recent_form_score / 100.0 if player2_profile.recent_form_score else 0.0,
                                'surface_performance': getattr(player2_profile, 'surface_win_rate', 0.0),
                                'pressure_performance': getattr(player2_profile, 'pressure_performance', 0.0),
                            }
                            
                            self.v3_5_logger.log_match_prediction(
                                match_data={
                                    'player1_name': player1_name,
                                    'player2_name': player2_name,
                                    'tournament': tournament.name if tournament else 'Unknown',
                                    'surface': surface,
                                    'player1_weights': self.WEIGHTS,
                                    'player2_weights': self.WEIGHTS
                                },
                                player1_factors=player1_factors,
                                player2_factors=player2_factors,
                                elo_data=elo_result if 'elo_result' in locals() else None,
                                prediction_result={
                                    'predicted_winner': prediction.predicted_winner,
                                    'confidence': prediction.confidence_level,
                                    'player1_set_probability': prediction.player1_probability,
                                    'player2_set_probability': prediction.player2_probability,
                                    'recommended_bet': result.get('recommended_bet', ''),
                                    'key_factors': prediction.key_factors
                                }
                            )
                        except Exception as e:
                            self.logger.warning(f"V3.5 logging error: {e}")
                    
"""
    
    # Find where result is returned and add logging before it
    pattern = r"(# Add Elo fields to result\s+result\.update\(elo_result\))"
    
    if re.search(pattern, content):
        content = re.sub(
            pattern,
            r"\1" + logging_code,
            content
        )
        print("✅ Step 2: Added V3.5 match logging call")
    else:
        print("⚠️  Warning: Could not find result.update(elo_result)")
        print("   You may need to manually add logging call")
    
    # Step 3: Add logger close in analyze_scheduled_matches cleanup
    close_code = """
            # Close V3.5 logger if active
            if self.v3_5_logger:
                try:
                    self.v3_5_logger.close()
                except Exception as e:
                    print(f"⚠️  Error closing V3.5 logger: {e}")
            
"""
    
    # Find the final return statement in analyze_scheduled_matches
    pattern = r"(return analysis_results\s+except:)"
    
    if re.search(pattern, content):
        content = re.sub(
            pattern,
            close_code + r"\1",
            content
        )
        print("✅ Step 3: Added V3.5 logger cleanup")
    else:
        print("⚠️  Warning: Could not find cleanup location")
        print("   Logger will still work but may not show session summary")
    
    # Write back to file
    backup_path = script_path + ".backup"
    
    # Create backup
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"\n✅ Backup created: {backup_path}")
    
    # Write modified version
    with open(script_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Integration complete: {script_path}")
    print("\n" + "=" * 80)
    print("🎯 NEXT STEPS:")
    print("=" * 80)
    print("1. Activate V3.5 config in weight_configs.json")
    print("   Change line: \"active_config\": \"SERVE_STRENGTH_V3_5_NOV2025\"")
    print("\n2. Run predictions:")
    print("   python3 main.py")
    print("\n3. Check V3.5 logs:")
    print("   cat logs/v3_5_predictions.log")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔧 V3.5 LOGGER INTEGRATION SCRIPT")
    print("=" * 80)
    print("\nThis script will:")
    print("  1. Add V3.5 logger initialization to betting_analysis_script.py")
    print("  2. Add match logging calls")
    print("  3. Add cleanup code")
    print("  4. Create backup of original file")
    print("\n⚠️  Note: If V3.5 config is not active, logger will be disabled")
    print("=" * 80)
    
    response = input("\nProceed with integration? (y/n): ")
    
    if response.lower() in ['y', 'yes']:
        success = integrate_v3_5_logger()
        if success:
            print("\n✅ SUCCESS! V3.5 logger is now integrated")
        else:
            print("\n❌ FAILED! Please check error messages above")
    else:
        print("\n❌ Integration cancelled")

