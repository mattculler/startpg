import sqlite3

from flask import Flask, render_template

from torso import Db, load_config

app = Flask(__name__)

conf = load_config()
try:
    db = Db.reader()
except sqlite3.OperationalError:
    # No DB yet (hiney hasn't run). Serve the list without statuses.
    db = None


@app.route("/")
def index():
    if db is not None:
        db.update_config(conf)
    return render_template("index.html", groups=conf)


def main():
    app.run(host="0.0.0.0")
