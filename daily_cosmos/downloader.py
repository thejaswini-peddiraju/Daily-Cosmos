"""Download the APOD image and check that it is a real, usable picture."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image

from .apod_client import ApodEntry
from .config import Config

MAX_DOWNLOAD_BYTES = 60 * 1024 * 1024  # refuse anything bigger than 60 MB
MIN_WIDTH = 800
MIN_HEIGHT = 600
EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png"}  # formats we accept as wallpapers
CHUNK_SIZE = 64 * 1024


class DownloadError(Exception):
    """The image could not be downloaded or failed validation."""


@dataclass(frozen=True)
class DownloadedImage:
    path: Path
    width: int
    height: int
    was_cached: bool  # True if we already had today's valid image


def _slug(title: str) -> str:
    """'Andromeda in Southern Spring' -> 'andromeda-in-southern-spring'."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50] or "image"


def _inspect_image(path: Path) -> tuple[str, int, int]:
    """Fully decode the file. Returns (format, width, height) or raises."""
    try:
        with Image.open(path) as img:
            img.load()  # reads every pixel, so truncated/corrupt files fail here
            fmt, (width, height) = img.format, img.size
    except Exception:
        raise DownloadError("The downloaded file is not a valid image.") from None

    if fmt not in EXTENSIONS:
        raise DownloadError(f"Unsupported image format: {fmt}.")
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        raise DownloadError(f"Image is too small ({width}x{height}).")
    return fmt, width, height


def _find_existing(images_dir: Path, date: str) -> Path | None:
    for path in sorted(images_dir.glob(f"{date}_*")):
        if path.suffix in EXTENSIONS.values():
            return path
    return None


def download_image(entry: ApodEntry, config: Config) -> DownloadedImage:
    """Download the entry's image into data/images. Raises DownloadError on failure."""
    if not entry.is_image or not entry.image_url:
        raise DownloadError(f"Entry is a {entry.media_type}, not an image.")

    images_dir = config.images_dir
    images_dir.mkdir(parents=True, exist_ok=True)

    # Already have today's picture? Reuse it (handy if the script runs twice).
    existing = _find_existing(images_dir, entry.date)
    if existing:
        try:
            _, width, height = _inspect_image(existing)
            return DownloadedImage(existing, width, height, was_cached=True)
        except DownloadError:
            existing.unlink(missing_ok=True)  # broken leftover: download again

    # Download to a temporary .part file first, so a failed download can
    # never leave a half-written file that looks like a real image.
    temp_path = images_dir / f"{entry.date}.part"
    try:
        try:
            with requests.get(
                entry.image_url,
                stream=True,
                headers={"User-Agent": config.user_agent},
                timeout=config.request_timeout,
            ) as response:
                if not response.ok:
                    raise DownloadError(f"Image server returned HTTP {response.status_code}.")
                content_type = response.headers.get("Content-Type", "").lower()
                if not content_type.startswith("image/"):
                    raise DownloadError(
                        f"Expected an image but received '{content_type or 'unknown'}'."
                    )
                total = 0
                with open(temp_path, "wb") as file:
                    for chunk in response.iter_content(CHUNK_SIZE):
                        total += len(chunk)
                        if total > MAX_DOWNLOAD_BYTES:
                            raise DownloadError("Image is too large to download.")
                        file.write(chunk)
        except requests.Timeout:
            raise DownloadError("Timed out while downloading the image.") from None
        except requests.RequestException as exc:
            raise DownloadError(
                f"Network error while downloading ({type(exc).__name__})."
            ) from None

        fmt, width, height = _inspect_image(temp_path)
        final_path = images_dir / f"{entry.date}_{_slug(entry.title)}{EXTENSIONS[fmt]}"
        os.replace(temp_path, final_path)  # only now does it get its real name
        return DownloadedImage(final_path, width, height, was_cached=False)
    finally:
        temp_path.unlink(missing_ok=True)  # clean up if anything went wrong