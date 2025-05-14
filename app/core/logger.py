import logging
from logging.config import dictConfig

def setup_logger():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
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

def get_logger(name: str = __name__):
    return logging.getLogger(name)

# # 사용 예시 (각 모듈에서)
# logger = get_logger(__name__)

# def some_function():
#     logger.info("This is a log message from %s", __name__)
