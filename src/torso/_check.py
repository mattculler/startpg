import socket
import ssl
import urllib.error
import urllib.request
import logging

from torso import Service

LOG = logging.getLogger(__file__)

TIMEOUT = 5

# last_check_status conventions (see Service.is_up / Service.status_label):
#   >= 0 for http(s): the HTTP status code
#   0    for tcp/ssh: the port was reachable
#   < 0          : could not connect at all
UNREACHABLE = -1
REACHABLE = 0

# LAN devices routinely serve self-signed certs; don't verify them.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def check_service(service: Service) -> tuple[int, str]:
    """Probe a service. Returns (status, human-readable info)."""
    if service.url.scheme in ("http", "https"):
        return _check_http(service.url)
    return _check_tcp(service.url)


def _check_http(url) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(str(url), timeout=TIMEOUT, context=_SSL_CTX) as resp:
            return resp.status, resp.reason
    except urllib.error.HTTPError as e:
        # A 4xx/5xx is still a live server responding.
        return e.code, e.reason
    except (urllib.error.URLError, OSError) as e:
        return UNREACHABLE, str(e)


def _check_tcp(url) -> tuple[int, str]:
    if url.host is None or url.port is None:
        return UNREACHABLE, "no host/port"
    try:
        with socket.create_connection((url.host, url.port), timeout=TIMEOUT):
            return REACHABLE, "reachable"
    except OSError as e:
        return UNREACHABLE, str(e)
