import unittest

from damspy_rpicontrol.main import create_app
from damspy_rpicontrol.rxcc_device import RxccController


class AppStructureTest(unittest.TestCase):
    def test_expected_routes_exist(self) -> None:
        app = create_app(controller=RxccController(device_factory=lambda: None, backend_name="test"))
        route_paths = {route.path for route in app.routes}

        self.assertIn("/", route_paths)
        self.assertIn("/health", route_paths)
        self.assertIn("/api/frontend/mode", route_paths)
        self.assertIn("/api/antenna", route_paths)
        self.assertIn("/api/rf/start", route_paths)
        self.assertIn("/api/rf/start/ch0", route_paths)
        self.assertIn("/api/rf/start/ch80", route_paths)
        self.assertIn("/api/rf/stop", route_paths)
        self.assertIn("/api/healthcheck", route_paths)


if __name__ == "__main__":
    unittest.main()
