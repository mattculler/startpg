import sqlite3
from pathlib import Path
from datetime import datetime
from enum import Enum, auto
import logging

from torso import util, Config, Host, Service

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
        self._db = sqlite3.connect(uri, autocommit=True, uri=True, check_same_thread=False)

        if _mode == DbMode.Writer:
            sql_dir = Path(__file__).parent / "sql"
            with (sql_dir / "spg.sql").open() as f:
                self._db.executescript(f.read())

    def insert_service(self, service: Service, host: Host) -> int:
        url = service.url.human_repr()
        LOG.info(f"Inserting service at {url}")
        try:
            self._db.execute(
                "INSERT INTO Services (host, url) VALUES (:host, :url)",
                {"host": host.hostname or host.name, "url": url},
            )
        except sqlite3.IntegrityError as e:
            if str(e) != "UNIQUE constraint failed: Services.url":
                raise

        row = self._db.execute(
            "SELECT service_id FROM Services WHERE url=:url", {"url": url}
        ).fetchone()
        return int(row[0])

    def insert_config(self, config: Config) -> None:
        """Do the initial insert of services from config."""
        for service, host, group in util.config_iter(config):
            service.service_id = self.insert_service(service, host)

    def update_service(self, service_id: int, status: int, info: str) -> None:
        self._db.execute(
            """
            UPDATE Services SET
                last_check_time=:last_check_time,
                last_check_status=:last_check_status,
                last_check_info=:last_check_info
            WHERE service_id=:service_id
            """,
            {
                "service_id": service_id,
                "last_check_time": datetime.now().isoformat(),
                "last_check_status": status,
                "last_check_info": info,
            },
        )

    def get_status_by_url(self) -> dict[str, sqlite3.Row]:
        self._db.row_factory = sqlite3.Row
        rows = self._db.execute(
            "SELECT url, last_check_time, last_check_status, last_check_info FROM Services"
        ).fetchall()
        return {row["url"]: row for row in rows}

    def update_config(self, config: Config) -> None:
        """Overlay the latest check results from the DB onto the config."""
        by_url = self.get_status_by_url()
        for service, host, group in util.config_iter(config):
            row = by_url.get(service.url.human_repr())
            if row is None:
                continue
            ts = row["last_check_time"]
            service.last_check_time = datetime.fromisoformat(ts) if ts else None
            service.last_check_status = row["last_check_status"]
            service.last_check_info = row["last_check_info"]

    @classmethod
    def writer(cls) -> "Db":
        return cls(DbMode.Writer)

    @classmethod
    def reader(cls) -> "Db":
        return cls(DbMode.Reader)
