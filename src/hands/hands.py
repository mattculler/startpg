#!/usr/bin/env python3
"""hands: sync startpg.yaml with the router's DHCP reservations.

Run it from the project directory, where it expects the router's API key file
(*_apikey.txt, as OPNsense names the download). It fetches the router's static
DHCP reservations, walks you through reconciling them with startpg.yaml, then
shows the diff and asks before writing.

A host linked to a reservation remembers it under `dhcp:`, and reservations
you'd rather not hear about again are remembered under `_dhcp: ignore:`.
Neither shows on the page. What's remembered is each reservation as of the
last sync, which is how the next sync tells what changed on the router --
including a device that kept its IP or hostname but got a new MAC.
"""

import difflib
import ipaddress
import os
import re
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from hands import opnsense, probe
from hands.opnsense import Reservation
from torso import DEFAULT_CONFIG, load_config

KEY_FILE_GLOB = "*_apikey.txt"

DEFAULT_PORTS = {"http": 80, "https": 443, "ssh": 22}


# -- startpg.yaml, raw ------------------------------------------------------
#
# hands edits the yaml as plain dicts, not through torso's load_config, which
# expands shorthands like `www:` in place and would write them back out.


def hosts(doc: dict):
    """(group name, host name, host dict) for every host."""
    for group_name, group in doc.items():
        if not group_name.startswith("_"):
            for host_name, host in (group or {}).items():
                yield group_name, host_name, host


def url_host(url: str) -> str | None:
    return urlsplit(url).hostname


def with_url_host(url: str, new_host: str) -> str:
    """url with its host swapped for new_host, all else left as written."""
    parts = urlsplit(url)
    userinfo, at, hostport = parts.netloc.rpartition("@")
    port = f":{parts.port}" if parts.port is not None else ""
    return parts._replace(netloc=f"{userinfo}{at}{new_host}{port}").geturl()


def service_ips(host: dict) -> set[str | None]:
    return {url_host(service["url"]) for service in host.get("services") or []}


def referenced_ports(doc: dict) -> set[int]:
    """Every port some service in the config uses."""
    ports = set()
    for _, _, host in hosts(doc):
        for service in host.get("services") or []:
            parts = urlsplit(service["url"])
            port = parts.port or DEFAULT_PORTS.get(parts.scheme)
            if port:
                ports.add(port)
            if service.get("https"):
                ports.add(443)
    return ports


def set_hostname(host: dict, hostname: str) -> None:
    """Set a host's hostname, keeping it the host's first key."""
    rest = {k: v for k, v in host.items() if k != "hostname"}
    host.clear()
    if hostname:
        host["hostname"] = hostname
    host.update(rest)


def snapshot(res: Reservation) -> dict:
    """What a link or ignore entry remembers of a reservation."""
    entry = {"mac": res.mac, "ip": res.ip}
    if res.hostname:
        entry["hostname"] = res.hostname
    if res.description:
        entry["description"] = res.description
    return entry


def reservation_changed(link, res: Reservation) -> bool:
    """Whether the reservation differs from what the link remembers of it."""
    return any(getattr(res, f) != getattr(link, f) for f in ("ip", "hostname", "description"))


def entry_ip(entry: dict):
    """Sort key putting remembered reservations in IP order."""
    return ipaddress.ip_address(entry["ip"])


class _Dumper(yaml.SafeDumper):
    """Writes startpg.yaml in the layout it was first written by hand in."""

    def increase_indent(self, flow=False, indentless=False):
        # Indent lists under their key rather than flush with it.
        return super().increase_indent(flow, False)

    def ignore_aliases(self, data):
        return True


def _represent_str(dumper, data):
    # Multi-line strings as | blocks, not one quoted line full of \n.
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_Dumper.add_representer(str, _represent_str)


def to_yaml(data) -> str:
    return yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=1000)


def dump(doc: dict) -> str:
    # Groups first, then the "_" metadata blocks.
    ordered = {k: v for k, v in doc.items() if not k.startswith("_")}
    ordered |= {k: v for k, v in doc.items() if k.startswith("_")}
    # A blank line between top-level blocks, which makes the file easier to scan.
    return re.sub(r"\n(?=\S)", "\n\n", to_yaml(ordered))


def write(path: Path, text: str) -> None:
    """Atomically replace path with text, keeping its permissions."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, path.stat().st_mode & 0o7777)
        load_config(Path(tmp))  # face and hiney must still be able to load it
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# -- prompts ----------------------------------------------------------------


def confirm(question: str, default: bool, skip: bool = False) -> bool | None:
    """Ask a yes/no question. With skip, "s" answers None: decide next time."""
    hint = ("Y/n" if default else "y/N") + ("/s" if skip else "")
    while True:
        answer = input(f"{question} [{hint}] ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        if skip and answer in ("s", "skip"):
            return None


def menu(question: str, choices: list[tuple[str, str]], default: str) -> str:
    """Ask a multiple-choice question and return the chosen key."""
    print(question)
    for key, text in choices:
        print(f"    {key}) {text}")
    keys = [key for key, _ in choices]
    while True:
        answer = input(f"  > [{default}] ").strip().lower() or default
        if answer in keys:
            return answer
        print(f"  Pick one of: {', '.join(keys)}")


def pick(question: str, options: list[str]) -> int | None:
    """Pick from a numbered list. Returns its index, or None to go back."""
    print(question)
    for i, option in enumerate(options, 1):
        print(f"    {i}) {option}")
    while True:
        answer = input("  > (Enter to go back) ").strip()
        if not answer:
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"  Pick a number from 1 to {len(options)}")


def show(ip: str, mac: str, hostname: str = "", description: str = "") -> str:
    text = f"{ip} {hostname or '(no hostname)'} [{mac}]"
    return f'{text} "{description}"' if description else text


def show_res(res: Reservation) -> str:
    return show(res.ip, res.mac, res.hostname, res.description)


# -- reconciling ------------------------------------------------------------


@dataclass(eq=False)
class Link:
    """A remembered reservation: a host's `dhcp:` entry, or an ignored one."""

    entry: dict  # the reservation as of the last sync, updated in place
    siblings: list  # the list holding entry, to unlink it from
    group: str | None = None  # None for an ignored reservation
    host: str | None = None

    @property
    def mac(self) -> str:
        return str(self.entry.get("mac", "")).lower()

    @property
    def ip(self) -> str:
        return str(self.entry.get("ip", ""))

    @property
    def hostname(self) -> str:
        return str(self.entry.get("hostname") or "")

    @property
    def description(self) -> str:
        return str(self.entry.get("description") or "")

    def show(self) -> str:
        return show(self.ip, self.mac, self.hostname, self.description)

    def unlink(self) -> None:
        self.siblings.remove(self.entry)


def show_reservation(heading: str, res: Reservation, was: Link | None = None) -> None:
    """Print every field of a reservation, marking any that changed since `was`."""
    print(f"  {heading}")
    for field in ("mac", "ip", "hostname", "description"):
        value = getattr(res, field)
        line = f"    {field + ':':<12} {value or '(none)'}"
        if was is not None and getattr(was, field) != value:
            line += f"  (was {getattr(was, field) or '(none)'})"
        print(line)


def show_host(heading: str, host_name: str, host: dict) -> None:
    """Print a host's whole section, as startpg.yaml has it."""
    print(f"  {heading}")
    print(textwrap.indent(to_yaml({host_name: host}), "    "), end="")


def hostname_question(current: str | None, new: str) -> str:
    if not new:
        return f"  The router's reservation has no hostname now. Remove the host's ({current})?"
    if not current:
        return f"  The host has no hostname. Use the router's ({new})?"
    return f"  Replace the host's hostname ({current}) with the router's ({new})?"


def rename_question(name: str, description: str) -> str:
    return f'  Rename the host "{name}" to the router\'s description, "{description}"?'


class Sync:
    def __init__(self, doc: dict, reservations: list[Reservation]):
        self.doc = doc
        self.reservations = {res.mac: res for res in reservations}
        self.claimed: set[str] = set()  # MACs a link now accounts for
        self.all_links: list[Link] = []

    def run(self) -> None:
        matched, gone = [], []
        self.all_links = self.links()
        for link in self.all_links:
            res = self.reservations.get(link.mac)
            if res is None:
                gone.append(link)
            else:
                matched.append((link, res))
                self.claimed.add(res.mac)

        changed = sum(
            1
            for link, res in matched
            if link.group and reservation_changed(link, res)
        )
        new = len(self.reservations) - len(self.claimed)
        print(
            f"{len(matched)} known ({changed} changed since the last sync), "
            f"{new} new, {len(gone)} gone from the router."
        )
        print("Answering s (skip) leaves that item be, to come up again next time.")

        for link, res in matched:
            self.update(link, res)
        for link in gone:
            self.handle_gone(link)
        # New reservations that look like existing hosts first: those are
        # mostly a matter of confirming the link, and once they're linked, any
        # second interfaces among the rest find their hosts already linked.
        for res in sorted(self.unclaimed(), key=lambda res: not self.candidates(res)):
            self.handle_new(res)
        self.tidy()

    def links(self) -> list[Link]:
        found = []
        for group_name, host_name, host in hosts(self.doc):
            entries = host.get("dhcp") or []
            found += [Link(e, entries, group_name, host_name) for e in entries]
        ignored = (self.doc.get("_dhcp") or {}).get("ignore") or []
        found += [Link(e, ignored) for e in ignored]
        return found

    def unclaimed(self) -> list[Reservation]:
        return sorted(
            (r for r in self.reservations.values() if r.mac not in self.claimed),
            key=lambda res: ipaddress.ip_address(res.ip),
        )

    def host(self, link: Link) -> dict | None:
        return (self.doc.get(link.group) or {}).get(link.host)

    def claim(self, link: Link, res: Reservation) -> None:
        """Point link at res (which may have a new MAC) and catch it up."""
        self.claimed.add(res.mac)
        self.update(link, res)  # before the MAC changes, so it can show the old one
        link.entry["mac"] = res.mac

    # A reservation that's still there, which may have changed.

    def update(self, link: Link, res: Reservation) -> None:
        if link.group is None:
            # Ignored: just keep track of it, so a new MAC is recognisable.
            link.entry.clear()
            link.entry.update(snapshot(res))
            return
        host = self.host(link)
        if host is None or not reservation_changed(link, res):
            return
        print(f"\n{link.host} ({link.group}): its reservation changed on the router.")
        show_reservation("The reservation, from the router:", res, was=link)
        show_host("The host, in startpg.yaml:", link.host, host)
        if res.ip != link.ip:
            self.change_ip(link, host, res)
        if res.hostname != link.hostname:
            self.change_hostname(link, host, res)
        if res.description != link.description:
            self.change_description(link, host, res)

    def change_ip(self, link: Link, host: dict, res: Reservation) -> None:
        services = [s for s in host.get("services") or [] if url_host(s["url"]) == link.ip]
        if not services:
            print(f"  None of the host's URLs use the old IP ({link.ip}), so there's nothing to rewrite.")
            link.entry["ip"] = res.ip
            return
        urls = "the host's URL" if len(services) == 1 else f"the host's {len(services)} URLs"
        answer = confirm(f"  Rewrite {urls} on {link.ip} to use {res.ip}?", True, skip=True)
        if answer is None:
            return
        if answer:
            for service in services:
                service["url"] = with_url_host(service["url"], res.ip)
        link.entry["ip"] = res.ip

    def change_hostname(self, link: Link, host: dict, res: Reservation) -> None:
        current = host.get("hostname")
        if (current or "") != res.hostname:
            # Follow the reservation by default, unless the host's hostname
            # was already its own thing.
            answer = confirm(
                hostname_question(current, res.hostname),
                not current or current == link.hostname,
                skip=True,
            )
            if answer is None:
                return
            if answer:
                set_hostname(host, res.hostname)
        if res.hostname:
            link.entry["hostname"] = res.hostname
        else:
            link.entry.pop("hostname", None)

    def change_description(self, link: Link, host: dict, res: Reservation) -> None:
        if res.description and res.description != link.host:
            # Follow the router by default if the host was named after the
            # old description.
            answer = confirm(
                rename_question(link.host, res.description),
                link.host == link.description,
                skip=True,
            )
            if answer is None:
                return
            if answer and not self.rename_host(link.group, link.host, res.description):
                return  # the name's taken; ask again next time
        if res.description:
            link.entry["description"] = res.description
        else:
            link.entry.pop("description", None)

    def rename_host(self, group_name: str, old: str, new: str) -> bool:
        """Rename a host, keeping its place in its group."""
        group = self.doc[group_name]
        if new in group:
            print(f'  {group_name} already has a host called "{new}", so the name stays.')
            return False
        renamed = {new if name == old else name: host for name, host in group.items()}
        group.clear()
        group.update(renamed)
        for link in self.all_links:
            if (link.group, link.host) == (group_name, old):
                link.host = new
        return True

    # A remembered reservation the router no longer has.

    def handle_gone(self, link: Link) -> None:
        if link.group is not None and self.host(link) is None:
            return  # its host was deleted earlier this run

        # Same device, new MAC -- a VM rebuilt without copying its MAC, or a
        # service moved to new hardware -- usually keeps its IP or hostname.
        new = self.unclaimed()
        lookalikes = []
        for res in new:
            same = [
                what
                for what, matches in (
                    ("IP", res.ip == link.ip),
                    ("hostname", bool(link.hostname) and res.hostname == link.hostname),
                )
                if matches
            ]
            if same:
                lookalikes.append((res, " and ".join(same)))

        if link.group is None:
            for res, same in lookalikes:
                print(f"\nThe ignored reservation {link.show()} is gone, but")
                print(f"  {show_res(res)} has the same {same}.")
                if confirm("  Keep ignoring it under its new MAC?", True):
                    self.claim(link, res)
                    return
            link.unlink()
            print(f"\nForgot the ignored reservation {link.show()}, which is gone.")
            return

        print(f"\n{link.host} ({link.group}): its reservation is gone from the router.")
        print(f"    {link.show()}")
        show_host("The host, in startpg.yaml:", link.host, self.host(link))
        for res, same in lookalikes:
            show_reservation(f"A new reservation with the same {same}, from the router:", res)
            if confirm("  Is it the same device with a new MAC?", True):
                self.claim(link, res)
                return

        while True:
            choices = []
            if new:
                choices.append(("r", "relink it to one of the new reservations"))
            choices += [
                ("u", "unlink it, keeping the host"),
                ("n", "unlink it, keeping the host but no longer checking it"),
                ("d", "delete the host"),
                ("s", "skip for now"),
            ]
            choice = menu("  What now?", choices, "s")
            if choice == "r":
                i = pick("  Which reservation?", [show_res(res) for res in new])
                if i is None:
                    continue
                self.claim(link, new[i])
            elif choice == "u":
                link.unlink()
            elif choice == "n":
                link.unlink()
                self.host(link)["nocheck"] = "its DHCP reservation is gone"
            elif choice == "d":
                group = self.doc[link.group]
                del group[link.host]
                if not group:
                    del self.doc[link.group]
                    print(f"  {link.group} is empty now, so it's gone too.")
            return

    # A reservation nothing remembers yet.

    def handle_new(self, res: Reservation) -> None:
        print(f"\nNew reservation: {show_res(res)}")
        candidates = self.candidates(res)
        while True:
            choices = []
            if candidates:
                group_name, host_name, why = candidates[0]
                choices.append(("l", f"link it to {host_name} ({group_name}), which has its {why}"))
            choices += [
                ("o", "link it to another host"),
                ("a", "add it as a new host"),
                ("i", "ignore it from now on"),
                ("s", "skip for now"),
            ]
            choice = menu("  What now?", choices, "l" if candidates else "s")
            if choice == "l":
                self.link(res, *candidates[0][:2])
            elif choice == "o":
                everyone = [(g, h) for g, h, _ in hosts(self.doc)]
                i = pick("  Which host?", [f"{h} ({g})" for g, h in everyone])
                if i is None:
                    continue
                self.link(res, *everyone[i])
            elif choice == "a":
                if not self.add_host(res):
                    continue
            elif choice == "i":
                meta = self.doc.get("_dhcp") or {}
                self.doc["_dhcp"] = meta
                meta.setdefault("ignore", []).append(snapshot(res))
                self.claimed.add(res.mac)
            return

    def candidates(self, res: Reservation) -> list[tuple[str, str, str]]:
        """(group, host, what matches) for hosts res might belong to."""
        found = []
        for group_name, host_name, host in hosts(self.doc):
            if res.ip in service_ips(host):
                found.append((group_name, host_name, "IP"))
            elif res.hostname and str(host.get("hostname") or "").lower() == res.hostname.lower():
                found.append((group_name, host_name, "hostname"))
        return found

    def link(self, res: Reservation, group_name: str, host_name: str) -> None:
        host = self.doc[group_name][host_name]
        print(f"  Linking it to {host_name} ({group_name}).")
        show_reservation("The reservation, from the router:", res)
        show_host("The host, in startpg.yaml:", host_name, host)

        # A host that's already linked is gaining a second interface, like an
        # IPMI port, whose hostname and description shouldn't displace the
        # host's own hostname and name.
        second_interface = bool(host.get("dhcp"))
        host.setdefault("dhcp", []).append(snapshot(res))
        self.claimed.add(res.mac)

        current = host.get("hostname")
        new_hostname = bool(res.hostname) and current != res.hostname
        new_name = bool(res.description) and res.description != host_name
        if second_interface:
            kept = [what for what, new in (("hostname", new_hostname), ("name", new_name)) if new]
            if kept:
                print(f"  Leaving the host's {' and '.join(kept)} be: this is its second reservation.")
        else:
            if new_hostname and confirm(hostname_question(current, res.hostname), not current):
                set_hostname(host, res.hostname)
            if new_name and confirm(rename_question(host_name, res.description), False):
                self.rename_host(group_name, host_name, res.description)

        if res.ip not in service_ips(host):
            question = f"  None of the host's URLs use {res.ip}. Probe it for services to add?"
            if confirm(question, True):
                host.setdefault("services", []).extend(self.choose_services(res.ip))

    def add_host(self, res: Reservation) -> bool:
        groups = [g for g in self.doc if not g.startswith("_")]
        i = pick("  Which group?", groups + ["(a new group)"])
        if i is None:
            return False
        if i < len(groups):
            group_name = groups[i]
        else:
            while True:
                group_name = input("  New group's name: ").strip()
                if not group_name:
                    return False
                if group_name.startswith("_") or group_name in self.doc:
                    print("  It can't start with _ or be an existing group's name.")
                    continue
                break
        group = self.doc.get(group_name) or {}

        default = res.description or res.hostname or res.ip
        while True:
            name = input(f"  Host's name [{default}]: ").strip() or default
            if name not in group:
                break
            print(f"  {group_name} already has a host called that.")

        host = {}
        if res.hostname:
            host["hostname"] = res.hostname
        host["services"] = self.choose_services(res.ip)
        host["dhcp"] = [snapshot(res)]
        group[name] = host
        self.doc[group_name] = group
        self.claimed.add(res.mac)
        show_host(f"Added to {group_name}:", name, host)
        return True

    def choose_services(self, ip: str) -> list[dict]:
        extra = referenced_ports(self.doc) - set(probe.WELL_KNOWN)
        print(
            f"  Probing {ip} on {len(probe.WELL_KNOWN)} well-known ports and "
            f"{len(extra)} more that startpg.yaml uses..."
        )
        found = probe.probe(ip, [*probe.WELL_KNOWN, *extra])

        def ports(which):
            return ", ".join(f"{p} ({found[p]})" for p in which) or "none"

        print(f"  Well-known ports open: {ports(p for p in probe.WELL_KNOWN if p in found)}")
        others = [p for p in sorted(found) if p not in probe.WELL_KNOWN]
        if others:
            print(f"  Other ports open: {ports(others)}")

        # Web services first and ssh last, as in the rest of the file.
        order = sorted(found, key=lambda p: (found[p] == "ssh", p))
        urls = [probe.url(found[p], ip, p) for p in order]
        for i, url in enumerate(urls, 1):
            print(f"    {i}) {url}")
        default = " ".join(str(i) for i in range(1, len(urls) + 1)) or "none"
        while True:
            answer = input(f"  Services to add, as numbers and/or URLs [{default}]: ")
            answer = answer.strip() or default
            if answer == "none":
                return []
            chosen, bad = [], []
            for token in answer.replace(",", " ").split():
                if token.isdigit() and 1 <= int(token) <= len(urls):
                    chosen.append(urls[int(token) - 1])
                elif "://" in token:
                    chosen.append(token)
                else:
                    bad.append(token)
            if not bad:
                return [{"url": url} for url in chosen]
            print(f"  Neither a listed number nor a URL: {' '.join(bad)}")

    def tidy(self) -> None:
        """Drop emptied lists and blocks, and keep the rest in IP order."""
        for _, _, host in hosts(self.doc):
            if "dhcp" in host:
                if host["dhcp"]:
                    host["dhcp"].sort(key=entry_ip)
                else:
                    del host["dhcp"]
        if "_dhcp" in self.doc:
            meta = self.doc["_dhcp"] or {}
            if meta.get("ignore"):
                meta["ignore"].sort(key=entry_ip)
            else:
                meta.pop("ignore", None)
            if meta:
                self.doc["_dhcp"] = meta
            else:
                del self.doc["_dhcp"]


# -- main -------------------------------------------------------------------


def print_diff(before: str, after: str) -> None:
    color = sys.stdout.isatty()
    for line in difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        "startpg.yaml",
        "startpg.yaml (synced)",
    ):
        if color and line.startswith("+") and not line.startswith("+++"):
            line = f"\033[32m{line}\033[0m"
        elif color and line.startswith("-") and not line.startswith("---"):
            line = f"\033[31m{line}\033[0m"
        print(line, end="")


def sync(config: Path, reservations: list[Reservation]) -> None:
    doc = yaml.safe_load(config.read_text())
    before = dump(doc)
    Sync(doc, reservations).run()
    after = dump(doc)
    if after == before:
        print("\nstartpg.yaml is in sync; nothing to write.")
        return
    print()
    print_diff(before, after)
    if config.read_text() != before:
        print("(Writing also tidies startpg.yaml's layout, which the diff leaves out.)")
    if confirm(f"Write {config}?", True):
        write(config, after)
        print("Written. Commit it and ./deploy-live to put it on the page.")
    else:
        print("Left startpg.yaml unchanged.")


def main():
    key_files = sorted(Path.cwd().glob(KEY_FILE_GLOB))
    if len(key_files) != 1:
        found = ", ".join(f.name for f in key_files) or "none"
        sys.exit(
            f"hands: want exactly one OPNsense API key file ({KEY_FILE_GLOB}) "
            f"in the current directory, found {found}"
        )

    try:
        backend = opnsense.find_backend(opnsense.Api(key_files[0]))
        reservations = backend.reservations()
    except opnsense.ApiError as e:
        sys.exit(f"hands: {e}")

    macs = [res.mac for res in reservations]
    dupes = sorted({mac for mac in macs if macs.count(mac) > 1})
    if dupes:
        sys.exit(
            "hands: reservations are told apart by MAC, but these have more "
            f"than one: {', '.join(dupes)}"
        )

    print(f"Read {len(reservations)} reservations from {backend.name} on {opnsense.ROUTER}.")
    try:
        doubt = backend.doubt()
        if doubt:
            print(f"Warning: {doubt}")
            if not confirm("Carry on with its reservations anyway?", False):
                sys.exit(1)
        sync(DEFAULT_CONFIG, reservations)
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nAborted; startpg.yaml unchanged.")


if __name__ == "__main__":
    main()
