import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    os.makedirs("logs", exist_ok=True)

    log_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)

    app_file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    app_file_handler.setLevel(logging.INFO)
    app_file_handler.setFormatter(log_format)

    error_file_handler = RotatingFileHandler(
        "logs/errors.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(app_file_handler)
        root_logger.addHandler(error_file_handler)