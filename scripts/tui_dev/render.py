"""SVG -> PNG conversion using headless Chrome.

Rich's ``Console.save_svg`` produces a styled terminal SVG that faithfully
reflects what the real terminal would show.  Claude Code's Read tool can
only display raster images, so we convert each SVG to PNG via a headless
Chrome process.  Chrome is the only external dependency required, and it
ships on macOS by default at the path below.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
]

_VIEWBOX_RE = re.compile(
    r'viewBox="\s*([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"'
)


def find_chrome() -> str:
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    which = shutil.which("google-chrome") or shutil.which("chromium")
    if which:
        return which
    raise RuntimeError(
        "Chrome/Chromium not found — install Google Chrome or set CHROME env var."
    )


def _svg_intrinsic_size(svg_path: Path) -> tuple[int, int]:
    """Parse the ``viewBox`` of a Rich-generated SVG and return (w, h)."""
    text = svg_path.read_text()
    match = _VIEWBOX_RE.search(text)
    if not match:
        return (1200, 900)
    _, _, w, h = match.groups()
    return (int(float(w)) + 4, int(float(h)) + 4)  # tiny padding for 1px strokes


def svg_to_png(svg_path: Path, png_path: Path) -> None:
    """Convert *svg_path* to a PNG at *png_path* via headless Chrome.

    The Chrome window is sized to match the SVG's intrinsic viewBox so
    the screenshot has no wasted whitespace.  A 2x device scale factor
    gives crisp text on Retina-equivalent output.
    """
    chrome = find_chrome()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = _svg_intrinsic_size(svg_path)
    subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            f"--screenshot={png_path}",
            f"--window-size={width},{height}",
            svg_path.resolve().as_uri(),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
