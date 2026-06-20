import sqlite3

from flask import Flask, render_template

from torso import Db, load_config

app = Flask(__name__)

conf = load_config()
db: Db | None = None


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
        except sqlite3.OperationalError:
            return None
    return db


@app.route("/")
def index():
    reader = _reader()
    if reader is not None:
        reader.update_config(conf)
    return render_template("index.html", groups=conf)


def main():
    app.run(host="0.0.0.0")
