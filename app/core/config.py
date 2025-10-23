"""
Configuration settings for the tennis prediction system.
"""

from typing import List
from pydantic_settings import BaseSettings

# Import API secrets (keep endpoints private)
try:
    from api_secrets import MATCH_DATA_CONFIG, RATE_LIMITS
    _match_data_url = MATCH_DATA_CONFIG.get('base_url', 'https://www.matchdata-api.example.com/api/v1')
    _match_data_rate = RATE_LIMITS.get('match_data', {}).get('requests_per_minute', 60)
    _match_data_timeout = MATCH_DATA_CONFIG.get('timeout', 30)
except ImportError:
    print("⚠️  WARNING: api_secrets.py not found! Using default configuration.")
    _match_data_url = 'https://www.matchdata-api.example.com/api/v1'
    _match_data_rate = 60
    _match_data_timeout = 30


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    api_title: str = "Tennis Set Prediction API"
    api_version: str = "1.0.0"
    api_description: str = "API for predicting tennis match outcomes using MatchDataProvider data"
    
    # Server Configuration
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True
    
    # CORS Configuration
    allowed_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE"]
    allowed_headers: List[str] = ["*"]
    
    # MatchDataProvider API Configuration (loaded from api_secrets.py)
    match_data_base_url: str = _match_data_url
    match_data_rate_limit: int = _match_data_rate  # requests per minute
    match_data_timeout: int = _match_data_timeout  # seconds
    
    # Cache Configuration
    cache_ttl: int = 300  # 5 minutes in seconds
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Data Storage
    data_directory: str = "data"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
