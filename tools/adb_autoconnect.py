#!/usr/bin/env python3
from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_ADB_PATHS = [
    "/Applications/BlueStacks.app/Contents/MacOS/hd-adb",
    "/Applications/BlueStacks.app/Contents/MacOS/HD-adb",
]

DEFAULT_PORTS = [
    5555,
    5556,
    5565,
    5575,
    5585,
    5595,
    5554,
]


def find_adb_path(explicit: str | None) -> str:
    if explicit:
        path = Path(explicit)
        if path.exists():
            return str(path)
        raise SystemExit(f"ADB executable does not exist: {explicit}")

    for candidate in DEFAULT_ADB_PATHS:
        if Path(candidate).exists():
            return candidate

    raise SystemExit("BlueStacks hd-adb was not found.")


def port_is_open(port: int, timeout: float) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def run_adb(adb_path: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [adb_path, *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def list_devices(adb_path: str) -> dict[str, str]:
    proc = run_adb(adb_path, ["devices"])
    devices: dict[str, str] = {}
    for line in proc.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices[parts[0]] = parts[1]
    return devices


def get_state(adb_path: str, serial: str) -> str:
    proc = run_adb(adb_path, ["-s", serial, "get-state"])
    return proc.stdout.strip()


def connect_port(adb_path: str, port: int, timeout: float, verbose: bool) -> bool:
    serial = f"127.0.0.1:{port}"
    devices = list_devices(adb_path)
    if devices.get(serial) == "device":
        if verbose:
            print(f"{serial} already online")
        return True

    if not port_is_open(port, timeout):
        if verbose:
            print(f"{serial} is not listening")
        return False

    proc = run_adb(adb_path, ["connect", serial])
    if verbose:
        print(proc.stdout.strip() or f"connect {serial}")

    state = get_state(adb_path, serial)
    ok = state == "device"
    if verbose:
        print(f"{serial} state={state or '<empty>'}")
    return ok


def connect_once(adb_path: str, ports: list[int], timeout: float, verbose: bool) -> int:
    connected = 0
    for port in ports:
        if connect_port(adb_path, port, timeout, verbose):
            connected += 1
    return connected


def parse_ports(value: str) -> list[int]:
    ports: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        ports.append(int(part))
    return ports


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-connect listening BlueStacks ADB ports so MXU/MaaToolkit can discover them.",
    )
    parser.add_argument("--adb", help="Path to BlueStacks hd-adb.")
    parser.add_argument(
        "--ports",
        default=",".join(str(p) for p in DEFAULT_PORTS),
        help="Comma-separated ADB ports to probe.",
    )
    parser.add_argument("--watch", action="store_true", help="Keep probing periodically.")
    parser.add_argument("--interval", type=float, default=5.0, help="Watch interval in seconds.")
    parser.add_argument("--timeout", type=float, default=0.2, help="TCP probe timeout in seconds.")
    parser.add_argument("--quiet", action="store_true", help="Reduce output.")
    args = parser.parse_args()

    adb_path = find_adb_path(args.adb)
    ports = parse_ports(args.ports)
    verbose = not args.quiet

    if verbose:
        print(f"adb={adb_path}")
        print(f"ports={ports}")

    while True:
        connected = connect_once(adb_path, ports, args.timeout, verbose)
        if verbose:
            devices = list_devices(adb_path)
            online = [serial for serial, state in devices.items() if state == "device"]
            print(f"online={online} connected_count={connected}")

        if not args.watch:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
