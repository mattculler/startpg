from flask import Flask, render_template

app = Flask(__name__)

from torso import load_config
from pprint import pprint

@app.route("/")
def hello_world():
    conf = load_config()
    pprint(conf)
    return render_template("index.html", groups=conf)
