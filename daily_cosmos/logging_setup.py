"""Send log messages to the screen and to logs/daily_cosmos.log."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import Config

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(config: Config) -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # already set up
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Log file (rotates so it never grows forever).
    try:
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            config.logs_dir / "daily_cosmos.log",
            maxBytes=256 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as exc:
        # Not being able to write a log must never stop the wallpaper update.
        if sys.stderr is not None:
            print(f"Warning: cannot write log file ({type(exc).__name__}).", file=sys.stderr)

    # Screen output (skipped when there is no console, e.g. some scheduled runs).
    if sys.stdout is not None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)