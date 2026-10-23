"""Run with:  python -m daily_cosmos"""

import sys

from .apod_client import ApodError, fetch_apod
from .config import load_config


def main() -> int:
    # Avoid crashes when a title/credit contains non-ASCII characters.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    config = load_config()

    try:
        entry = fetch_apod(config)
    except ApodError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    preview = entry.explanation[:200] + ("..." if len(entry.explanation) > 200 else "")
    print(f"Date:        {entry.date}")
    print(f"Title:       {entry.title}")
    print(f"Media type:  {entry.media_type}")
    print(f"Page:        {entry.page_url}")
    print(f"Image URL:   {entry.image_url or '(none)'}")
    print(f"Credit:      {entry.credit or '(none)'}")
    print(f"Copyright:   {entry.copyright or '(none)'}")
    print(f"Explanation: {preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())