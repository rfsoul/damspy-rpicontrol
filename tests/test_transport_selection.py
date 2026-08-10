import unittest

from damspy_rpicontrol.m5_transport import RemoteDeviceInfo
from damspy_rpicontrol.main import create_app
from damspy_rpicontrol.models import TransportConfigRequest
from damspy_rpicontrol.rxcc_device import RxccController


class FakeM5Device:
    def write(self, data: bytes) -> int:
        return len(data)

    def read(self, length: int, timeout_ms: int) -> bytes:
        return b""

    def close(self) -> None:
        return None


class FakeM5Transport:
    def __init__(self, port: str, info: RemoteDeviceInfo | None = None) -> None:
        self.port = port
        self.backend_name = f"m5-serial:{port}"
        self.info = info or RemoteDeviceInfo(True, 0x19F7, 0x008C)
        self.pinged = False
        self.closed = False

    def device_factory(self) -> FakeM5Device:
        return FakeM5Device()

    def ping(self) -> None:
        self.pinged = True

    def get_remote_device_info(self) -> RemoteDeviceInfo:
        return self.info

    def close(self) -> None:
        self.closed = True


class TransportSelectionTest(unittest.TestCase):
    def make_app(self, info: RemoteDeviceInfo | None = None):
        transports = []

        def factory(port: str):
            transport = FakeM5Transport(port, info)
            transports.append(transport)
            return transport

        app = create_app(
            controller=RxccController(device_factory=lambda: FakeM5Device(), backend_name="test-usb"),
            m5_transport_factory=factory,
        )
        return app, transports

    def test_usb_is_default(self) -> None:
        app, _ = self.make_app()
        route = next(route for route in app.routes if route.path == "/api/transport" and "GET" in route.methods)

        status = route.endpoint()

        self.assertEqual(status.mode.value, "usb")
        self.assertEqual(status.serial_port, "/dev/ttyACM0")

    def test_m5_selection_reuses_one_transport_without_vid_pid_gating(self) -> None:
        app, transports = self.make_app(RemoteDeviceInfo(True, 0x9999, 0x1234))
        route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)

        status = route.endpoint(TransportConfigRequest(mode="m5", serial_port="/dev/ttyACM7"))

        self.assertEqual(status.mode.value, "m5")
        self.assertTrue(status.connected)
        self.assertEqual(len(transports), 1)
        self.assertIs(app.state.m5_transport, transports[0])
        self.assertEqual(app.state.controller.backend_name, "m5-serial:/dev/ttyACM7")
        self.assertEqual(app.state.tx_controller.backend_name, "m5-serial:/dev/ttyACM7")
        self.assertEqual(app.state.controller.product_id, 0x008C)
        self.assertEqual(app.state.tx_controller.product_id, 0x008A)

    def test_m5_health_reports_known_remote_identity(self) -> None:
        app, _ = self.make_app(RemoteDeviceInfo(True, 0x19F7, 0x008C))
        select_route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)
        health_route = next(route for route in app.routes if route.path == "/api/healthcheck")
        select_route.endpoint(TransportConfigRequest(mode="m5", serial_port="/dev/ttyACM0"))

        response = health_route.endpoint()

        self.assertTrue(response.passed)
        self.assertTrue(response.connected)
        self.assertEqual(response.vendor_id, "0x19F7")
        self.assertEqual(response.product_id, "0x008C")
        self.assertEqual(response.device_name, "RODE RXCC")

    def test_remote_identity_mismatch_does_not_change_selected_controller(self) -> None:
        app, _ = self.make_app(RemoteDeviceInfo(True, 0x9999, 0x1234))
        select_route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)
        health_route = next(route for route in app.routes if route.path == "/api/healthcheck")
        select_route.endpoint(TransportConfigRequest(mode="m5", serial_port="/dev/ttyACM0"))

        response = health_route.endpoint()

        self.assertTrue(response.passed)
        self.assertIsNone(response.device_name)
        self.assertEqual(app.state.tx_controller.product_id, 0x008A)


if __name__ == "__main__":
    unittest.main()
