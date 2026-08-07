from __future__ import annotations

import dataclasses
from enum import IntEnum


class DisplayUnit(IntEnum):
    """Pressure unit currently shown on the device's own display."""

    MMHG = 0
    KPA = 1


@dataclasses.dataclass
class BPReading:
    """A single completed blood-pressure measurement for one user slot.

    Attributes:
        user: Device user slot the reading belongs to (0 = User 1, 1 = User 2).
        systolic_mmhg: Systolic pressure in mmHg.
        diastolic_mmhg: Diastolic pressure in mmHg.
        systolic_kpa: Systolic pressure in kPa.
        diastolic_kpa: Diastolic pressure in kPa.
        pulse_bpm: Pulse rate in beats per minute.
        irregular_heartbeat: Whether an irregular heartbeat was detected.
        motion_detected: Whether arm motion was detected during measurement.
    """

    user: int
    systolic_mmhg: int | None = None
    diastolic_mmhg: int | None = None
    systolic_kpa: float | None = None
    diastolic_kpa: float | None = None
    pulse_bpm: int | None = None
    irregular_heartbeat: bool = False
    motion_detected: bool = False


@dataclasses.dataclass
class BPData:
    """Response data with information about the device and its last reading.

    Attributes:
        name: Name of the device.
        address: Bluetooth address of the device.
        hw_version: Hardware version of the device.
        sw_version: Software version of the device.
        display_unit: Current display unit shown on the device.
        error_code: Last error code reported by the device ("OK" if none).
        reading: The most recently completed measurement, if any.
    """

    name: str = ""
    address: str = ""
    hw_version: str = ""
    sw_version: str = ""
    display_unit: DisplayUnit = DisplayUnit.MMHG
    error_code: str = "OK"
    reading: BPReading | None = None
