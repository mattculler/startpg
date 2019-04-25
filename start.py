#!/usr/bin/python3
from flask import Flask, render_template, url_for, jsonify
import requests
from collections import OrderedDict


from machine import Machine
from services import *

app = Flask(__name__)


MACHINES = OrderedDict()
MACHINES["Internal Services"] = [
  Machine("modem", "192.168.100.1", [
    HttpService(),
    # Spectrum analyzer - more info:
    # http://www.dslreports.com/forum/r31563033-Broadcom-Chip-Spectrum-Analyzer
    HttpService(port="8080", description="spectrum analyzer")
  ], check_up=False),
  Machine("opnsense", "192.168.1.1"),
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

# TODO: Add option to generate and download ssh_config from this
# 192.168.1.2 - Engenius bridge - needs special legacy config option
# Host engenius garagebridge
#   User admin
#   #Password changeme
#   KexAlgorithms +diffie-hellman-group1-sha1


@app.route("/")
def hello():

  to_show = []
  for group in MACHINES:
    to_show_group = [group]
    for machine in MACHINES[group]:
      to_show_machine = {
        "name": machine.name,
        "endpoints": []
      }
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
          except requests.exceptions.ConnectionError as e:
            status = "<span style='color:red;'>Server seems to be down!</span>"
          except requests.exceptions.RequestException as e:
            # Catch anything else
            status = str(e)

        # Only show the full URL and description if there are multiple endpoints
        display_url = machine.ip
        if len(machine.endpoint_list) > 1:
          display_url = url
          description = endpoint.get_description()
          if description:
            description = "(" + description + ")"
          status = "{} {}".format(status, description)

        to_show_machine["endpoints"].append({
          "full_url": url,
          "display_url": display_url,
          "status": status
        })

      # Append
      to_show_group.append(to_show_machine)
    to_show.append(to_show_group)   
  import json
  print(json.dumps(to_show, indent=2))
  # Render
  return render_template("index.html", machinegroups=to_show)


if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0")

