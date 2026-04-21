"""
Logging configuration for the Personal Learning Database.
"""

import logging
import sys


def setup_logging(level=logging.INFO, log_file=None):
    """
    Configure logging for the application.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path to write logs to
    """
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
