#!/usr/bin/env python3
"""
Elo Rating Service - Modular and Toggleable
==========================================

Provides Elo rating integration for tennis predictions.
Can be enabled/disabled via configuration.

Features:
- Fetches Elo ratings from Tennis Abstract (when available)
- Calculates Elo-based probabilities
- Surface-specific Elo adjustments
- Fallback mechanisms for missing data
- Completely decoupled from main prediction flow

Usage:
    from elo_rating_service import EloRatingService
    
    elo_service = EloRatingService(enabled=True)
    
    if elo_service.is_enabled():
        elo_data = elo_service.get_elo_blend_factor(
            player1_name="Novak Djokovic",
            player2_name="Carlos Alcaraz",
            player1_atp_rank=1,
            player2_atp_rank=2,
            surface="hardcourt"
        )
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

# Try to import Tennis Abstract scraper
try:
    from tennis_abstract_integration import TennisAbstractScraper
    TENNIS_ABSTRACT_AVAILABLE = True
except ImportError:
    TENNIS_ABSTRACT_AVAILABLE = False
    print("⚠️  Tennis Abstract integration not available")

# Try to import fuzzy matching libraries
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    try:
        from fuzzywuzzy import fuzz, process
        RAPIDFUZZ_AVAILABLE = True
        print("ℹ️  Using fuzzywuzzy (consider upgrading to rapidfuzz for better performance)")
    except ImportError:
        RAPIDFUZZ_AVAILABLE = False
        print("ℹ️  Fuzzy matching not available (install rapidfuzz or fuzzywuzzy)")


class EloRatingService:
    """Modular Elo rating service that can be toggled on/off"""
    
    def __init__(self, enabled: bool = False, csv_path: str = "tennis_abstract_elo.csv", 
                 auto_update: bool = True, freshness_days: int = 7):
        """
        Initialize Elo rating service
        
        Args:
            enabled: Whether Elo integration is enabled
            csv_path: Path to Tennis Abstract Elo CSV export
            auto_update: Whether to automatically update stale data
            freshness_days: Number of days before CSV is considered stale
        """
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)
        self.cache = {}
        self.tennis_abstract = None
        self.csv_elo_data = {}
        self.csv_path = csv_path
        self.auto_update = auto_update
        self.freshness_days = freshness_days
        
        if self.enabled:
            self.logger.info("✅ Elo Rating Service ENABLED")
            
            # Try to load Tennis Abstract CSV first (fastest, no dependencies)
            self._load_tennis_abstract_csv()
            
            # Fallback to scraper if CSV not available and pandas installed
            if not self.csv_elo_data and TENNIS_ABSTRACT_AVAILABLE:
                try:
                    self.tennis_abstract = TennisAbstractScraper(rate_limit_seconds=2)
                    self.logger.info("✅ Tennis Abstract web scraper initialized")
                except Exception as e:
                    self.logger.warning(f"⚠️  Tennis Abstract scraper init failed: {e}")
            
            if not self.csv_elo_data and not self.tennis_abstract:
                self.logger.info("ℹ️  Tennis Abstract not available, using ATP-derived Elo fallback")
        else:
            self.logger.info("❌ Elo Rating Service DISABLED")
    
    def _check_csv_freshness(self) -> bool:
        """
        Check if Tennis Abstract CSV is fresh (< freshness_days old)
        
        Returns:
            True if CSV is fresh, False if stale or missing
        """
        try:
            import os
            
            if not os.path.exists(self.csv_path):
                self.logger.info(f"📄 Tennis Abstract CSV not found: {self.csv_path}")
                return False
            
            # Check file modification time
            mtime = os.path.getmtime(self.csv_path)
            file_age = datetime.now() - datetime.fromtimestamp(mtime)
            
            if file_age > timedelta(days=self.freshness_days):
                self.logger.info(f"📅 Tennis Abstract CSV is {file_age.days} days old (stale, threshold: {self.freshness_days} days)")
                return False
            
            self.logger.info(f"✅ Tennis Abstract CSV is {file_age.days} days old (fresh, threshold: {self.freshness_days} days)")
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️  Error checking CSV freshness: {e}")
            return False
    
    def _auto_update_csv(self):
        """
        Automatically fetch fresh Tennis Abstract data and update CSV
        Only runs if Tennis Abstract scraper is available
        """
        if not TENNIS_ABSTRACT_AVAILABLE:
            self.logger.warning("⚠️  Cannot auto-update: Tennis Abstract scraper not available")
            return False
        
        try:
            self.logger.info("🔄 Auto-updating Tennis Abstract Elo data...")
            
            # Initialize scraper if needed
            if not self.tennis_abstract:
                self.tennis_abstract = TennisAbstractScraper(rate_limit_seconds=2)
            
            # Fetch ATP data
            self.logger.info("   Fetching ATP rankings...")
            atp_players = self.tennis_abstract.fetch_atp_elo_rankings(force_refresh=True)
            
            # Fetch WTA data
            self.logger.info("   Fetching WTA rankings...")
            wta_players = self.tennis_abstract.fetch_wta_elo_rankings(force_refresh=True)
            
            if not atp_players:
                self.logger.error("❌ Failed to fetch ATP data")
                return False
            
            # Combine ATP and WTA
            all_players = atp_players + (wta_players if wta_players else [])
            
            # Write to CSV
            import pandas as pd
            df = pd.DataFrame(all_players)
            df.to_csv(self.csv_path, index=False)
            
            self.logger.info(f"✅ Auto-update complete: {len(all_players)} players (ATP: {len(atp_players)}, WTA: {len(wta_players) if wta_players else 0})")
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️  Auto-update failed: {e}")
            return False
    
    def _load_tennis_abstract_csv(self):
        """Load Tennis Abstract Elo data from CSV export (with auto-update)"""
        try:
            import csv
            import os
            
            # Auto-update logic (only if enabled)
            if self.auto_update:
                # Check if CSV exists and is fresh
                if not os.path.exists(self.csv_path):
                    self.logger.info(f"📄 Tennis Abstract CSV not found, attempting auto-update...")
                    if self._auto_update_csv():
                        self.logger.info("✅ Auto-update successful, loading data...")
                    else:
                        self.logger.warning("⚠️  Auto-update failed, CSV not available")
                        return
                elif not self._check_csv_freshness():
                    # CSV exists but is stale
                    self.logger.info(f"📅 Tennis Abstract CSV is stale, attempting auto-update...")
                    if self._auto_update_csv():
                        self.logger.info("✅ Auto-update successful, loading fresh data...")
                    else:
                        self.logger.warning("⚠️  Auto-update failed, using existing CSV")
            else:
                self.logger.info("ℹ️  Auto-update disabled, using existing CSV")
            
            # Load CSV data
            if not os.path.exists(self.csv_path):
                return
            
            with open(self.csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row['name']
                    self.csv_elo_data[name] = {
                        'elo_rating': float(row['elo_rating']),
                        'hard_elo': float(row['hard_elo']) if row.get('hard_elo') else None,
                        'clay_elo': float(row['clay_elo']) if row.get('clay_elo') else None,
                        'grass_elo': float(row['grass_elo']) if row.get('grass_elo') else None,
                        'elo_rank': int(row['elo_rank']) if row.get('elo_rank') else None,
                        'atp_rank': int(float(row['atp_rank'])) if row.get('atp_rank') and row['atp_rank'] != '' else None
                    }
            
            self.logger.info(f"✅ Loaded {len(self.csv_elo_data)} players from Tennis Abstract CSV")
            
        except Exception as e:
            self.logger.warning(f"Failed to load Tennis Abstract CSV: {e}")
    
    def is_enabled(self) -> bool:
        """Check if Elo integration is enabled"""
        return self.enabled
    
    def get_elo_blend_factor(
        self,
        player1_name: str,
        player2_name: str,
        player1_atp_rank: int,
        player2_atp_rank: int,
        surface: str = "hardcourt"
    ) -> Dict:
        """
        Get Elo-based blend factor for predictions
        
        Args:
            player1_name: Player 1 name
            player2_name: Player 2 name
            player1_atp_rank: Player 1 ATP ranking
            player2_atp_rank: Player 2 ATP ranking
            surface: Court surface
            
        Returns:
            Dict with:
                - 'elo_factor': Blend factor (0.0-1.0) for Elo influence
                - 'p1_elo': Player 1 Elo rating
                - 'p2_elo': Player 2 Elo rating
                - 'elo_probability': Elo-based win probability for Player 1
                - 'confidence': Confidence in Elo data (0.0-1.0)
        """
        if not self.enabled:
            return self._get_disabled_response()
        
        try:
            # Get Elo ratings for both players
            p1_elo_data = self._get_player_elo(player1_name, surface)
            p2_elo_data = self._get_player_elo(player2_name, surface)
            
            p1_elo = p1_elo_data['rating']
            p2_elo = p2_elo_data['rating']
            
            # Calculate Elo-based probability
            elo_probability = self._calculate_elo_probability(p1_elo, p2_elo, surface)
            
            # Calculate confidence in Elo data
            confidence = self._calculate_elo_confidence(
                p1_elo_data['source'],
                p2_elo_data['source'],
                player1_atp_rank,
                player2_atp_rank
            )
            
            # Determine blend factor based on confidence
            elo_factor = confidence * 0.15  # Max 15% influence when confidence is 100%
            
            return {
                'elo_factor': elo_factor,
                'p1_elo': p1_elo,
                'p2_elo': p2_elo,
                'elo_probability': elo_probability,
                'confidence': confidence,
                'enabled': True
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to get Elo data: {e}")
            return self._get_fallback_response(player1_atp_rank, player2_atp_rank)
    
    def _get_player_elo(self, player_name: str, surface: str) -> Dict:
        """
        Get Elo rating for a player from Tennis Abstract
        
        Priority: CSV data > Web scraper > Default
        
        Returns:
            Dict with 'rating' and 'source' ('tennis_abstract_csv', 'tennis_abstract_web', 'default')
        """
        # Map surface name to Elo key
        surface_mapping = {
            'hardcourt': 'hard_elo',
            'hardcourt indoor': 'hard_elo',
            'hardcourt outdoor': 'hard_elo',
            'hard': 'hard_elo',
            'clay': 'clay_elo',
            'red clay': 'clay_elo',
            'grass': 'grass_elo'
        }
        surface_key = surface_mapping.get(surface.lower(), 'hard_elo')
        
        # Try CSV data first (fastest)
        if self.csv_elo_data:
            # Try exact match
            if player_name in self.csv_elo_data:
                player_data = self.csv_elo_data[player_name]
                surface_elo = player_data.get(surface_key)
                rating = surface_elo if surface_elo is not None else player_data['elo_rating']
                
                self.logger.debug(f"✅ Tennis Abstract CSV Elo for {player_name}: {rating} ({surface})")
                
                return {
                    'rating': rating,
                    'source': 'tennis_abstract_csv',
                    'overall_elo': player_data['elo_rating'],
                    'elo_rank': player_data.get('elo_rank'),
                    'surface_elo': surface_elo
                }
            
            # Try fuzzy matching (with RapidFuzz/FuzzyWuzzy if available)
            if RAPIDFUZZ_AVAILABLE:
                # Use RapidFuzz/FuzzyWuzzy for intelligent matching
                matches = process.extract(
                    player_name,
                    self.csv_elo_data.keys(),
                    scorer=fuzz.token_sort_ratio,  # Handles reordering, middle names, etc.
                    limit=1
                )
                
                if matches and matches[0][1] >= 75:  # 75% match threshold
                    best_match = matches[0][0]
                    player_data = self.csv_elo_data[best_match]
                    surface_elo = player_data.get(surface_key)
                    rating = surface_elo if surface_elo is not None else player_data['elo_rating']
                    
                    self.logger.debug(f"✅ Tennis Abstract CSV Elo for {player_name} (matched {best_match}, {matches[0][1]:.0f}% confidence): {rating}")
                    
                    return {
                        'rating': rating,
                        'source': 'tennis_abstract_csv',
                        'overall_elo': player_data['elo_rating'],
                        'elo_rank': player_data.get('elo_rank'),
                        'surface_elo': surface_elo
                    }
            else:
                # Fallback to basic substring matching if fuzzy libs not available
                name_lower = player_name.lower()
                for csv_name, player_data in self.csv_elo_data.items():
                    if name_lower in csv_name.lower() or csv_name.lower() in name_lower:
                        surface_elo = player_data.get(surface_key)
                        rating = surface_elo if surface_elo is not None else player_data['elo_rating']
                        
                        self.logger.debug(f"✅ Tennis Abstract CSV Elo for {player_name} (substring matched {csv_name}): {rating}")
                        
                        return {
                            'rating': rating,
                            'source': 'tennis_abstract_csv',
                            'overall_elo': player_data['elo_rating'],
                            'elo_rank': player_data.get('elo_rank'),
                            'surface_elo': surface_elo
                        }
        
        # Try Tennis Abstract scraper if available
        if self.tennis_abstract:
            try:
                player_data = self.tennis_abstract.get_player_elo_data(player_name, tour='both')
                
                if player_data:
                    surface_elo = player_data.get(surface_key)
                    rating = surface_elo if surface_elo is not None else player_data['elo_rating']
                    
                    self.logger.debug(f"✅ Tennis Abstract Web Elo for {player_name}: {rating} ({surface})")
                    
                    return {
                        'rating': rating,
                        'source': 'tennis_abstract_web',
                        'overall_elo': player_data['elo_rating'],
                        'elo_rank': player_data.get('elo_rank'),
                        'surface_elo': surface_elo
                    }
                    
            except Exception as e:
                self.logger.debug(f"Tennis Abstract web lookup failed for {player_name}: {e}")
        
        # Fallback to default
        self.logger.debug(f"Using default Elo for {player_name}")
        return {
            'rating': 1500,  # Neutral default
            'source': 'default'
        }
    
    def _calculate_elo_probability(
        self,
        elo1: float,
        elo2: float,
        surface: str
    ) -> float:
        """
        Calculate match probability based on Elo ratings
        
        Uses standard Elo formula: P = 1 / (1 + 10^(-diff/400))
        
        Args:
            elo1: Player 1 Elo rating
            elo2: Player 2 Elo rating
            surface: Court surface for adjustments
            
        Returns:
            Probability of player 1 winning (0-1)
        """
        elo_diff = elo1 - elo2
        
        # Standard Elo probability
        probability = 1 / (1 + 10 ** (-elo_diff / 400))
        
        # Surface-specific adjustments (makes predictions more/less confident)
        surface_adjustments = {
            'clay': 0.02,         # Clay is more predictable (serve matters less)
            'red clay': 0.02,
            'grass': -0.03,       # Grass is more volatile (serve-dominant)
            'hardcourt': 0.0,     # Neutral
            'hardcourt indoor': -0.01,  # Slightly more volatile (fast)
            'hardcourt outdoor': 0.0
        }
        
        adjustment = surface_adjustments.get(surface.lower(), 0.0)
        adjusted_probability = probability + (adjustment * (0.5 - probability))
        
        # Clamp to reasonable bounds
        return max(0.1, min(0.9, adjusted_probability))
    
    def _calculate_elo_confidence(
        self,
        p1_source: str,
        p2_source: str,
        p1_atp_rank: int,
        p2_atp_rank: int
    ) -> float:
        """
        Calculate confidence in Elo data
        
        Confidence is higher when:
        - Elo data comes from Tennis Abstract (not derived)
        - Both players have good data
        - Players are highly ranked (more matches = better Elo)
        
        Returns:
            Confidence score (0.0-1.0)
        """
        # Source confidence
        source_confidence = {
            'tennis_abstract_csv': 1.0,      # Real Tennis Abstract data from CSV
            'tennis_abstract_web': 1.0,      # Real Tennis Abstract data from web
            'tennis_abstract': 1.0,          # Legacy compatibility
            'atp_derived': 0.6,
            'default': 0.0
        }
        
        p1_conf = source_confidence.get(p1_source, 0.0)
        p2_conf = source_confidence.get(p2_source, 0.0)
        avg_source_conf = (p1_conf + p2_conf) / 2
        
        # Ranking confidence (better ranked players have more stable Elo)
        def ranking_confidence(rank: int) -> float:
            if rank <= 50:
                return 1.0
            elif rank <= 100:
                return 0.9
            elif rank <= 200:
                return 0.7
            elif rank <= 500:
                return 0.5
            else:
                return 0.3
        
        p1_rank_conf = ranking_confidence(p1_atp_rank) if p1_atp_rank else 0.5
        p2_rank_conf = ranking_confidence(p2_atp_rank) if p2_atp_rank else 0.5
        avg_rank_conf = (p1_rank_conf + p2_rank_conf) / 2
        
        # Combined confidence (weighted 60% source, 40% ranking)
        total_confidence = (avg_source_conf * 0.6) + (avg_rank_conf * 0.4)
        
        return total_confidence
    
    def _get_disabled_response(self) -> Dict:
        """Return response when Elo is disabled"""
        return {
            'elo_factor': 0.0,
            'p1_elo': None,
            'p2_elo': None,
            'elo_probability': None,
            'confidence': 0.0,
            'enabled': False
        }
    
    def _get_fallback_response(self, p1_rank: Optional[int], p2_rank: Optional[int]) -> Dict:
        """Return fallback response when Elo fetch fails"""
        # Use ATP ranking to estimate Elo
        p1_elo = self._atp_rank_to_elo(p1_rank) if p1_rank else 1500
        p2_elo = self._atp_rank_to_elo(p2_rank) if p2_rank else 1500
        
        elo_probability = self._calculate_elo_probability(p1_elo, p2_elo, "hardcourt")
        
        return {
            'elo_factor': 0.02,  # Low influence when using fallback
            'p1_elo': p1_elo,
            'p2_elo': p2_elo,
            'elo_probability': elo_probability,
            'confidence': 0.3,  # Low confidence in derived Elo
            'enabled': True
        }
    
    def _atp_rank_to_elo(self, atp_rank: Optional[int]) -> float:
        """
        Convert ATP ranking to approximate Elo rating
        
        Rough approximation based on typical Elo distributions:
        - #1: ~2400
        - #10: ~2200
        - #50: ~2000
        - #100: ~1850
        - #200: ~1700
        - #500: ~1500
        """
        if not atp_rank or atp_rank <= 0:
            return 1500  # Default
        
        # Logarithmic decay from top to lower ranks
        if atp_rank == 1:
            return 2400
        elif atp_rank <= 10:
            return 2200 + (200 * (10 - atp_rank) / 9)
        elif atp_rank <= 50:
            return 2000 + (200 * (50 - atp_rank) / 40)
        elif atp_rank <= 100:
            return 1850 + (150 * (100 - atp_rank) / 50)
        elif atp_rank <= 200:
            return 1700 + (150 * (200 - atp_rank) / 100)
        elif atp_rank <= 500:
            return 1500 + (200 * (500 - atp_rank) / 300)
        else:
            return 1500
    
    def integrate_elo_into_prediction(
        self,
        base_probability: float,
        elo_blend_data: Dict
    ) -> float:
        """
        Integrate Elo rating into existing prediction
        
        Args:
            base_probability: Current prediction probability (0-1)
            elo_blend_data: Output from get_elo_blend_factor()
            
        Returns:
            Adjusted probability with Elo blended in
        """
        if not self.enabled or not elo_blend_data.get('enabled'):
            return base_probability
        
        elo_factor = elo_blend_data.get('elo_factor', 0.0)
        elo_probability = elo_blend_data.get('elo_probability')
        
        if elo_probability is None or elo_factor == 0.0:
            return base_probability
        
        # Blend: base * (1 - factor) + elo * factor
        blended = base_probability * (1 - elo_factor) + elo_probability * elo_factor
        
        self.logger.debug(
            f"Elo blend: base={base_probability:.3f}, "
            f"elo={elo_probability:.3f}, "
            f"factor={elo_factor:.3f}, "
            f"result={blended:.3f}"
        )
        
        return blended


# Convenience function for quick access
def create_elo_service(config: Optional[Dict] = None) -> EloRatingService:
    """
    Create Elo service from configuration
    
    Args:
        config: Configuration dict with 'elo_integration' key
        
    Returns:
        Configured EloRatingService instance
    """
    if config and config.get('features', {}).get('elo_integration', False):
        return EloRatingService(enabled=True)
    else:
        return EloRatingService(enabled=False)

