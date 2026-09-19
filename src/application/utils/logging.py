"""
Structured logging configuration.
"""

import logging
import sys


def setup_logging(level: str = "INFO", log_format: str | None = None) -> logging.Logger:
    """Configure root application logger."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    if log_format is None:
        log_format = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger("wireless_analyzer")
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicate log entries
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under wireless_analyzer namespace."""
    return logging.getLogger(f"wireless_analyzer.{name}")

