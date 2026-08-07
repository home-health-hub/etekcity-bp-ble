"""BLE client for the Etekcity Smart Blood Pressure Monitor.

Connects when scanning detects an advertisement from the target address,
subscribes to the blood-pressure notification characteristic, and delivers a
BPData snapshot to `notification_callback` each time a measurement completes.
The connection is kept open (rather than reconnected per packet burst) since
the device only pushes data while connected; a cooldown window avoids a
connect storm against a device still finishing its disconnect handshake.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak_retry_connector import establish_connection

from .const import (
    BLOOD_PRESSURE_CHARACTERISTIC_UUID,
    CLIENT_CHARACTERISTIC_CONFIG_DATA,
    CLIENT_CHARACTERISTIC_CONFIG_HANDLE,
    HW_REVISION_CHARACTERISTIC_UUID,
    LOCAL_NAME,
    MANUFACTURER_ID,
    SW_REVISION_CHARACTERISTIC_UUID,
)
from .data import BPData
from .protocol import NotificationParser

DEFAULT_COOLDOWN_SECONDS = 5


def supported(local_name: str | None, manufacturer_data: dict[int, bytes]) -> bool:
    """Return whether an advertisement looks like this device."""
    return MANUFACTURER_ID in manufacturer_data or local_name == LOCAL_NAME


async def discover(timeout: float = 10.0) -> list[BLEDevice]:
    """Scan for nearby devices matching this integration's advertisement."""
    found: dict[str, BLEDevice] = {}

    def _callback(device: BLEDevice, advertisement_data: AdvertisementData) -> None:
        if supported(device.name, advertisement_data.manufacturer_data):
            found[device.address] = device

    async with BleakScanner(detection_callback=_callback):
        await asyncio.sleep(timeout)

    return list(found.values())


class BloodPressureMonitor:
    """Client that scans for, connects to, and streams readings from one device."""

    def __init__(
        self,
        address: str,
        notification_callback: Callable[[BPData], None],
        adapter: str | None = None,
        logger: logging.Logger | None = None,
        *,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        """Initialize the client.

        Args:
            address: Bluetooth address of the device.
            notification_callback: Called with a BPData snapshot each time a
                measurement completes.
            adapter: Bluetooth adapter to use (Linux only).
            logger: Optional logger instance; defaults to this module's logger.
            cooldown_seconds: How long to ignore advertisements after a
                disconnect, so a device still finishing its own disconnect
                handshake doesn't trigger a reconnect storm.
        """
        self._logger = logger or logging.getLogger(__name__)
        self.address = address
        self._notification_callback = notification_callback
        self._cooldown_seconds = cooldown_seconds

        self._data = BPData(address=address)
        self._parser = NotificationParser()

        self._client: BleakClient | None = None
        self._initializing = False
        self._cooldown_end_time: float = 0
        self._lock = asyncio.Lock()

        scanner_kwargs: dict = {"detection_callback": self._advertisement_callback}
        if adapter:
            scanner_kwargs["adapter"] = adapter
        self._scanner = BleakScanner(**scanner_kwargs)

    async def async_start(self) -> None:
        """Start scanning for the device."""
        self._logger.debug("Starting monitor for %s", self.address)
        await self._scanner.start()

    async def async_stop(self) -> None:
        """Stop scanning and disconnect if connected."""
        self._logger.debug("Stopping monitor for %s", self.address)
        await self._scanner.stop()
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    async def _advertisement_callback(
        self, device: BLEDevice, advertisement_data: AdvertisementData
    ) -> None:
        if device.address != self.address:
            return
        if time.time() < self._cooldown_end_time:
            return

        async with self._lock:
            if self._client is not None or self._initializing:
                return
            self._initializing = True

        try:
            await self._connect(device)
        finally:
            self._initializing = False

    async def _connect(self, device: BLEDevice) -> None:
        try:
            self._logger.debug("Connecting to %s", self.address)
            client = await establish_connection(
                BleakClient, device, self.address, self._disconnected_callback
            )
        except Exception:
            self._logger.exception("Could not connect to %s", self.address)
            return

        self._client = client
        self._data.name = device.name or self._data.name

        try:
            await self._read_version_info(client)
            await client.start_notify(
                BLOOD_PRESSURE_CHARACTERISTIC_UUID, self._notification_handler
            )
            await client.write_gatt_descriptor(
                CLIENT_CHARACTERISTIC_CONFIG_HANDLE, CLIENT_CHARACTERISTIC_CONFIG_DATA
            )
        except Exception:
            self._logger.exception("Error setting up notifications for %s", self.address)
            await client.disconnect()

    async def _read_version_info(self, client: BleakClient) -> None:
        if not self._data.hw_version:
            try:
                value = await client.read_gatt_char(HW_REVISION_CHARACTERISTIC_UUID)
                self._data.hw_version = value.decode()
            except Exception:
                self._logger.warning("Could not read hardware version", exc_info=True)

        if not self._data.sw_version:
            try:
                value = await client.read_gatt_char(SW_REVISION_CHARACTERISTIC_UUID)
                self._data.sw_version = value.decode()
            except Exception:
                self._logger.warning("Could not read software version", exc_info=True)

    def _notification_handler(self, _characteristic, payload: bytearray) -> None:
        self._logger.debug("Notification: %s", payload.hex())
        reading = self._parser.feed(bytes(payload))
        self._data.display_unit = self._parser.display_unit
        self._data.error_code = self._parser.error_code

        if reading is not None:
            self._data.reading = reading
            self._notification_callback(self._data)

    def _disconnected_callback(self, _client: BleakClient) -> None:
        self._logger.debug("Disconnected from %s", self.address)
        self._cooldown_end_time = time.time() + self._cooldown_seconds
        self._client = None
