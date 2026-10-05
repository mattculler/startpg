#!/usr/bin/env python3

import logging
from concurrent.futures import ThreadPoolExecutor

from torso import Db, check_service, fetch_drive_health, load_config, load_settings, util

LOG = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)
    conf = load_config()
    db = Db.writer()
    db.insert_config(conf)  # ensure rows exist and service_ids are populated

    services = [s for s, host, group in util.config_iter(conf) if s.check]
    # Network probes are slow and independent, so fan them out; write results
    # back sequentially to keep all sqlite access on this thread.
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda s: (s, *check_service(s)), services))

    for service, status, info in results:
        LOG.info(f"{service.url.human_repr()} -> {status} ({info})")
        db.update_service(service.service_id, status, info)

    sync_drives(db)


def sync_drives(db: Db) -> None:
    """Refresh drive health from drivecanary, if the config names a hub.

    Optional: with no _drivecanary block there's nothing to fetch, and the
    page shows no drive health.
    """
    settings = load_settings().get("drivecanary")
    hub = settings.get("url") if isinstance(settings, dict) else None
    if not hub:
        db.replace_drives([])
        return
    try:
        drives = fetch_drive_health(hub)
    except (OSError, ValueError) as e:
        # Its hosts stay on the page, but unknown rather than stale.
        LOG.warning(f"drivecanary at {hub}: {e}")
        db.mark_drives_unknown(f"couldn't reach drivecanary: {e}")
        return
    LOG.info(f"drivecanary at {hub}: {len(drives)} hosts")
    db.replace_drives(drives)


if __name__ == "__main__":
    main()
