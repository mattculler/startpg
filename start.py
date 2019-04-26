#!/usr/bin/python3
import flask
import requests
from collections import OrderedDict


from machine import Machine
from services import *
from auths import *

app = flask.Flask(__name__)


# TODO: Add everything with a static IP and split up the internal services some more

MACHINES = OrderedDict()
MACHINES["Internal Services"] = [
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
  ])
  # NOTE: Cannot include startpg itself, as this will always cause an infinite loop and time out!  Haha
]
MACHINES["OOB Management Interfaces"] = [
  Machine("matryoshka", "192.168.1.20")
  #Machine("svalbard", "192.168.1.?"),
  #Machine("vault101", "192.168.1.?")
]
MACHINES["External Services"] = [
  Machine("site", "site.example.net"),
  Machine("Fund", "fund.example.org"),
  Machine("Blog", "www.blog.example.com")
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
        url = endpoint.get_full_url(with_auth=False)
        status = "(not checked)"
        
        print("making request for machine", machine.name, "to", url)
        if machine.check_up:
          try:
            # These requests.get() calls use verify to ignore certificate issues
            if endpoint.requires_auth():
              status = requests.get(
                  url, 
                  verify=False, 
                  timeout=5, 
                  auth=endpoint.auth.get_tuple()).status_code
            else:
              status = requests.get(url, verify=False, timeout=5).status_code
            status = str(status)

            # Make it yell if error
            if len(status) == 3:
              if status[0] != "2":
                # HTTP error code
                status = "<span style='color: red;'>" + status + "</span>"
              else:
                status = "<span style='color: green;'>" + status + "</span>"

            # Tell the user if their link will log in for them
            if endpoint.requires_auth():
              status = "&#x1F5DD;&#xFE0F; " + status
          except requests.exceptions.ConnectionError as e:
            # The flask.escape function returns some kind of mutant string that corrupts
            #  any string it touches.  The explicit str over it is required!
            status = (
                "<span style='color:red;' title='" + str(flask.escape(str(e))) + "'>"
                "  Server seems to be down!"
                "</span>")
          except requests.exceptions.RequestException as e:
            # Catch anything else, who the fuck knows
            status = str(e)
        print("  status:", status)

        # Only show the full URL and description if there are multiple endpoints
        display_url = machine.ip
        if len(machine.endpoint_list) > 1:
          display_url = url
          description = endpoint.description
          if description:
            description = "(" + description + ")"
          status = "{} {}".format(status, description)

        to_show_machine["endpoints"].append({
          "full_url": endpoint.get_full_url(),
          "display_url": display_url,
          "status": status
        })

      # Append
      to_show_group.append(to_show_machine)
    to_show.append(to_show_group)   
  # Render
  return flask.render_template("index.html", machinegroups=to_show)


if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0")

