import unittest

from fastapi import HTTPException

from damspy_rpicontrol.m5_transport import M5TransportError, RemoteDeviceInfo
from damspy_rpicontrol.main import create_app
from damspy_rpicontrol.models import TransportConfigRequest
from damspy_rpicontrol.rxcc_device import RxccController


class FakeDevice:
    def write(self, data: bytes) -> int:
        return len(data)

    def read(self, length: int, timeout_ms: int) -> bytes:
        return b""

    def close(self) -> None:
        return None


class FakeSurveyTransport:
    backend_name = "m5-serial:/dev/fake"

    def __init__(self, port: str, error: M5TransportError | None = None) -> None:
        self.port = port
        self.error = error
        self.survey_started = False

    def device_factory(self) -> FakeDevice:
        return FakeDevice()

    def get_remote_device_info(self) -> RemoteDeviceInfo:
        return RemoteDeviceInfo(True, True, 0x19F7, 0x008C)

    def start_standalone_survey(self) -> None:
        if self.error:
            raise self.error
        self.survey_started = True

    def close(self) -> None:
        return None


class SurveyEndpointTest(unittest.TestCase):
    def make_app(self, error: M5TransportError | None = None):
        transports = []

        def factory(port: str):
            transport = FakeSurveyTransport(port, error)
            transports.append(transport)
            return transport

        app = create_app(
            controller=RxccController(device_factory=FakeDevice, backend_name="test"),
            m5_transport_factory=factory,
        )
        return app, transports

    def test_success_confirms_response_was_received_before_survey_loop(self) -> None:
        app, transports = self.make_app()
        select = next(
            route for route in app.routes
            if route.path == "/api/transport" and "PUT" in route.methods
        )
        survey = next(route for route in app.routes if route.path == "/api/m5/survey/start")
        select.endpoint(TransportConfigRequest(mode="m5", serial_port="/dev/ttyACM0"))

        response = survey.endpoint()

        self.assertTrue(transports[0].survey_started)
        self.assertIn("disconnect the Stick", response.detail)
        self.assertIn("Reset the Stick", response.detail)
        self.assertEqual(response.operation, "start_standalone_range_survey")
        self.assertFalse(app.state.transport_connected)

    def test_failure_says_to_keep_stick_connected(self) -> None:
        app, _ = self.make_app(M5TransportError("bad response"))
        select = next(
            route for route in app.routes
            if route.path == "/api/transport" and "PUT" in route.methods
        )
        survey = next(route for route in app.routes if route.path == "/api/m5/survey/start")
        select.endpoint(TransportConfigRequest(mode="m5", serial_port="/dev/ttyACM0"))

        with self.assertRaises(HTTPException) as caught:
            survey.endpoint()

        self.assertEqual(caught.exception.status_code, 502)
        self.assertIn("Keep the Stick connected", caught.exception.detail)
        self.assertIn("not intentionally stopped", caught.exception.detail)
        self.assertTrue(app.state.transport_connected)

    def test_web_ui_contains_survey_control_and_warning(self) -> None:
        app, _ = self.make_app()
        root = next(route for route in app.routes if route.path == "/")

        body = root.endpoint().body.decode("utf-8")

        self.assertIn("Start Standalone Range Survey", body)
        self.assertIn("stops normal HID control until the Stick is reset", body)
        self.assertIn("/static/transport.js", body)

    def test_requires_applied_m5_connection(self) -> None:
        app, _ = self.make_app()
        survey = next(route for route in app.routes if route.path == "/api/m5/survey/start")

        with self.assertRaises(HTTPException) as caught:
            survey.endpoint()

        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("Select and apply the M5 connection first", caught.exception.detail)


if __name__ == "__main__":
    unittest.main()
