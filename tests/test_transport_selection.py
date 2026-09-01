import unittest

from fastapi import HTTPException

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
        self.info = info or RemoteDeviceInfo(True, True, 0x19F7, 0x008C)
        self.pinged = False
        self.closed = False
        self.status_checks = 0

    def device_factory(self) -> FakeM5Device:
        return FakeM5Device()

    def ping(self) -> None:
        self.pinged = True

    def get_remote_device_info(self) -> RemoteDeviceInfo:
        self.status_checks += 1
        return self.info

    def close(self) -> None:
        self.closed = True


class TransportSelectionTest(unittest.TestCase):
    STICK_PORT = "/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_STICK-if00"

    def make_app(
        self,
        info: RemoteDeviceInfo | None = None,
        ports: list[str] | None = None,
    ):
        transports = []
        detected_ports = [self.STICK_PORT] if ports is None else ports

        def factory(port: str):
            transport = FakeM5Transport(port, info)
            transports.append(transport)
            return transport

        app = create_app(
            controller=RxccController(device_factory=lambda: FakeM5Device(), backend_name="test-usb"),
            m5_transport_factory=factory,
            m5_port_provider=lambda: detected_ports,
        )
        return app, transports

    def test_usb_is_default(self) -> None:
        app, _ = self.make_app()
        route = next(route for route in app.routes if route.path == "/api/transport" and "GET" in route.methods)

        status = route.endpoint()

        self.assertEqual(status.mode.value, "usb")
        self.assertEqual(status.serial_port, "/dev/ttyACM0")

    def test_web_ui_explains_both_rode_transport_paths(self) -> None:
        app, _ = self.make_app()
        root = next(route for route in app.routes if route.path == "/")

        body = root.endpoint().body.decode("utf-8")

        self.assertIn("RØDE transport", body)
        self.assertIn("Apply transport", body)
        self.assertIn('value="m5-proxy"', body)
        self.assertIn("USB path: this server", body)
        self.assertIn("validates the selected transport", body)

    def test_m5_selection_reuses_one_transport_without_vid_pid_gating(self) -> None:
        app, transports = self.make_app(RemoteDeviceInfo(True, True, 0x9999, 0x1234))
        route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)

        status = route.endpoint(TransportConfigRequest(mode="m5"))

        self.assertEqual(status.mode.value, "m5")
        self.assertTrue(status.connected)
        self.assertEqual(len(transports), 1)
        self.assertIs(app.state.m5_transport, transports[0])
        self.assertEqual(app.state.controller.backend_name, f"m5-serial:{self.STICK_PORT}")
        self.assertEqual(app.state.tx_controller.backend_name, f"m5-serial:{self.STICK_PORT}")
        self.assertEqual(app.state.controller.product_id, 0x008C)
        self.assertEqual(app.state.tx_controller.product_id, 0x008A)

    def test_m5_selection_does_not_contact_remote_node(self) -> None:
        app, transports = self.make_app()
        route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)

        status = route.endpoint(TransportConfigRequest(mode="m5"))

        self.assertTrue(status.connected)
        self.assertEqual(len(transports), 1)
        self.assertEqual(transports[0].status_checks, 0)
        self.assertIn("detected locally", status.detail)
        self.assertIn("has not been checked", status.detail)

    def test_m5_health_reports_known_remote_identity(self) -> None:
        app, _ = self.make_app(RemoteDeviceInfo(True, True, 0x19F7, 0x008C))
        select_route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)
        health_route = next(route for route in app.routes if route.path == "/api/healthcheck")
        select_route.endpoint(TransportConfigRequest(mode="m5"))

        response = health_route.endpoint()

        self.assertTrue(response.passed)
        self.assertTrue(response.connected)
        self.assertTrue(response.hid_ready)
        self.assertEqual(response.vendor_id, "0x19F7")
        self.assertEqual(response.product_id, "0x008C")
        self.assertEqual(response.device_name, "RODE RXCC")

    def test_remote_identity_mismatch_does_not_change_selected_controller(self) -> None:
        app, _ = self.make_app(RemoteDeviceInfo(True, True, 0x9999, 0x1234))
        select_route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)
        health_route = next(route for route in app.routes if route.path == "/api/healthcheck")
        select_route.endpoint(TransportConfigRequest(mode="m5"))

        response = health_route.endpoint()

        self.assertTrue(response.passed)
        self.assertIsNone(response.device_name)
        self.assertEqual(app.state.tx_controller.product_id, 0x008A)

    def test_m5_selection_reports_none_found(self) -> None:
        app, _ = self.make_app(ports=[])
        route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)

        with self.assertRaises(HTTPException) as raised:
            route.endpoint(TransportConfigRequest(mode="m5"))

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("No M5 Gateway candidate", raised.exception.detail)

    def test_m5_selection_reports_stick_plus_core_as_multiple(self) -> None:
        other = "/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_CORE-if00"
        app, transports = self.make_app(ports=[other, self.STICK_PORT])
        route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)

        with self.assertRaises(HTTPException) as raised:
            route.endpoint(TransportConfigRequest(mode="m5"))

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("Disconnect all but the intended Gateway", raised.exception.detail)
        self.assertEqual(transports, [])

    def test_m5_selection_reports_multiple_bridges(self) -> None:
        second = "/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_STICK2-if00"
        app, transports = self.make_app(ports=[self.STICK_PORT, second])
        route = next(route for route in app.routes if route.path == "/api/transport" and "PUT" in route.methods)

        with self.assertRaises(HTTPException) as raised:
            route.endpoint(TransportConfigRequest(mode="m5"))

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("Multiple M5 Gateway candidates", raised.exception.detail)
        self.assertEqual(transports, [])


if __name__ == "__main__":
    unittest.main()
