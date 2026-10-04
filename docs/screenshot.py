#!/usr/bin/env python3
"""Regenerate docs/screenshot.png and docs/screenshot-dark.png, the README's
pictures of the page in its light and dark themes.

Renders face's real template and CSS for docs/demo.yaml, with the made-up
statuses below (nothing gets checked), screenshots it with headless Chromium,
and shrinks it with ImageMagick. Run it with the project installed, e.g.

    .venv/bin/python docs/screenshot.py

It needs chromium and ImageMagick's convert on the PATH, but no config of
your own.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DOCS = Path(__file__).resolve().parent
DEMO = DOCS / "demo.yaml"
OUTPUT = DOCS / "screenshot.png"
OUTPUT_DARK = DOCS / "screenshot-dark.png"

# How Chromium is told the page should see prefers-color-scheme: dark.
DARK_FLAGS = ("--force-dark-mode", "--blink-settings=preferredColorScheme=0")

WIDTH = 960  # CSS px: wide enough for two columns of cards
SCALE = 2  # render at 2x so it stays sharp on high-DPI screens

COLLAPSED = {"groups": ["Smart home"], "hosts": ["Networking/Access point"]}

# Made-up check results, by URL, as hiney would record them: an HTTP status
# or 0 for a reachable port, else -1 for down.
UP, REACHABLE = (200, "OK"), (0, "reachable")
STATUS = {
    "https://192.0.2.10:5001/": UP,
    "ssh://192.0.2.10:22/": REACHABLE,
    "https://192.0.2.11:8006/": UP,
    "https://192.0.2.31/": UP,
    "ssh://192.0.2.11:22/": REACHABLE,
    "ssh://192.0.2.31:22/": REACHABLE,
    "http://192.0.2.12:8096/": (-1, "timed out"),
    "ssh://192.0.2.12:22/": (-1, "[Errno 113] No route to host"),
    "http://example.com/": UP,
    "http://www.example.com/": UP,
    "http://192.0.2.20:8080/": UP,
    "https://wiki.example.org/": (503, "Service Unavailable"),
    "ssh://192.0.2.21:2222/": REACHABLE,
    "http://192.0.2.1/": UP,
    "https://192.0.2.1/": UP,
    "ssh://192.0.2.1:22/": REACHABLE,
    "http://192.0.2.2/": UP,
    "http://192.0.2.3/": UP,
    "http://192.0.2.40:8123/": UP,
}


def render(html_dir: Path) -> None:
    """Write face's page for the demo, and its static files, to html_dir."""
    state = Path(tempfile.mkdtemp())
    (state / "collapsed.json").write_text(json.dumps(COLLAPSED))
    os.environ["STATE_DIRECTORY"] = str(state)

    # face loads its config as it's imported, so point that at the demo first.
    import torso

    load_config = torso.load_config
    torso.load_config = lambda config_file=DEMO: load_config(config_file)
    import face.face as face

    for group in face.conf.values():
        for host in group.hosts.values():
            for service in host.services:
                if service.check:
                    url = service.url.human_repr()
                    if url not in STATUS:
                        sys.exit(f"screenshot: no made-up status for {url}")
                    service.last_check_status, service.last_check_info = STATUS[url]
    face._reader = lambda: None  # no status DB, so the made-up statuses stand

    html = face.app.test_client().get("/").get_data(as_text=True)
    (html_dir / "index.html").write_text(html)
    shutil.copytree(Path(face.__file__).parent / "static", html_dir / "static")


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        sys.exit(f"screenshot: {args[0]} failed:\n{result.stderr}")
    return result.stdout


def capture(page: str, output: Path, tmp: Path, *flags: str) -> None:
    raw = tmp / "raw.png"
    # Taller than the page needs; the trim below cuts it to fit. The time
    # budget lets the fonts load before the shot.
    run("chromium", "--headless", "--disable-gpu", "--hide-scrollbars",
        "--virtual-time-budget=10000",
        f"--force-device-scale-factor={SCALE}", f"--window-size={WIDTH},2400",
        *flags, f"--screenshot={raw}", page)
    # Crop to the page with a margin of its own background, then cut it to
    # 256 colours, which looks no different for a flat page at well under half
    # the size. No metadata or timestamps, so an unchanged page makes an
    # unchanged file.
    background = run("convert", str(raw), "-format", "%[pixel:p{0,0}]", "info:")
    run("convert", str(raw), "-bordercolor", background, "-border", "1",
        "-trim", "+repage", "-border", str(8 * SCALE),
        "-dither", "None", "-colors", "256",
        "-strip", "-define", "png:exclude-chunk=date,time", f"PNG8:{output}")
    print(f"wrote {output}")


def main():
    for tool in ("chromium", "convert"):
        if not shutil.which(tool):
            sys.exit(f"screenshot: needs {tool} on the PATH")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        render(tmp)
        page = (tmp / "index.html").as_uri()
        capture(page, OUTPUT, tmp)
        capture(page, OUTPUT_DARK, tmp, *DARK_FLAGS)


if __name__ == "__main__":
    main()
