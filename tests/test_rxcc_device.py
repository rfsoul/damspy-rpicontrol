import unittest
import unittest.mock

from damspy_rpicontrol.models import AntennaPath, FrontendMode
from damspy_rpicontrol.rxcc_device import (
    DeviceCommunicationError,
    RxccController,
    VENDOR_ID,
    WIRELESS_PRO_PRODUCT_IDS,
    WirelessProRxController,
    antenna_reports,
    build_gpio_report,
    build_rf_start_report,
    build_rf_stop_report,
    build_wireless_pro_rf_start_report,
    detect_hid_backend,
    frontend_mode_reports,
)


class RecordingDevice:
    def __init__(self, reads: list[bytes | list[int] | None] | None = None) -> None:
        self.writes: list[bytes | list[int]] = []
        self.reads = list(reads or [])
        self.closed = False

    def write(self, data: bytes | list[int]) -> int:
        self.writes.append(bytes(data))
        return len(data)

    def read(self, length: int, timeout_ms: int) -> bytes | None:
        if not self.reads:
            return b""
        response = self.reads.pop(0)
        if response is None:
            return None
        return bytes(response)

    def close(self) -> None:
        self.closed = True


class DeviceFactory:
    def __init__(self, reads: list[bytes | list[int] | None] | None = None) -> None:
        self.devices: list[RecordingDevice] = []
        self.reads = list(reads or [])

    def __call__(self) -> RecordingDevice:
        device = RecordingDevice(reads=self.reads)
        self.devices.append(device)
        return device


class FakeHidDevice:
    def close(self) -> None:
        return None


class FakeHidApiModule:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []
        self.device = FakeHidDevice()

    def Device(self, vendor_id: int, product_id: int) -> FakeHidDevice:
        self.calls.append((vendor_id, product_id))
        if product_id == WIRELESS_PRO_PRODUCT_IDS[0]:
            raise OSError("primary product ID unavailable")
        return self.device


class RxccDeviceTest(unittest.TestCase):
    def test_gpio_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_gpio_report(3, 1), bytes([0x0F, 0x0E, 0x00, 0x02, 0x03, 0x01]))

    def test_rf_start_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_start_report(10, 5), bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]))

    def test_rf_stop_report_matches_reference_shape(self) -> None:
        self.assertEqual(build_rf_stop_report(), bytes([0x0F, 0x0D, 0x00]))

    def test_wireless_pro_rf_start_report_encodes_antenna_and_signed_power(self) -> None:
        self.assertEqual(
            build_wireless_pro_rf_start_report(wirepro_freq=78, antenna=AntennaPath.SECONDARY, wirepro_power=-4),
            bytes([0x0F, 0x03, 0x00, 78, 0x01, 0xFC]),
        )

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

    def test_start_rf_raw_sends_single_start_report(self) -> None:
        factory = DeviceFactory()
        controller = RxccController(device_factory=factory, backend_name="test")

        reports_sent = controller.start_rf_raw(channel=10, power=5)

        self.assertEqual(reports_sent, 1)
        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x03, 0x00, 10, 0x00, 5])])
        self.assertTrue(factory.devices[0].closed)

    def test_set_charging_enable_sends_single_enable_report(self) -> None:
        factory = DeviceFactory()
        controller = RxccController(device_factory=factory, backend_name="test")

        reports_sent = controller.set_charging(enabled=True)

        self.assertEqual(reports_sent, 1)
        self.assertEqual(factory.devices[0].writes, [bytes([21, 0x55, 0x01])])
        self.assertTrue(factory.devices[0].closed)

    def test_set_charging_disable_sends_single_disable_report(self) -> None:
        factory = DeviceFactory()
        controller = RxccController(device_factory=factory, backend_name="test")

        reports_sent = controller.set_charging(enabled=False)

        self.assertEqual(reports_sent, 1)
        self.assertEqual(factory.devices[0].writes, [bytes([21, 0x55, 0x00])])
        self.assertTrue(factory.devices[0].closed)

    def test_apply_gpio_records_device_response_when_present(self) -> None:
        factory = DeviceFactory(reads=[bytes([0xAA, 0x55])])
        controller = RxccController(device_factory=factory, backend_name="test")

        controller.apply_gpio(pin=0, level=1)
        written_reports, response = controller.get_last_io_trace()

        self.assertEqual(written_reports, [bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x01])])
        self.assertEqual(response, bytes([0xAA, 0x55]))

    def test_apply_gpio_treats_none_response_as_no_bytes_returned(self) -> None:
        factory = DeviceFactory(reads=[None])
        controller = RxccController(device_factory=factory, backend_name="test")

        controller.apply_gpio(pin=0, level=1)
        written_reports, response = controller.get_last_io_trace()

        self.assertEqual(written_reports, [bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x01])])
        self.assertIsNone(response)

    def test_apply_gpio_polls_until_delayed_response_arrives(self) -> None:
        factory = DeviceFactory(reads=[None, b"", bytes([0xAA, 0x55])])
        controller = RxccController(device_factory=factory, backend_name="test")

        with unittest.mock.patch("damspy_rpicontrol.rxcc_device.COMMAND_READ_POLL_INTERVAL_S", 0):
            controller.apply_gpio(pin=0, level=1)
        _, response = controller.get_last_io_trace()

        self.assertEqual(response, bytes([0xAA, 0x55]))

    def test_wireless_pro_start_rf_sends_single_embedded_antenna_report(self) -> None:
        factory = DeviceFactory()
        controller = WirelessProRxController(device_factory=factory, backend_name="test")

        reports_sent = controller.start_rf(AntennaPath.MAIN, wirepro_freq=78, wirepro_power=-4)

        self.assertEqual(reports_sent, 1)
        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x03, 0x00, 78, 0x00, 0xFC])])
        self.assertTrue(factory.devices[0].closed)

    def test_rxcc_read_battery_writes_request_then_parses_response(self) -> None:
        factory = DeviceFactory(reads=[bytes([0x02, 0x61, ord("A"), 0xBF, 0x0E, 0x64, 0x00, 0x1A, 0x00, 0x01, 0x2C, 0x01])])
        controller = RxccController(device_factory=factory, backend_name="test")

        battery_info = controller.read_battery_info()

        self.assertEqual(battery_info.battery_mv, 3775)
        self.assertEqual(battery_info.temperature_c, 26)
        self.assertEqual(battery_info.charge_state_code, 1)
        self.assertEqual(battery_info.charge_current_ma, 300)
        self.assertEqual(factory.devices[0].writes, [bytes([0x01, 0x61] + [0x00] * 15)])
        self.assertTrue(factory.devices[0].closed)

    def test_rxcc_read_battery_rejects_none_response(self) -> None:
        factory = DeviceFactory(reads=[None])
        controller = RxccController(device_factory=factory, backend_name="test")

        with self.assertRaises(DeviceCommunicationError):
            controller.read_battery_mv()

    def test_read_serial_number_writes_request_then_parses_response(self) -> None:
        factory = DeviceFactory(
            reads=[bytes([14, 0x00, ord("A"), ord("R"), ord("X"), ord("C"), ord("C"), ord("0"), ord("0"), ord("8"), ord("C")] + [0x00] * 23)]
        )
        controller = RxccController(device_factory=factory, backend_name="test")

        serial_number = controller.read_serial_number()

        self.assertEqual(serial_number, "RXCC008C")
        self.assertEqual(
            factory.devices[0].writes,
            [bytes([13, 0x00, ord("N"), ord("O"), ord("R"), ord("D"), ord("I"), ord("C"), ord("_"), ord("I"), ord("D")] + [0x00] * 7 + [0x00] * 16)],
        )
        self.assertTrue(factory.devices[0].closed)

    def test_wireless_pro_read_battery_writes_request_then_parses_response(self) -> None:
        factory = DeviceFactory(reads=[bytes([0x02, 0x61, ord("A"), 0xBF, 0x0E, 0x64, 0x00, 0x1A, 0x00, 0x01, 0x2C, 0x01])])
        controller = WirelessProRxController(device_factory=factory, backend_name="test")

        battery_info = controller.read_battery_info()

        self.assertEqual(battery_info.battery_mv, 3775)
        self.assertEqual(battery_info.temperature_c, 26)
        self.assertEqual(battery_info.charge_state_code, 1)
        self.assertEqual(battery_info.charge_current_ma, 300)
        self.assertEqual(factory.devices[0].writes, [bytes([0x01, 0x61] + [0x00] * 15)])
        self.assertTrue(factory.devices[0].closed)

    def test_wireless_pro_read_battery_rejects_none_response(self) -> None:
        factory = DeviceFactory(reads=[None])
        controller = WirelessProRxController(device_factory=factory, backend_name="test")

        with self.assertRaises(DeviceCommunicationError):
            controller.read_battery_mv()

    def test_detect_hid_backend_tries_wireless_pro_fallback_product_id(self) -> None:
        hidapi_module = FakeHidApiModule()

        with unittest.mock.patch("damspy_rpicontrol.rxcc_device.importlib.import_module", return_value=hidapi_module):
            factory, backend_name = detect_hid_backend(product_id=WIRELESS_PRO_PRODUCT_IDS)

        self.assertEqual(backend_name, "hidapi.Device")
        self.assertIsNotNone(factory)
        device = factory()

        self.assertIs(device, hidapi_module.device)
        self.assertEqual(
            hidapi_module.calls,
            [
                (VENDOR_ID, WIRELESS_PRO_PRODUCT_IDS[0]),
                (VENDOR_ID, WIRELESS_PRO_PRODUCT_IDS[1]),
            ],
        )


if __name__ == "__main__":
    unittest.main()
