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

That rsyncs the source to `/opt/startpg`, sets up a venv (`pip install -e .`),
and installs the systemd units in `packaging/systemd/`:

- `face.service` - long-running frontend (Flask dev server, LAN-only)
- `hiney.service` + `hiney.timer` - status sweep every 5 minutes

Both units use `RuntimeDirectory=startpg` (with `RuntimeDirectoryPreserve=yes`,
since the shared `/run/startpg` DB outlives hiney's one-shot runs). The DB lives
on tmpfs and is rebuilt by hiney each cycle, so it's fine to lose on reboot.

todo
----
- Talk to opnsense and incorporate that DHCP data
- Add option to generate and download ssh configs
- Try HTTP basic auth for some of these devices and add it if they work.  See if I can implement other auth methods
- 
