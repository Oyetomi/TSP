"""
Match Data Service - Backwards Compatibility Wrapper
====================================================

This module provides backwards compatibility by importing from
the abstracted match_data_provider module.

All actual implementation is in match_data_provider.py
Source details are configured in api_secrets.py
"""

# Import from abstracted module
from .match_data_provider import (
    MatchDataProvider,
    MatchDataProviderError,
)

# Create backwards compatible aliases
MatchDataProviderServiceError = MatchDataProviderError
MatchDataProviderService = MatchDataProvider
