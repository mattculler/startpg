from flask import Flask, render_template, url_for, jsonify
import requests


from machine import Machine
from services import *

app = Flask(__name__)


# TODO: Add non-HTTP stuff and non-user-facing (e.g. nginx) stuff here
MACHINES = {
  "Internal Services": [
    Machine("modem", "192.168.100.1"),
    Machine("router", "192.168.1.1"),
    Machine("switch", "192.168.1.3", [
      HttpService(auth=("admin", "changeme"))
    ]),
    Machine("pfSense", "192.168.1.68"),
    Machine("ownCloud", "192.168.1.71", [
      HttpService(url="/owncloud")
    ]),
    Machine("Proxmox", "192.168.1.73", [
      HttpsService(port="8006")
    ]),
    Machine("Wiki", "192.168.1.76", [
      HttpService(url="/mediawiki/index.php/Special:UserLogin")
    ]),
    Machine("GOGS", "192.168.1.79", [
      HttpService(port="3000")
    ])
  ],
  "External Services": [
    Machine("site", "site.example.net"),
    Machine("Wiki", "wiki.example.org"),
    Machine("Owncloud", "cloud.example.com"),
    Machine("Blog", "www.blog.example.com")
  ]
}


@app.route("/")
def hello():

  to_show = {}
  for group in MACHINES:
    for machine in MACHINES[group]:
      endpoint_statuses = []
      for endpoint in machine.get_endpoints():
        # Make a request and see if it's live
        url = "{0}://{1}:{2}{3}".format(endpoint.get_protocol(), machine.get_ip(), endpoint.get_port(), endpoint.get_url())
        print("about to request to " + url)
        try:
          # These requests.get() calls use verify to ignore certificate issues
          if endpoint.requires_auth():
            status = requests.get(url, verify=False, timeout=2, auth=endpoint.get_auth()).status_code
          else:
            status = requests.get(url, verify=False, timeout=2).status_code
        except BaseException as e:
          status = e.message
        endpoint_status = {
          "full_url": url,
          "display_url": machine.get_ip(),
          "status": status
        }
        endpoint_statuses.append(endpoint_status)

      # Append
      if not group in to_show:
        to_show[group] = []
      to_show[group].append({
        "name": machine.get_name(),
        "endpoints": endpoint_statuses
      })
  
  # Render
  return render_template("index.html", machinegroups=to_show)


if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0")

