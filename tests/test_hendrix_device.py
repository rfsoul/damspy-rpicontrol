import unittest
from unittest.mock import patch

from damspy_rpicontrol.hendrix_device import (
    DeviceCommunicationError,
    HendrixController,
    build_battery_info_request,
    build_ctx_low_report,
    build_ctx_high_report,
    build_led_test_report,
    build_rf_start_report,
    build_rf_stop_report,
    parse_battery_info_response,
)


class RecordingDevice:
    def __init__(self, reads: list[bytes | list[int]] | None = None) -> None:
        self.writes: list[bytes | list[int]] = []
        self.reads = list(reads or [])
        self.closed = False

    def write(self, data: bytes | list[int]) -> int:
        self.writes.append(bytes(data))
        return len(data)

    def read(self, length: int, timeout_ms: int) -> bytes:
        if not self.reads:
            return b""
        return bytes(self.reads.pop(0))

    def close(self) -> None:
        self.closed = True


class DeviceFactory:
    def __init__(self, reads: list[bytes | list[int]] | None = None) -> None:
        self.devices: list[RecordingDevice] = []
        self.reads = list(reads or [])

    def __call__(self) -> RecordingDevice:
        device = RecordingDevice(reads=self.reads)
        self.devices.append(device)
        return device


class HendrixDeviceTest(unittest.TestCase):
    def test_ctx_high_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_ctx_high_report(), bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x01]))

    def test_ctx_low_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_ctx_low_report(), bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x00]))

    def test_rf_start_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_start_report(10, 5), bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]))

    def test_rf_stop_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_stop_report(), bytes([0x0F, 0x0D, 0x00]))

    def test_led_test_report_matches_reference_shape(self) -> None:
        self.assertEqual(
            build_led_test_report(color_index=0, enabled=True, brightness=255),
            bytes([21, 0x4E, 0x00, 0x01, 0xFF] + [0x00] * 12),
        )

    def test_battery_request_matches_reference_shape(self) -> None:
        self.assertEqual(
            build_battery_info_request(),
            bytes([0x01, 0x61] + [0x00] * 15),
        )

    def test_parse_battery_response_reads_little_endian_millivolts(self) -> None:
        battery_mv = parse_battery_info_response(bytes([0x02, 0x61, ord("A"), 0xBF, 0x0E]))

        self.assertEqual(battery_mv, 3775)

    def test_start_rf_sends_single_start_report(self) -> None:
        factory = DeviceFactory()
        controller = HendrixController(product_id=0x008A, device_factory=factory, backend_name="test")

        reports_sent = controller.start_rf(channel=10, power=5)

        self.assertEqual(reports_sent, 1)
        self.assertEqual(
            factory.devices[0].writes,
            [
                bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]),
            ],
        )
        self.assertTrue(factory.devices[0].closed)

    def test_set_ctx_low_sends_single_low_report(self) -> None:
        factory = DeviceFactory()
        controller = HendrixController(product_id=0x008A, device_factory=factory, backend_name="test")

        reports_sent = controller.set_ctx(high=False)

        self.assertEqual(reports_sent, 1)
        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x00])])
        self.assertTrue(factory.devices[0].closed)

    def test_rx_start_rf_sends_short_reports(self) -> None:
        factory = DeviceFactory()
        controller = HendrixController(product_id=0x008B, device_factory=factory, backend_name="test")

        reports_sent = controller.start_rf(channel=10, power=5)

        self.assertEqual(reports_sent, 1)
        self.assertEqual(
            factory.devices[0].writes,
            [
                bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]),
            ],
        )
        self.assertTrue(factory.devices[0].closed)

    def test_start_rf_records_command_response_when_present(self) -> None:
        factory = DeviceFactory(reads=[bytes([0x10, 0xAA, 0x55])])
        controller = HendrixController(product_id=0x008B, device_factory=factory, backend_name="test")

        controller.start_rf(channel=10, power=5)
        written_reports, response = controller.get_last_io_trace()

        self.assertEqual(written_reports, [bytes([0x0F, 0x03, 0x00, 10, 0x00, 5])])
        self.assertEqual(response, bytes([0x10, 0xAA, 0x55]))

    def test_flash_led_sends_two_on_off_cycles(self) -> None:
        factory = DeviceFactory()
        controller = HendrixController(product_id=0x008A, device_factory=factory, backend_name="test")

        with patch("damspy_rpicontrol.hendrix_device.POST_OPEN_DELAY_S", 0), patch(
            "damspy_rpicontrol.hendrix_device.LED_FLASH_STEP_DELAY_S", 0
        ):
            reports_sent = controller.flash_led(color_index=1)

        self.assertEqual(reports_sent, 4)
        self.assertEqual(
            factory.devices[0].writes,
            [
                bytes([21, 0x4E, 0x01, 0x01, 0xFF] + [0x00] * 12),
                bytes([21, 0x4E, 0x01, 0x00, 0x00] + [0x00] * 12),
                bytes([21, 0x4E, 0x01, 0x01, 0xFF] + [0x00] * 12),
                bytes([21, 0x4E, 0x01, 0x00, 0x00] + [0x00] * 12),
            ],
        )
        self.assertTrue(factory.devices[0].closed)

    def test_read_battery_writes_request_then_parses_response(self) -> None:
        factory = DeviceFactory(reads=[bytes([0x02, 0x61, ord("A"), 0xBF, 0x0E])])
        controller = HendrixController(product_id=0x008A, device_factory=factory, backend_name="test")

        battery_mv = controller.read_battery_mv()

        self.assertEqual(battery_mv, 3775)
        self.assertEqual(factory.devices[0].writes, [bytes([0x01, 0x61] + [0x00] * 15)])
        self.assertTrue(factory.devices[0].closed)

    def test_parse_battery_response_rejects_unexpected_status(self) -> None:
        with self.assertRaises(DeviceCommunicationError):
            parse_battery_info_response(bytes([0x02, 0x61, ord("E"), 0xBF, 0x0E]))


if __name__ == "__main__":
    unittest.main()
