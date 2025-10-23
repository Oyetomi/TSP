#!/usr/bin/env python3
"""
Simple script to configure prediction system features
Usage: python3 configure_prediction.py [enable|disable] [feature_name]
       python3 configure_prediction.py show
"""

import sys
from prediction_config import config

def main():
    if len(sys.argv) < 2:
        print("🎾 TENNIS PREDICTION CONFIGURATOR")
        print("=" * 50)
        print("\nUsage:")
        print("  python3 configure_prediction.py show")
        print("  python3 configure_prediction.py enable [feature]")
        print("  python3 configure_prediction.py disable [feature]")
        print("\nAvailable features:")
        for feature in config.ENHANCED_FEATURES.keys():
            print(f"  - {feature}")
        return
    
    command = sys.argv[1].lower()
    
    if command == "show":
        config.print_active_configuration()
    elif command == "enable" and len(sys.argv) == 3:
        feature = sys.argv[2]
        config.enable_feature(feature)
        print(f"\n🔄 Updated configuration:")
        config.print_active_configuration()
    elif command == "disable" and len(sys.argv) == 3:
        feature = sys.argv[2]
        config.disable_feature(feature)
        print(f"\n🔄 Updated configuration:")
        config.print_active_configuration()
    else:
        print("❌ Invalid command. Use 'show', 'enable [feature]', or 'disable [feature]'")

if __name__ == "__main__":
    main()
