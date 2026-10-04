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
    def is_ssh(self) -> bool:
        """SSH endpoints are shown as a bare status icon, not a link."""
        return self.url.scheme == "ssh"

    @property
    def ssh_port_suffix(self) -> str:
        """":2222" for a non-standard ssh port, empty when it's the usual 22."""
        port = self.url.port
        return "" if port is None or port == 22 else f":{port}"

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
class Section:
    """Services the page shows together: a host's own, or ones sharing a name.

    The SSH ones show as badges on the section's title line, and the rest are
    listed under it.
    """
    name: str | None
    ssh: list[Service] = field(default_factory=list)
    links: list[Service] = field(default_factory=list)

@dataclass 
class Host:
    name: str
    hostname: str | None
    services: list[Service] = field(default_factory=list)

    @property
    def sections(self) -> list[Section]:
        """The host's own (unnamed) services, then each name's in turn, in the
        order the names first appear."""
        by_name = {None: Section(None)}
        for service in self.services:
            section = by_name.setdefault(service.name, Section(service.name))
            (section.ssh if service.is_ssh else section.links).append(service)
        return list(by_name.values())

@dataclass
class Group:
    name: str
    hosts: dict[str, Host] = field(default_factory=dict)

# group name -> Group
type Config = dict[str, Group]

