#!/usr/bin/env python3

import logging
from concurrent.futures import ThreadPoolExecutor

from torso import Db, check_service, load_config, util

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


if __name__ == "__main__":
    main()
