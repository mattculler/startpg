from dataclasses import dataclass, field
from yarl import URL
from datetime import datetime

@dataclass
class Service:
    url: URL  # Ties config to db
    name: str | None
    check: bool
    description: str | None
    nocheck_reason: str | None = None  # why check is disabled, shown in the UI

    service_id: int | None = None  # autoincrement PK

    # DB fields, NULL until checks are done.
    # last_check_status convention (set by torso._check):
    #   >= 0 for http(s): the HTTP status code
    #   0    for tcp/ssh: the port was reachable
    #   < 0          : could not connect at all
    last_check_time: datetime | None = None
    last_check_status: int | None = None
    last_check_info: str | None = None

    @property
    def is_up(self) -> bool | None:
        """Tri-state health: None if not yet determined, else healthy?"""
        if not self.check or self.last_check_status is None:
            return None
        if self.last_check_status < 0:
            return False
        if self.url.scheme in ("http", "https"):
            # A 4xx/5xx response means the server answered but is unhealthy.
            return self.last_check_status < 400
        return True  # tcp/ssh: a non-negative status means the port was reachable

    @property
    def status_label(self) -> str:
        """Short human-readable status for display."""
        if not self.check:
            if self.nocheck_reason:
                return f"not checked - {self.nocheck_reason}"
            return "not checked"
        if self.last_check_status is None:
            return "?"
        if self.last_check_status < 0:
            return "down"
        if self.url.scheme in ("http", "https"):
            return str(self.last_check_status)
        return "up"

@dataclass 
class Host:
    name: str
    hostname: str | None
    services: list[Service] = field(default_factory=list)

@dataclass
class Group:
    name: str
    hosts: dict[str, Host] = field(default_factory=dict)

# group name -> Group
type Config = dict[str, Group]

