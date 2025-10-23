"""
Services package for tennis prediction system.
"""

from .match_data_provider import MatchDataProvider
from .player_analysis_service import PlayerAnalysisService

# Backwards compatibility aliases
MatchDataProviderService = MatchDataProvider

__all__ = ["MatchDataProvider", "PlayerAnalysisService", "MatchDataProviderService"]
