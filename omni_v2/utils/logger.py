"""Logger V2 - Data Inside Project Root"""
import sys

from omni_v2.core.paths import LOGS_DIR

def setup_logger(debug=False, log_dir=None):
    try:
        from loguru import logger as loguru_logger
        loguru_logger.remove()
        level = "DEBUG" if debug else "INFO"
        loguru_logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level=level, colorize=True)
        if log_dir is None:
            log_dir = LOGS_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        loguru_logger.add(log_dir / "omni_v2_{time}.log", rotation="100 MB", retention="7 days", level="DEBUG")
        loguru_logger.info(f"Logger V2 initialized (level={level}) at {log_dir}")
    except Exception:
        pass
