import unittest

from fastapi import Request

from damspy_rpicontrol.main import create_app
from damspy_rpicontrol.models import (
    AntennaRequest,
    DeviceCommandRequest,
    FrontendMode,
    FrontendModeRequest,
    RawCommandRequest,
    StartRfRequest,
)
from damspy_rpicontrol.rxcc_device import RxccController, WirelessProRxController


class StubHendrixController:
    def __init__(
        self,
        battery_mv: int = 3775,
        command_response: bytes | None = None,
        serial_number: str = "TX008A1234",
    ) -> None:
        self.battery_mv = battery_mv
        self.temperature_c = 26
        self.charge_state = "0x01"
        self.charge_state_code = 1
        self.charge_current_ma = 300
        self.command_response = command_response
        self.serial_number = serial_number
        self.ctx_high: bool | None = None
        self.charging_enabled: bool | None = None
        self.flash_color_index: int | None = None
        self.rf_start_args: tuple[int, int] | None = None
        self.serial_number_read = False
        self.stop_rf_called = False
        self.last_written_reports: list[bytes] = []
        self.last_response: bytes | None = None

    def read_battery_mv(self) -> int:
        return self.battery_mv

    def read_battery_info(self):
        self.last_written_reports = [bytes([0x01, 0x61] + [0x00] * 15)]
        self.last_response = bytes([0x02, 0x61, ord("A"), 0xE4, 0x0E, 0x64, 0x00, 0x1A, 0x00, 0x01, 0x2C, 0x01])
        return type(
            "StubBatteryInfo",
            (),
            {
                "battery_mv": self.battery_mv,
                "temperature_c": self.temperature_c,
                "charge_state": self.charge_state,
                "charge_state_code": self.charge_state_code,
                "charge_current_ma": self.charge_current_ma,
            },
        )()

    def read_serial_number(self) -> str:
        encoded = self.serial_number.encode("ascii")
        self.serial_number_read = True
        self.last_written_reports = [
            bytes([13, 0x00, ord("N"), ord("O"), ord("R"), ord("D"), ord("I"), ord("C"), ord("_"), ord("I"), ord("D")] + [0x00] * 7 + [0x00] * 16)
        ]
        self.last_response = bytes([14, 0x00, ord("A")] + list(encoded) + [0x00] * (16 - len(encoded)) + [0x00] * 15)
        return self.serial_number

    def set_ctx(self, high: bool) -> int:
        self.ctx_high = high
        self.last_written_reports = [
            bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x01 if high else 0x00])
        ]
        self.last_response = self.command_response
        return 1

    def set_charging(self, enabled: bool) -> int:
        self.charging_enabled = enabled
        self.last_written_reports = [bytes([21, 0x55, 0x01 if enabled else 0x00])]
        self.last_response = self.command_response
        return 1

    def start_rf(self, channel: int, power: int) -> int:
        self.rf_start_args = (channel, power)
        self.last_written_reports = [bytes([0x0F, 0x03, 0x00, channel, 0x00, power])]
        self.last_response = self.command_response
        return 1

    def stop_rf(self) -> int:
        self.stop_rf_called = True
        self.last_written_reports = [bytes([0x0F, 0x0D, 0x00])]
        self.last_response = self.command_response
        return 1

    def flash_led(self, color_index: int) -> int:
        self.flash_color_index = color_index
        self.last_written_reports = [
            bytes([21, 0x4E, color_index, 0x01, 0xFF] + [0x00] * 12),
            bytes([21, 0x4E, color_index, 0x00, 0x00] + [0x00] * 12),
            bytes([21, 0x4E, color_index, 0x01, 0xFF] + [0x00] * 12),
            bytes([21, 0x4E, color_index, 0x00, 0x00] + [0x00] * 12),
        ]
        self.last_response = None
        return 4

    def turn_off_all_leds(self) -> int:
        self.flash_color_index = None
        self.last_written_reports = [
            bytes([21, 0x4E, 0x00, 0x00, 0x00] + [0x00] * 12),
            bytes([21, 0x4E, 0x01, 0x00, 0x00] + [0x00] * 12),
            bytes([21, 0x4E, 0x02, 0x00, 0x00] + [0x00] * 12),
            bytes([21, 0x4E, 0x03, 0x00, 0x00] + [0x00] * 12),
        ]
        self.last_response = None
        return 4

    def get_last_io_trace(self) -> tuple[list[bytes], bytes | None]:
        return list(self.last_written_reports), self.last_response


class RecordingRxccDevice:
    def __init__(self, reads: list[bytes] | None = None) -> None:
        self.writes: list[bytes] = []
        self.reads = list(reads or [])
        self.closed = False

    def write(self, data: bytes) -> int:
        self.writes.append(bytes(data))
        return len(data)

    def read(self, length: int, timeout_ms: int) -> bytes:
        if not self.reads:
            return b""
        return bytes(self.reads.pop(0))

    def close(self) -> None:
        self.closed = True


class RxccDeviceFactory:
    def __init__(self, reads: list[bytes] | None = None) -> None:
        self.devices: list[RecordingRxccDevice] = []
        self.reads = list(reads or [])

    def __call__(self) -> RecordingRxccDevice:
        device = RecordingRxccDevice(reads=self.reads)
        self.devices.append(device)
        return device


class AppStructureTest(unittest.TestCase):
    def test_expected_routes_exist(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        route_paths = {route.path for route in app.routes}

        self.assertIn("/", route_paths)
        self.assertIn("/devices/{device_type}", route_paths)
        self.assertIn("/health", route_paths)
        self.assertIn("/api/frontend/mode", route_paths)
        self.assertIn("/api/antenna", route_paths)
        self.assertIn("/api/rxcc/gpio/{pin}/{level}", route_paths)
        self.assertIn("/api/rf/start", route_paths)
        self.assertIn("/api/rf/start/rxcc/raw", route_paths)
        self.assertIn("/api/rf/start/wireless-pro-rx/raw", route_paths)
        self.assertIn("/api/rf/stop", route_paths)
        self.assertIn("/api/rf/stop/{device_type}", route_paths)
        self.assertIn("/api/battery/{device_type}", route_paths)
        self.assertIn("/api/serial-number/{device_type}", route_paths)
        self.assertIn("/api/ctx/{device_type}/{level}", route_paths)
        self.assertIn("/api/charging/{device_type}/{state}", route_paths)
        self.assertIn("/api/led/{device_type}/flash/{color}", route_paths)
        self.assertIn("/api/led/{device_type}/off/all", route_paths)
        self.assertIn("/api/devices/{device_type}/commands/{command}", route_paths)
        self.assertIn("/api/healthcheck", route_paths)
        self.assertIn("/api/test-command", route_paths)

    def test_root_defaults_to_rxcc_page(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        root_route = next(route for route in app.routes if route.path == "/")
        response = root_route.endpoint()

        self.assertEqual(response.status_code, 200)
        body = response.body.decode("utf-8")
        self.assertIn("RODE RXCC 008C", body)
        self.assertIn("Devices:", body)
        self.assertIn("RODE Wireless PRO RX 0058", body)
        self.assertIn("RXCC GPIO Guide: ports, pins, and mode presets", body)
        self.assertIn("15 14 0 2 pin level", body)
        self.assertIn("Transmitting PA Mode", body)
        self.assertIn("Bypass Mode", body)
        self.assertIn("Receiving Mode", body)
        self.assertIn("Signal", body)
        self.assertIn("CTX", body)
        self.assertIn("CPS", body)
        self.assertIn("CRX", body)
        self.assertIn("ANT_SEL", body)
        self.assertIn("/static/rxcc/GPIO-ports.png", body)
        self.assertIn("/static/rxcc/sky66112-mode-table.png", body)
        self.assertIn("/static/rxcc/antenna-paths.png", body)
        self.assertLess(body.index("/static/rxcc/GPIO-ports.png"), body.index("/static/rxcc/antenna-paths.png"))
        self.assertLess(body.index("/static/rxcc/antenna-paths.png"), body.index("/static/rxcc/sky66112-mode-table.png"))
        self.assertIn("data-gpio-pin=\"0\"", body)
        self.assertIn("data-gpio-pin=\"3\"", body)
        self.assertIn("name=\"antenna\"", body)
        self.assertIn("Start RF (Full)", body)
        self.assertIn("Start RF Only", body)
        self.assertLess(body.index("Start RF Only"), body.index("Start RF (Full)"))
        self.assertIn("Battery Voltage (mV)", body)
        self.assertIn("Temperature (C)", body)
        self.assertIn("Charge State", body)
        self.assertIn("Charge Current (mA)", body)
        self.assertIn("Read Battery", body)
        self.assertIn("Serial Number", body)
        self.assertIn("Read Serial Number", body)
        self.assertIn("Charging Control (Experimental)", body)
        self.assertIn("Enable Charging", body)
        self.assertIn("Disable Charging", body)
        self.assertEqual(body.count("value=\"40\""), 2)
        self.assertEqual(body.count("value=\"10\""), 2)

    def test_health_endpoint_reports_rxcc_alias_support(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        health_route = next(route for route in app.routes if route.path == "/health")
        request = Request({"type": "http", "app": app, "headers": [], "method": "GET", "path": "/health"})

        response = health_route.endpoint(request)

        self.assertEqual(response.vendor_id, "0x19F7 or 0x1A86")
        self.assertEqual(response.product_id, "0x008C or 0x8091")

    def test_tx_page_uses_tx_specific_template(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        device_route = next(route for route in app.routes if route.path == "/devices/{device_type}")
        response = device_route.endpoint("tx")

        self.assertEqual(response.status_code, 200)
        body = response.body.decode("utf-8")
        self.assertIn("<code>tx</code>", body)
        self.assertNotIn("Front-end Mode", body)
        self.assertNotIn("Antenna Path", body)
        self.assertNotIn("name=\"antenna\"", body)
        self.assertIn("Battery Voltage (mV)", body)
        self.assertIn("Temperature (C)", body)
        self.assertIn("Charge State", body)
        self.assertIn("Charge Current (mA)", body)
        self.assertIn("Read Battery", body)
        self.assertIn("Serial Number", body)
        self.assertIn("Read Serial Number", body)
        self.assertIn("CTX LOW", body)
        self.assertIn("CTX HIGH", body)
        self.assertIn("Enable Charging", body)
        self.assertIn("Disable Charging", body)
        self.assertIn("Flash LED Red (toggle)", body)
        self.assertIn("Flash LED Green (toggle)", body)
        self.assertIn("Turn Off All LEDs", body)
        self.assertLess(body.index("RF Start"), body.index("RF Stop"))

    def test_rx_page_uses_rx_specific_template(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        device_route = next(route for route in app.routes if route.path == "/devices/{device_type}")
        response = device_route.endpoint("rx")

        self.assertEqual(response.status_code, 200)
        body = response.body.decode("utf-8")
        self.assertIn("<code>rx</code>", body)
        self.assertIn("CTX LOW", body)
        self.assertIn("CTX HIGH", body)
        self.assertNotIn("Battery Voltage (mV)", body)

    def test_wireless_pro_rx_page_uses_rxcc_style_template(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        device_route = next(route for route in app.routes if route.path == "/devices/{device_type}")
        response = device_route.endpoint("wireless-pro-rx")

        self.assertEqual(response.status_code, 200)
        body = response.body.decode("utf-8")
        self.assertIn("RODE Wireless PRO RX 0058", body)
        self.assertIn("<code>wireless pro rx</code>", body)
        self.assertIn("PA always on", body)
        self.assertIn("wirepro_freq", body)
        self.assertIn("wirepro_power", body)
        self.assertIn("2478 MHz -> 78", body)
        self.assertIn("PCB antenna", body)
        self.assertIn("FPC antenna", body)
        self.assertIn("15 3 0 freq ant_id pwr", body)
        self.assertIn("/api/rf/start/wireless-pro-rx/raw", body)
        self.assertIn("Battery Voltage (mV)", body)
        self.assertIn("Temperature (C)", body)
        self.assertIn("Charge State", body)
        self.assertIn("Charge Current (mA)", body)
        self.assertIn("Read Battery", body)
        self.assertNotIn("Transmitting PA Mode", body)
        self.assertNotIn("Bypass Mode", body)
        self.assertNotIn("Receiving Mode", body)
        self.assertNotIn("data-gpio-pin", body)

    def test_test_command_page_renders_raw_command_form(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        device_route = next(route for route in app.routes if route.path == "/devices/{device_type}")
        response = device_route.endpoint("test-command")

        self.assertEqual(response.status_code, 200)
        body = response.body.decode("utf-8")
        self.assertIn("Test Command", body)
        self.assertIn("Space-separated decimal bytes", body)
        self.assertIn("value=\"15 13 0\"", body)
        self.assertIn("/api/test-command", body)
        self.assertIn("Response", body)

    def test_rxcc_frontend_mode_endpoint_formats_hendrix_command_byte(self) -> None:
        factory = RxccDeviceFactory()
        app = create_app(controller=RxccController(device_factory=factory, backend_name="test"))
        frontend_route = next(route for route in app.routes if route.path == "/api/frontend/mode")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/frontend/mode"})

        response = frontend_route.endpoint(FrontendModeRequest(mode=FrontendMode.TRANSMITTING_PA), request)

        self.assertEqual(response.command_sent, ["15 14 0 2 0 1", "15 14 0 2 1 0", "15 14 0 2 2 0"])
        self.assertEqual(
            factory.devices[0].writes,
            [
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x00, 0x01]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x01, 0x00]),
                bytes([0x0F, 0x0E, 0x00, 0x02, 0x02, 0x00]),
            ],
        )
        self.assertTrue(response.read_attempted)

    def test_rxcc_antenna_endpoint_sends_only_antenna_report(self) -> None:
        factory = RxccDeviceFactory()
        app = create_app(controller=RxccController(device_factory=factory, backend_name="test"))
        antenna_route = next(route for route in app.routes if route.path == "/api/antenna")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/antenna"})

        response = antenna_route.endpoint(AntennaRequest(path="secondary"), request)

        self.assertEqual(response.command_sent, ["15 14 0 2 3 1"])
        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x0E, 0x00, 0x02, 0x03, 0x01])])
        self.assertTrue(response.read_attempted)

    def test_rxcc_start_rf_endpoint_enforces_mode_then_antenna_then_start(self) -> None:
        factory = RxccDeviceFactory()
        app = create_app(controller=RxccController(device_factory=factory, backend_name="test"))
        start_route = next(route for route in app.routes if route.path == "/api/rf/start")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/rf/start"})

        response = start_route.endpoint(StartRfRequest(device="rxcc", antenna="main", channel=10, power=5), request)

        self.assertEqual(
            response.command_sent,
            ["15 14 0 2 0 1", "15 14 0 2 1 0", "15 14 0 2 2 0", "15 14 0 2 3 0", "15 3 0 10 0 5"],
        )
        self.assertEqual(
            response.detail,
            "Applied transmitting-pa mode, selected `main` antenna, and started RF on channel 10 at power 5.",
        )
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
        self.assertTrue(response.read_attempted)

    def test_rxcc_raw_start_rf_endpoint_sends_only_start_report(self) -> None:
        factory = RxccDeviceFactory()
        app = create_app(controller=RxccController(device_factory=factory, backend_name="test"))
        raw_start_route = next(route for route in app.routes if route.path == "/api/rf/start/rxcc/raw")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/rf/start/rxcc/raw"})

        response = raw_start_route.endpoint(DeviceCommandRequest(channel=10, power=5), request)

        self.assertEqual(response.command_sent, ["15 3 0 10 0 5"])
        self.assertEqual(response.detail, "Sent raw RXCC RF start on channel 10 at power 5.")
        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x03, 0x00, 10, 0x00, 5])])
        self.assertTrue(response.read_attempted)

    def test_rxcc_gpio_endpoint_returns_device_response(self) -> None:
        factory = RxccDeviceFactory(reads=[bytes([0xA5, 0x5A])])
        app = create_app(controller=RxccController(device_factory=factory, backend_name="test"))
        gpio_route = next(route for route in app.routes if route.path == "/api/rxcc/gpio/{pin}/{level}")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/rxcc/gpio/0/1"})

        response = gpio_route.endpoint(0, 1, request)

        self.assertEqual(response.command_sent, ["15 14 0 2 0 1"])
        self.assertEqual(response.device_response, "165 90")
        self.assertTrue(response.read_attempted)

    def test_test_command_endpoint_sends_raw_report_and_returns_response(self) -> None:
        factory = RxccDeviceFactory(reads=[bytes([0x10, 0xAA, 0x55])])
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        app.state.test_command_controller = RxccController(device_factory=factory, backend_name="test")
        raw_command_route = next(route for route in app.routes if route.path == "/api/test-command")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/test-command"})

        response = raw_command_route.endpoint(RawCommandRequest(command="15 13 0"), request)

        self.assertEqual(response.operation, "send_raw_command")
        self.assertEqual(response.command_sent, ["15 13 0"])
        self.assertEqual(response.device_response, "16 170 85")
        self.assertTrue(response.read_attempted)
        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x0D, 0x00])])

    def test_wireless_pro_rx_start_rf_endpoint_sends_single_embedded_antenna_command(self) -> None:
        factory = RxccDeviceFactory()
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        app.state.wireless_pro_rx_controller = WirelessProRxController(device_factory=factory, backend_name="test")
        start_route = next(route for route in app.routes if route.path == "/api/rf/start")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/rf/start"})

        response = start_route.endpoint(
            StartRfRequest(device="wireless-pro-rx", antenna="secondary", wirepro_freq=78, wirepro_power=-4),
            request,
        )

        self.assertEqual(
            response.command_sent,
            ["15 3 0 78 1 252"],
        )
        self.assertEqual(
            response.detail,
            "Sent RF start for `wireless-pro-rx` with wirepro_freq 78 using `secondary` antenna at wirepro_power -4 dBm.",
        )
        self.assertEqual(
            factory.devices[0].writes,
            [
                bytes([0x0F, 0x03, 0x00, 78, 0x01, 0xFC]),
            ],
        )
        self.assertTrue(response.read_attempted)

    def test_wireless_pro_rx_raw_start_endpoint_requires_antenna_and_sends_single_start_report(self) -> None:
        factory = RxccDeviceFactory()
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        app.state.wireless_pro_rx_controller = WirelessProRxController(device_factory=factory, backend_name="test")
        raw_start_route = next(route for route in app.routes if route.path == "/api/rf/start/wireless-pro-rx/raw")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/rf/start/wireless-pro-rx/raw"}
        )

        response = raw_start_route.endpoint(DeviceCommandRequest(antenna="main", wirepro_freq=78, wirepro_power=-4), request)

        self.assertEqual(response.command_sent, ["15 3 0 78 0 252"])
        self.assertEqual(
            response.detail,
            "Sent raw RF start for `wireless-pro-rx` with wirepro_freq 78 using `main` antenna at wirepro_power -4 dBm.",
        )
        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x03, 0x00, 78, 0x00, 0xFC])])
        self.assertTrue(response.read_attempted)

    def test_wireless_pro_rx_stop_rf_endpoint_returns_device_response_when_present(self) -> None:
        factory = RxccDeviceFactory(reads=[bytes([0x10, 0xAA, 0x55])])
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        app.state.wireless_pro_rx_controller = WirelessProRxController(device_factory=factory, backend_name="test")
        stop_route = next(route for route in app.routes if route.path == "/api/rf/stop/{device_type}")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/rf/stop/wireless-pro-rx"}
        )

        response = stop_route.endpoint("wireless-pro-rx", request)

        self.assertEqual(factory.devices[0].writes, [bytes([0x0F, 0x0D, 0x00])])
        self.assertEqual(response.command_sent, ["15 13 0"])
        self.assertEqual(response.device_response, "16 170 85")
        self.assertTrue(response.read_attempted)

    def test_tx_battery_endpoint_returns_battery_mv(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        app.state.tx_controller = StubHendrixController(battery_mv=3812)
        battery_route = next(route for route in app.routes if route.path == "/api/battery/{device_type}")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/battery/tx"})

        response = battery_route.endpoint("tx", request)

        self.assertEqual(response.device.value, "tx")
        self.assertEqual(response.battery_mv, 3812)
        self.assertEqual(response.temperature_c, 26)
        self.assertEqual(response.charge_state, "0x01")
        self.assertEqual(response.charge_state_code, 1)
        self.assertEqual(response.charge_current_ma, 300)
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["1 97 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"])
        self.assertEqual(response.device_response, "2 97 65 228 14 100 0 26 0 1 44 1")

    def test_rxcc_battery_endpoint_returns_battery_mv(self) -> None:
        factory = RxccDeviceFactory(reads=[bytes([0x02, 0x61, ord("A"), 0xB6, 0x0E, 0x64, 0x00, 0x1A, 0x00, 0x01, 0x2C, 0x01])])
        app = create_app(controller=RxccController(device_factory=factory, backend_name="test"))
        battery_route = next(route for route in app.routes if route.path == "/api/battery/{device_type}")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/battery/rxcc"})

        response = battery_route.endpoint("rxcc", request)

        self.assertEqual(response.device.value, "rxcc")
        self.assertEqual(response.battery_mv, 3766)
        self.assertEqual(response.temperature_c, 26)
        self.assertEqual(response.charge_state, "0x01")
        self.assertEqual(response.charge_state_code, 1)
        self.assertEqual(response.charge_current_ma, 300)
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["1 97 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"])
        self.assertEqual(response.device_response, "2 97 65 182 14 100 0 26 0 1 44 1")

    def test_tx_serial_number_endpoint_returns_serial_number(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController(serial_number="TXSN0001")
        app.state.tx_controller = stub_controller
        serial_route = next(route for route in app.routes if route.path == "/api/serial-number/{device_type}")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/serial-number/tx"}
        )

        response = serial_route.endpoint("tx", request)

        self.assertEqual(response.device.value, "tx")
        self.assertEqual(response.serial_number, "TXSN0001")
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["13 0 78 79 82 68 73 67 95 73 68 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"])
        self.assertEqual(response.device_response, "14 0 65 84 88 83 78 48 48 48 49 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0")
        self.assertTrue(stub_controller.serial_number_read)

    def test_rxcc_serial_number_endpoint_returns_serial_number(self) -> None:
        factory = RxccDeviceFactory(
            reads=[bytes([14, 0x00, ord("A"), ord("R"), ord("X"), ord("C"), ord("C"), ord("0"), ord("0"), ord("8"), ord("C")] + [0x00] * 23)]
        )
        app = create_app(controller=RxccController(device_factory=factory, backend_name="test"))
        serial_route = next(route for route in app.routes if route.path == "/api/serial-number/{device_type}")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/serial-number/rxcc"}
        )

        response = serial_route.endpoint("rxcc", request)

        self.assertEqual(response.device.value, "rxcc")
        self.assertEqual(response.serial_number, "RXCC008C")
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["13 0 78 79 82 68 73 67 95 73 68 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"])
        self.assertEqual(response.device_response, "14 0 65 82 88 67 67 48 48 56 67 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0")

    def test_wireless_pro_rx_battery_endpoint_returns_battery_mv(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        app.state.wireless_pro_rx_controller = StubHendrixController(battery_mv=3899)
        battery_route = next(route for route in app.routes if route.path == "/api/battery/{device_type}")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/battery/wireless-pro-rx"}
        )

        response = battery_route.endpoint("wireless-pro-rx", request)

        self.assertEqual(response.device.value, "wireless-pro-rx")
        self.assertEqual(response.battery_mv, 3899)
        self.assertEqual(response.temperature_c, 26)
        self.assertEqual(response.charge_state, "0x01")
        self.assertEqual(response.charge_state_code, 1)
        self.assertEqual(response.charge_current_ma, 300)
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["1 97 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"])
        self.assertEqual(response.device_response, "2 97 65 228 14 100 0 26 0 1 44 1")

    def test_tx_ctx_endpoint_sends_requested_level(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController()
        app.state.tx_controller = stub_controller
        ctx_route = next(route for route in app.routes if route.path == "/api/ctx/{device_type}/{level}")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/ctx/tx/low"})

        response = ctx_route.endpoint("tx", "low", request)

        self.assertEqual(response.operation, "set_ctx")
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["15 14 0 2 0 0"])
        self.assertIsNone(response.device_response)
        self.assertEqual(stub_controller.ctx_high, False)

    def test_rx_ctx_endpoint_sends_requested_level(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController()
        app.state.rx_controller = stub_controller
        ctx_route = next(route for route in app.routes if route.path == "/api/ctx/{device_type}/{level}")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/ctx/rx/high"})

        response = ctx_route.endpoint("rx", "high", request)

        self.assertEqual(response.operation, "set_ctx")
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["15 14 0 2 0 1"])
        self.assertIsNone(response.device_response)
        self.assertEqual(stub_controller.ctx_high, True)

    def test_rx_ctx_endpoint_returns_device_response_when_present(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController(command_response=bytes([0x10, 0xAA, 0x55]))
        app.state.rx_controller = stub_controller
        ctx_route = next(route for route in app.routes if route.path == "/api/ctx/{device_type}/{level}")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/ctx/rx/high"})

        response = ctx_route.endpoint("rx", "high", request)

        self.assertEqual(response.command_sent, ["15 14 0 2 0 1"])
        self.assertEqual(response.device_response, "16 170 85")
        self.assertTrue(response.read_attempted)

    def test_tx_charging_endpoint_sends_requested_state(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController()
        app.state.tx_controller = stub_controller
        charging_route = next(route for route in app.routes if route.path == "/api/charging/{device_type}/{state}")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/charging/tx/enable"}
        )

        response = charging_route.endpoint("tx", "enable", request)

        self.assertEqual(response.operation, "set_charging")
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["21 85 1"])
        self.assertIsNone(response.device_response)
        self.assertEqual(stub_controller.charging_enabled, True)

    def test_tx_charging_disable_endpoint_sends_requested_state(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController()
        app.state.tx_controller = stub_controller
        charging_route = next(route for route in app.routes if route.path == "/api/charging/{device_type}/{state}")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/charging/tx/disable"}
        )

        response = charging_route.endpoint("tx", "disable", request)

        self.assertEqual(response.operation, "set_charging")
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["21 85 0"])
        self.assertIsNone(response.device_response)
        self.assertEqual(stub_controller.charging_enabled, False)

    def test_rxcc_charging_endpoint_sends_requested_state(self) -> None:
        factory = RxccDeviceFactory()
        app = create_app(controller=RxccController(device_factory=factory, backend_name="test"))
        charging_route = next(route for route in app.routes if route.path == "/api/charging/{device_type}/{state}")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/charging/rxcc/enable"}
        )

        response = charging_route.endpoint("rxcc", "enable", request)

        self.assertEqual(response.operation, "set_charging")
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["21 85 1"])
        self.assertIsNone(response.device_response)
        self.assertTrue(response.read_attempted)
        self.assertEqual(factory.devices[0].writes, [bytes([21, 0x55, 0x01])])

    def test_rxcc_charging_disable_endpoint_sends_requested_state(self) -> None:
        factory = RxccDeviceFactory()
        app = create_app(controller=RxccController(device_factory=factory, backend_name="test"))
        charging_route = next(route for route in app.routes if route.path == "/api/charging/{device_type}/{state}")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/charging/rxcc/disable"}
        )

        response = charging_route.endpoint("rxcc", "disable", request)

        self.assertEqual(response.operation, "set_charging")
        self.assertEqual(response.reports_sent, 1)
        self.assertEqual(response.command_sent, ["21 85 0"])
        self.assertIsNone(response.device_response)
        self.assertTrue(response.read_attempted)
        self.assertEqual(factory.devices[0].writes, [bytes([21, 0x55, 0x00])])

    def test_rx_start_rf_endpoint_returns_device_response_when_present(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController(command_response=bytes([0x10, 0xAA, 0x55]))
        app.state.rx_controller = stub_controller
        start_route = next(route for route in app.routes if route.path == "/api/rf/start")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/rf/start"})

        response = start_route.endpoint(StartRfRequest(device="rx", channel=10, power=5), request)

        self.assertEqual(stub_controller.rf_start_args, (10, 5))
        self.assertEqual(response.command_sent, ["15 3 0 10 0 5"])
        self.assertEqual(response.device_response, "16 170 85")
        self.assertTrue(response.read_attempted)

    def test_rx_stop_rf_endpoint_returns_device_response_when_present(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController(command_response=bytes([0x10, 0xAA, 0x55]))
        app.state.rx_controller = stub_controller
        stop_route = next(route for route in app.routes if route.path == "/api/rf/stop/{device_type}")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/rf/stop/rx"})

        response = stop_route.endpoint("rx", request)

        self.assertTrue(stub_controller.stop_rf_called)
        self.assertEqual(response.command_sent, ["15 13 0"])
        self.assertEqual(response.device_response, "16 170 85")
        self.assertTrue(response.read_attempted)

    def test_tx_led_flash_endpoint_sends_red_flash_sequence(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController()
        app.state.tx_controller = stub_controller
        led_route = next(route for route in app.routes if route.path == "/api/led/{device_type}/flash/{color}")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/led/tx/flash/red"}
        )

        response = led_route.endpoint("tx", "red", request)

        self.assertEqual(response.operation, "flash_led")
        self.assertEqual(response.reports_sent, 4)
        self.assertEqual(stub_controller.flash_color_index, 0)
        self.assertEqual(
            response.command_sent,
            [
                "21 78 0 1 255 0 0 0 0 0 0 0 0 0 0 0 0",
                "21 78 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
                "21 78 0 1 255 0 0 0 0 0 0 0 0 0 0 0 0",
                "21 78 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
            ],
        )
        self.assertIsNone(response.device_response)

    def test_tx_led_off_endpoint_turns_off_all_leds(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController()
        app.state.tx_controller = stub_controller
        led_route = next(route for route in app.routes if route.path == "/api/led/{device_type}/off/all")
        request = Request(
            {"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/led/tx/off/all"}
        )

        response = led_route.endpoint("tx", request)

        self.assertEqual(response.operation, "turn_off_leds")
        self.assertEqual(response.reports_sent, 4)
        self.assertEqual(
            response.command_sent,
            [
                "21 78 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
                "21 78 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
                "21 78 2 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
                "21 78 3 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
            ],
        )
        self.assertIsNone(response.device_response)


if __name__ == "__main__":
    unittest.main()
