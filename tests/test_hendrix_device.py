import unittest

from damspy_rpicontrol.hendrix_device import (
    DeviceCommunicationError,
    HendrixController,
    build_battery_info_request,
    build_ctx_low_report,
    build_ctx_high_report,
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
            raise AssertionError("Unexpected HID read")
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
        self.assertEqual(build_ctx_high_report(), bytes([0x0F, 0x14, 0x00, 0x02, 0x00, 0x01]))

    def test_ctx_low_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_ctx_low_report(), bytes([0x0F, 0x14, 0x00, 0x02, 0x00, 0x00]))

    def test_rf_start_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_start_report(10, 5), bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]))

    def test_rf_stop_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_stop_report(), bytes([0x0F, 0x0D, 0x00]))

    def test_battery_request_matches_reference_shape(self) -> None:
        self.assertEqual(
            build_battery_info_request(),
            bytes([0x01, 0x61] + [0x00] * 15),
        )

    def test_parse_battery_response_reads_little_endian_millivolts(self) -> None:
        battery_mv = parse_battery_info_response(bytes([0x02, 0x61, ord("A"), 0xBF, 0x0E]))

        self.assertEqual(battery_mv, 3775)

    def test_start_rf_sends_ctx_high_then_start(self) -> None:
        factory = DeviceFactory()
        controller = HendrixController(product_id=0x008A, device_factory=factory, backend_name="test")

        reports_sent = controller.start_rf(channel=10, power=5)

        self.assertEqual(reports_sent, 2)
        self.assertEqual(
            factory.devices[0].writes,
            [
                bytes([0x0F, 0x14, 0x00, 0x02, 0x00, 0x01]),
                bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]),
            ],
        )
        self.assertTrue(factory.devices[0].closed)

    def test_set_ctx_low_sends_single_low_report(self) -> None:
        factory = DeviceFactory()
        controller = HendrixController(product_id=0x008A, device_factory=factory, backend_name="test")

        reports_sent = controller.set_ctx(high=False)

        self.assertEqual(reports_sent, 1)
        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x14, 0x00, 0x02, 0x00, 0x00])])
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
