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
    data_dir: Path = PROJECT_ROOT / "data"
    logs_dir: Path = PROJECT_ROOT / "logs"
    retention_days: int = 7  # delete downloaded images older than this

    @property
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def history_file(self) -> Path:
        return self.data_dir / "history.json"


def load_config() -> Config:
    return Config()