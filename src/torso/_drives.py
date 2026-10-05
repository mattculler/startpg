"""Read drive health from a drivecanary hub's API."""

import json
import urllib.request
from urllib.parse import urljoin

from torso import DriveHealth

TIMEOUT = 10


def fetch_drive_health(hub: str) -> list[DriveHealth]:
    """The drive health of every host the drivecanary hub at `hub` watches.

    Raises OSError if the hub can't be reached, and ValueError if its answer
    isn't what its API promises.
    """
    base = hub.rstrip("/") + "/"
    with urllib.request.urlopen(urljoin(base, "api/v1/hosts"), timeout=TIMEOUT) as resp:
        data = json.load(resp)
    try:
        return [
            DriveHealth(
                host=h["host"],
                status=h["status"],
                problems=list(h["problems"]),
                url=urljoin(base, h["url"]),
            )
            for h in data["hosts"]
        ]
    except (KeyError, TypeError) as e:
        raise ValueError(f"unexpected answer from {base}api/v1/hosts: {e!r}") from e
