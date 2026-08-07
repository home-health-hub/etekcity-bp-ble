# etekcity-bp-ble

A standalone, Home-Assistant-free Python client for the Etekcity Smart Blood
Pressure Monitor (BLE). It connects over Bluetooth Low Energy, decodes the
device's measurement notifications, and hands back structured readings so
any Python script can use the device directly.

## Disclaimer

This is an unofficial, reverse-engineered client. The author and
contributors are not affiliated with Etekcity Corporation or Guangdong
Transtek Medical Electronics Co., Ltd.

## Features

- Discovers and connects to the device over BLE (via [bleak](https://github.com/hbldh/bleak)).
- Decodes systolic/diastolic/pulse measurements in both mmHg and kPa.
- Reports irregular heartbeat and motion-detected flags.
- Reports the device's current display-unit setting and last error code.
- Supports both device user slots.
- Ships a `etekcity-bp-monitor` CLI for one-off use without writing any code.

## Requirements

- Etekcity Smart Blood Pressure Monitor (only the TMB-1583-BS has been
  tested, but other models using the same protocol may work).
- A Bluetooth Low Energy adapter reachable by [bleak](https://github.com/hbldh/bleak)
  (a local adapter, or anything bleak can reach, e.g. via BlueZ D-Bus).

## Installation

```bash
pip install git+https://github.com/bonelifer/etekcity-bp-ble.git
```

## Library usage

```python
import asyncio

from etekcity_bp_ble import BloodPressureMonitor, BPData


def on_reading(data: BPData) -> None:
    reading = data.reading
    print(f"User {reading.user + 1}: {reading.systolic_mmhg}/{reading.diastolic_mmhg} mmHg, "
          f"pulse {reading.pulse_bpm} bpm")


async def main() -> None:
    monitor = BloodPressureMonitor("AA:BB:CC:DD:EE:FF", on_reading)
    await monitor.async_start()
    try:
        await asyncio.Event().wait()  # run until interrupted
    finally:
        await monitor.async_stop()


asyncio.run(main())
```

`notification_callback` is called with a `BPData` snapshot every time a
measurement completes. Power on the device with the `MEM` button; it
advertises, gets connected automatically, and pushes its reading within a
few seconds.

### Discovering a device's address

```python
import asyncio
from etekcity_bp_ble import discover

async def main() -> None:
    for device in await discover(timeout=10):
        print(device.address, device.name)

asyncio.run(main())
```

## CLI usage

```bash
# Find nearby devices
etekcity-bp-monitor --discover

# Stream readings from a known address until Ctrl+C
etekcity-bp-monitor --address AA:BB:CC:DD:EE:FF

# Print a single reading and exit
etekcity-bp-monitor --address AA:BB:CC:DD:EE:FF --once
```

Run `etekcity-bp-monitor --help` for all options.

## Protocol notes

The device is not documented publicly. Measurement data arrives as a
sequence of notification packets on one GATT characteristic, identified by
fixed 5-byte headers and exact packet lengths:

| Packet | Header | Length | Carries |
| ------ | ------ | ------ | ------- |
| Display units | `a502010700` | 13 | mmHg/kPa setting |
| Systolic/diastolic | `a522021300` | 20 | user slot, systolic, diastolic |
| Pulse/motion | `00...` | 5 | pulse, motion flag, irregular-heartbeat flag |
| Error | `a522020a00` | 16 | error code |

The pulse/motion packet is what completes a reading; see
[`protocol.py`](src/etekcity_bp_ble/protocol.py) for the exact byte offsets.

## Contributing

Contributions are welcome!

- **Bug reports**: [Open an issue](https://github.com/bonelifer/etekcity-bp-ble/issues).
- **Everything else** (questions, feature requests, ideas, general discussion): [Use Discussions](https://github.com/bonelifer/etekcity-bp-ble/discussions).
- Pull requests are welcome for bug fixes or discussed features.

## Acknowledgments

- The BLE protocol decoding is based on the reverse-engineering work in
  [EdLeckert/ha_etekcity_blood_pressure_monitor](https://github.com/EdLeckert/ha_etekcity_blood_pressure_monitor),
  a Home Assistant integration for the same device.
- Code review, ported implementation, and documentation assisted by [Claude](https://www.anthropic.com/claude).

## License

This project is licensed under the **GNU General Public License v3.0**.

See [LICENSE](LICENSE) for more information.
