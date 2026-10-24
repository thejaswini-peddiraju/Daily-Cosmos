"""Client for NASA's Astronomy Picture of the Day (APOD) on science.nasa.gov."""

import html
import re
from dataclasses import dataclass
from datetime import datetime

import requests

from .config import Config


# --- Our own error types -----------------------------------------------------

class ApodError(Exception):
    """Base class for every error this module raises on purpose."""


class ApodNetworkError(ApodError):
    """Could not reach NASA (offline, DNS failure, timeout, ...)."""


class ApodApiError(ApodError):
    """NASA answered, but with an error status."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApodDataError(ApodError):
    """NASA answered 200 OK, but the data isn't what we expected."""


# --- Data model --------------------------------------------------------------

@dataclass(frozen=True)
class ApodEntry:
    """One day's APOD, cleaned up and ready to use."""

    date: str
    title: str
    explanation: str
    media_type: str          # "image", "video" or "iframe"
    page_url: str            # the article page on science.nasa.gov
    image_url: str | None    # the picture itself (a still frame for videos)
    credit: str | None
    copyright: str | None

    @property
    def is_image(self) -> bool:
        return self.media_type == "image"


_TAG_RE = re.compile(r"<[^>]+>")


def html_to_text(value: object) -> str | None:
    """NASA sends some fields as HTML. Turn them into plain text."""
    if value is None:
        return None
    text = _TAG_RE.sub(" ", str(value))
    text = html.unescape(text)
    text = " ".join(text.split())
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)  # tidy "word ," -> "word,"
    return text or None


def parse_apod_response(data: object) -> ApodEntry:
    """Turn NASA's JSON into an ApodEntry, or raise ApodDataError."""
    # "Latest" requests return a list of entries; single-date requests an object.
    if isinstance(data, list):
        if not data:
            raise ApodDataError("NASA returned an empty list.")
        data = data[0]
    if not isinstance(data, dict):
        raise ApodDataError("Unexpected response: expected a JSON object.")

    missing = [name for name in ("date", "title", "media_type") if not data.get(name)]
    if missing:
        raise ApodDataError(f"Response is missing field(s): {', '.join(missing)}")

    media_type = str(data["media_type"]).lower()
    image_url = html_to_text(data.get("hdurl"))
    if media_type == "image" and not image_url:
        raise ApodDataError("Image entry has no image URL (hdurl).")

    return ApodEntry(
        date=str(data["date"]),
        title=html_to_text(data["title"]) or "Untitled",
        explanation=re.sub(r"^Explanation:\s*", "", html_to_text(data.get("explanation")) or ""),
        media_type=media_type,
        page_url=html_to_text(data.get("permalink") or data.get("url")) or "",
        image_url=image_url,
        credit=html_to_text(data.get("credit")),
        copyright=html_to_text(data.get("copyright")),
    )


def _date_code(apod_date: str) -> str:
    """'2026-10-13' -> '261013' (the format the new API uses in its URL)."""
    try:
        return datetime.strptime(apod_date, "%Y-%m-%d").strftime("%y%m%d")
    except ValueError:
        raise ApodError("Date must look like YYYY-MM-DD.") from None


def fetch_apod(config: Config, apod_date: str | None = None) -> ApodEntry:
    """Fetch APOD metadata. Defaults to the latest; pass 'YYYY-MM-DD' for a day.

    Raises a subclass of ApodError on any failure.
    """
    url = config.apod_url
    params = None
    if apod_date:
        url = f"{url}/{_date_code(apod_date)}"
    else:
        params = {"per_page": 1}  # just the newest entry

    headers = {"User-Agent": config.user_agent, "Accept": "application/json"}

    try:
        response = requests.get(
            url, params=params, headers=headers, timeout=config.request_timeout
        )
    except requests.Timeout:
        raise ApodNetworkError(
            f"NASA did not respond within {config.request_timeout:g} seconds."
        ) from None
    except requests.RequestException as exc:
        raise ApodNetworkError(
            f"Could not reach NASA ({type(exc).__name__}). Check your connection."
        ) from None

    if response.status_code == 404:
        raise ApodApiError("NASA has no APOD for that date.", 404)
    if response.status_code == 429:
        raise ApodApiError("NASA rate limit reached. Try again later.", 429)
    if not response.ok:
        raise ApodApiError(
            f"NASA API returned HTTP {response.status_code}.", response.status_code
        )

    try:
        data = response.json()
    except ValueError:
        raise ApodDataError("NASA's response was not valid JSON.") from None

    return parse_apod_response(data)