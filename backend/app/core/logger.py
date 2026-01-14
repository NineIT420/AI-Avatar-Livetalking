"""
Logging configuration
"""
import logging
import sys


def setup_logging(level: int = logging.INFO):
    """Setup application logging"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Suppress aioice STUN transaction retry errors
    aioice_logger = logging.getLogger("aioice")
    aioice_logger.setLevel(logging.WARNING)

