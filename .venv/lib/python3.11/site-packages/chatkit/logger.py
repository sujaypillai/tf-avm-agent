import logging
import os

logger = logging.getLogger("chatkit")

log_level = os.getenv("LOG_LEVEL")
if log_level:
    logger.setLevel(log_level.upper())
    handler = logging.StreamHandler()
    handler.setLevel(log_level.upper())
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
