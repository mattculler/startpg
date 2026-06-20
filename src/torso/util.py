from importlib.metadata import packages_distributions
from collections.abc import Iterator

from torso import Group, Host, Service, Config

def get_distribution_name() -> str:
    # 1. Dynamically get the top-level package name (e.g., "torso")
    #    __name__ will be "torso.utils"; we split to get just "torso".
    root_package = __name__.split('.')[0]
    
    # 2. Get the mapping of {package: [distributions]}
    dists = packages_distributions()
    
    # 3. Look up the distribution that owns this root package
    #    This returns a list, so we take the first item.
    dist_name = dists.get(root_package, [None])[0]
    
    return dist_name

def config_iter(config: Config) -> Iterator[tuple[Service, Host, Group]]:
    for _, group in config.items():
        for _, host in group.hosts.items():
            for service in host.services:
                yield service, host, group
