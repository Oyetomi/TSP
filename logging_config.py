#!/usr/bin/env python3
"""
Logging Configuration

Sets up comprehensive logging for the tennis prediction system:
- Terminal output with colors
- File logging that clears on each run
- Separate logs for different components
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to level name (make a copy to avoid affecting other handlers)
        log_record = logging.makeLogRecord(record.__dict__)
        levelname = log_record.levelname
        if levelname in self.COLORS:
            log_record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        return super().format(log_record)

def setup_logging(
    log_file: str = "logs/betting_analysis.log",
    level: int = logging.INFO,
    clear_on_start: bool = True
) -> logging.Logger:
    """
    Setup comprehensive logging system
    
    Args:
        log_file: Path to log file (will be created/cleared)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        clear_on_start: Clear log file on startup
        
    Returns:
        Main logger instance
    """
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)
    
    # Clear log file if requested
    if clear_on_start and log_path.exists():
        log_path.unlink()
    
    # Create main logger
    logger = logging.getLogger('TennisPrediction')
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # ====================
    # TERMINAL HANDLER (with colors)
    # ====================
    terminal_handler = logging.StreamHandler(sys.stdout)
    terminal_handler.setLevel(level)
    
    terminal_format = ColoredFormatter(
        '%(levelname)s | %(message)s'
    )
    terminal_handler.setFormatter(terminal_format)
    logger.addHandler(terminal_handler)
    
    # ====================
    # FILE HANDLER (detailed)
    # ====================
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # File gets everything
    
    file_format = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # ====================
    # STARTUP MESSAGE
    # ====================
    logger.info("=" * 80)
    logger.info(f"🎾 TENNIS PREDICTION SYSTEM - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    logger.info(f"📝 Logging to: {log_file}")
    logger.info(f"📊 Log level: {logging.getLevelName(level)}")
    if clear_on_start:
        logger.info(f"🧹 Log file cleared on startup")
    logger.info("=" * 80)
    
    return logger

def get_component_logger(component_name: str, parent_logger: logging.Logger = None) -> logging.Logger:
    """
    Get a logger for a specific component
    
    Args:
        component_name: Name of the component (e.g., 'Forebet', 'MatchData', 'Odds')
        parent_logger: Parent logger to inherit from
        
    Returns:
        Component-specific logger
    """
    if parent_logger:
        logger_name = f"{parent_logger.name}.{component_name}"
    else:
        logger_name = f"TennisPrediction.{component_name}"
    
    logger = logging.getLogger(logger_name)
    
    # Inherit level from parent or set to INFO
    if parent_logger:
        logger.setLevel(parent_logger.level)
    else:
        logger.setLevel(logging.INFO)
    
    return logger

def log_section_header(logger: logging.Logger, title: str, width: int = 80):
    """
    Log a formatted section header
    
    Args:
        logger: Logger instance
        title: Section title
        width: Width of the header line
    """
    logger.info("")
    logger.info("=" * width)
    logger.info(f" {title}")
    logger.info("=" * width)

def log_match_info(logger: logging.Logger, player1: str, player2: str, tournament: str = None):
    """
    Log formatted match information
    
    Args:
        logger: Logger instance
        player1: First player name
        player2: Second player name
        tournament: Optional tournament name
    """
    logger.info("")
    logger.info(f"🎾 {player1} vs {player2}")
    if tournament:
        logger.info(f"   📍 Tournament: {tournament}")

def log_forebet_status(
    logger: logging.Logger,
    available: bool,
    predicted_winner: str = None,
    probability: str = None,
    agrees: bool = False
):
    """
    Log Forebet prediction status
    
    Args:
        logger: Logger instance
        available: Whether Forebet has this match
        predicted_winner: Forebet's prediction
        probability: Forebet's probability
        agrees: Whether Forebet agrees with our prediction
    """
    if not available:
        logger.info("   🔍 Forebet: Not available")
        return
    
    if agrees:
        emoji = "✅"
        status = "AGREES"
    else:
        emoji = "❌"
        status = "DISAGREES"
    
    logger.info(f"   🔍 Forebet: {emoji} {status}")
    logger.info(f"      Predicted: {predicted_winner} ({probability}%)")

# Example usage and testing
if __name__ == "__main__":
    # Test the logging setup
    logger = setup_logging(clear_on_start=True)
    
    log_section_header(logger, "TESTING LOGGING SYSTEM")
    
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    
    log_match_info(logger, "Rafael Nadal", "Roger Federer", "Wimbledon")
    log_forebet_status(logger, True, "Rafael Nadal", "65", True)
    
    log_match_info(logger, "Novak Djokovic", "Andy Murray", "US Open")
    log_forebet_status(logger, True, "Novak Djokovic", "72", False)
    
    log_match_info(logger, "Carlos Alcaraz", "Jannik Sinner")
    log_forebet_status(logger, False)
    
    # Test component logger
    forebet_logger = get_component_logger("Forebet", logger)
    forebet_logger.info("Component logger test")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ Logging test complete - check logs/betting_analysis.log")
    logger.info("=" * 80)

