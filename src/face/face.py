from flask import Flask, render_template

app = Flask(__name__)

from torso import load_config, Db
from pprint import pprint

conf = load_config()
#pprint(conf)
db = Db.reader()

@app.route("/")
def hello_world():
    db.update_config(conf)
    return render_template("index.html", groups=conf)
