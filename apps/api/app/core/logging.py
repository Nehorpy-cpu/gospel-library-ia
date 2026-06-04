import logging
import sys

import structlog

from app.services.privacy import sanitize_event


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            sanitize_event,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def logger(name: str):
    return structlog.get_logger(name)
