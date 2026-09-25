startpg
-------

Are you concerned about the security of your shit?

- face - Frontend (webserver) process
- torso - Lib shared between face and hiney
- hiney - Backend (monitor, daemon) process
- hands - Interactive tool that syncs startpg.yaml with the router's DHCP reservations

Running locally
---------------
- `./runface-debug` - run the frontend with the Flask dev server + reloader
- `hiney` - run a one-off status sweep (writes `/run/startpg/spg.db`)
- `hands` - sync `startpg.yaml` with the router's DHCP reservations (see below)

Running in production
---------------------
Targets a Debian VM running as `mrc:mrc`. Set the VM in `deploy-live`, then:

    ./deploy-live

That rsyncs the source to `/opt/startpg`, sets up a uv-managed venv
(`uv pip install -e .`; uv is auto-installed if missing, avoiding apt's
~300MB python3-pip), and installs the systemd units in `packaging/systemd/`:

- `face.service` - long-running frontend (Flask dev server, LAN-only)
- `hiney.service` + `hiney.timer` - status sweep every 5 minutes

face serves on port 80 directly: the unit sets `STARTPG_PORT=80` and
`AmbientCapabilities=CAP_NET_BIND_SERVICE`, which lets the unprivileged user
bind a low port. Do NOT also run a NAT redirect for 80 - a `nat PREROUTING`
rule only rewrites packets arriving from other hosts, so hiney (probing from
on the VM, which goes through `OUTPUT`) would see a refused connection and
report startpg itself as down. Binding 80 for real keeps every vantage point
in agreement. Run `face` by hand and it falls back to port 5000.

Clicking a group or host name collapses it. That state is persisted server-side
in `/var/lib/startpg/collapsed.json` (via `StateDirectory=startpg`) and rendered
into the HTML, so it survives reloads and reboots, applies across every browser
and device, and never flashes open on load. It's global rather than per-user,
which suits a single-user homepage.

Both units use `RuntimeDirectory=startpg` (with `RuntimeDirectoryPreserve=yes`,
since the shared `/run/startpg` DB outlives hiney's one-shot runs). The DB lives
on tmpfs and is rebuilt by hiney each cycle, so it's fine to lose on reboot.

Syncing with DHCP reservations
------------------------------
`hands` asks the OPNsense router for its static DHCP reservations and walks
you through reconciling `startpg.yaml` with them:

- new reservations: link one to an existing host (and maybe rename the host
  after the reservation's description), add it as a new host, or ignore it for
  good
- changed ones: rewrite the URLs that use the old IP, follow a hostname change,
  rename the host after a new description
- a device that got a new MAC but kept its IP or hostname (a rebuilt VM, a
  service moved to new hardware): carry its link over
- ones that are gone: relink the host to another reservation, unlink it, stop
  checking it, or delete it

Anything can be skipped, and comes up again next time. It shows the diff and
asks before writing; commit the result and `./deploy-live`.

Adding a host (or a second interface, like an IPMI port, to one) probes its IP
on the common ports (22, 80, 443, 5000, 8000, 8006, 8080) plus every port
another service in the yaml uses, shows which are open, and offers them as
services.

It reads the router's API key from the directory you run it in:

1. System > Access > Users: add a `startpg` user with just the
   "Services: ISC DHCPv4: Leases" privilege.
2. Click the user's API key button and drop the downloaded `*_apikey.txt` into
   the project directory. It's gitignored, and `deploy-live` leaves it behind.

The router's self-signed cert is pinned in `src/hands/opnsense.py`. Only the
ISC DHCP backend is supported so far; `BACKENDS` there is where Kea or Dnsmasq
would slot in.

What hands remembers lives in the yaml but never shows on the page. A linked
host's `dhcp:` list holds its reservations (mac, ip, hostname, description) as
of the last sync, which is how the next sync tells what changed, and
`_dhcp: ignore:` holds the ones you've ignored. Top-level keys starting with
`_` aren't groups. hands rewrites the whole file with PyYAML, so comments in it
don't survive; keep notes here instead.

todo
----
- Add option to generate and download ssh configs
- Try HTTP basic auth for some of these devices and add it if they work.  See if I can implement other auth methods
- Add to Networking: the new smart switch, the 10g uplink switch, and any other networking equipment with a status page
- Incorporate OOB management interfaces into their respective hosts.  Should be oob: and oob-ssh: keys for each, with auth info
- Not sure where these go:
  - nginx (How to include when I have it set to drop connections not from given source domains?)
  - IP cameras
