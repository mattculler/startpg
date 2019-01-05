#!/usr/bin/python3
from flask import Flask, render_template, url_for, jsonify
import requests
from collections import OrderedDict


from machine import Machine
from services import *

app = Flask(__name__)


MACHINES = OrderedDict()
MACHINES["Internal Services"] = [
  Machine("modem", "192.168.100.1", check_up=False),
  Machine("pfsense", "192.168.1.1"),
  Machine("SMC switch", "192.168.1.3", [
    HttpService(auth=("admin", "changeme"))
  ]),
  Machine("Proxmox", "192.168.1.73", [
    HttpsService(port="8006")
  ]),
  Machine("Gitea SCM", "192.168.1.83", [
    HttpService(port="3000")
  ]),
  Machine("Deluge", "192.168.1.84"),
  #Machine("Zoneminder", "192.168.1.80"), # doesn't work great as a VM
  # VM websites
  Machine("site VM", "192.168.1.82", [
    HttpService(port="5000")
  ]),
  Machine("Fund VM", "192.168.1.85", [
    HttpService(port="8000")
  ]),
  # NOTE: Cannot include startpg itself, as this will always cause an infinite loop and time out!  Haha
]
MACHINES["OOB Management Interfaces"] = [
  Machine("vault101", "192.168.1.20"),
  Machine("matryoshka", "192.168.1.19")
]
MACHINES["External Services"] = [
  Machine("site", "site.example.net"),
  Machine("Fund", "fund.example.org"),
  Machine("Blog", "www.blog.example.com")
]


# TODO: Add stuff that's ssh-only and add ssh support
# (prisoner) - 192.168.1.69 (windows - no ssh)
# matryoshka - 192.168.1.70
# vault101 - 192.168.1.127
# svalbard - 192.168.1.128
# steambox - 192.168.1.72
# wmrc (raspberry pi radio) - 192.168.1.68

# TODO: Add option to generate and download ssh_config from this???


@app.route("/")
def hello():

  to_show = {}
  for group in MACHINES:
    for machine in MACHINES[group]:
      endpoint_statuses = []
      for endpoint in machine.endpoint_list:
        # Make a request and see if it's live
        url = "{0}://{1}:{2}{3}".format(endpoint.get_protocol(), machine.ip, endpoint.get_port(), endpoint.get_url())
        print("about to request to " + url)
        if not machine.check_up:
          status = "(not checked)"
        else:
          try:
            # These requests.get() calls use verify to ignore certificate issues
            if endpoint.requires_auth():
              status = requests.get(url, verify=False, timeout=5, auth=endpoint.get_auth()).status_code
            else:
              status = requests.get(url, verify=False, timeout=5).status_code
          except requests.exceptions.RequestException as e:
            status = str(e)
        endpoint_status = {
          "full_url": url,
          "display_url": machine.ip,
          "status": status
        }
        endpoint_statuses.append(endpoint_status)

      # Append
      if not group in to_show:
        to_show[group] = []
      to_show[group].append({
        "name": machine.name,
        "endpoints": endpoint_statuses
      })
  
  # Render
  return render_template("index.html", machinegroups=to_show)


if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0")

