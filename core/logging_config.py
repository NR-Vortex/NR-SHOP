import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(level: str = "INFO"):

    Path("logs").mkdir(exist_ok=True)

    log_level = getattr(
        logging,
        level.upper(),
        logging.INFO
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        "logs/nr_shop.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8"
    )

    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=log_level,
        handlers=[console, file_handler],
        force=True
    )