import logging
from logging.config import dictConfig

def setup_logger():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "INFO",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
    }
    dictConfig(logging_config)

setup_logger()
logger = logging.getLogger()  # root logger 사용

# Example usage:
# logger.info("Logger is configured for FastAPI.")