from etekcity_bp_ble.data import DisplayUnit
from etekcity_bp_ble.protocol import NotificationParser


def _units_packet(kpa: bool) -> bytes:
    data = bytearray(13)
    data[0:5] = bytes.fromhex("a502010700")
    data[10] = 0x01 if kpa else 0x00
    return bytes(data)


def _systolic_diastolic_packet(user: int, systolic: int, diastolic: int) -> bytes:
    data = bytearray(20)
    data[0:5] = bytes.fromhex("a522021300")
    data[14] = user
    data[15] = systolic
    data[17] = diastolic
    return bytes(data)


def _pulse_packet(pulse: int, *, motion: bool = False, irregular: bool = False) -> bytes:
    data = bytearray(5)
    data[0] = 0x00
    data[1] = pulse
    if irregular:
        data[3] = 0x04
    elif motion:
        data[3] = 0x01
    return bytes(data)


def _error_packet(error_index: int) -> bytes:
    data = bytearray(16)
    data[0:5] = bytes.fromhex("a522020a00")
    data[15] = error_index
    return bytes(data)


def test_full_reading_sequence():
    parser = NotificationParser()

    assert parser.feed(_systolic_diastolic_packet(0, 102, 70)) is None
    reading = parser.feed(_pulse_packet(72))

    assert reading is not None
    assert reading.user == 0
    assert reading.systolic_mmhg == 102
    assert reading.diastolic_mmhg == 70
    assert reading.pulse_bpm == 72
    assert round(reading.systolic_kpa, 1) == 13.6
    assert round(reading.diastolic_kpa, 1) == 9.3
    assert reading.irregular_heartbeat is False
    assert reading.motion_detected is False


def test_second_user_slot():
    parser = NotificationParser()
    parser.feed(_systolic_diastolic_packet(1, 118, 80))
    reading = parser.feed(_pulse_packet(65))

    assert reading.user == 1
    assert reading.systolic_mmhg == 118
    assert reading.diastolic_mmhg == 80


def test_motion_and_irregular_heartbeat_flags():
    parser = NotificationParser()
    parser.feed(_systolic_diastolic_packet(0, 110, 75))
    reading = parser.feed(_pulse_packet(80, motion=True))
    assert reading.motion_detected is True
    assert reading.irregular_heartbeat is False

    parser.feed(_systolic_diastolic_packet(0, 110, 75))
    reading = parser.feed(_pulse_packet(80, irregular=True))
    assert reading.irregular_heartbeat is True


def test_display_units_packet_updates_state_without_reading():
    parser = NotificationParser()
    assert parser.feed(_units_packet(kpa=True)) is None
    assert parser.display_unit == DisplayUnit.KPA

    assert parser.feed(_units_packet(kpa=False)) is None
    assert parser.display_unit == DisplayUnit.MMHG


def test_error_packet_sets_error_code_and_clears_pending_reading():
    parser = NotificationParser()
    parser.feed(_systolic_diastolic_packet(0, 102, 70))
    assert parser.feed(_error_packet(0)) is None
    assert parser.error_code == "E01"

    # The pending systolic/diastolic values were cleared by the error, so a
    # stray pulse packet must not produce a reading.
    assert parser.feed(_pulse_packet(72)) is None


def test_pulse_packet_with_no_pending_reading_is_ignored():
    parser = NotificationParser()
    assert parser.feed(_pulse_packet(72)) is None


def test_empty_packet_is_ignored():
    parser = NotificationParser()
    assert parser.feed(b"") is None


def test_unrecognized_packet_is_ignored():
    parser = NotificationParser()
    assert parser.feed(bytes(range(8))) is None
