"""Run with:  python -m daily_cosmos"""

import logging
import sys
from pathlib import Path

from .apod_client import ApodError, fetch_apod
from .config import Config, load_config
from .downloader import DownloadError, download_image
from .history import cleanup_old_images, record_download
from .logging_setup import setup_logging
from .wallpaper import WallpaperError, set_wallpaper

logger = logging.getLogger("daily_cosmos")


def run(config: Config) -> int:
    """Do one update. Returns 0 on success, 1 on failure."""
    logger.info("Starting update")

    try:
        entry = fetch_apod(config)
    except ApodError as exc:
        logger.error("Could not fetch today's APOD: %s Wallpaper unchanged.", exc)
        return 1

    logger.info("APOD %s: %s (%s)", entry.date, entry.title, entry.media_type)
    logger.info("Credit: %s", entry.copyright or entry.credit or "n/a")

    if not entry.is_image:
        logger.warning("Entry is a %s, not a picture. Wallpaper left unchanged.", entry.media_type)
        return 0

    try:
        result = download_image(entry, config)
    except DownloadError as exc:
        logger.error("Image download failed: %s Wallpaper unchanged.", exc)
        return 1

    logger.info(
        "%s: %s (%dx%d)",
        "Already downloaded" if result.was_cached else "Downloaded",
        result.path, result.width, result.height,
    )

    try:
        previous = set_wallpaper(result.path)
    except WallpaperError as exc:
        logger.error("Could not set wallpaper: %s", exc)
        return 1

    logger.info("Wallpaper set")

    # Housekeeping only happens after a fully successful update.
    # A problem here is reported but does not count as a failed run.
    keep = {result.path}
    if previous:
        keep.add(Path(previous))
    try:
        record_download(entry, result.path, config)
        deleted = cleanup_old_images(config, keep)
    except OSError as exc:
        logger.warning("History/cleanup problem (%s).", type(exc).__name__)
    else:
        logger.info(
            "History saved. Cleanup removed %d image(s) older than %d days.",
            len(deleted), config.retention_days,
        )
    return 0


def main() -> int:
    # Avoid crashes when a title/credit contains non-ASCII characters.
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    config = load_config()
    setup_logging(config)

    try:
        return run(config)
    except Exception:
        # Safety net: record any unexpected crash, with details, in the log.
        logger.exception("Unexpected error")
        return 1


if __name__ == "__main__":
    sys.exit(main())