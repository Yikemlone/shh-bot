import logging
import colorlog
from pathlib import Path
from logging.config import dictConfig


path = Path('./logs/infos.log')
path.touch(exist_ok=True)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": { 
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s%(asctime)s [%(levelname)s] - %(module)s - %(funcName)s - Line %(lineno)d: %(message)s%(reset)s",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "colored",
        },
        "console2": {
            "level": "WARN", 
            "class": "logging.StreamHandler",
            "formatter": "colored",
        },
        "file": {
            "level": "DEBUG",  
            "class": "logging.FileHandler",
            "filename": "logs/infos.log",
            "mode": "w",
            "formatter": "colored",
        },
    },
    "loggers": {
        "shh-bot": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False}, 
        "discord": {
            "handlers": ["console2", "file"],
            "level": "INFO", 
            "propagate": False,
        },
        "discord.http": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

SHH_BOT = "shh-bot"

dictConfig(LOGGING_CONFIG)
