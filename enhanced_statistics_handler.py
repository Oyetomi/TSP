"""
Enhanced Statistics Handler for Year Transitions and Data Quality

Handles insufficient data scenarios with intelligent multi-year fallback system.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import logging

class EnhancedStatisticsHandler:
    """Smart statistics handler with year transition support (2 or 3 years)"""
    
    def __init__(self, player_service, config=None):
        self.player_service = player_service
        self.config = config  # PredictionConfig instance
        
        # Minimum sample sizes for reliable statistics
        self.MIN_SAMPLE_SIZES = {
            'matches': 5,           # At least 5 matches for basic stats
            'tiebreaks': 3,         # At least 3 tiebreaks for TB stats
            'break_points': 10,     # At least 10 break points for pressure stats
            'serve_points': 50      # At least 50 serve points for serve stats
        }
        
        # Season progress thresholds for weighting strategy
        self.SEASON_THRESHOLDS = {
            'very_early': 3,    # Jan-Mar: Use previous year heavily
            'early': 6,         # Apr-Jun: Blend years
            'mid_late': 12      # Jul-Dec: Primarily current year
        }
    
    def get_enhanced_player_statistics(
        self, 
        player_id: int, 
        surface: str = None,
        current_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get enhanced player statistics with intelligent year fallback (2 or 3 years)
        
        Args:
            player_id: MatchDataProvider player ID
            surface: Specific surface to analyze
            current_date: Current date (for testing scenarios)
            
        Returns:
            Enhanced statistics with quality metrics
        """
        if current_date is None:
            current_date = datetime.now()
        
        current_year = current_date.year
        previous_year = current_year - 1
        two_years_ago = current_year - 2
        
        # Check if 3-year mode is enabled
        use_three_years = False
        min_years_required = 2
        if self.config and hasattr(self.config, 'MULTI_YEAR_STATS'):
            use_three_years = self.config.MULTI_YEAR_STATS.get('enable_three_year_stats', False)
            min_years_required = self.config.MULTI_YEAR_STATS.get('min_years_required', 2)
        
        # Determine season progress and strategy
        strategy = self._determine_strategy(current_date, use_three_years)
        
        # Fetch statistics for 2 or 3 years
        current_stats = self._fetch_year_stats(player_id, current_year)
        previous_stats = self._fetch_year_stats(player_id, previous_year)
        old_stats = None
        
        if use_three_years:
            old_stats = self._fetch_year_stats(player_id, two_years_ago)
        
        # Validate minimum years requirement
        available_years = []
        if current_stats and not current_stats.get('_404_error'):
            available_years.append(current_year)
        if previous_stats and not previous_stats.get('_404_error'):
            available_years.append(previous_year)
        if old_stats and not old_stats.get('_404_error'):
            available_years.append(two_years_ago)
        
        # Check if we have enough years
        if len(available_years) < min_years_required:
            logging.warning(f"Player {player_id} has only {len(available_years)} years of data "
                          f"(required: {min_years_required}). Available: {available_years}")
        
        # Combine statistics based on strategy
        if use_three_years:
            combined_stats = self._combine_three_year_statistics(
                current_stats, 
                previous_stats,
                old_stats,
                strategy,
                surface
            )
        else:
            combined_stats = self._combine_year_statistics(
                current_stats, 
                previous_stats, 
                strategy,
                surface
            )
        
        # Check for critical 404 errors
        has_404_error = False
        if current_stats and current_stats.get('_404_error'):
            has_404_error = True
        if previous_stats and previous_stats.get('_404_error'):
            has_404_error = True
        if old_stats and old_stats.get('_404_error'):
            has_404_error = True
        
        # Extract current-year-only stats for quality checks
        current_year_only_stats = None
        if current_stats:
            current_year_only_stats = self._extract_surface_stats(current_stats, surface)
        
        # LOG SURFACE-SPECIFIC STATISTICS EXTRACTION - ENHANCED
        if surface and combined_stats:
            matches = combined_stats.get('matches', 0)
            wins = combined_stats.get('wins', 0)
            aces = combined_stats.get('aces', 0)
            ground_type = combined_stats.get('groundType', 'Unknown')
            
            # Current year only stats
            curr_matches = current_year_only_stats.get('matches', 0) if current_year_only_stats else 0
            curr_wins = current_year_only_stats.get('wins', 0) if current_year_only_stats else 0
            curr_win_rate = (curr_wins/curr_matches*100) if curr_matches > 0 else 0
            
            # Previous year stats for comparison
            prev_year_stats = None
            if previous_stats:
                prev_year_stats = self._extract_surface_stats(previous_stats, surface)
            prev_matches = prev_year_stats.get('matches', 0) if prev_year_stats else 0
            prev_wins = prev_year_stats.get('wins', 0) if prev_year_stats else 0
            prev_win_rate = (prev_wins/prev_matches*100) if prev_matches > 0 else 0
            
            # Old year stats (if using 3-year mode)
            old_year_stats = None
            old_matches = 0
            old_wins = 0
            old_win_rate = 0
            if use_three_years and old_stats:
                old_year_stats = self._extract_surface_stats(old_stats, surface)
                old_matches = old_year_stats.get('matches', 0) if old_year_stats else 0
                old_wins = old_year_stats.get('wins', 0) if old_year_stats else 0
                old_win_rate = (old_wins/old_matches*100) if old_matches > 0 else 0
            
            print(f"\n   📈 RAW MATCH_DATA STATISTICS (SURFACE: {surface}):")
            print(f"      Player ID: {player_id}")
            print(f"      Surface matched: {ground_type}")
            print(f"      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"      📅 {current_year} DATA: {curr_matches} matches | {curr_wins} wins | {curr_win_rate:.1f}% win rate")
            print(f"      📅 {previous_year} DATA: {prev_matches} matches | {prev_wins} wins | {prev_win_rate:.1f}% win rate")
            if use_three_years and old_year_stats:
                print(f"      📅 {two_years_ago} DATA: {old_matches} matches | {old_wins} wins | {old_win_rate:.1f}% win rate")
            
            # Show blended stats with appropriate weights
            if use_three_years:
                blend_desc = f"{int(strategy['current_weight']*100)}% current + {int(strategy['previous_weight']*100)}% prev + {int(strategy.get('old_weight', 0)*100)}% old"
            else:
                blend_desc = f"{int(strategy['current_weight']*100)}% current + {int(strategy['previous_weight']*100)}% prev"
            
            print(f"      📊 BLENDED ({blend_desc}): {matches} matches | {wins} wins | {(wins/matches*100) if matches > 0 else 0:.1f}%")
            print(f"      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # Warnings
            if curr_matches == 0:
                print(f"      🚨 CRITICAL: NO {current_year} DATA - Using {previous_year} extrapolation only")
            elif curr_matches < 5:
                print(f"      ⚠️  WARNING: SMALL {current_year} SAMPLE ({curr_matches} matches) - Unreliable prediction")
            
            if curr_win_rate < 45 and curr_matches >= 3:
                print(f"      ⚠️  WARNING: Poor {current_year} performance ({curr_win_rate:.1f}% < 45% threshold)")
            
            if curr_win_rate < 50 and prev_win_rate < 50 and curr_matches >= 5 and prev_matches >= 5:
                print(f"      🎲 WARNING: Both years below 50% - Mediocre/inconsistent player on {surface}")
            print(f"      Aces: {aces} | Aces/match: {(aces/matches) if matches > 0 else 0:.1f}")
            print(f"      Strategy: {strategy['name']} ({strategy['description']})")
            print(f"      Reliability score: {self._calculate_reliability_score(combined_stats, strategy):.1%}")
            
        return {
            'statistics': combined_stats,
            'current_year_only': current_year_only_stats,  # NEW: Separate current year tracking
            'strategy_used': strategy,
            'data_quality': self._assess_data_quality(combined_stats),
            'sample_sizes': self._calculate_sample_sizes(combined_stats),
            'reliability_score': self._calculate_reliability_score(combined_stats, strategy),
            'has_404_error': has_404_error  # Critical: indicates missing player data
        }
    
    def _determine_strategy(self, current_date: datetime, use_three_years: bool = False) -> Dict[str, Any]:
        """Determine weighting strategy based on date and year mode"""
        month = current_date.month
        
        # Get weights from config if available, otherwise use defaults
        if use_three_years:
            if self.config and hasattr(self.config, 'MULTI_YEAR_STATS'):
                year_weights = self.config.MULTI_YEAR_STATS['year_weights']['three_year_mode']
                return {
                    'name': 'three_year_mode',
                    'description': '3-year stats - deeper historical context',
                    'current_weight': year_weights['current_year'],
                    'previous_weight': year_weights['previous_year'],
                    'old_weight': year_weights['two_years_ago'],
                    'min_current_matches': 5,
                    'mode': '3-year'
                }
            else:
                # Fallback default for 3-year mode
                return {
                    'name': 'three_year_mode',
                    'description': '3-year stats - deeper historical context',
                    'current_weight': 0.6,
                    'previous_weight': 0.3,
                    'old_weight': 0.1,
                    'min_current_matches': 5,
                    'mode': '3-year'
                }
        
        # 2-year mode (standard behavior)
        if self.config and hasattr(self.config, 'MULTI_YEAR_STATS'):
            year_weights = self.config.MULTI_YEAR_STATS['year_weights']['two_year_mode']
            current_w = year_weights['current_year']
            previous_w = year_weights['previous_year']
        else:
            # Season-based strategy (legacy behavior)
            if month <= self.SEASON_THRESHOLDS['very_early']:
                current_w, previous_w = 0.2, 0.8
            elif month <= self.SEASON_THRESHOLDS['early']:
                current_w, previous_w = 0.6, 0.4
            else:
                current_w, previous_w = 0.9, 0.1
        
        return {
            'name': 'two_year_mode',
            'description': '2-year stats - standard behavior',
            'current_weight': current_w,
            'previous_weight': previous_w,
            'min_current_matches': 8 if month > self.SEASON_THRESHOLDS['early'] else 3,
            'mode': '2-year'
        }
    
    def _fetch_year_stats(self, player_id: int, year: int) -> Optional[Dict[str, Any]]:
        """Safely fetch year statistics and track 404 errors"""
        try:
            stats = self.player_service.get_player_year_statistics(player_id, year)
            return stats if stats and stats.get('statistics') else None
        except Exception as e:
            if "404" in str(e) or "HTTP Error 404" in str(e):
                # This is a critical data quality issue - player has no stats for this year
                logging.warning(f"404 ERROR: No {year} stats found for player {player_id} - {e}")
                return {'_404_error': True, 'year': year}
            else:
                logging.warning(f"Failed to fetch {year} stats for player {player_id}: {e}")
                return None
    
    def _combine_year_statistics(
        self, 
        current_stats: Optional[Dict], 
        previous_stats: Optional[Dict],
        strategy: Dict[str, Any],
        surface: str = None
    ) -> Dict[str, Any]:
        """Intelligently combine statistics from multiple years"""
        
        if not current_stats and not previous_stats:
            return self._get_neutral_fallback()
        
        if not current_stats:
            # No current year data - use previous year
            return self._extract_surface_stats(previous_stats, surface) if previous_stats else self._get_neutral_fallback()
        
        if not previous_stats:
            # No previous year data - use current year
            return self._extract_surface_stats(current_stats, surface)
        
        # Both years available - blend based on strategy
        current_surface = self._extract_surface_stats(current_stats, surface)
        previous_surface = self._extract_surface_stats(previous_stats, surface)
        
        # Check if current year has sufficient data
        current_matches = current_surface.get('matches', 0)
        min_matches = strategy.get('min_current_matches', 5)
        
        if current_matches < min_matches:
            # Insufficient current year data - increase previous year weight
            actual_current_weight = max(0.1, strategy['current_weight'] * (current_matches / min_matches))
            actual_previous_weight = 1.0 - actual_current_weight
            
            logging.info(f"Insufficient current year data ({current_matches} matches). "
                        f"Adjusted weights: Current {actual_current_weight:.1%}, Previous {actual_previous_weight:.1%}")
        else:
            actual_current_weight = strategy['current_weight']
            actual_previous_weight = strategy['previous_weight']
        
        # Weighted combination of statistics
        return self._weighted_combine_stats(
            current_surface, 
            previous_surface, 
            actual_current_weight, 
            actual_previous_weight
        )
    
    def _combine_three_year_statistics(
        self, 
        current_stats: Optional[Dict], 
        previous_stats: Optional[Dict],
        old_stats: Optional[Dict],
        strategy: Dict[str, Any],
        surface: str = None
    ) -> Dict[str, Any]:
        """Intelligently combine statistics from 3 years"""
        
        # Extract surface stats for each year
        current_surface = self._extract_surface_stats(current_stats, surface) if current_stats else {}
        previous_surface = self._extract_surface_stats(previous_stats, surface) if previous_stats else {}
        old_surface = self._extract_surface_stats(old_stats, surface) if old_stats else {}
        
        # Count available years
        available_years = []
        if current_surface and current_surface.get('matches', 0) > 0:
            available_years.append('current')
        if previous_surface and previous_surface.get('matches', 0) > 0:
            available_years.append('previous')
        if old_surface and old_surface.get('matches', 0) > 0:
            available_years.append('old')
        
        # Handle cases with insufficient data
        if len(available_years) == 0:
            return self._get_neutral_fallback()
        
        # Get min years required from config
        min_years = 2
        if self.config and hasattr(self.config, 'MULTI_YEAR_STATS'):
            min_years = self.config.MULTI_YEAR_STATS.get('min_years_required', 2)
        
        # Check if we have enough years
        if len(available_years) < min_years:
            logging.warning(f"Only {len(available_years)} years available (required: {min_years})")
            # Return neutral fallback if not enough years
            if min_years > len(available_years):
                return self._get_neutral_fallback()
        
        # Adjust weights based on available data
        if len(available_years) == 1:
            # Only one year - use it with 100% weight
            if 'current' in available_years:
                return current_surface
            elif 'previous' in available_years:
                return previous_surface
            else:
                return old_surface
        
        elif len(available_years) == 2:
            # Two years available - use 2-year blending
            if 'current' in available_years and 'previous' in available_years:
                # Current + Previous: Use standard 70/30 split
                return self._weighted_combine_stats(
                    current_surface, previous_surface, 0.7, 0.3
                )
            elif 'current' in available_years and 'old' in available_years:
                # Current + Old: Use 80/20 split (old data less relevant)
                return self._weighted_combine_stats(
                    current_surface, old_surface, 0.8, 0.2
                )
            else:
                # Previous + Old: Use 70/30 split
                return self._weighted_combine_stats(
                    previous_surface, old_surface, 0.7, 0.3
                )
        
        else:
            # All 3 years available - use 3-way weighting
            current_weight = strategy.get('current_weight', 0.6)
            previous_weight = strategy.get('previous_weight', 0.3)
            old_weight = strategy.get('old_weight', 0.1)
            
            # Check if current year has sufficient matches
            current_matches = current_surface.get('matches', 0)
            min_matches = strategy.get('min_current_matches', 5)
            
            if current_matches < min_matches and current_matches > 0:
                # Insufficient current year data - redistribute weight
                deficit = 1.0 - (current_matches / min_matches)
                current_weight = max(0.3, current_weight * (current_matches / min_matches))
                # Redistribute deficit to previous and old proportionally
                extra_weight = (previous_weight + old_weight) * deficit / (previous_weight + old_weight) if (previous_weight + old_weight) > 0 else 0
                previous_weight += extra_weight * (previous_weight / (previous_weight + old_weight)) if (previous_weight + old_weight) > 0 else 0
                old_weight += extra_weight * (old_weight / (previous_weight + old_weight)) if (previous_weight + old_weight) > 0 else 0
                
                # Normalize to ensure weights sum to 1.0
                total = current_weight + previous_weight + old_weight
                current_weight /= total
                previous_weight /= total
                old_weight /= total
                
                logging.info(f"Adjusted 3-year weights due to low current matches ({current_matches}): "
                          f"Current {current_weight:.1%}, Previous {previous_weight:.1%}, Old {old_weight:.1%}")
            
            # Perform 3-way weighted combination
            return self._weighted_combine_three_stats(
                current_surface, 
                previous_surface,
                old_surface,
                current_weight, 
                previous_weight,
                old_weight
            )
    
    def _normalize_surface_name(self, surface: str) -> str:
        """
        Normalize surface names for consistent matching
        
        CRITICAL FIX: Preserve indoor/outdoor hardcourt distinction
        
        MatchDataProvider API uses specific surface names like:
        - "Red clay", "Clay" → "Clay" 
        - "Hardcourt outdoor" → "Hardcourt outdoor"
        - "Hardcourt indoor" → "Hardcourt indoor" 
        - "Hard" → "Hard" (generic fallback)
        - "Grass" → "Grass"
        """
        if not surface:
            return None
            
        surface_lower = surface.lower()
        
        # Clay variants
        if any(clay_type in surface_lower for clay_type in ['clay', 'red clay', 'blue clay']):
            return 'Clay'
        
        # Hardcourt variants - PRESERVE INDOOR/OUTDOOR DISTINCTION!
        elif 'hardcourt indoor' in surface_lower or 'indoor' in surface_lower:
            return 'Hardcourt indoor'
        elif 'hardcourt outdoor' in surface_lower or ('hardcourt' in surface_lower and 'outdoor' in surface_lower):
            return 'Hardcourt outdoor'
        elif 'hardcourt' in surface_lower or 'hard' in surface_lower:
            return 'Hard'  # Generic hardcourt fallback
        
        # Grass
        elif 'grass' in surface_lower:
            return 'Grass'
        
        # Return original if no match
        return surface

    def _find_surface_match(self, stats_list: list, requested_surface: str) -> Dict[str, Any]:
        """
        Find surface statistics with intelligent matching
        
        CRITICAL FIX: This fixes the bug where "Red clay" != "Clay" exact matching
        caused massive data loss (23 matches → 4 matches for players like Simona Waltert)
        """
        if not requested_surface:
            return {}
        
        normalized_requested = self._normalize_surface_name(requested_surface)
        
        # First try: Exact match (for backward compatibility)
        for stat in stats_list:
            if stat.get('groundType') == requested_surface:
                return stat
        
        # Second try: Normalized matching (THE FIX!)
        for stat in stats_list:
            api_surface = stat.get('groundType', '')
            normalized_api = self._normalize_surface_name(api_surface)
            
            if normalized_api == normalized_requested:
                print(f"   🔧 SURFACE MAPPING FIX: '{requested_surface}' → '{api_surface}' (normalized)")
                return stat
        
        # Third try: Partial matching for edge cases
        requested_lower = requested_surface.lower()
        for stat in stats_list:
            api_surface = stat.get('groundType', '').lower()
            if requested_lower in api_surface or api_surface in requested_lower:
                print(f"   🔧 SURFACE PARTIAL MATCH: '{requested_surface}' → '{stat.get('groundType')}' (partial)")
                return stat
        
        return {}  # No match found

    def _extract_surface_stats(self, year_stats: Dict, surface: str = None) -> Dict[str, Any]:
        """Extract surface-specific statistics with intelligent surface matching"""
        if not year_stats or not year_stats.get('statistics'):
            return {}
        
        stats_list = year_stats['statistics']
        
        if surface:
            # Use the new intelligent surface matching (CRITICAL FIX!)
            return self._find_surface_match(stats_list, surface)
        else:
            # Aggregate all surfaces
            return self._aggregate_surface_stats(stats_list)
    
    def _aggregate_surface_stats(self, stats_list: list) -> Dict[str, Any]:
        """Aggregate statistics across all surfaces"""
        if not stats_list:
            return {}
        
        # Sum up all numeric fields
        aggregated = {}
        numeric_fields = [
            'matches', 'wins', 'aces', 'doubleFaults', 'totalServeAttempts',
            'firstServeTotal', 'firstServePointsScored', 'firstServePointsTotal',
            'secondServeTotal', 'secondServePointsScored', 'secondServePointsTotal',
            'breakPointsScored', 'breakPointsTotal', 'opponentBreakPointsTotal',
            'opponentBreakPointsScored', 'tiebreaksWon', 'tiebreakLosses',
            'winnersTotal', 'unforcedErrorsTotal', 'tournamentsPlayed', 'tournamentsWon'
        ]
        
        for field in numeric_fields:
            aggregated[field] = sum(stat.get(field, 0) for stat in stats_list)
        
        aggregated['groundType'] = 'All Surfaces'
        return aggregated
    
    def _weighted_combine_stats(
        self, 
        current: Dict[str, Any], 
        previous: Dict[str, Any], 
        current_weight: float, 
        previous_weight: float
    ) -> Dict[str, Any]:
        """Combine two stat dictionaries with weights"""
        if not current and not previous:
            return {}
        if not current:
            return previous
        if not previous:
            return current
        
        combined = {}
        
        # Numeric fields to combine
        numeric_fields = [
            'matches', 'wins', 'aces', 'doubleFaults', 'totalServeAttempts',
            'firstServeTotal', 'firstServePointsScored', 'firstServePointsTotal',
            'secondServeTotal', 'secondServePointsScored', 'secondServePointsTotal',
            'breakPointsScored', 'breakPointsTotal', 'opponentBreakPointsTotal',
            'opponentBreakPointsScored', 'tiebreaksWon', 'tiebreakLosses',
            'winnersTotal', 'unforcedErrorsTotal'
        ]
        
        for field in numeric_fields:
            current_val = current.get(field, 0)
            previous_val = previous.get(field, 0)
            combined[field] = (current_val * current_weight) + (previous_val * previous_weight)
        
        # Keep surface info
        combined['groundType'] = current.get('groundType', previous.get('groundType', 'Unknown'))
        combined['data_source'] = f"Weighted: {current_weight:.1%} current + {previous_weight:.1%} previous"
        
        return combined
    
    def _weighted_combine_three_stats(
        self, 
        current: Dict[str, Any], 
        previous: Dict[str, Any],
        old: Dict[str, Any],
        current_weight: float, 
        previous_weight: float,
        old_weight: float
    ) -> Dict[str, Any]:
        """Combine three stat dictionaries with weights"""
        if not current and not previous and not old:
            return {}
        
        combined = {}
        
        # Numeric fields to combine
        numeric_fields = [
            'matches', 'wins', 'aces', 'doubleFaults', 'totalServeAttempts',
            'firstServeTotal', 'firstServePointsScored', 'firstServePointsTotal',
            'secondServeTotal', 'secondServePointsScored', 'secondServePointsTotal',
            'breakPointsScored', 'breakPointsTotal', 'opponentBreakPointsTotal',
            'opponentBreakPointsScored', 'tiebreaksWon', 'tiebreakLosses',
            'winnersTotal', 'unforcedErrorsTotal'
        ]
        
        for field in numeric_fields:
            current_val = current.get(field, 0) if current else 0
            previous_val = previous.get(field, 0) if previous else 0
            old_val = old.get(field, 0) if old else 0
            combined[field] = (current_val * current_weight) + (previous_val * previous_weight) + (old_val * old_weight)
        
        # Keep surface info from most recent available
        if current:
            combined['groundType'] = current.get('groundType', 'Unknown')
        elif previous:
            combined['groundType'] = previous.get('groundType', 'Unknown')
        else:
            combined['groundType'] = old.get('groundType', 'Unknown')
        
        combined['data_source'] = f"3-Year Weighted: {current_weight:.1%} current + {previous_weight:.1%} previous + {old_weight:.1%} old"
        
        return combined
    
    def _get_neutral_fallback(self) -> Dict[str, Any]:
        """Return neutral fallback statistics when no data available"""
        return {
            'matches': 0,
            'wins': 0,
            'groundType': 'Unknown',
            'data_source': 'Neutral Fallback - No Data Available',
            'reliability_score': 0.0
        }
    
    def _assess_data_quality(self, stats: Dict[str, Any]) -> str:
        """Assess the quality of the statistics data"""
        matches = stats.get('matches', 0)
        tiebreaks = stats.get('tiebreaksWon', 0) + stats.get('tiebreakLosses', 0)
        break_points = stats.get('breakPointsTotal', 0)
        
        if matches >= 20 and tiebreaks >= 5 and break_points >= 30:
            return 'Excellent'
        elif matches >= 10 and break_points >= 15:
            return 'Good'
        elif matches >= 5:
            return 'Fair'
        else:
            return 'Poor'
    
    def _calculate_sample_sizes(self, stats: Dict[str, Any]) -> Dict[str, int]:
        """Calculate sample sizes for different statistics"""
        return {
            'matches': stats.get('matches', 0),
            'tiebreaks': stats.get('tiebreaksWon', 0) + stats.get('tiebreakLosses', 0),
            'break_points': stats.get('breakPointsTotal', 0),
            'serve_points': stats.get('totalServeAttempts', 0)
        }
    
    def _calculate_reliability_score(self, stats: Dict[str, Any], strategy: Dict[str, Any]) -> float:
        """Calculate overall reliability score (0.0 - 1.0)"""
        sample_sizes = self._calculate_sample_sizes(stats)
        
        # Base score from sample sizes
        reliability_scores = []
        
        for stat_type, min_size in self.MIN_SAMPLE_SIZES.items():
            actual_size = sample_sizes.get(stat_type, 0)
            if actual_size >= min_size:
                reliability_scores.append(1.0)
            elif actual_size > 0:
                reliability_scores.append(actual_size / min_size)
            else:
                reliability_scores.append(0.0)
        
        base_reliability = sum(reliability_scores) / len(reliability_scores)
        
        # Adjust based on strategy confidence
        strategy_confidence = {
            'current_year_focus': 1.0,
            'balanced_blend': 0.85,
            'previous_year_heavy': 0.7
        }
        
        strategy_adjustment = strategy_confidence.get(strategy['name'], 0.8)
        
        return min(1.0, base_reliability * strategy_adjustment)


# Example usage functions
def calculate_enhanced_tiebreak_performance(stats_handler, player_id: int, surface: str = None) -> float:
    """Calculate tiebreak performance with year transition handling"""
    enhanced_stats = stats_handler.get_enhanced_player_statistics(player_id, surface)
    stats = enhanced_stats['statistics']
    reliability = enhanced_stats['reliability_score']
    
    tb_won = stats.get('tiebreaksWon', 0)
    tb_lost = stats.get('tiebreakLosses', 0)
    tb_total = tb_won + tb_lost
    
    if tb_total >= 3:  # Sufficient sample
        tb_rate = tb_won / tb_total
    elif tb_total > 0:  # Some data but insufficient
        tb_rate = (tb_won / tb_total) * 0.7 + 0.15  # Weighted toward neutral
    else:  # No tiebreak data
        tb_rate = 0.5
    
    # Adjust confidence based on data reliability
    confidence_adjustment = 0.5 + (reliability * 0.5)  # 0.5 to 1.0 range
    return tb_rate * confidence_adjustment + 0.5 * (1 - confidence_adjustment)


def calculate_enhanced_pressure_performance(stats_handler, player_id: int, surface: str = None) -> float:
    """Calculate pressure performance with year transition handling"""
    enhanced_stats = stats_handler.get_enhanced_player_statistics(player_id, surface)
    stats = enhanced_stats['statistics']
    reliability = enhanced_stats['reliability_score']
    
    # Break point conversion
    bp_scored = stats.get('breakPointsScored', 0)
    bp_total = stats.get('breakPointsTotal', 0)
    conversion_rate = bp_scored / bp_total if bp_total >= 10 else 0.35  # Default for insufficient data
    
    # Break point save rate
    opp_bp_total = stats.get('opponentBreakPointsTotal', 0)
    opp_bp_scored = stats.get('opponentBreakPointsScored', 0)
    save_rate = (opp_bp_total - opp_bp_scored) / opp_bp_total if opp_bp_total >= 10 else 0.6
    
    # Combined pressure performance
    pressure_score = (conversion_rate * 0.6) + (save_rate * 0.4)
    
    # Adjust based on reliability
    confidence_adjustment = 0.5 + (reliability * 0.5)
    return pressure_score * confidence_adjustment + 0.5 * (1 - confidence_adjustment)


def calculate_enhanced_serve_dominance(stats_handler, player_id: int, surface: str = None) -> float:
    """Calculate serve dominance with year transition handling"""
    enhanced_stats = stats_handler.get_enhanced_player_statistics(player_id, surface)
    stats = enhanced_stats['statistics']
    reliability = enhanced_stats['reliability_score']
    
    matches = stats.get('matches', 1)
    
    # Aces per match
    aces_per_match = stats.get('aces', 0) / matches if matches > 0 else 0
    ace_score = min(aces_per_match / 15.0, 1.0)
    
    # First serve win rate
    first_serve_won = stats.get('firstServePointsScored', 0)
    first_serve_total = stats.get('firstServePointsTotal', 1)
    first_serve_rate = first_serve_won / first_serve_total if first_serve_total >= 20 else 0.65
    
    # Combined serve dominance
    serve_score = (ace_score * 0.4) + (first_serve_rate * 0.6)
    
    # Adjust based on reliability
    confidence_adjustment = 0.5 + (reliability * 0.5)
    return serve_score * confidence_adjustment + 0.5 * (1 - confidence_adjustment)
