import sqlite3
from importlib.metadata import packages_distributions
from pathlib import Path
from datetime import datetime
from typing import Iterable

from torso import Service

def get_my_distribution_name():
    # 1. Dynamically get the top-level package name (e.g., "torso")
    #    __name__ will be "torso.utils"; we split to get just "torso".
    root_package = __name__.split('.')[0]
    
    # 2. Get the mapping of {package: [distributions]}
    dists = packages_distributions()
    
    # 3. Look up the distribution that owns this root package
    #    This returns a list, so we take the first item.
    dist_name = dists.get(root_package, [None])[0]
    
    return dist_name

class Db:

    def __init__(self, _mode: str):
        conf_dir = Path("/run") / get_my_distribution_name()
        conf_dir.mkdir(exist_ok=True)
        self._db_file = conf_dir / "spg.db"

        if _mode == "reader":
            uri_mode = "ro"
        elif _mode == "writer":
            uri_mode = "rwc"

        uri = f"file:{self._db_file}?mode={uri_mode}"
        self._db = sqlite3.connect(self._db_file, autocommit=True, uri=True)

        sql_dir = Path(__file__).parent / "sql"
        with (sql_dir / "sdb.db").open() as f:
            self._db.executescript(f.read())

    def get_service_data(self) -> Iterable[Service]:
        for row in self._db.execute("SELECT * FROM Services").fetchall():
            breakpoint()

    def update_service(self, service_id: int, status: str, info: str) -> None:
        self._db.execute("""
            UPDATE Services SET 
                last_check_time=:last_check_time,
                last_check_status=:last_check_status, 
                last_check_info=:last_check_info
            WHERE service_id=:service_id
        """, {
            "service_id": service_id,
            "last_check_time": datetime.now().isoformat(),
            "last_check_status": status,
            "last_check_info": info,
        })

    def insert_service(self, service: Service) -> None:
        self._db.execute("""
            INSERT INTO Services VALUES (
                :service_id,
                :host,
                :url
            )
        """, {
            "service_id": service.service_id,
            "host": service.host,
            "url": service.url,
        })

    @classmethod
    def writer(cls) -> "Db":
        return cls("writer")

    @classmethod
    def reader(cls) -> "Db":
        return cls("reader")



