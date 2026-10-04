import yaml
from pathlib import Path
from typing import Any
import logging
from yarl import URL
from torso import Service, Host, Group, Config

# Site config lives in config/, which the repo ignores; see the README.
DEFAULT_CONFIG = (Path(__file__) / "../../../config/startpg.yaml").resolve()

LOG = logging.getLogger(__file__)

def _to_hostname(s: str) -> str:
    # TODO: Add some checks for invalid hostnames
    return s.lower()

def _auto_hostname(host_display_name: str, host):
    if "hostname" not in host:
        host["hostname"] = _to_hostname(host_display_name)
        LOG.info(f"    Set hostname to '{host['hostname']}', from display name")

def load_config(config_file: Path = DEFAULT_CONFIG) -> Config:
    if not config_file.exists():
        raise FileNotFoundError(
            f"no config at {config_file}; start one from startpg.example.yaml"
        )
    with config_file.open() as f:
        root_conf = yaml.safe_load(f)

    # Top-level keys starting with "_" hold tool metadata (like hands' _dhcp
    # block), not groups.
    root_conf = {k: v for k, v in root_conf.items() if not k.startswith("_")}

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

            # A host/service is checked unless it carries a `nocheck:` key,
            # whose value is the reason to surface in the UI.
            host_nocheck = "nocheck" in host
            host_reason = host.get("nocheck")

            for i, service in enumerate(host["services"]):
                LOG.info(f"    - Service {service['url']}")

                service["url"] = URL(service["url"])

                # Set defaults and cascade `nocheck` from the parent host.
                if "nocheck" in service:
                    service["check"] = False
                    reason = service["nocheck"]
                elif host_nocheck:
                    service["check"] = False
                    reason = host_reason
                else:
                    service["check"] = True
                    reason = None
                service["nocheck_reason"] = reason if isinstance(reason, str) else None
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
                    nocheck_reason=service_dict["nocheck_reason"],
                )
                host_obj.services.append(service_obj)
            group_obj.hosts[host_display_name] = host_obj
        groups[group_name] = group_obj
    return groups
