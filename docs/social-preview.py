#!/usr/bin/env python3
"""Regenerate docs/social-preview.png, the repo's 1280x640 social preview.

GitHub shows it wherever the repo's link is shared. It has no API for it, so
upload it by hand, under Social preview in the repo's Settings > General.

It's the favicon's monitor, drawn by docs/favicon.py, as an app icon on a
teal tile beside the name and a tagline, in the page's own fonts and colours:
laid out in HTML and screenshotted with headless Chromium. Run it with e.g.

    uv run --no-project --with pillow python docs/social-preview.py

Pillow is for docs/favicon.py's drawing. It also needs chromium on the PATH.
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from string import Template

DOCS = Path(__file__).resolve().parent
FONTS = DOCS.parent / "src" / "face" / "static" / "fonts"
OUTPUT = DOCS / "social-preview.png"

TAGLINE = "your homelab's homepage"

PAGE = Template("""<!doctype html>
<style>
@font-face { font-family: "IBM Plex Sans"; font-weight: 400; src: url("$fonts/IBMPlexSans-Regular.woff2"); }
@font-face { font-family: "IBM Plex Mono"; font-weight: 600; src: url("$fonts/IBMPlexMono-SemiBold.woff2"); }

html, body { margin: 0; width: 1280px; height: 640px; overflow: hidden; }
body { background: #f4f5f7; color: #1b1f24; }
.wrap { display: flex; align-items: center; justify-content: center; height: 640px; gap: 84px; }

/* The monitor as an app icon: its 32x32 pixels at 8x, unsmoothed. */
.tile {
  display: grid; place-items: center; flex: none;
  width: 300px; height: 300px; border-radius: 56px; background: #008080;
  box-shadow: 0 1px 2px rgba(0, 0, 0, .08), 0 12px 32px rgba(0, 60, 60, .18);
}
.tile img { width: 256px; height: 256px; image-rendering: pixelated; }

/* The page header's wordmark, block cursor and all. */
.name { font: 600 112px/1 "IBM Plex Mono"; letter-spacing: -0.01em; }
.name::after {
  content: ""; display: inline-block; width: 0.55em; height: 0.92em;
  margin-left: 0.08em; vertical-align: -0.12em; background: #0e8a6a;
}
.tagline { margin-top: 26px; font: 400 40px/1.3 "IBM Plex Sans"; color: #69717c; }
</style>
<div class="wrap">
  <div class="tile"><img src="monitor.png" alt=""></div>
  <div><div class="name">startpg</div><div class="tagline">$tagline</div></div>
</div>
""")


def draw_monitor(path: Path) -> None:
    """Save the favicon's 32x32 monitor, drawn by docs/favicon.py."""
    spec = importlib.util.spec_from_file_location("favicon", DOCS / "favicon.py")
    favicon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(favicon)
    favicon.large().image().save(path)


def main():
    if not shutil.which("chromium"):
        sys.exit("social-preview: needs chromium on the PATH")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        draw_monitor(tmp / "monitor.png")
        page = tmp / "index.html"
        page.write_text(PAGE.substitute(fonts=FONTS.as_uri(), tagline=TAGLINE))
        # The time budget lets the fonts load before the shot.
        result = subprocess.run(
            ["chromium", "--headless", "--disable-gpu", "--hide-scrollbars",
             "--virtual-time-budget=10000", "--force-device-scale-factor=1",
             "--window-size=1280,640", f"--screenshot={OUTPUT}", page.as_uri()],
            capture_output=True, text=True,
        )
        if result.returncode:
            sys.exit(f"social-preview: chromium failed:\n{result.stderr}")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
