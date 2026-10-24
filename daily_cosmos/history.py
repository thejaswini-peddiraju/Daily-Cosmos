"""Keep a small history of downloaded pictures and delete old image files."""

import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from .apod_client import ApodEntry
from .config import Config

# Only files named like "2026-10-24_some-title.png" are ever considered for deletion.
_IMAGE_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_.+\.(?:jpg|png)$")


def _load_records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        os.replace(path, path.with_suffix(".json.bad"))  # keep the broken file, start fresh
        return []
    return data if isinstance(data, list) else []


def record_download(entry: ApodEntry, image_path: Path, config: Config) -> None:
    """Add (or update) today's record in data/history.json."""
    config.data_dir.mkdir(parents=True, exist_ok=True)
    records = [r for r in _load_records(config.history_file) if r.get("date") != entry.date]
    records.append(
        {
            "date": entry.date,
            "title": entry.title,
            "credit": entry.credit,
            "copyright": entry.copyright,
            "page_url": entry.page_url,
            "file": image_path.name,
            "recorded_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    records.sort(key=lambda r: r.get("date", ""))

    # Write to a temp file first, then swap it in, so a crash can't corrupt history.
    temp = config.history_file.with_suffix(".json.tmp")
    temp.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, config.history_file)


def cleanup_old_images(
    config: Config, keep: set[Path], today: date | None = None
) -> list[Path]:
    """Delete images older than config.retention_days. Returns what was deleted.

    Never deletes anything in `keep`, and never deletes the newest image.
    """
    if not config.images_dir.is_dir():
        return []

    today = today or date.today()
    cutoff = today - timedelta(days=config.retention_days)

    images: list[tuple[date, Path]] = []
    for path in config.images_dir.iterdir():
        match = _IMAGE_NAME.match(path.name)
        if not (match and path.is_file()):
            continue
        try:
            image_date = date.fromisoformat(match.group(1))
        except ValueError:
            continue  # name looks like a date but isn't one: leave it alone
        images.append((image_date, path))

    if not images:
        return []

    newest = max(images)[1]
    protected = {p.resolve() for p in keep} | {newest.resolve()}

    deleted: list[Path] = []
    for image_date, path in images:
        if image_date >= cutoff or path.resolve() in protected:
            continue
        try:
            path.unlink()
            deleted.append(path)
        except OSError:
            continue  # in use or locked: try again next run
    return deleted