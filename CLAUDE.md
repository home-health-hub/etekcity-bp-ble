# Project notes for etekcity-bp-ble

## Upstream sources to watch

- **EdLeckert/ha_etekcity_blood_pressure_monitor** --
  https://github.com/EdLeckert/ha_etekcity_blood_pressure_monitor -- the
  Home Assistant integration this library's BLE protocol decoding is
  based on. The actual reverse-engineered protocol knowledge lives there;
  a fix or a newly-supported device variant landing upstream is the kind
  of thing that wouldn't otherwise be noticed.

- **etekcity_esf551_ble** --
  https://github.com/ronnnnnnnnnnnnn/etekcity_esf551_ble -- not a protocol
  source for this device (it's for Etekcity smart scales, a different
  product), but this library's client architecture (scanner lifecycle,
  cooldown-gated reconnects, dataclass notification callbacks) was
  deliberately patterned after it. Worth a look if that project's
  architecture evolves in a way worth mirroring here too.

## Verification status

See the README for current hardware-verification status against a real
Etekcity blood pressure monitor.
