startpg
-------

Are you concerned about the security of your shit?

- face - Frontend (webserver) process
- torso - Lib shared between face and hiney
- hiney - Backend (monitor, daemon) process

Running locally
---------------
- `./runface-debug` - run the frontend with the Flask dev server + reloader
- `hiney` - run a one-off status sweep (writes `/run/startpg/spg.db`)

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

todo
----
- Talk to opnsense and incorporate that DHCP data
- Add option to generate and download ssh configs
- Try HTTP basic auth for some of these devices and add it if they work.  See if I can implement other auth methods
- 
