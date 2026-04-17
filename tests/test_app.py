import unittest

from fastapi import Request

from damspy_rpicontrol.main import create_app
from damspy_rpicontrol.rxcc_device import RxccController


class StubHendrixController:
    def __init__(self, battery_mv: int = 3775) -> None:
        self.battery_mv = battery_mv
        self.ctx_high: bool | None = None

    def read_battery_mv(self) -> int:
        return self.battery_mv

    def set_ctx(self, high: bool) -> int:
        self.ctx_high = high
        return 1


class AppStructureTest(unittest.TestCase):
    def test_expected_routes_exist(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        route_paths = {route.path for route in app.routes}

        self.assertIn("/", route_paths)
        self.assertIn("/devices/{device_type}", route_paths)
        self.assertIn("/health", route_paths)
        self.assertIn("/api/frontend/mode", route_paths)
        self.assertIn("/api/antenna", route_paths)
        self.assertIn("/api/rf/start", route_paths)
        self.assertIn("/api/rf/stop", route_paths)
        self.assertIn("/api/rf/stop/{device_type}", route_paths)
        self.assertIn("/api/battery/{device_type}", route_paths)
        self.assertIn("/api/ctx/{device_type}/{level}", route_paths)
        self.assertIn("/api/devices/{device_type}/commands/{command}", route_paths)
        self.assertIn("/api/healthcheck", route_paths)

    def test_root_defaults_to_rxcc_page(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        root_route = next(route for route in app.routes if route.path == "/")
        response = root_route.endpoint()

        self.assertEqual(response.status_code, 200)
        body = response.body.decode("utf-8")
        self.assertIn("RODE RXCC 008C", body)
        self.assertIn("Devices:", body)

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
        self.assertIn("Read Battery", body)
        self.assertIn("CTX LOW", body)
        self.assertIn("CTX HIGH", body)

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

    def test_tx_battery_endpoint_returns_battery_mv(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        app.state.tx_controller = StubHendrixController(battery_mv=3812)
        battery_route = next(route for route in app.routes if route.path == "/api/battery/{device_type}")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/battery/tx"})

        response = battery_route.endpoint("tx", request)

        self.assertEqual(response.device.value, "tx")
        self.assertEqual(response.battery_mv, 3812)
        self.assertEqual(response.reports_sent, 1)

    def test_tx_ctx_endpoint_sends_requested_level(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        stub_controller = StubHendrixController()
        app.state.tx_controller = stub_controller
        ctx_route = next(route for route in app.routes if route.path == "/api/ctx/{device_type}/{level}")
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST", "path": "/api/ctx/tx/low"})

        response = ctx_route.endpoint("tx", "low", request)

        self.assertEqual(response.operation, "set_ctx")
        self.assertEqual(response.reports_sent, 1)
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
        self.assertEqual(stub_controller.ctx_high, True)


if __name__ == "__main__":
    unittest.main()
