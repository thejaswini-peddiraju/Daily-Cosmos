"""Application settings."""

from dataclasses import dataclass
from pathlib import Path

# The folder that contains the daily_cosmos package (the project root).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

APOD_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"


@dataclass(frozen=True)
class Config:
    """All settings in one place. 'frozen' means they can't change by accident."""

    apod_url: str = APOD_URL
    request_timeout: float = 15.0  # seconds to wait for NASA before giving up
    user_agent: str = "DailyCosmos/1.0 (personal wallpaper script)"


def load_config() -> Config:
    return Config()