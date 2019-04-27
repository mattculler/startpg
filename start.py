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
MACHINES["Internal Services"] = [
  Machine("Deluge torrent server", "192.168.1.84", [
    HttpService(),
    SshService()
  ]),
  Machine("Gitea git server", "192.168.1.83", [
    HttpService(port="3000"),
    SshService()
  ])
]
MACHINES["External Services"] = [
  Machine("Fund", "fund.example.org", [
    HttpService(),
    HttpService(host="www"),
    HttpService(host="test", check=False)
  ]),
  Machine("site", "site.example.net", [
    HttpService(),
    HttpService(host="www")
  ]),
  Machine("Blog", "blog.example.com", [
    HttpService(),
    HttpService(host="www")
  ])
]
MACHINES["Hardware"] = [
  Machine("opnsense", "192.168.1.1", [
    HttpService(),
    SshService()
  ]),
  Machine("Proxmox", "192.168.1.73", [
    HttpsService(port="8006"),
    SshService()
  ]),
  Machine("modem", "192.168.100.1", [
    HttpService(),
    # Spectrum analyzer - more info:
    # http://www.dslreports.com/forum/r31563033-Broadcom-Chip-Spectrum-Analyzer
    HttpService(port="8080", description="spectrum analyzer")
  ], check=False),
  Machine("Wifi AP", "192.168.1.5", [
    HttpService(auth_type=HttpWebAuth),
    SshService()
  ], auth=("admin", "changeme")),
  Machine("Engenius bridge", "192.168.1.2", [
    HttpService(),
    SshService(description="super weird embedded thing")
  ], auth=("admin", "changeme")),
  Machine("SMC switch", "192.168.1.3", auth=("admin", "changeme")),
  Machine("TP-Link switch", "192.168.1.4", auth=HttpWebAuth("admin", "changeme"))
]
MACHINES["VM Websites"] = [
  # VM websites
  Machine("site VM", "192.168.1.82", [
    HttpService(),
    SshService()
  ]),
  Machine("Fund VM", "192.168.1.85", [
    HttpService(port="8000"),
    SshService()
  ])
  # TODO: Cannot include startpg itself here, as this will always cause an infinite
  #  loop and time out!  Haha.  Will have to rearchitect to do out of band up checking
  #  for this to work.
  # TODO: How to include nginx when I have it set to drop connections not from given
  #  source domains?
]
MACHINES["OOB Management"] = [
  Machine("matryoshka", "192.168.1.20", [
    HttpService(auth_type=HttpWebAuth),
    SshService(description="another super weird one - not linux")
  ], auth=("ADMIN", "changeme"))
  #Machine("svalbard", "192.168.1.?"),
  #Machine("vault101", "192.168.1.?")
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

# TODO: Add login links for trackers?

# TODO: Style!


def _get_status_html(status, tooltip="", color="", fontsize=""):
  if tooltip:
    tooltip = "title='" + tooltip + "'"
  if color:
    color = "color: " + color + ";"
  if fontsize:
    fontsize = "font-size: " + fontsize + ";"

  style = ""
  if color or fontsize:
    style = "style='" + color + fontsize + "'"
  return "<span " + style + " " + tooltip + ">" + status + "</span>"


NOT_CHECKED = _get_status_html("(not checked)", fontsize="smaller")


def _get_http_status_html(status):
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

  return _get_status_html(display, tooltip=tooltip, color=color)


def _check_http_endpoint(endpoint, machine):
  if (not issubclass(type(endpoint), HttpService) and 
      not issubclass(type(endpoint), HttpsService)):
    return False, ""

  url = endpoint.get_fqdn(with_auth=False)
  description = ""
  if endpoint.description:
    description = " (" + endpoint.description + ") "

  if not machine.check:
    status = ""
  elif not endpoint.check:
    print("  not checking", url)
    status = NOT_CHECKED
  else:
    print("  making request to", url)
    try:
      # These requests.get() calls use verify to ignore certificate issues
      if endpoint.auth:
        code = requests.get(
            url, 
            verify=False, 
            timeout=5, 
            auth=endpoint.auth.get_tuple()).status_code
      else:
        code = requests.get(url, verify=False, timeout=5).status_code

      # Get some nice html and tell the user if the link will log in for them
      status = _get_http_status_html(code)
    except requests.exceptions.ConnectionError as e:
      # The flask.escape function returns some kind of mutant string that corrupts any 
      #  string it touches.  The explicit str over it is required!
      status = _get_http_status_html(e)
    except requests.exceptions.RequestException as e:
      # Catch anything else, who the fuck knows
      status = _get_http_status_html(e)
  if endpoint.auth:
    # Add any auth emoji
    status = endpoint.auth.icon + description + status
  return True, status


def _check_ssh_endpoint(endpoint, machine):
  # TODO: Implement actual checking
  if not issubclass(type(endpoint), SshService):
    return False, ""

  description = "SSH"
  if endpoint.description:
    description += " - " + endpoint.description

  tooltip = ""
  if endpoint.auth:
    tooltip = str(endpoint.auth)
  return True, _get_status_html(description, tooltip=tooltip, fontsize="smaller")


@app.route("/")
def hello():
  to_show = []
  for group in MACHINES:
    to_show_group = [group]
    for machine in MACHINES[group]:
      print("dealing with machine", machine.name)
      machine_checked = " "
      if not machine.check:
        print("  not checking any endpoint")
        machine_checked = NOT_CHECKED
      to_show_machine = {
        "name": machine.name,
        "status": machine_checked,
        "endpoints": [],
        "other": []
      }
      for endpoint in machine.endpoints:
        status = NOT_CHECKED
        if not machine.check:
          # The not checked message will be displayed next to the machine rather than
          #  it's endpoints
          status = ""
        
        # Make a request and see if it's live
        for checker in {_check_http_endpoint, _check_ssh_endpoint}:
          checked, newstatus = checker(endpoint, machine)
          if checked:
            status = newstatus
            break

        if endpoint.show_url:
          to_show_machine["endpoints"].append({
            "full_url": endpoint.get_fqdn(),
            "display_url": machine.get_display_url(endpoint),
            "status": status
          })
        else:
          to_show_machine["other"].append(status)

      # Append
      to_show_group.append(to_show_machine)
    to_show.append(to_show_group)   
  # Render
  return flask.render_template("index.html", machinegroups=to_show)


if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0")

