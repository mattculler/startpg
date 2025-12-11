from dataclasses import dataclass
from yarl import URL
from datetime import datetime

@dataclass
class Service:
    # DB fields
    service_id: int | None  # autoincrement
    host: str
    url: URL
    
    # DB fields, NUll until checks are done
    last_check_time: datetime | None
    last_check_status: int | None
    last_check_info: str | None
    
    # Fields from configs
    name: str
    group: str
    description: str | None
    check: bool
    user: str | None
    password: str | None
