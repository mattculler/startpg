import yaml
from pathlib import Path
from typing import Any
import logging
from yarl import URL
from torso import Service, Host, Group

DEFAULT_CONFIG = (Path(__file__) / "../../../startpg.yaml").resolve()

LOG = logging.getLogger(__file__)

def _to_hostname(s: str) -> str:
    # TODO: Add some checks for invalid hostnames
    return s.lower()

def _auto_hostname(host_display_name: str, host):
    if "hostname" not in host:
        host["hostname"] = _to_hostname(host_display_name)
        LOG.info(f"    Set hostname to '{host['hostname']}', from display name")

def load_config(config_file: Path = DEFAULT_CONFIG) -> dict[str, Group]:
    with config_file.open() as f:
        root_conf = yaml.safe_load(f)

    # Normalize
    for group_name, group in root_conf.items():
        LOG.info(f"- Group {group_name}")
        for host_display_name, host in group.items():
            LOG.info(f"  - Host {host_display_name}")

            # Disabled because maybe for some of these we don't want to set a hostname
            #_auto_hostname(host_display_name, host)
    
            # Set defaults
            if "hostname" not in host:
                host["hostname"] = None
            if "check" not in host:
                host["check"] = True

            for i, service in enumerate(host["services"]):
                LOG.info(f"    - Service {service['url']}")

                service["url"] = URL(service["url"])

                # Set defaults and cascade from parent
                if "check" not in service:
                    service["check"] = host["check"]
                if "name" not in service:
                    service["name"] = None
                if "description" not in service:
                    service["description"] = None
                if "www" in service:
                    www_url = service["url"].with_host("www." + service["url"].host)
                    host["services"].insert(i + 1, {"url": www_url})
                if "https" in service:
                    https_url = service["url"].with_scheme("https")
                    host["services"].insert(i + 1, {"url": https_url})

    # Type convert
    groups = {}
    for group_name, group_dict in root_conf.items():
        group_obj = Group(name=group_name)
        for host_display_name, host_dict in group_dict.items():
            host_obj = Host(
                name=host_display_name, 
                hostname=host_dict["hostname"],
            )
            for service_dict in host_dict["services"]:
                service_obj = Service(
                    name=service_dict["name"],
                    url=service_dict["url"],
                    description=service_dict["description"],
                    check=service_dict["check"],
                )
                host_obj.services.append(service_obj)
            group_obj.hosts[host_display_name] = host_obj
        groups[group_name] = group_obj
    return groups
