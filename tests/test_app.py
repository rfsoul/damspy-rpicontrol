import unittest

from damspy_rpicontrol.main import create_app
from damspy_rpicontrol.rxcc_device import RxccController


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


if __name__ == "__main__":
    unittest.main()
