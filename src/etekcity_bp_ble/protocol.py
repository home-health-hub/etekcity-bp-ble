"""Decoder for the device's GATT notification stream.

The device does not send one packet per reading. Instead it emits a fixed
sequence of notification packets on the blood-pressure characteristic:

1. An optional display-units packet.
2. A systolic/diastolic packet, which also carries the active user slot.
3. A pulse/motion/irregular-heartbeat packet, which completes the reading.

An error packet can arrive instead of steps 2-3 if the measurement failed.
Packets are identified by a fixed 5-byte header plus an exact length.
"""

from __future__ import annotations

from .data import BPReading, DisplayUnit
from .const import MMHG_TO_KPA

_HEADER_DISPLAY_UNITS = 0xA502010700
_HEADER_SYSTOLIC_DIASTOLIC = 0xA522021300
_HEADER_ERROR = 0xA522020A00


class NotificationParser:
    """Stateful decoder that turns raw notification packets into BPReadings.

    One instance should be used per connection session; it tracks the
    in-progress reading (active user, systolic/diastolic) between packets.
    """

    def __init__(self) -> None:
        self.display_unit: DisplayUnit = DisplayUnit.MMHG
        self.error_code: str = "OK"
        self._user: int | None = None
        self._systolic_mmhg: int | None = None
        self._diastolic_mmhg: int | None = None

    def feed(self, data: bytes) -> BPReading | None:
        """Process one notification packet.

        Returns a completed BPReading once the pulse/motion packet that ends
        a measurement arrives, otherwise None (the packet only updated
        internal state, or was not recognized).
        """
        if not data:
            return None

        header = int.from_bytes(data[0:5], "big")

        if header == _HEADER_DISPLAY_UNITS and len(data) == 13:
            self.display_unit = DisplayUnit.KPA if data[10] == 0x01 else DisplayUnit.MMHG
            return None

        if header == _HEADER_SYSTOLIC_DIASTOLIC and len(data) == 20:
            self._user = data[14]
            self._systolic_mmhg = data[15]
            self._diastolic_mmhg = data[17]
            self.error_code = "OK"
            return None

        if data[0] == 0x00 and len(data) == 5:
            return self._complete_reading(data)

        if header == _HEADER_ERROR and len(data) == 16:
            self.error_code = f"E{data[15] + 1:02d}"
            self._systolic_mmhg = None
            self._diastolic_mmhg = None
            return None

        return None

    def _complete_reading(self, data: bytes) -> BPReading | None:
        # A pulse packet with no preceding systolic/diastolic packet in this
        # session (e.g. one dropped notification) carries no valid reading.
        if self._user is None or self._systolic_mmhg is None or self._diastolic_mmhg is None:
            return None

        reading = BPReading(
            user=self._user,
            systolic_mmhg=self._systolic_mmhg,
            diastolic_mmhg=self._diastolic_mmhg,
            systolic_kpa=self._systolic_mmhg * MMHG_TO_KPA,
            diastolic_kpa=self._diastolic_mmhg * MMHG_TO_KPA,
            pulse_bpm=data[1],
            motion_detected=bool(data[3] & 0x01),
            irregular_heartbeat=data[3] == 0x04,
        )
        self._systolic_mmhg = None
        self._diastolic_mmhg = None
        return reading
