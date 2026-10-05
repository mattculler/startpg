import sqlite3
from pathlib import Path
from datetime import datetime
from enum import Enum, auto
import logging

from torso import util, Config, DriveHealth, Host, Service

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
        """Sync the Services table to the config.

        Inserts rows for new services and deletes rows for services no longer
        in the config, so they stop lingering in the DB until the next reboot.
        """
        urls = []
        for service, host, group in util.config_iter(config):
            service.service_id = self.insert_service(service, host)
            urls.append(service.url.human_repr())

        placeholders = ", ".join("?" * len(urls))
        cur = self._db.execute(
            f"DELETE FROM Services WHERE url NOT IN ({placeholders})", urls
        )
        if cur.rowcount:
            LOG.info(f"Deleted {cur.rowcount} service(s) no longer in config")

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

    def replace_drives(self, drives: list[DriveHealth]) -> None:
        """Make the Drives table exactly these, in one go so that a reader
        never sees it half written."""
        self._db.execute("BEGIN")
        try:
            self._db.execute("DELETE FROM Drives")
            self._db.executemany(
                "INSERT INTO Drives (host, status, problems, url) VALUES (?, ?, ?, ?)",
                [(d.host, d.status, "\n".join(d.problems), d.url) for d in drives],
            )
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        self._db.execute("COMMIT")

    def mark_drives_unknown(self, why: str) -> None:
        """Keep the hosts last heard of, but with their health unknown, and why."""
        self._db.execute("UPDATE Drives SET status = 'unknown', problems = ?", (why,))

    def get_drives(self) -> dict[str, DriveHealth]:
        """Drive health by host name, lowercased."""
        try:
            rows = self._db.execute("SELECT host, status, problems, url FROM Drives").fetchall()
        except sqlite3.OperationalError:
            return {}  # a DB from before the Drives table, until hiney next runs
        return {
            host.lower(): DriveHealth(host, status, problems.splitlines(), url)
            for host, status, problems, url in rows
        }

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

        # Drive health goes on the host drivecanary knows by its hostname.
        drives = self.get_drives()
        for group in config.values():
            for host in group.hosts.values():
                host.drives = drives.get((host.hostname or "").lower())

    @classmethod
    def writer(cls) -> "Db":
        return cls(DbMode.Writer)

    @classmethod
    def reader(cls) -> "Db":
        return cls(DbMode.Reader)
