from dataclasses import dataclass, field
from yarl import URL
from datetime import datetime

@dataclass
class Service:
    url: URL  # Ties config to db
    name: str | None
    check: bool
    description: str | None

    service_id: int | None = None  # autoincrement PK

    # DB fields, NULL until checks are done
    last_check_time: datetime | None = None
    last_check_status: int | None = None
    last_check_info: str | None = None

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

