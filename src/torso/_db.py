import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Iterable
from enum import Enum, auto
import logging

from torso import Service, util, Config, Host

LOG = logging.getLogger(__file__)


class DbMode(Enum):
    Reader = auto()
    Writer = auto()

class Db:

    def __init__(self, _mode: DbMode):
        conf_dir = Path("/run") / util.get_distribution_name()
        conf_dir.mkdir(exist_ok=True)
        self._db_file = conf_dir / "spg.db"

        if _mode == DbMode.Reader:
            uri_mode = "ro"
        elif _mode == DbMode.Writer:
            uri_mode = "rwc"

        uri = f"file:{self._db_file}?mode={uri_mode}"
        self._db = sqlite3.connect(self._db_file, autocommit=True, uri=True, check_same_thread=False)

        if _mode == DbMode.Writer:
            sql_dir = Path(__file__).parent / "sql"
            with (sql_dir / "spg.sql").open() as f:
                self._db.executescript(f.read())

    def get_all_service_data(self) -> Iterable[Service]:
        for row in self._db.execute("SELECT * FROM Services").fetchall():
            breakpoint()

    def get_service_data(self, service: Service):
        full_service = self._db.execute("SELECT * FROM Services WHERE url=:url", {"url": url}).fetchone()
        #for row in self._db.execute("SELECT * FROM Services").fetchall():


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

    def insert_service(self, service: Service, host: Host) -> int:
        url = service.url.human_repr()
        LOG.info(f"Inserting service at {url}")
        if not host or not host.hostname:
            breakpoint()
        try:
            self._db.execute("""
                INSERT INTO Services (host, url) VALUES (
                    :host,
                    :url
                )
            """, {
                "host": host.hostname,
                "url": url,
            })
        except sqlite3.IntegrityError as e:
            if str(e) != "UNIQUE constraint failed: Services.url":
                raise
            
        return int(self._db.execute("SELECT service_id FROM Services WHERE url=:url", {"url": url}).fetchone()[0])

    def insert_config(self, config: Config) -> None:
        """Do the initial insert of services."""
        for service, host, group in util.config_iter(config):
            service_id = self.insert_service(service, host)
            service.service_id = service_id


    def update_service(self, service: Service) -> None:
        """Update the service object with live data from the DB."""
        self.get_service_data(service)

    def update_config(self, config: Config) -> None:
        """Update the config object with live data from the DB."""
        for service, host, group in util.config_iter(config):
            self.update_service(service)

    @classmethod
    def writer(cls) -> "Db":
        return cls(DbMode.Writer)

    @classmethod
    def reader(cls) -> "Db":
        return cls(DbMode.Reader)



