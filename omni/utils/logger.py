"""OMNI Logger - Centralized logging configuration"""
import sys
from pathlib import Path
from loguru import logger

def setup_logger(debug: bool = False, log_dir: Path = None) -> None:
    """Setup OMNI logger."""
    logger.remove()
    level = "DEBUG" if debug else "INFO"
    
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level=level, colorize=True)
    
    if log_dir is None:
        log_dir = Path.home() / ".omni" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(log_dir / "omni_{time}.log", rotation="100 MB", retention="7 days", level="DEBUG", enqueue=True)
    logger.info(f"Logger initialized (level={level})")
