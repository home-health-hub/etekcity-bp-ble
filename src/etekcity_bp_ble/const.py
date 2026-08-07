"""Constants for the Etekcity Smart Blood Pressure Monitor BLE protocol."""

MANUFACTURER = "Etekcity"

#: Manufacturer ID in BLE advertisements (company identifier 1744).
MANUFACTURER_ID = 1744

#: Local name advertised by the device, used as a discovery fallback.
LOCAL_NAME = "Smart Blood Pressure Monitor"

HW_REVISION_CHARACTERISTIC_UUID = "00002a27-0000-1000-8000-00805f9b34fb"
SW_REVISION_CHARACTERISTIC_UUID = "00002a28-0000-1000-8000-00805f9b34fb"
BLOOD_PRESSURE_CHARACTERISTIC_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
CLIENT_CHARACTERISTIC_CONFIG_HANDLE = 14
CLIENT_CHARACTERISTIC_CONFIG_DATA = b"\x01\x00"

#: Conversion factor from mmHg to kPa, as used by the device's own display.
MMHG_TO_KPA = 0.13332
