import unittest

from damspy_rpicontrol.hendrix_device import (
    HendrixController,
    build_ctx_high_report,
    build_rf_start_report,
    build_rf_stop_report,
)


class RecordingDevice:
    def __init__(self) -> None:
        self.writes: list[bytes | list[int]] = []
        self.closed = False

    def write(self, data: bytes | list[int]) -> int:
        self.writes.append(bytes(data))
        return len(data)

    def close(self) -> None:
        self.closed = True


class DeviceFactory:
    def __init__(self) -> None:
        self.devices: list[RecordingDevice] = []

    def __call__(self) -> RecordingDevice:
        device = RecordingDevice()
        self.devices.append(device)
        return device


class HendrixDeviceTest(unittest.TestCase):
    def test_ctx_high_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_ctx_high_report(), bytes([0x0F, 0x14, 0x00, 0x02, 0x00, 0x01]))

    def test_rf_start_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_start_report(10, 5), bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]))

    def test_rf_stop_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_stop_report(), bytes([0x0F, 0x0D, 0x00]))

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


if __name__ == "__main__":
    unittest.main()
