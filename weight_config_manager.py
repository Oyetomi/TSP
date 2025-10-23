#!/usr/bin/env python3
"""
Weight Configuration Manager
Manages different weight configurations with code names for tracking parlay performance
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

class WeightConfigManager:
    """Manages weight configurations with performance tracking"""
    
    def __init__(self, config_file: str = "weight_configs.json"):
        self.config_file = config_file
        self.configs = self.load_configs()
    
    def load_configs(self) -> Dict[str, Any]:
        """Load weight configurations from JSON file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading configs: {e}")
                return self._create_default_configs()
        else:
            return self._create_default_configs()
    
    def save_configs(self):
        """Save configurations to JSON file"""
        try:
            self.configs['metadata']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
            with open(self.config_file, 'w') as f:
                json.dump(self.configs, f, indent=2)
            print(f"✅ Configurations saved to {self.config_file}")
        except Exception as e:
            print(f"❌ Error saving configs: {e}")
    
    def _create_default_configs(self) -> Dict[str, Any]:
        """Create default configuration structure"""
        return {
            "configs": {},
            "active_config": None,
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.now().strftime('%Y-%m-%d'),
                "total_configs": 0
            }
        }
    
    def add_config(self, code_name: str, name: str, description: str, weights: Dict[str, float], 
                   features: Dict[str, bool] = None) -> bool:
        """Add a new weight configuration"""
        
        # Validate weights sum to 1.0
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.001:
            print(f"❌ Error: Weights sum to {total_weight:.3f}, must sum to 1.0")
            return False
        
        if features is None:
            features = {
                "tiebreak_performance": False,
                "pressure_performance": False,
                "serve_dominance": False,
                "enhanced_year_blending": True,
                "crowd_sentiment": True,
                "dual_weighted_form": True
            }
        
        config = {
            "name": name,
            "description": description,
            "created": datetime.now().strftime('%Y-%m-%d'),
            "weights": weights,
            "features": features,
            "performance": {
                "total_bets": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit_loss": 0.0,
                "roi": 0.0,
                "last_updated": datetime.now().strftime('%Y-%m-%d')
            }
        }
        
        self.configs['configs'][code_name] = config
        self.configs['metadata']['total_configs'] = len(self.configs['configs'])
        self.save_configs()
        
        print(f"✅ Added configuration '{code_name}': {name}")
        return True
    
    def get_config(self, code_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific configuration"""
        return self.configs['configs'].get(code_name)
    
    def set_active_config(self, code_name: str) -> bool:
        """Set the active configuration"""
        if code_name in self.configs['configs']:
            self.configs['active_config'] = code_name
            self.save_configs()
            print(f"✅ Set active configuration to: {code_name}")
            return True
        else:
            print(f"❌ Configuration '{code_name}' not found")
            return False
    
    def get_active_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently active configuration"""
        active_code = self.configs.get('active_config')
        if active_code:
            return self.configs['configs'].get(active_code)
        return None
    
    def get_active_code_name(self) -> Optional[str]:
        """Get the active configuration code name"""
        return self.configs.get('active_config')
    
    def list_configs(self):
        """List all available configurations"""
        print("🎾 AVAILABLE WEIGHT CONFIGURATIONS")
        print("=" * 60)
        
        active_code = self.configs.get('active_config')
        
        for code_name, config in self.configs['configs'].items():
            active_marker = " ← ACTIVE" if code_name == active_code else ""
            print(f"\n📊 {code_name}{active_marker}")
            print(f"   Name: {config['name']}")
            print(f"   Description: {config['description']}")
            print(f"   Created: {config['created']}")
            
            # Performance stats
            perf = config['performance']
            if perf['total_bets'] > 0:
                print(f"   Performance: {perf['wins']}/{perf['total_bets']} ({perf['win_rate']:.1%})")
                print(f"   ROI: {perf['roi']:.1%}")
            else:
                print(f"   Performance: No data yet")
    
    def update_performance(self, code_name: str, bet_result: str, amount: float = 1.0, 
                          payout: float = 0.0):
        """Update performance tracking for a configuration"""
        if code_name not in self.configs['configs']:
            print(f"❌ Configuration '{code_name}' not found")
            return False
        
        config = self.configs['configs'][code_name]
        perf = config['performance']
        
        perf['total_bets'] += 1
        
        if bet_result.lower() in ['win', 'w', 'won']:
            perf['wins'] += 1
            perf['profit_loss'] += payout - amount
        else:
            perf['losses'] += 1
            perf['profit_loss'] -= amount
        
        perf['win_rate'] = perf['wins'] / perf['total_bets'] if perf['total_bets'] > 0 else 0.0
        perf['roi'] = (perf['profit_loss'] / (perf['total_bets'] * amount)) if perf['total_bets'] > 0 else 0.0
        perf['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        self.save_configs()
        print(f"✅ Updated performance for {code_name}: {perf['wins']}/{perf['total_bets']} ({perf['win_rate']:.1%})")
        return True
    
    def export_config_for_parlay(self, code_name: str) -> Dict[str, Any]:
        """Export configuration in a format suitable for parlay tagging"""
        config = self.get_config(code_name)
        if not config:
            return {}
        
        return {
            "code_name": code_name,
            "name": config['name'],
            "description": config['description'],
            "created": config['created'],
            "weights_summary": {
                f"{k}": f"{v:.1%}" for k, v in config['weights'].items()
            },
            "top_factors": self._get_top_factors(config['weights']),
            "parlay_tag": f"#{code_name}_{datetime.now().strftime('%Y%m%d')}"
        }
    
    def _get_top_factors(self, weights: Dict[str, float]) -> List[str]:
        """Get top 3 factors by weight"""
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        return [f"{factor}({weight:.1%})" for factor, weight in sorted_weights[:3]]


# Global instance
config_manager = WeightConfigManager()

# Convenience functions
def get_current_config_name() -> str:
    """Get the current active configuration code name"""
    return config_manager.get_active_code_name() or "UNKNOWN"

def get_current_weights() -> Dict[str, float]:
    """Get weights from the active configuration"""
    config = config_manager.get_active_config()
    if config:
        return config['weights']
    else:
        # Fallback to default
        return {
            'set_performance': 0.31,
            'recent_form': 0.22,
            'momentum': 0.12,
            'surface_performance': 0.11,
            'ranking_advantage': 0.10,
            'clutch_factor': 0.09,
            'physical_factors': 0.05
        }

def tag_parlay(code_name: str = None) -> str:
    """Generate a parlay tag for the current or specified configuration"""
    if code_name is None:
        code_name = get_current_config_name()
    
    export_data = config_manager.export_config_for_parlay(code_name)
    return export_data.get('parlay_tag', f"#{code_name}_{datetime.now().strftime('%Y%m%d')}")


if __name__ == "__main__":
    # Demo usage
    print("🎾 WEIGHT CONFIGURATION MANAGER DEMO")
    print("=" * 50)
    
    # List current configurations
    config_manager.list_configs()
    
    print(f"\n🏷️ Current parlay tag: {tag_parlay()}")
    
    # Show export format
    current_code = get_current_config_name()
    if current_code != "UNKNOWN":
        print(f"\n📋 Export format for {current_code}:")
        export_data = config_manager.export_config_for_parlay(current_code)
        for key, value in export_data.items():
            print(f"   {key}: {value}")
