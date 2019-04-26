#!/usr/bin/python3
import flask
import requests
from collections import OrderedDict
import re

from machine import Machine
from services import *
from auths import *

app = flask.Flask(__name__)


# TODO: Add everything with a static IP and split up the internal services some more

MACHINES = OrderedDict()
MACHINES["Devices"] = [
  Machine("modem", "192.168.100.1", [
    HttpService(),
    # Spectrum analyzer - more info:
    # http://www.dslreports.com/forum/r31563033-Broadcom-Chip-Spectrum-Analyzer
    HttpService(port="8080", description="spectrum analyzer")
  ], check_up=False),
  Machine("opnsense", "192.168.1.1"),
  Machine("Engenius bridge", "192.168.1.2", [
    HttpService(auth=HttpBasicAuth("admin", "changeme"))
  ]),
  Machine("SMC switch", "192.168.1.3", [
    HttpService(auth=HttpBasicAuth("admin", "changeme"))
  ]),
  Machine("TP-Link switch", "192.168.1.4"),
  Machine("Proxmox", "192.168.1.73", [
    HttpsService(port="8006")
  ])
]
MACHINES["VM Services"] = [
  Machine("Gitea git server", "192.168.1.83", [
    HttpService(port="3000")
  ]),
  Machine("Deluge torrent server", "192.168.1.84")
]
MACHINES["VM Websites"] = [
  # VM websites
  Machine("site VM", "192.168.1.82", [
    HttpService(port="5000")
  ]),
  Machine("Fund VM", "192.168.1.85", [
    HttpService(port="8000")
  ])
  # NOTE: Cannot include startpg itself here, as this will always cause an infinite
  #  loop and time out!  Haha.  Will have to rearchitect to do out of band up checking
  #  for this to work.
]
MACHINES["OOB Management Interfaces"] = [
  Machine("matryoshka", "192.168.1.20")
  #Machine("svalbard", "192.168.1.?"),
  #Machine("vault101", "192.168.1.?")
]
MACHINES["External Services"] = [
  Machine("site", "site.example.net"),
  Machine("Fund", "fund.example.org", [
    HttpService(),
    HttpService(host="www"),
    HttpService(host="test")
  ]),
  Machine("Blog", "blog.example.com", [
    HttpService(),
    HttpService(host="www")
  ])
]

# TODO: Try HTTP basic auth for some of these devices and add it if they work.  See if I
#  can implement other auth methods

# TODO: Add stuff that's ssh-only and add ssh support

# TODO: Add option to generate and download ssh_config from this
# 192.168.1.2 - Engenius bridge - needs special legacy config option
# Host engenius garagebridge
#   User admin
#   #Password changeme
#   KexAlgorithms +diffie-hellman-group1-sha1


def _get_status_html(status):
  display = ""
  color = ""
  tooltip = ""
  if type(status) == int:
    display = str(status)
    
    if status // 100 != 2:
      # 2xx - HTTP error code
      color = "red"
    else:
      color = "green"
    
    # This fun line just takes a status string like "internal_server_error" and turns
    #  it nicer, like "Internal Server Error"
    tooltip = re.sub(
        r"\b([a-z])", 
        lambda match: match.group(1).upper(), 
        requests.status_codes._codes[status][0].replace("_", " "))
  else:
    # Something else bad, probably an exception.  String it, hard
    display = "Could not connect!"
    color = "red"
    tooltip = str(flask.escape(str(status)))

  if tooltip:
    tooltip = "title='" + tooltip + "'"
  return "<span style='color:" + color + "' " + tooltip + ">" + display + "</span>"


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
      for endpoint in machine.endpoints:
        # Make a request and see if it's live
        url = endpoint.get_fqdn(with_auth=False)
        status = "(not checked)"
        
        print("making request for machine", machine.name, "to", url)
        if machine.check_up:
          try:
            # These requests.get() calls use verify to ignore certificate issues
            if endpoint.requires_auth():
              code = requests.get(
                  url, 
                  verify=False, 
                  timeout=5, 
                  auth=endpoint.auth.get_tuple()).status_code
            else:
              code = requests.get(url, verify=False, timeout=5).status_code

            # Get some nice html and tell the user if the link will log in for them
            status = _get_status_html(code)
            if endpoint.requires_auth():
              # Add the key emoji
              status = "&#x1F5DD;&#xFE0F; " + status
          except requests.exceptions.ConnectionError as e:
            # The flask.escape function returns some kind of mutant string that corrupts
            #  any string it touches.  The explicit str over it is required!
            status = _get_status_html(e)
          except requests.exceptions.RequestException as e:
            # Catch anything else, who the fuck knows
            status = _get_status_html(e)

        # Only show the description if there are multiple endpoints
        if len(machine.endpoints) > 1:
          description = endpoint.description
          if description:
            description = "(" + description + ")"
          status = "{} {}".format(status, description)

        to_show_machine["endpoints"].append({
          "full_url": endpoint.get_fqdn(),
          "display_url": machine.get_display_url(endpoint),
          "status": status
        })

      # Append
      to_show_group.append(to_show_machine)
    to_show.append(to_show_group)   
  # Render
  return flask.render_template("index.html", machinegroups=to_show)


if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0")

