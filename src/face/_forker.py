import subprocess
import signal
import sys
from pathlib import Path
import psutil
import logging

# This prevents zombies. If a child dies, the kernel cleans it up 
# instantly without you needing to call .wait().
signal.signal(signal.SIGCHLD, signal.SIG_IGN)

LOG = logging.getLogger(__file__)

def _fork(cmd: list[str | Path]) -> None:
    subprocess.Popen(
        cmd,
        # Detach from terminal/session so it survives parent exit
        start_new_session=True,
        # Silence I/O so it doesn't hold onto the parent's pipes
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def _proc_exists(name: str) -> bool:
    for proc in psutil.process_iter(["name"]):
        if name in proc.info["name"]:
            print(proc.info["name"])

def ensure_hiney() -> None:
    _proc_exists("hiney")
