from flask import Flask, render_template

from torso import load_config

app = Flask(__name__)

conf = load_config()


@app.route("/")
def index():
    return render_template("index.html", groups=conf)


def main():
    app.run(host="0.0.0.0", debug=True)
