import json
import os
import sqlite3
import tempfile
import threading
from pathlib import Path

from flask import Flask, render_template, request

from torso import Db, load_config

app = Flask(__name__)

conf = load_config()
db: Db | None = None

STATE_FILE = "collapsed.json"

# Serialises the read-modify-write in set_collapsed. Two clicks in the same
# tick land on different threads of the dev server and would otherwise race,
# with the second read missing the first's write.
_state_lock = threading.Lock()


def _reader() -> Db | None:
    """Open the reader lazily, retrying until the DB exists.

    face may start before hiney has ever created /run/startpg/spg.db, so we
    can't open it once at import -- we'd be stuck with no data forever. Once
    opened, the connection sees each subsequent hiney write.
    """
    global db
    if db is None:
        try:
            db = Db.reader()
        except (sqlite3.Error, OSError):
            # Not just a missing DB file: /run/startpg may not exist yet, and
            # creating it there needs privileges we don't have. Degrade to the
            # bare service list rather than 500ing.
            return None
    return db


def _state_dir() -> Path:
    """Where collapsed-section state lives.

    systemd exports STATE_DIRECTORY from StateDirectory=startpg in the unit
    (/var/lib/startpg), which survives reboots -- unlike the DB in /run. Fall
    back to the XDG state dir so a bare `face` still persists something.
    """
    from_systemd = os.environ.get("STATE_DIRECTORY")
    if from_systemd:
        return Path(from_systemd.split(":")[0])
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "startpg"


def _load_collapsed() -> dict[str, set[str]]:
    """Collapsed group/host keys. Missing or corrupt state just means none."""
    try:
        raw = json.loads((_state_dir() / STATE_FILE).read_text())
    except (OSError, ValueError):
        return {"groups": set(), "hosts": set()}
    return {
        "groups": set(raw.get("groups", [])),
        "hosts": set(raw.get("hosts", [])),
    }


def _save_collapsed(state: dict[str, set[str]]) -> None:
    directory = _state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({k: sorted(v) for k, v in state.items()})
    # Unique temp file per write: a shared name lets concurrent writers scribble
    # over each other's partial output. Rename is atomic, so readers only ever
    # see a whole file.
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".collapsed-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(payload)
        os.replace(tmp, directory / STATE_FILE)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _known_keys() -> dict[str, set[str]]:
    """The collapse keys the loaded config can actually render."""
    return {
        "groups": set(conf),
        "hosts": {
            f"{group_name}/{host_name}"
            for group_name, group in conf.items()
            for host_name in group.hosts
        },
    }


@app.route("/")
def index():
    reader = _reader()
    if reader is not None:
        reader.update_config(conf)
    collapsed = _load_collapsed()
    # Rendered server-side so collapsed sections never flash open on load.
    return render_template(
        "index.html",
        groups=conf,
        collapsed_groups=collapsed["groups"],
        collapsed_hosts=collapsed["hosts"],
    )


@app.route("/api/collapsed", methods=["POST"])
def set_collapsed():
    payload = request.get_json(silent=True) or {}
    bucket = {"group": "groups", "host": "hosts"}.get(payload.get("kind"))
    key = payload.get("key")
    if bucket is None or not isinstance(key, str):
        return {"error": "want kind of 'group' or 'host' and a string key"}, 400

    try:
        with _state_lock:
            collapsed = _load_collapsed()
            if payload.get("collapsed"):
                collapsed[bucket].add(key)
            else:
                collapsed[bucket].discard(key)
            # Forget keys the config no longer has, so sections that get
            # renamed or deleted in startpg.yaml don't pile up forever.
            known = _known_keys()
            for name, keys in collapsed.items():
                collapsed[name] = keys & known[name]
            _save_collapsed(collapsed)
    except OSError as e:
        return {"error": f"could not persist state: {e}"}, 500
    return "", 204


def main():
    # The port comes from the environment so the systemd unit can ask for 80
    # (granted via AmbientCapabilities=CAP_NET_BIND_SERVICE) while a bare
    # `face` run by hand still works unprivileged on 5000.
    app.run(host="0.0.0.0", port=int(os.environ.get("STARTPG_PORT", "5000")))
