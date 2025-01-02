from loguru import logger
import sys
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'app.log')

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logger.remove()


logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "<level>{message}</level>",
    level="DEBUG",
    colorize=True,
    enqueue=True
)

logger.add(
    LOG_FILE,
    rotation="100 MB",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

logger.info("Logger initialized and configured.")
