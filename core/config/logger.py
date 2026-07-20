import logging.config
import sys
from pathlib import Path

def setup_logging(
    *,
    log_level: str = "INFO",
    log_directory: str = "logs",
) -> None:
    directory = Path(log_directory)

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,

            "formatters": {
                "console": {
                    "format": (
                        "%(asctime)s | "
                        "%(levelname)-8s | "
                        "%(name)s | "
                        "%(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },

                "file": {
                    "format": (
                        "%(asctime)s | "
                        "%(levelname)-8s | "
                        "%(name)s | "
                        "%(funcName)s:%(lineno)d | "
                        "%(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },

            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level.upper(),
                    "formatter": "console",
                    "stream": sys.stdout,
                },

                "app_file": {
                    "class": (
                        "logging.handlers."
                        "TimedRotatingFileHandler"
                    ),
                    "level": "DEBUG",
                    "formatter": "file",
                    "filename": str(directory / "app.log"),
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 14,
                    "encoding": "utf-8",
                    "utc": True,
                },

                "error_file": {
                    "class": (
                        "logging.handlers."
                        "TimedRotatingFileHandler"
                    ),
                    "level": "ERROR",
                    "formatter": "file",
                    "filename": str(directory / "errors.log"),
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 30,
                    "encoding": "utf-8",
                    "utc": True,
                },
            },

            "root": {
                "level": "DEBUG",
                "handlers": [
                    "console",
                    "app_file",
                    "error_file",
                ],
            },

            "loggers": {
                "aiogram": {
                    "level": "INFO",
                    "propagate": True,
                },

                "sqlalchemy.engine": {
                    "level": "WARNING",
                    "propagate": True,
                },

                "aiohttp": {
                    "level": "WARNING",
                    "propagate": True,
                },

                "asyncio": {
                    "level": "WARNING",
                    "propagate": True,
                },
            },
        }
    )