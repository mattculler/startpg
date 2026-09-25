"""Find what a host serves by probing its TCP ports."""

import socket
import ssl
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

# Always probed: ssh, http(s), common alternate web ports, and Proxmox's web
# UI on 8006.
WELL_KNOWN = (22, 80, 443, 5000, 8000, 8006, 8080)

CONNECT_TIMEOUT = 1  # LAN hosts answer fast; a filtered port shouldn't stall us
BANNER_WAIT = 1
TLS_TIMEOUT = 5  # embedded devices can be slow to handshake

_TLS_CTX = ssl.create_default_context()
_TLS_CTX.check_hostname = False
_TLS_CTX.verify_mode = ssl.CERT_NONE


def probe(ip: str, ports: Iterable[int]) -> dict[int, str]:
    """Probe ports on ip in parallel. Returns {open port: scheme}."""
    ports = sorted(set(ports))
    with ThreadPoolExecutor(max_workers=len(ports) or 1) as pool:
        schemes = list(pool.map(lambda port: _scheme(ip, port), ports))
    return {port: scheme for port, scheme in zip(ports, schemes) if scheme}


def url(scheme: str, ip: str, port: int) -> str:
    """A service URL in startpg.yaml's style.

    ssh URLs always carry their port; http(s) ones only when it isn't the
    scheme's default.
    """
    if scheme != "ssh" and port == {"http": 80, "https": 443}[scheme]:
        return f"{scheme}://{ip}"
    return f"{scheme}://{ip}:{port}"


def _scheme(ip: str, port: int) -> str | None:
    """"ssh", "https" or "http" for an open port, None for a closed one."""
    try:
        conn = socket.create_connection((ip, port), timeout=CONNECT_TIMEOUT)
    except OSError:
        return None
    with conn:
        # SSH servers speak first, whatever port they're on; web servers wait
        # for a request.
        conn.settimeout(BANNER_WAIT)
        try:
            banner = conn.recv(16)
        except OSError:
            banner = b""
    if banner.startswith(b"SSH-"):
        return "ssh"
    return "https" if _speaks_tls(ip, port) else "http"


def _speaks_tls(ip: str, port: int) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=CONNECT_TIMEOUT) as conn:
            conn.settimeout(TLS_TIMEOUT)
            with _TLS_CTX.wrap_socket(conn):
                return True
    except OSError:
        return False
