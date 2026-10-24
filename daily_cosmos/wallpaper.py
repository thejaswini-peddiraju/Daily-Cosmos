"""Set the Windows desktop wallpaper."""

import ctypes
import sys
import winreg
from pathlib import Path

SPI_SETDESKWALLPAPER = 0x0014
SPI_GETDESKWALLPAPER = 0x0073
SPIF_UPDATEINIFILE = 0x01  # remember the change after logout/restart
SPIF_SENDCHANGE = 0x02     # tell running programs the wallpaper changed
MAX_PATH = 260

# style name -> (WallpaperStyle, TileWallpaper) values Windows stores in the registry
STYLES = {
    "fill": ("10", "0"),     # fills the screen, may crop the edges
    "fit": ("6", "0"),       # whole picture visible, bars if the shape differs
    "stretch": ("2", "0"),   # distorts the picture to fill the screen
    "tile": ("0", "1"),
    "center": ("0", "0"),
    "span": ("22", "0"),     # across multiple monitors
}


class WallpaperError(Exception):
    """The wallpaper could not be changed."""


def get_current_wallpaper() -> str:
    """Return the path of the current wallpaper ('' if unknown)."""
    buffer = ctypes.create_unicode_buffer(MAX_PATH)
    ok = ctypes.windll.user32.SystemParametersInfoW(
        SPI_GETDESKWALLPAPER, MAX_PATH, buffer, 0
    )
    return buffer.value if ok else ""


def _apply_style(style: str) -> None:
    wallpaper_style, tile = STYLES[style]
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, wallpaper_style)
        winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, tile)


def _set_raw(path: str) -> bool:
    return bool(
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
    )


def set_wallpaper(image_path: Path, style: str = "fit") -> str:
    """Set the wallpaper. Returns the PREVIOUS wallpaper's path.

    Raises WallpaperError on failure (after trying to restore the old one).
    """
    if sys.platform != "win32":
        raise WallpaperError("Setting the wallpaper is only supported on Windows.")
    if style not in STYLES:
        raise WallpaperError(f"Unknown wallpaper style '{style}'.")

    path = Path(image_path).resolve()  # Windows needs a full, absolute path
    if not path.is_file():
        raise WallpaperError(f"Image file not found: {path}")

    previous = get_current_wallpaper()

    try:
        _apply_style(style)
    except OSError:
        raise WallpaperError("Could not write the wallpaper style to the registry.") from None

    if not _set_raw(str(path)):
        if previous:
            _set_raw(previous)  # put the old wallpaper back
        raise WallpaperError("Windows refused to change the wallpaper.")

    return previous