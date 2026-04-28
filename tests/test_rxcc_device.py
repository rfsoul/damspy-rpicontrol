import unittest

from damspy_rpicontrol.models import AntennaPath, FrontendMode
from damspy_rpicontrol.rxcc_device import (
    RxccController,
    antenna_reports,
    build_gpio_report,
    build_rf_start_report,
    build_rf_stop_report,
    frontend_mode_reports,
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


class RxccDeviceTest(unittest.TestCase):
    def test_gpio_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_gpio_report(3, 1), bytes([0x0F, 0x0E, 0x00, 0x02, 0x03, 0x01]))

    def test_rf_start_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_start_report(10, 5), bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]))

    def test_rf_stop_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_stop_report(), bytes([0x0F, 0x0D, 0x00]))

    def test_transmitting_pa_mode_reports_match_expected_sequence(self) -> None:
        self.assertEqual(
            frontend_mode_reports(FrontendMode.TRANSMITTING_PA),
            [
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x01]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x01, 0x00]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x02, 0x00]),
            ],
        )

    def test_bypass_mode_reports_match_expected_sequence(self) -> None:
        self.assertEqual(
            frontend_mode_reports(FrontendMode.BYPASS),
            [
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x00]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x01, 0x01]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x02, 0x00]),
            ],
        )

    def test_receiving_mode_reports_match_expected_sequence(self) -> None:
        self.assertEqual(
            frontend_mode_reports(FrontendMode.RECEIVING),
            [
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x00]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x01, 0x00]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x02, 0x01]),
            ],
        )

    def test_antenna_report_matches_documented_sequence(self) -> None:
        self.assertEqual(
            antenna_reports(AntennaPath.SECONDARY),
            [bytes([0x0F, 0x0E, 0x00, 0x02, 0x03, 0x01])],
        )

    def test_apply_antenna_sends_single_antenna_report(self) -> None:
        factory = DeviceFactory()
        controller = RxccController(device_factory=factory, backend_name="test")

        reports_sent = controller.apply_antenna(AntennaPath.SECONDARY)

        self.assertEqual(reports_sent, 1)
        self.assertEqual(len(factory.devices), 1)
        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x0E, 0x00, 0x02, 0x03, 0x01])])
        self.assertTrue(factory.devices[0].closed)

    def test_start_rf_enforces_mode_then_antenna_then_start(self) -> None:
        factory = DeviceFactory()
        controller = RxccController(device_factory=factory, backend_name="test")

        reports_sent = controller.start_rf(AntennaPath.MAIN, channel=10, power=5)

        self.assertEqual(reports_sent, 5)
        self.assertEqual(len(factory.devices), 1)
        self.assertEqual(
            factory.devices[0].writes,
            [
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x01]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x01, 0x00]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x02, 0x00]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x03, 0x00]),
                bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]),
            ],
        )
        self.assertTrue(factory.devices[0].closed)

    def test_apply_gpio_records_device_response_when_present(self) -> None:
        factory = DeviceFactory(reads=[bytes([0xAA, 0x55])])
        controller = RxccController(device_factory=factory, backend_name="test")

        controller.apply_gpio(pin=0, level=1)
        written_reports, response = controller.get_last_io_trace()

        self.assertEqual(written_reports, [bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x01])])
        self.assertEqual(response, bytes([0xAA, 0x55]))


if __name__ == "__main__":
    unittest.main()
