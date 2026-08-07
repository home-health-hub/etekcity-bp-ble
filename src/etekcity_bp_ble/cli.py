#!/usr/bin/env python3
"""Standalone command-line client for the Etekcity Blood Pressure Monitor."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import logging
import sys

from ._version import __version__
from .data import BPData
from .monitor import BloodPressureMonitor, discover

_LOGGER = logging.getLogger("etekcity_bp_ble")


def _print_reading(data: BPData) -> None:
    print(json.dumps(dataclasses.asdict(data), indent=2, default=str))


async def _run_discover(timeout: float) -> None:
    print(f"Scanning for {timeout:.0f}s...", file=sys.stderr)
    devices = await discover(timeout=timeout)
    if not devices:
        print("No devices found.", file=sys.stderr)
        return
    for device in devices:
        print(f"{device.address}  {device.name or '(unknown name)'}")


async def _run_monitor(address: str, adapter: str | None, once: bool) -> None:
    done = asyncio.Event()

    def _callback(data: BPData) -> None:
        _print_reading(data)
        if once:
            done.set()

    monitor = BloodPressureMonitor(address, _callback, adapter=adapter, logger=_LOGGER)
    await monitor.async_start()
    try:
        if once:
            await done.wait()
        else:
            await asyncio.Event().wait()
    finally:
        await monitor.async_stop()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-d", "--discover", action="store_true", help="scan for devices and exit"
    )
    parser.add_argument("-a", "--address", help="Bluetooth address of the device")
    parser.add_argument(
        "-t", "--timeout", type=float, default=10.0, help="discovery scan duration in seconds"
    )
    parser.add_argument(
        "-1", "--once", action="store_true", help="exit after the first reading"
    )
    parser.add_argument("-A", "--adapter", help="Bluetooth adapter to use (Linux only)")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the etekcity-bp-monitor console script."""
    args = _parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    if args.discover:
        asyncio.run(_run_discover(args.timeout))
        return

    if not args.address:
        print("error: --address is required unless --discover is given", file=sys.stderr)
        raise SystemExit(2)

    try:
        asyncio.run(_run_monitor(args.address, args.adapter, args.once))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
