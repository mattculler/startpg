"""Read static DHCP reservations from the OPNsense router's API."""

import base64
import hashlib
import http.client
import json
import ssl
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TIMEOUT = 10


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Reservation:
    """A static DHCP mapping: the router always gives `mac` the address `ip`."""

    mac: str  # lowercase, colon-separated
    ip: str
    hostname: str  # may be empty
    description: str  # may be empty


class Api:
    """The router's API, reached at `router` over TLS.

    The router's web GUI serves a self-signed cert as a rule, so there's no CA
    to verify it against. We're sending it an API key, so the cert is pinned
    instead, by its SHA-256 (`cert_sha256`). Without a pin, connecting reports
    the router's fingerprint, to be checked against what a browser shows for
    the router before pinning it.
    """

    def __init__(self, key_file: Path, router: str, cert_sha256: str | None):
        self.router = router
        self._cert_sha256 = (cert_sha256 or "").replace(":", "").lower()
        # The file as downloaded from System > Access > Users: key=... and
        # secret=... lines.
        fields = {}
        for line in key_file.read_text().splitlines():
            name, sep, value = line.partition("=")
            if sep:
                fields[name.strip()] = value.strip()
        if "key" not in fields or "secret" not in fields:
            raise ApiError(f"{key_file.name} should have key= and secret= lines")
        creds = f"{fields['key']}:{fields['secret']}"
        self._auth = "Basic " + base64.b64encode(creds.encode()).decode()

    def get(self, path: str):
        """GET an API path and return its parsed JSON."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = http.client.HTTPSConnection(self.router, timeout=TIMEOUT, context=ctx)
        try:
            # Check the pin before sending anything, the key least of all.
            conn.connect()
            cert = conn.sock.getpeercert(binary_form=True)
            fingerprint = hashlib.sha256(cert).hexdigest()
            if not self._cert_sha256:
                raise ApiError(
                    f"the router's TLS cert isn't pinned yet. Its SHA-256 is {fingerprint}; "
                    "if that matches what a browser shows for the router, pin it "
                    "as cert_sha256 under _dhcp in the config"
                )
            if fingerprint != self._cert_sha256:
                raise ApiError(
                    f"the router's TLS cert has changed (SHA-256 {fingerprint}); "
                    "if that's expected, update cert_sha256 under _dhcp in the config"
                )
            conn.request(
                "GET",
                path,
                headers={"Authorization": self._auth, "Accept": "application/json"},
            )
            resp = conn.getresponse()
            body = resp.read()
        except OSError as e:
            raise ApiError(f"couldn't talk to the router at {self.router}: {e}") from e
        finally:
            conn.close()

        if resp.status == 401:
            raise ApiError("the router rejected the API key", resp.status)
        if resp.status != 200:
            raise ApiError(f"GET {path}: {resp.status} {resp.reason}", resp.status)
        return json.loads(body)


class IscDhcp:
    """ISC DHCPv4, which OPNsense 26.1 moved out into the os-isc-dhcp plugin.

    It has no API for static mappings as such, but its leases search merges
    them in as rows of type "static". That endpoint is all the key's user
    needs: the "Services: ISC DHCPv4: Leases" privilege.
    """

    name = "ISC DHCPv4"
    LEASES = "/api/dhcpv4/leases/search_lease"

    def __init__(self, rows: list[dict]):
        self._rows = rows

    @classmethod
    def detect(cls, api: Api) -> "IscDhcp | None":
        try:
            data = api.get(cls.LEASES)
        except ApiError as e:
            if e.status == 404:  # plugin not installed
                return None
            if e.status == 403:
                raise ApiError(
                    "the API key's user needs the "
                    '"Services: ISC DHCPv4: Leases" privilege'
                ) from e
            raise
        return cls(data["rows"])

    def reservations(self) -> list[Reservation]:
        return [
            Reservation(
                mac=row["mac"].lower(),
                ip=row["address"],
                hostname=row["hostname"],
                description=row["descr"],
            )
            for row in self._rows
            # Mappings by client ID have no MAC, and ones without an address
            # only name a host; neither reserves an IP we could key on.
            if row["type"] == "static" and row["mac"] and row["address"]
        ]

    def doubt(self) -> str | None:
        """Why this might not be the router's active DHCP server, if it might not.

        Nothing the key can reach reports whether the ISC service is running
        (the plugin's service API is admin-only), but a server that isn't
        running stops handing out leases. `ends` is in the router's local
        time, which is presumably ours too.
        """
        now = datetime.now()
        for row in self._rows:
            if row["type"] == "dynamic" and row["ends"]:
                if datetime.strptime(row["ends"], "%Y/%m/%d %H:%M:%S") > now:
                    return None
        return (
            f"{self.name} has no current dynamic leases, so it may not be the "
            "router's DHCP server any more. If the router has moved to Kea or "
            "Dnsmasq, its reservations live there instead, and hands needs a "
            "backend for it."
        )


# Tried in order; the first one installed on the router wins. Kea
# (/api/kea/dhcpv4/search_reservation) and Dnsmasq
# (/api/dnsmasq/settings/search_host) would slot in here.
BACKENDS = [IscDhcp]


def find_backend(api: Api):
    for backend in BACKENDS:
        found = backend.detect(api)
        if found is not None:
            return found
    names = ", ".join(backend.name for backend in BACKENDS)
    raise ApiError(f"none of the DHCP servers hands supports ({names}) is on the router")
