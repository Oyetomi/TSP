#!/usr/bin/env python3
"""
Weight Configuration Management Tool
Command-line interface for managing weight configurations and tracking performance
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weight_config_manager import config_manager, get_current_config_name, tag_parlay

def show_help():
    """Show help information"""
    print("""
🎾 WEIGHT CONFIGURATION MANAGER
================================

USAGE:
    python3 manage_weights.py <command> [options]

COMMANDS:
    list                    - List all configurations
    show <code_name>        - Show details for a specific configuration
    set <code_name>         - Set active configuration
    tag [code_name]         - Get parlay tag for current or specified config
    add <code_name> <name> <description> - Add new configuration interactively
    performance <code_name> <result> [amount] [payout] - Update performance
    current                 - Show current active configuration

EXAMPLES:
    python3 manage_weights.py list
    python3 manage_weights.py set RANK_BOOST_V1
    python3 manage_weights.py tag
    python3 manage_weights.py tag RANK_BOOST_V1
    python3 manage_weights.py performance RANK_BOOST_V1 win 10 15
    python3 manage_weights.py add MY_CONFIG_V1 "My Custom Config" "Description here"
""")

def show_config_details(code_name: str):
    """Show detailed information about a configuration"""
    config = config_manager.get_config(code_name)
    if not config:
        print(f"❌ Configuration '{code_name}' not found")
        return
    
    print(f"\n🎾 CONFIGURATION: {code_name}")
    print("=" * 50)
    print(f"Name: {config['name']}")
    print(f"Description: {config['description']}")
    print(f"Created: {config['created']}")
    
    print(f"\n📊 WEIGHTS:")
    for factor, weight in config['weights'].items():
        print(f"   {factor:<20}: {weight:>6.1%}")
    
    print(f"\n⚙️ FEATURES:")
    for feature, enabled in config['features'].items():
        status = "✅ ENABLED" if enabled else "❌ DISABLED"
        print(f"   {feature:<25}: {status}")
    
    print(f"\n📈 PERFORMANCE:")
    perf = config['performance']
    if perf['total_bets'] > 0:
        print(f"   Total Bets: {perf['total_bets']}")
        print(f"   Wins: {perf['wins']}")
        print(f"   Losses: {perf['losses']}")
        print(f"   Win Rate: {perf['win_rate']:.1%}")
        print(f"   Profit/Loss: {perf['profit_loss']:+.2f}")
        print(f"   ROI: {perf['roi']:+.1%}")
        print(f"   Last Updated: {perf['last_updated']}")
    else:
        print("   No performance data yet")
    
    # Show parlay tag
    export_data = config_manager.export_config_for_parlay(code_name)
    print(f"\n🏷️ PARLAY TAG: {export_data.get('parlay_tag', 'N/A')}")

def add_configuration_interactive(code_name: str, name: str, description: str):
    """Add a new configuration interactively"""
    print(f"\n🎾 ADDING NEW CONFIGURATION: {code_name}")
    print("=" * 50)
    print(f"Name: {name}")
    print(f"Description: {description}")
    print()
    
    # Get current weights as starting point
    current_config = config_manager.get_active_config()
    if current_config:
        weights = current_config['weights'].copy()
        print("Starting with current active weights:")
        for factor, weight in weights.items():
            print(f"   {factor}: {weight:.1%}")
    else:
        # Default weights
        weights = {
            'set_performance': 0.31,
            'recent_form': 0.22,
            'momentum': 0.12,
            'surface_performance': 0.11,
            'ranking_advantage': 0.10,
            'clutch_factor': 0.09,
            'physical_factors': 0.05
        }
    
    print("\nEnter new weights (press Enter to keep current value):")
    
    for factor in weights.keys():
        current = weights[factor]
        try:
            new_value = input(f"   {factor} [{current:.1%}]: ").strip()
            if new_value:
                if new_value.endswith('%'):
                    new_value = new_value[:-1]
                weights[factor] = float(new_value) / 100
        except ValueError:
            print(f"   Invalid value, keeping {current:.1%}")
    
    # Validate and add
    total = sum(weights.values())
    print(f"\nTotal weight: {total:.1%}")
    
    if abs(total - 1.0) > 0.01:
        print("❌ Weights must sum to 100%. Please adjust.")
        return False
    
    # Add the configuration
    success = config_manager.add_config(code_name, name, description, weights)
    if success:
        print(f"✅ Configuration '{code_name}' added successfully!")
        
        # Ask if user wants to set it as active
        set_active = input("Set as active configuration? (y/N): ").strip().lower()
        if set_active in ['y', 'yes']:
            config_manager.set_active_config(code_name)
    
    return success

def main():
    """Main command-line interface"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "help" or command == "-h" or command == "--help":
        show_help()
    
    elif command == "list":
        config_manager.list_configs()
    
    elif command == "current":
        current_code = get_current_config_name()
        if current_code != "UNKNOWN":
            show_config_details(current_code)
        else:
            print("❌ No active configuration set")
    
    elif command == "show":
        if len(sys.argv) < 3:
            print("❌ Usage: python3 manage_weights.py show <code_name>")
            return
        show_config_details(sys.argv[2])
    
    elif command == "set":
        if len(sys.argv) < 3:
            print("❌ Usage: python3 manage_weights.py set <code_name>")
            return
        config_manager.set_active_config(sys.argv[2])
    
    elif command == "tag":
        if len(sys.argv) >= 3:
            tag = tag_parlay(sys.argv[2])
        else:
            tag = tag_parlay()
        print(f"🏷️ Parlay tag: {tag}")
    
    elif command == "add":
        if len(sys.argv) < 5:
            print("❌ Usage: python3 manage_weights.py add <code_name> <name> <description>")
            return
        add_configuration_interactive(sys.argv[2], sys.argv[3], sys.argv[4])
    
    elif command == "performance":
        if len(sys.argv) < 4:
            print("❌ Usage: python3 manage_weights.py performance <code_name> <result> [amount] [payout]")
            return
        
        code_name = sys.argv[2]
        result = sys.argv[3]
        amount = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
        payout = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
        
        config_manager.update_performance(code_name, result, amount, payout)
    
    else:
        print(f"❌ Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main()
