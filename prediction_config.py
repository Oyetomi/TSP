#!/usr/bin/env python3
"""
Tennis Set Prediction Configuration
Configurable weights and feature toggles for the prediction system
"""

from typing import Dict, Any

class PredictionConfig:
    """Configuration management for tennis set predictions"""
    
    def __init__(self):
        # Base prediction weights (total = 100%)
        self.BASE_WEIGHTS = {
            'set_performance': 0.28,        # 28% - Core set win rate foundation (reduced for Hannah Fry factors)
            'recent_form': 0.20,            # 20% - Current form and condition (reduced for Hannah Fry factors)
            'momentum': 0.11,               # 11% - Recent match trend
            'surface_performance': 0.10,    # 10% - Surface-specific performance
            'clutch_factor': 0.09,          # 9%  - Performance in pressure situations
            'physical_factors': 0.05,       # 5%  - Age, fitness, injury considerations
            'ranking_advantage': 0.09,      # 9%  - Ranking difference impact
            'return_of_serve': 0.08         # 8%  - Hannah Fry: "1% better at returning = amplified advantage"
        }
        
        # Enhanced statistics feature toggles
        self.ENHANCED_FEATURES = {
            'tiebreak_performance': False,   # Disable due to low frequency/sample size issues
            'pressure_performance': False,   # Disable - covered by clutch_factor
            'serve_dominance': False,        # Disable - may be redundant with surface_performance
            'enhanced_year_blending': True,  # Keep year transition strategy
            'crowd_sentiment': True,         # Keep as confidence modifier
            'dual_weighted_form': True,      # Keep 75% recent + 25% comprehensive
            'hannah_fry_amplification': True, # Hannah Fry's mathematical tennis insights
            'return_of_serve_focus': True    # Focus on return-of-serve performance
        }
        
        # Game Handicap vs Set Betting Thresholds (empirically derived from UTR analysis)
        self.BETTING_STRATEGY = {
            # UTR thresholds based on empirical analysis of top 500 players
            'utr_very_close_threshold': 0.05,     # Ultra-close matches (75th+ percentile)
            'utr_close_match_threshold': 0.15,     # Close matches (broader range)
            'utr_moderate_threshold': 0.30,        # Moderate gaps (wider field)
            
            # Active threshold (choose one of the above)
            'active_utr_threshold': 0.75,          # Close match threshold - gaps under this trigger game handicap
            
            # Fallback for when UTR unavailable
            'ranking_close_match_threshold': 12,   # ATP/WTA ranking gap ≤ this → game handicap
            
            # Feature toggles
            'enable_game_handicap_mode': True,     # Master toggle for game handicap analysis
            'enable_conflicting_prediction_detection': True,  # Detect UTR vs set performance conflicts
            'game_handicap_confidence_boost': 0.05, # Confidence adjustment for close matches
            
            # Conflicting Prediction Logic
            'conflicting_prediction_rules': {
                'description': 'When UTR skill favorite ≠ set performance favorite',
                'examples': [
                    'Higher ranked player has lower set win probability',
                    'UTR advantage but worse recent form/surface performance',
                    'Perfect scenario for game handicap betting'
                ],
                'triggers_game_handicap': True
            },
            
            # Empirical insights (for reference)
            'empirical_notes': {
                'men_utr_range': '13.79-16.45 (top 500)',
                'women_utr_range': '11.06-12.98 (top 500)', 
                'p75_gap': 0.010,
                'median_gap': 0.000,
                'mean_gap': 0.005,
                'analysis_date': '2025-01-28'
            }
        }
        
        # Enhanced weights (used only if features are enabled)
        self.ENHANCED_WEIGHTS = {
            'set_performance': 0.26,        # Reduced to make room for enhanced features
            'tiebreak_performance': 0.15,   # Only if enabled
            'pressure_performance': 0.12,   # Only if enabled  
            'serve_dominance': 0.08,        # Only if enabled
            'recent_form': 0.17,            # Reduced
            'surface_performance': 0.08,    # Reduced
            'clutch_factor': 0.06,          # Reduced
            'momentum': 0.02,               # Reduced
            'ranking_advantage': 0.06       # Increased to maintain ranking importance in enhanced mode
        }
        
        # Crowd sentiment thresholds (always active as confidence modifier)
        self.CROWD_CONFIDENCE_THRESHOLDS = {
            'ignore_threshold': 100,        # <100 votes = ignore completely
            'light_threshold': 1000,        # 100-1000 = consider lightly  
            'serious_threshold': 5000       # 1000+ = take seriously
        }
        
        # Loss Analysis Improvements Configuration
        self.LOSS_ANALYSIS_IMPROVEMENTS = {
            'enable_opponent_quality_penalty': True,  # Penalize set performance when player hasn't faced quality opponents
            'opponent_quality_threshold': 0.30,        # If <30% of matches vs quality opponents, apply penalty
            'opponent_quality_penalty': 0.30,          # 30% reduction to set performance score
            
            'enable_enhanced_form_weight': True,       # Increase form weight when gap is significant
            'form_gap_threshold': 30.0,                # Form gap >30% triggers enhanced weighting
            'enhanced_form_multiplier': 1.5,           # 50% increase to form weight
            
            'skip_coin_flip_matches': True,            # Skip matches with "Coin flip" edge classification
            'coin_flip_score_threshold': 0.05,         # Score diff <5% = coin flip
            
            'enable_conflicting_signals_skip': True,   # Skip when UTR+Form+Ranking oppose set performance
            'conflicting_signals_threshold': 2,        # Require 2+ skill metrics to align
            
            'description': 'Improvements based on analysis of failed predictions',
            'rationale': {
                'opponent_quality': 'Players with inflated set win rates from weak opponents mislead model',
                'form_weight': 'Recent form proved more predictive than historical set performance',
                'coin_flip_skip': 'Low confidence "coin flip" matches have poor risk/reward',
                'conflicting_signals': 'When skill metrics align against set perf, trust the skill metrics'
            }
        }
        
        # Multi-Year Statistics Configuration
        self.MULTI_YEAR_STATS = {
            'enable_three_year_stats': True,      # Master toggle: False = 2 years (2024-2025), True = 3 years (2023-2024-2025)
            'years_to_fetch': 3,                  # Number of years to fetch (2 or 3)
            'min_years_required': 2,              # Minimum years with data required (e.g., 2 out of 3)
            'year_weights': {
                'two_year_mode': {
                    'current_year': 0.7,          # 70% weight for current year (2025)
                    'previous_year': 0.3          # 30% weight for previous year (2024)
                },
                'three_year_mode': {
                    'current_year': 0.6,          # 60% weight for current year (2025)
                    'previous_year': 0.3,         # 30% weight for previous year (2024)
                    'two_years_ago': 0.1          # 10% weight for 2 years ago (2023)
                }
            },
            'fallback_strategy': {
                'description': 'What to do when not enough years have data',
                'if_only_current': 'Use current year only (100% weight)',
                'if_current_and_previous': 'Use 2-year mode weights',
                'if_current_and_old': 'Blend 70% current + 30% oldest available',
                'if_previous_and_old': 'Blend 70% previous + 30% oldest',
                'reject_if_fewer_than': 1  # Reject player if fewer than this many years have data
            },
            'description': 'Configurable multi-year statistics fetching for deeper historical context',
            'rationale': 'More years = better sample size for players with limited recent matches',
            'notes': {
                '2_year_mode': 'Default - Uses 2024 & 2025 (current behavior)',
                '3_year_mode': 'Experimental - Adds 2023 for more historical depth',
                'benefit': 'Helps with players who have inconsistent play schedules',
                'risk': '2023 data may be outdated for rapidly improving/declining players'
            }
        }
        
        # Form analysis configuration
        self.FORM_ANALYSIS = {
            'recent_matches': 10,           # Recent form sample size (increased for better accuracy)
            'comprehensive_matches': 100,   # Comprehensive form sample size (increased for more context)
            'recent_weight': 0.75,          # Weight for recent form
            'comprehensive_weight': 0.25    # Weight for comprehensive form
        }
        
        # CRITICAL: Risk Management Settings (Based on Failed Prediction Analysis)
        self.RISK_MANAGEMENT = {
            # Ranking Gap Protection
            'massive_ranking_gap_threshold': 75,      # Positions - trigger enhanced ranking weight
            'extreme_ranking_gap_threshold': 100,     # Positions - trigger maximum protection
            'ranking_gap_weight_boost': 0.20,         # Increase ranking weight to 20% for large gaps
            'ranking_gap_max_weight': 0.25,           # Maximum ranking weight for extreme gaps
            
            # Crowd Sentiment Circuit Breaker (ENHANCED after failed prediction analysis)
            'crowd_disagreement_skip_threshold': 0.65,  # Skip bets if crowd disagrees >65% (was 50%, too aggressive for women's tennis)
            'crowd_disagreement_warning_threshold': 0.30, # Warning if crowd disagrees >30% (was 25%)
            'minimum_crowd_votes': 500,                # Minimum votes to consider crowd sentiment (reduced from 1000 for women's matches)
            
            # Data Quality Thresholds
            'minimum_set_sample_size': 25,             # Minimum sets for reliable performance data
            'minimum_match_sample_size': 15,           # Minimum matches for form analysis
            'surface_quality_discount': 0.5,           # Discount factor for poor quality surface data
            'form_quality_discount': 0.3,              # Discount factor for small form samples
            
            # Upset Prediction Protection
            'upset_confidence_cap': 0.65,              # Maximum confidence for upset predictions
            'top_player_ranking_threshold': 50,        # Consider top-50 as "top players"
            'upset_ranking_gap_threshold': 50,         # Minimum gap to consider an "upset"
            'upset_multiple_factors_required': 3,      # Require 3+ strong factors for upset predictions
            
            # CRITICAL: Form-Based Protection (NEW - based on failed prediction analysis)
            'terrible_form_threshold': 20,             # Form score below this triggers protection
            'terrible_form_confidence_cap': 0.55,      # Hard cap for players with terrible form
            'major_form_gap_threshold': 20,            # Form difference that triggers amplification
            'extreme_form_gap_threshold': 30,          # Form difference for extreme measures
            'form_amplification_factor': 1.8,          # Multiply form weight by this for major gaps
            'extreme_form_amplification_factor': 2.2,  # For extreme form gaps
            'form_ranking_reduction_factor': 0.6,      # Reduce ranking weight by this
            'extreme_form_ranking_reduction_factor': 0.4, # For extreme form gaps
            'bagel_confidence_cap': 0.65,              # Max confidence when multiple red flags present
            
            # Emergency Overrides
            'enable_ranking_gap_protection': True,     # Master switch for ranking protection
            'enable_crowd_circuit_breaker': True,      # Master switch for crowd circuit breaker
            'enable_data_quality_gates': True,         # Master switch for data quality checks
            'enable_upset_protection': True,           # Master switch for upset protection
            'enable_form_protection': True,            # Master switch for form-based protection
            'enable_bagel_protection': True,           # Master switch for bagel protection
            'emergency_mode': False                    # Emergency mode = extra conservative
        }
        
        # Home Country Advantage Configuration
        self.HOME_ADVANTAGE = {
            'enable_home_advantage': False,  # Master toggle to enable/disable home advantage bonus (DISABLED)
            'bonus_percentage': 0.10,        # 10% bonus applied to player's score when playing in home country
            'log_to_file': True,             # Log home advantage applications to logs/home_advantage.log
            'description': 'Applies bonus when player competes in their home country (crowd support, familiarity, no jet lag)'
        }
        
        # Injury/Retirement Checker Configuration
        self.INJURY_CHECKER = {
            'enable_injury_check': True,     # Master toggle to enable/disable injury checking
            'days_back': 5,                  # How many days back to check for injuries/retirements (DEFAULT: 5)
            'description': 'Automatically skips matches with recently injured or retired players',
            'data_source': 'https://www.tennisexplorer.com/list-players/injured/',
            'rationale': 'Covers full tournament cycle (2-3 day rounds) while avoiding overly conservative skips',
            'notes': {
                '1_day': 'Aggressive - only same-day retirements (RISKY)',
                '3_days': 'Moderate - catches recent issues but may miss tournament re-entries',
                '5_days': 'Optimal - full tournament cycle coverage without being overly conservative (DEFAULT)',
                '7_days': 'Conservative - maximum protection, may skip recovered players',
                'recommendation': 'Use 5 days for optimal balance between safety and betting opportunities'
            }
        }
        
        # Probability conversion settings
        self.PROBABILITY_SETTINGS = {
            'min_match_prob': 0.05,         # Minimum match probability
            'max_match_prob': 0.90,         # Maximum match probability
            'min_set_prob': 0.35,           # Minimum set probability
            'max_set_prob': 0.85            # Maximum set probability
        }
        
        # Hannah Fry Mathematical Tennis Insights
        self.HANNAH_FRY_FACTORS = {
            'three_percent_rule': 0.03,     # 3% better = "wipe the floor" - threshold for dominance
            'federer_amplification': 30.0,  # 80% match wins from 52% points = 30% amplification factor
            'serve_advantage_weight': 1.4,  # Serve gives "massive advantage" - weight multiplier
            'return_importance': 1.6,       # Return is crucial for breaking serve advantage
            'hierarchical_amplification': {
                'point_to_game': 1.2,       # Small point advantages → game advantages
                'game_to_set': 1.5,         # Game advantages → set advantages  
                'set_to_match': 2.0         # Set advantages → match advantages
            },
            'resilience_factor': 0.15,      # "mindset towards failure" - psychological component
            'small_edge_threshold': 0.01    # 1% better at returning = meaningful advantage
        }
    
    def get_active_weights(self) -> Dict[str, float]:
        """Get the active weight configuration based on feature toggles"""
        
        if any(self.ENHANCED_FEATURES.values()):
            # Use enhanced weights but only for enabled features
            active_weights = {}
            total_weight = 0.0
            
            # Start with base weights for core features
            active_weights.update(self.BASE_WEIGHTS)
            
            # Add enhanced features if enabled
            if self.ENHANCED_FEATURES.get('tiebreak_performance', False):
                active_weights['tiebreak_performance'] = self.ENHANCED_WEIGHTS['tiebreak_performance']
                # Reduce other weights proportionally
                active_weights['set_performance'] = self.ENHANCED_WEIGHTS['set_performance']
                
            if self.ENHANCED_FEATURES.get('pressure_performance', False):
                active_weights['pressure_performance'] = self.ENHANCED_WEIGHTS['pressure_performance']
                # Reduce clutch_factor since they overlap
                active_weights['clutch_factor'] = self.ENHANCED_WEIGHTS['clutch_factor']
                
            if self.ENHANCED_FEATURES.get('serve_dominance', False):
                active_weights['serve_dominance'] = self.ENHANCED_WEIGHTS['serve_dominance']
                # Reduce surface_performance since they overlap
                active_weights['surface_performance'] = self.ENHANCED_WEIGHTS['surface_performance']
            
            # Normalize weights to ensure they sum to 1.0
            total_weight = sum(active_weights.values())
            if total_weight != 1.0:
                for key in active_weights:
                    active_weights[key] = active_weights[key] / total_weight
                    
            return active_weights
        else:
            # Use base weights only
            return self.BASE_WEIGHTS.copy()
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific enhanced feature is enabled"""
        return self.ENHANCED_FEATURES.get(feature_name, False)
    
    def enable_feature(self, feature_name: str):
        """Enable a specific enhanced feature"""
        if feature_name in self.ENHANCED_FEATURES:
            self.ENHANCED_FEATURES[feature_name] = True
            print(f"✅ Enabled feature: {feature_name}")
        else:
            print(f"❌ Unknown feature: {feature_name}")
    
    def disable_feature(self, feature_name: str):
        """Disable a specific enhanced feature"""
        if feature_name in self.ENHANCED_FEATURES:
            self.ENHANCED_FEATURES[feature_name] = False
            print(f"❌ Disabled feature: {feature_name}")
        else:
            print(f"❌ Unknown feature: {feature_name}")
    
    def print_active_configuration(self):
        """Print the current active configuration"""
        print("🎾 TENNIS SET PREDICTION CONFIGURATION")
        print("=" * 60)
        
        print("\n⚖️ ACTIVE WEIGHTS:")
        active_weights = self.get_active_weights()
        for factor, weight in active_weights.items():
            print(f"   {factor:<20}: {weight:>6.1%}")
        
        print(f"\n   TOTAL: {sum(active_weights.values()):>6.1%}")
        
        print("\n🔧 ENHANCED FEATURES:")
        for feature, enabled in self.ENHANCED_FEATURES.items():
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"   {feature:<25}: {status}")
        
        print("\n📊 FORM ANALYSIS:")
        print(f"   Recent matches: {self.FORM_ANALYSIS['recent_matches']}")
        print(f"   Comprehensive matches: {self.FORM_ANALYSIS['comprehensive_matches']}")
        print(f"   Recent weight: {self.FORM_ANALYSIS['recent_weight']:.1%}")
        print(f"   Comprehensive weight: {self.FORM_ANALYSIS['comprehensive_weight']:.1%}")
        
        print("\n🎲 PROBABILITY BOUNDS:")
        print(f"   Match probability: {self.PROBABILITY_SETTINGS['min_match_prob']:.1%} - {self.PROBABILITY_SETTINGS['max_match_prob']:.1%}")
        print(f"   Set probability: {self.PROBABILITY_SETTINGS['min_set_prob']:.1%} - {self.PROBABILITY_SETTINGS['max_set_prob']:.1%}")
    
    def apply_hannah_fry_amplification(self, advantage_diff: float, factor_type: str = 'general') -> float:
        """
        Apply Hannah Fry's mathematical amplification to advantage differences
        
        Args:
            advantage_diff: Raw advantage difference between players (0-1 scale)
            factor_type: Type of advantage ('serve', 'return', 'general')
            
        Returns:
            Amplified advantage based on tennis scoring mathematics
        """
        if not self.ENHANCED_FEATURES.get('hannah_fry_amplification', False):
            return advantage_diff
            
        # Apply the 3% rule - small differences get amplified
        if abs(advantage_diff) >= self.HANNAH_FRY_FACTORS['three_percent_rule']:
            # Above 3% = significant advantage, apply full amplification
            amplification = self.HANNAH_FRY_FACTORS['federer_amplification'] / 100  # Convert to decimal
            amplified_diff = advantage_diff * (1 + amplification)
        elif abs(advantage_diff) >= self.HANNAH_FRY_FACTORS['small_edge_threshold']:
            # 1-3% = meaningful advantage, apply hierarchical amplification
            hierarchy_multiplier = (
                self.HANNAH_FRY_FACTORS['hierarchical_amplification']['point_to_game'] *
                self.HANNAH_FRY_FACTORS['hierarchical_amplification']['game_to_set'] *
                self.HANNAH_FRY_FACTORS['hierarchical_amplification']['set_to_match']
            )
            amplified_diff = advantage_diff * hierarchy_multiplier
        else:
            # <1% = minimal advantage, no amplification
            amplified_diff = advantage_diff
            
        # Apply factor-specific weights
        if factor_type == 'serve':
            amplified_diff *= self.HANNAH_FRY_FACTORS['serve_advantage_weight']
        elif factor_type == 'return':
            amplified_diff *= self.HANNAH_FRY_FACTORS['return_importance']
            
        # Cap the amplification to prevent extreme values
        return max(-0.5, min(0.5, amplified_diff))
    
    def calculate_psychological_resilience(self, recent_losses: int, total_recent: int) -> float:
        """
        Calculate psychological resilience factor based on Hannah Fry's insights
        about "mindset towards failure and resilience to losing"
        
        Args:
            recent_losses: Number of recent losses
            total_recent: Total recent matches
            
        Returns:
            Resilience factor (0-1 scale, where 1 = maximum resilience)
        """
        if total_recent == 0:
            return 0.5  # Neutral
            
        loss_rate = recent_losses / total_recent
        
        # Players who maintain performance despite losses show resilience
        # Inverse relationship: more losses require more resilience to maintain performance
        if loss_rate <= 0.2:  # 80%+ win rate
            resilience = 0.9  # High resilience assumed
        elif loss_rate <= 0.4:  # 60-80% win rate
            resilience = 0.7  # Good resilience
        elif loss_rate <= 0.6:  # 40-60% win rate  
            resilience = 0.5  # Average resilience
        else:  # <40% win rate
            resilience = 0.3  # Lower resilience
            
        return resilience
        
    def get_three_percent_threshold(self) -> float:
        """Get the 3% threshold for dominance as defined by Hannah Fry"""
        return self.HANNAH_FRY_FACTORS['three_percent_rule']
    
    # CRITICAL: Risk Management Methods
    def check_ranking_gap_protection(self, ranking_gap: int) -> Dict[str, Any]:
        """Check if ranking gap protection should be applied"""
        if not self.RISK_MANAGEMENT['enable_ranking_gap_protection']:
            return {'apply_protection': False, 'reason': 'Protection disabled'}
        
        result = {
            'apply_protection': False,
            'ranking_weight_boost': 0.0,
            'reason': '',
            'risk_level': 'LOW'
        }
        
        if ranking_gap >= self.RISK_MANAGEMENT['extreme_ranking_gap_threshold']:
            result.update({
                'apply_protection': True,
                'ranking_weight_boost': self.RISK_MANAGEMENT['ranking_gap_max_weight'],
                'reason': f'Extreme ranking gap ({ranking_gap} positions) - applying maximum protection',
                'risk_level': 'EXTREME'
            })
        elif ranking_gap >= self.RISK_MANAGEMENT['massive_ranking_gap_threshold']:
            result.update({
                'apply_protection': True,
                'ranking_weight_boost': self.RISK_MANAGEMENT['ranking_gap_weight_boost'],
                'reason': f'Large ranking gap ({ranking_gap} positions) - applying enhanced protection',
                'risk_level': 'HIGH'
            })
        else:
            result['reason'] = f'Ranking gap ({ranking_gap} positions) below protection threshold'
        
        return result
    
    def check_crowd_sentiment_circuit_breaker(self, crowd_disagreement_pct: float, total_votes: int) -> Dict[str, Any]:
        """Check if crowd sentiment circuit breaker should trigger"""
        if not self.RISK_MANAGEMENT['enable_crowd_circuit_breaker']:
            return {'skip_bet': False, 'reason': 'Circuit breaker disabled'}
        
        result = {
            'skip_bet': False,
            'apply_warning': False,
            'reason': '',
            'risk_level': 'LOW'
        }
        
        # Check if we have enough votes to consider crowd sentiment
        if total_votes < self.RISK_MANAGEMENT['minimum_crowd_votes']:
            result['reason'] = f'Insufficient crowd votes ({total_votes}) - ignoring sentiment'
            return result
        
        if crowd_disagreement_pct >= self.RISK_MANAGEMENT['crowd_disagreement_skip_threshold']:
            result.update({
                'skip_bet': True,
                'reason': f'CIRCUIT BREAKER: {crowd_disagreement_pct:.1%} crowd disagreement (>{self.RISK_MANAGEMENT["crowd_disagreement_skip_threshold"]:.1%}) with {total_votes:,} votes',
                'risk_level': 'EXTREME'
            })
        elif crowd_disagreement_pct >= self.RISK_MANAGEMENT['crowd_disagreement_warning_threshold']:
            result.update({
                'apply_warning': True,
                'reason': f'HIGH RISK: {crowd_disagreement_pct:.1%} crowd disagreement (>{self.RISK_MANAGEMENT["crowd_disagreement_warning_threshold"]:.1%}) with {total_votes:,} votes',
                'risk_level': 'HIGH'
            })
        else:
            result['reason'] = f'Crowd disagreement ({crowd_disagreement_pct:.1%}) within acceptable range'
        
        return result
    
    def check_data_quality_gates(self, set_sample_size: int, match_sample_size: int, surface_quality: str) -> Dict[str, Any]:
        """Check if data quality gates should be applied"""
        if not self.RISK_MANAGEMENT['enable_data_quality_gates']:
            return {'apply_discounts': False, 'reason': 'Quality gates disabled'}
        
        result = {
            'apply_discounts': False,
            'set_performance_discount': 1.0,
            'form_discount': 1.0,
            'surface_discount': 1.0,
            'warnings': [],
            'risk_level': 'LOW'
        }
        
        # Check set sample size
        if set_sample_size < self.RISK_MANAGEMENT['minimum_set_sample_size']:
            result['apply_discounts'] = True
            # Progressive discount based on how far below threshold
            discount_factor = max(0.2, set_sample_size / self.RISK_MANAGEMENT['minimum_set_sample_size'])
            result['set_performance_discount'] = discount_factor
            result['warnings'].append(f'Small set sample ({set_sample_size} < {self.RISK_MANAGEMENT["minimum_set_sample_size"]}) - discount factor: {discount_factor:.2f}')
            result['risk_level'] = 'MEDIUM'
        
        # Check match sample size
        if match_sample_size < self.RISK_MANAGEMENT['minimum_match_sample_size']:
            result['apply_discounts'] = True
            result['form_discount'] = self.RISK_MANAGEMENT['form_quality_discount']
            result['warnings'].append(f'Small match sample ({match_sample_size} < {self.RISK_MANAGEMENT["minimum_match_sample_size"]}) - form discount: {result["form_discount"]:.2f}')
            result['risk_level'] = 'MEDIUM'
        
        # Check surface quality
        if surface_quality and surface_quality.lower() != 'strong':
            result['apply_discounts'] = True
            result['surface_discount'] = self.RISK_MANAGEMENT['surface_quality_discount']
            result['warnings'].append(f'Poor surface quality ({surface_quality}) - surface discount: {result["surface_discount"]:.2f}')
            result['risk_level'] = 'MEDIUM'
        
        return result
    
    def check_upset_prediction_protection(self, predicted_winner_ranking: int, opponent_ranking: int, confidence: float) -> Dict[str, Any]:
        """Check if upset prediction protection should be applied"""
        if not self.RISK_MANAGEMENT['enable_upset_protection']:
            return {'apply_protection': False, 'reason': 'Upset protection disabled'}
        
        result = {
            'apply_protection': False,
            'cap_confidence': False,
            'new_confidence': confidence,
            'require_extra_factors': False,
            'reason': '',
            'risk_level': 'LOW'
        }
        
        # Check if this is an upset (betting on lower-ranked player)
        ranking_gap = abs(predicted_winner_ranking - opponent_ranking)
        is_upset = predicted_winner_ranking > opponent_ranking
        opponent_is_top_player = opponent_ranking <= self.RISK_MANAGEMENT['top_player_ranking_threshold']
        
        if is_upset and ranking_gap >= self.RISK_MANAGEMENT['upset_ranking_gap_threshold']:
            result['apply_protection'] = True
            result['risk_level'] = 'HIGH'
            
            if opponent_is_top_player:
                # Betting against top-50 player
                result.update({
                    'cap_confidence': True,
                    'new_confidence': min(confidence, self.RISK_MANAGEMENT['upset_confidence_cap']),
                    'require_extra_factors': True,
                    'reason': f'UPSET PROTECTION: Betting #{predicted_winner_ranking} vs top-{opponent_ranking} player (gap: {ranking_gap}) - confidence capped at {self.RISK_MANAGEMENT["upset_confidence_cap"]:.1%}',
                    'risk_level': 'EXTREME'
                })
            else:
                # Regular upset
                result.update({
                    'cap_confidence': True,
                    'new_confidence': min(confidence, self.RISK_MANAGEMENT['upset_confidence_cap']),
                    'reason': f'Upset prediction: #{predicted_winner_ranking} vs #{opponent_ranking} (gap: {ranking_gap}) - confidence capped at {self.RISK_MANAGEMENT["upset_confidence_cap"]:.1%}'
                })
        else:
            result['reason'] = f'Not an upset or gap too small: #{predicted_winner_ranking} vs #{opponent_ranking} (gap: {ranking_gap})'
        
        return result
    
    def check_form_protection(self, p1_form: float, p2_form: float, predicted_player_form: float) -> Dict[str, Any]:
        """Check if form-based protection should be applied (NEW - based on failed prediction analysis)"""
        if not self.RISK_MANAGEMENT['enable_form_protection']:
            return {'apply_protection': False, 'reason': 'Form protection disabled'}
        
        result = {
            'apply_protection': False,
            'terrible_form_detected': False,
            'major_form_gap': False,
            'extreme_form_gap': False,
            'confidence_cap': None,
            'form_weight_multiplier': 1.0,
            'ranking_weight_multiplier': 1.0,
            'warnings': [],
            'reason': '',
            'risk_level': 'LOW'
        }
        
        form_gap = abs(p1_form - p2_form)
        
        # Check for terrible form
        if predicted_player_form < self.RISK_MANAGEMENT['terrible_form_threshold']:
            result.update({
                'apply_protection': True,
                'terrible_form_detected': True,
                'confidence_cap': self.RISK_MANAGEMENT['terrible_form_confidence_cap'],
                'warnings': [f'TERRIBLE FORM: Predicted player form ({predicted_player_form:.1f}) below threshold ({self.RISK_MANAGEMENT["terrible_form_threshold"]})'],
                'reason': f'Terrible form protection: Form {predicted_player_form:.1f} < {self.RISK_MANAGEMENT["terrible_form_threshold"]} - confidence capped at {self.RISK_MANAGEMENT["terrible_form_confidence_cap"]:.1%}',
                'risk_level': 'EXTREME'
            })
        
        # Check for major form gaps
        if form_gap >= self.RISK_MANAGEMENT['extreme_form_gap_threshold']:
            result.update({
                'apply_protection': True,
                'extreme_form_gap': True,
                'form_weight_multiplier': self.RISK_MANAGEMENT['extreme_form_amplification_factor'],
                'ranking_weight_multiplier': self.RISK_MANAGEMENT['extreme_form_ranking_reduction_factor'],
                'warnings': [f'EXTREME FORM GAP: {form_gap:.1f} points - amplifying form weight to {self.RISK_MANAGEMENT["extreme_form_amplification_factor"]:.1f}x'],
                'reason': f'Extreme form gap ({form_gap:.1f} points) - form weight ×{self.RISK_MANAGEMENT["extreme_form_amplification_factor"]:.1f}, ranking weight ×{self.RISK_MANAGEMENT["extreme_form_ranking_reduction_factor"]:.1f}',
                'risk_level': 'EXTREME'
            })
        elif form_gap >= self.RISK_MANAGEMENT['major_form_gap_threshold']:
            result.update({
                'apply_protection': True,
                'major_form_gap': True,
                'form_weight_multiplier': self.RISK_MANAGEMENT['form_amplification_factor'],
                'ranking_weight_multiplier': self.RISK_MANAGEMENT['form_ranking_reduction_factor'],
                'warnings': [f'MAJOR FORM GAP: {form_gap:.1f} points - amplifying form weight to {self.RISK_MANAGEMENT["form_amplification_factor"]:.1f}x'],
                'reason': f'Major form gap ({form_gap:.1f} points) - form weight ×{self.RISK_MANAGEMENT["form_amplification_factor"]:.1f}, ranking weight ×{self.RISK_MANAGEMENT["form_ranking_reduction_factor"]:.1f}',
                'risk_level': 'HIGH'
            })
        
        if not result['apply_protection']:
            result['reason'] = f'Form protection not triggered: gap {form_gap:.1f} < {self.RISK_MANAGEMENT["major_form_gap_threshold"]}, predicted form {predicted_player_form:.1f} ≥ {self.RISK_MANAGEMENT["terrible_form_threshold"]}'
        
        return result
    
    def check_bagel_protection(self, confidence: float, red_flags_count: int, form_issues: bool, crowd_disagreement: bool) -> Dict[str, Any]:
        """Check if bagel protection should be applied (NEW - prevents 0-set outcomes)"""
        if not self.RISK_MANAGEMENT['enable_bagel_protection']:
            return {'apply_protection': False, 'reason': 'Bagel protection disabled'}
        
        result = {
            'apply_protection': False,
            'confidence_cap': None,
            'red_flags': [],
            'reason': '',
            'risk_level': 'LOW'
        }
        
        # Count red flags
        if form_issues:
            result['red_flags'].append('Form issues detected')
        if crowd_disagreement:
            result['red_flags'].append('Crowd disagreement')
        if confidence > 0.8:
            result['red_flags'].append('Very high confidence (>80%)')
        
        total_red_flags = len(result['red_flags'])
        
        # Apply protection if multiple red flags and high confidence
        if total_red_flags >= 2 and confidence > 0.70:
            result.update({
                'apply_protection': True,
                'confidence_cap': self.RISK_MANAGEMENT['bagel_confidence_cap'],
                'reason': f'BAGEL PROTECTION: {total_red_flags} red flags detected - confidence capped at {self.RISK_MANAGEMENT["bagel_confidence_cap"]:.1%}',
                'risk_level': 'HIGH'
            })
        else:
            result['reason'] = f'Bagel protection not triggered: {total_red_flags} red flags, confidence {confidence:.1%}'
        
        return result
    
    def get_dynamic_ranking_weight(self, ranking_gap: int) -> float:
        """Get dynamic ranking weight based on ranking gap"""
        protection = self.check_ranking_gap_protection(ranking_gap)
        if protection['apply_protection']:
            return protection['ranking_weight_boost']
        else:
            return self.BASE_WEIGHTS['ranking_advantage']  # Use base weight
    
    # Home Advantage Management Methods
    def enable_home_advantage(self, bonus_percentage: float = 0.10):
        """Enable home advantage bonus
        
        Args:
            bonus_percentage: Bonus to apply (default: 0.10 = 10%)
        """
        if bonus_percentage < 0 or bonus_percentage > 0.25:
            print(f"❌ Invalid bonus percentage. Must be between 0 and 0.25 (0-25%)")
            return
        
        self.HOME_ADVANTAGE['enable_home_advantage'] = True
        self.HOME_ADVANTAGE['bonus_percentage'] = bonus_percentage
        print(f"✅ Home advantage ENABLED")
        print(f"   Bonus: {int(bonus_percentage * 100)}%")
        print(f"   Description: {self.HOME_ADVANTAGE['description']}")
    
    def disable_home_advantage(self):
        """Disable home advantage bonus"""
        self.HOME_ADVANTAGE['enable_home_advantage'] = False
        print(f"❌ Home advantage DISABLED")
        print(f"   Players will not receive bonus for playing in their home country")
    
    def set_home_advantage_bonus(self, bonus_percentage: float):
        """Set home advantage bonus percentage
        
        Args:
            bonus_percentage: Bonus to apply (e.g., 0.10 = 10%, 0.07 = 7%)
        """
        if bonus_percentage < 0 or bonus_percentage > 0.25:
            print(f"❌ Invalid bonus percentage. Must be between 0 and 0.25 (0-25%)")
            return
        
        self.HOME_ADVANTAGE['bonus_percentage'] = bonus_percentage
        print(f"✅ Home advantage bonus set to {int(bonus_percentage * 100)}%")
    
    def print_home_advantage_status(self):
        """Print current home advantage configuration"""
        print("\n🏠 HOME ADVANTAGE STATUS:")
        print("=" * 60)
        
        if not self.HOME_ADVANTAGE['enable_home_advantage']:
            print("   Status: ❌ DISABLED")
            print("   Players will not receive home country bonus")
        else:
            bonus = self.HOME_ADVANTAGE['bonus_percentage']
            print(f"   Status: ✅ ENABLED")
            print(f"   Bonus: {int(bonus * 100)}% ({bonus:.3f} added to score)")
            print(f"   Description: {self.HOME_ADVANTAGE['description']}")
            print(f"   Logging: {'✅ Enabled' if self.HOME_ADVANTAGE['log_to_file'] else '❌ Disabled'}")
        
        print("=" * 60)
    
    def enable_three_year_stats(self):
        """Enable 3-year statistics mode (2023, 2024, 2025)"""
        self.MULTI_YEAR_STATS['enable_three_year_stats'] = True
        self.MULTI_YEAR_STATS['years_to_fetch'] = 3
        print("✅ 3-YEAR STATISTICS MODE ENABLED")
        print("   Will fetch data from 2023, 2024, and 2025")
        print("   Weights: 60% current, 30% previous, 10% two years ago")
    
    def disable_three_year_stats(self):
        """Disable 3-year mode and revert to 2-year mode (2024, 2025)"""
        self.MULTI_YEAR_STATS['enable_three_year_stats'] = False
        self.MULTI_YEAR_STATS['years_to_fetch'] = 2
        print("✅ 2-YEAR STATISTICS MODE (DEFAULT)")
        print("   Will fetch data from 2024 and 2025 only")
        print("   Weights: 70% current, 30% previous")
    
    def set_min_years_required(self, min_years: int):
        """Set minimum number of years required (1-3)
        
        Args:
            min_years: Minimum years of data required
                      1 = Accept players with any single year of data
                      2 = Require at least 2 out of 3 years (recommended)
                      3 = Require all 3 years (very conservative)
        """
        if min_years not in [1, 2, 3]:
            print("❌ min_years must be 1, 2, or 3")
            return
        
        self.MULTI_YEAR_STATS['min_years_required'] = min_years
        print(f"✅ Minimum years required set to: {min_years}")
        
        if min_years == 1:
            print("   ⚠️  Very permissive - will use players with only 1 year of data")
        elif min_years == 2:
            print("   ✅ Balanced - requires 2 out of 3 years (RECOMMENDED)")
        else:
            print("   ⚠️  Very conservative - requires all 3 years of data")
    
    def print_multi_year_stats_status(self):
        """Print current multi-year statistics configuration"""
        print("\n📊 MULTI-YEAR STATISTICS STATUS:")
        print("=" * 60)
        
        mode_enabled = self.MULTI_YEAR_STATS['enable_three_year_stats']
        years_to_fetch = self.MULTI_YEAR_STATS['years_to_fetch']
        min_years = self.MULTI_YEAR_STATS['min_years_required']
        
        from datetime import datetime
        current_year = datetime.now().year
        
        if mode_enabled:
            print(f"   Status: ✅ 3-YEAR MODE ENABLED")
            print(f"   Years: {current_year-2}, {current_year-1}, {current_year}")
            weights = self.MULTI_YEAR_STATS['year_weights']['three_year_mode']
            print(f"   Weights: {int(weights['current_year']*100)}% current, "
                  f"{int(weights['previous_year']*100)}% previous, "
                  f"{int(weights['two_years_ago']*100)}% oldest")
        else:
            print(f"   Status: ✅ 2-YEAR MODE (DEFAULT)")
            print(f"   Years: {current_year-1}, {current_year}")
            weights = self.MULTI_YEAR_STATS['year_weights']['two_year_mode']
            print(f"   Weights: {int(weights['current_year']*100)}% current, "
                  f"{int(weights['previous_year']*100)}% previous")
        
        print(f"   Min Years Required: {min_years} out of {years_to_fetch}")
        
        if min_years == 1:
            print(f"   ⚠️  Will accept players with just 1 year of data")
        elif min_years == 2:
            print(f"   ✅ Will require at least 2 years of data (RECOMMENDED)")
        else:
            print(f"   ⚠️  Will require all {years_to_fetch} years of data (very strict)")
        
        print("=" * 60)


# Global configuration instance
config = PredictionConfig()

# Convenience functions
def get_weights() -> Dict[str, float]:
    """Get active prediction weights"""
    return config.get_active_weights()

def enable_enhanced_feature(feature_name: str):
    """Enable an enhanced feature"""
    config.enable_feature(feature_name)

def disable_enhanced_feature(feature_name: str):
    """Disable an enhanced feature"""
    config.disable_feature(feature_name)

def is_enhanced_feature_enabled(feature_name: str) -> bool:
    """Check if enhanced feature is enabled"""
    return config.is_feature_enabled(feature_name)

def print_config():
    """Print current configuration"""
    config.print_active_configuration()

def get_form_analysis_config() -> Dict[str, Any]:
    """Get current form analysis configuration"""
    return config.FORM_ANALYSIS.copy()

def update_form_analysis(recent_matches: int = None, comprehensive_matches: int = None, 
                        recent_weight: float = None, comprehensive_weight: float = None):
    """Update form analysis configuration"""
    if recent_matches is not None:
        config.FORM_ANALYSIS['recent_matches'] = recent_matches
        print(f"✅ Updated recent matches to: {recent_matches}")
    
    if comprehensive_matches is not None:
        config.FORM_ANALYSIS['comprehensive_matches'] = comprehensive_matches
        print(f"✅ Updated comprehensive matches to: {comprehensive_matches}")
    
    if recent_weight is not None:
        config.FORM_ANALYSIS['recent_weight'] = recent_weight
        print(f"✅ Updated recent weight to: {recent_weight:.1%}")
        
    if comprehensive_weight is not None:
        config.FORM_ANALYSIS['comprehensive_weight'] = comprehensive_weight
        print(f"✅ Updated comprehensive weight to: {comprehensive_weight:.1%}")
        
    # Validate weights sum to 1.0
    total_weight = config.FORM_ANALYSIS['recent_weight'] + config.FORM_ANALYSIS['comprehensive_weight']
    if abs(total_weight - 1.0) > 0.01:
        print(f"⚠️  Warning: Form weights sum to {total_weight:.3f}, not 1.0")
        
def reset_form_analysis_to_defaults():
    """Reset form analysis to original default values"""
    config.FORM_ANALYSIS = {
        'recent_matches': 10,
        'comprehensive_matches': 50,
        'recent_weight': 0.75,
        'comprehensive_weight': 0.25
    }
    print("✅ Reset form analysis to original defaults")

def enable_home_advantage(bonus_percentage: float = 0.10):
    """Enable home advantage bonus"""
    config.enable_home_advantage(bonus_percentage)

def disable_home_advantage():
    """Disable home advantage bonus"""
    config.disable_home_advantage()

def set_home_advantage_bonus(bonus_percentage: float):
    """Set home advantage bonus percentage"""
    config.set_home_advantage_bonus(bonus_percentage)

def print_home_advantage_status():
    """Print current home advantage configuration"""
    config.print_home_advantage_status()

def enable_three_year_stats():
    """Enable 3-year statistics mode (2023-2024-2025)"""
    config.enable_three_year_stats()

def disable_three_year_stats():
    """Disable 3-year mode, revert to 2-year mode (2024-2025)"""
    config.disable_three_year_stats()

def set_min_years_required(min_years: int):
    """Set minimum number of years required (1-3)"""
    config.set_min_years_required(min_years)

def print_multi_year_stats_status():
    """Print current multi-year statistics configuration"""
    config.print_multi_year_stats_status()


if __name__ == "__main__":
    # Demo configuration
    print("🎾 TENNIS PREDICTION CONFIGURATION DEMO")
    print("=" * 50)
    
    print("\n1. BASE CONFIGURATION (Enhanced features disabled):")
    config.print_active_configuration()
    
    print("\n" + "=" * 50)
    print("\n2. ENABLING TIEBREAK PERFORMANCE:")
    config.enable_feature('tiebreak_performance')
    config.print_active_configuration()
    
    print("\n" + "=" * 50)
    print("\n3. DISABLING TIEBREAK PERFORMANCE:")
    config.disable_feature('tiebreak_performance')
    config.print_active_configuration()
