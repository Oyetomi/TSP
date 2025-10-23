"""
API Secrets and Endpoints Configuration - EXAMPLE TEMPLATE
===========================================================

This is a template file showing the structure of api_secrets.py
Copy this file to api_secrets.py and fill in your actual API credentials.

⚠️  NEVER commit api_secrets.py to version control!
"""

# =============================================================================
# DATA PROVIDER IDENTIFICATION (Abstracted)
# =============================================================================

PROVIDER_NAMES = {
    'primary_data': 'YOUR_PRIMARY_SOURCE',    # e.g., tennis data aggregator
    'odds_provider': 'YOUR_ODDS_SOURCE',      # e.g., betting platform
    'stats_source': 'YOUR_STATS_SOURCE',      # e.g., player statistics API
}

# =============================================================================
# PRIMARY MATCH DATA PROVIDER CONFIGURATION
# =============================================================================

PRIMARY_DATA_CONFIG = {
    'base_url': 'https://api.example.com/v1',  # Your primary data API endpoint
    
    'headers': {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'baggage': 'sentry-environment=production,sentry-release=YOUR_RELEASE_ID,sentry-public_key=YOUR_PUBLIC_KEY,sentry-trace_id=YOUR_TRACE_ID',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Chromium";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"YOUR_OS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'sentry-trace': 'YOUR_SENTRY_TRACE_ID',
        'user-agent': 'Mozilla/5.0 (Platform; Details) Browser/Version',
        'x-requested-with': 'YOUR_REQUEST_ID'
    },
    
    'cookies': {
        'perf_dv6Tr4n': '1'  # Example cookie
    },
    
    'impersonate': 'chrome120',
    'timeout': 30,
    'max_retries': 3
}


# =============================================================================
# ODDS PROVIDER CONFIGURATION
# =============================================================================

ODDS_PROVIDER_CONFIG = {
    'base_url': 'https://api.bettingprovider.com/v1',  # Your odds provider API endpoint
    
    # User authentication - REPLACE WITH YOUR OWN
    'user_id': 'YOUR_USER_ID_HERE',
    'access_token': None,
    
    'headers': {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'clientid': 'wap',
        'content-type': 'application/json',
        'operid': '2',
        'origin': 'https://www.odds-api.example.com',
        'platform': 'wap',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.odds-api.example.com/ng/m/sport/tennis/today?source=sport_menu&sort=0',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Chromium";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"YOUR_OS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'traceparent': 'YOUR_TRACE_PARENT_ID',
        'user-agent': 'Mozilla/5.0 (Platform; Details) Browser/Version'
    },
    
    'cookies': {},
    
    'endpoints': {
        'markets': '/wapConfigurableEventsByOrder',
        'match_details': '/wapMatchDetail',
        'odds': '/wapOdds'
    },
    
    'page_size': 20,
    'max_retries': 3,
    'timeout': 30
}


# =============================================================================
# UTR (UNIVERSAL TENNIS RATING) API
# =============================================================================

UTR_CONFIG = {
    'enabled': True,
    'fallback_to_ranking': True
}


# =============================================================================
# INJURY DATA SOURCES
# =============================================================================

INJURY_SOURCES = {
    'flashscore_url': 'https://www.flashscore.com/tennis/injuries/',
    'backup_sources': [
        'https://www.atptour.com/en/players/player-activity',
        'https://www.wtatennis.com/players'
    ]
}


# =============================================================================
# API RATE LIMITING
# =============================================================================

RATE_LIMITS = {
    'match_data': {
        'requests_per_minute': 60,
        'concurrent_requests': 10,
        'retry_delay': 2
    },
    'odds_provider': {
        'requests_per_minute': 30,
        'concurrent_requests': 5,
        'retry_delay': 3
    }
}


# =============================================================================
# BACKWARDS COMPATIBILITY ALIASES
# =============================================================================

# These aliases maintain backwards compatibility with existing code
MATCH_DATA_CONFIG = PRIMARY_DATA_CONFIG  
ODDS_PROVIDER_CONFIG = ODDS_PROVIDER_CONFIG

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_primary_data_headers():
    """Get primary data provider API headers"""
    return PRIMARY_DATA_CONFIG['headers'].copy()

def get_primary_data_base_url():
    """Get primary data provider base URL"""
    return PRIMARY_DATA_CONFIG['base_url']

def get_odds_provider_headers():
    """Get odds provider API headers"""
    return ODDS_PROVIDER_CONFIG['headers'].copy()

def get_odds_provider_base_url():
    """Get odds provider base URL"""
    return ODDS_PROVIDER_CONFIG['base_url']

def get_odds_provider_user_id():
    """Get odds provider user ID"""
    return ODDS_PROVIDER_CONFIG['user_id']

# Legacy aliases
get_match_data_headers = get_primary_data_headers
get_match_data_base_url = get_primary_data_base_url
get_odds_provider_headers = get_odds_provider_headers
get_odds_provider_base_url = get_odds_provider_base_url
get_odds_provider_user_id = get_odds_provider_user_id

