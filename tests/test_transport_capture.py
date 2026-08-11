from __future__ import annotations

from datetime import datetime, timezone
import unittest
import json
from unittest.mock import patch


from damspy_rpicontrol.hendrix_device import HendrixController
from damspy_rpicontrol.main import create_app
from damspy_rpicontrol.models import TransportCaptureRequest
from damspy_rpicontrol.m5_transport import RemoteDeviceInfo
from damspy_rpicontrol.rxcc_device import RxccController
from damspy_rpicontrol.transport_capture import operation_matrix, run_transport_capture


BATTERY_RESPONSE = bytes([2, 97, 65, 0xB6, 0x0E, 100, 0, 26, 0, 1, 44, 1, 0, 0, 0, 0, 0])
SERIAL_RESPONSE = bytes([14, 0, 65]) + b"SERIAL01" + bytes(23)
COMMAND_RESPONSE = bytes([16, 0xAA, 0x55])


class SmartDevice:
    def __init__(self, writes: list[bytes]) -> None:
        self.writes = writes
        self.last_write = b""

    def write(self, data: bytes) -> int:
        self.last_write = bytes(data)
        self.writes.append(self.last_write)
        return len(data)

    def read(self, length: int, timeout_ms: int) -> bytes:
        if self.last_write[:2] == bytes([1, 97]):
            return BATTERY_RESPONSE
        if self.last_write[:2] == bytes([13, 0]):
            return SERIAL_RESPONSE
        return COMMAND_RESPONSE

    def close(self) -> None:
        return None


class SmartFactory:
    def __init__(self) -> None:
        self.writes: list[bytes] = []

    def __call__(self) -> SmartDevice:
        return SmartDevice(self.writes)


class FakeM5Transport:
    def __init__(self, port: str) -> None:
        self.port = port
        self.backend_name = f"fake-m5:{port}"
        self.factory = SmartFactory()
        self.status_calls = 0
        self.closed = False

    def device_factory(self) -> SmartDevice:
        return self.factory()

    def get_remote_device_info(self) -> RemoteDeviceInfo:
        self.status_calls += 1
        return RemoteDeviceInfo(True, True, 0x19F7, 0x008C)

    def close(self) -> None:
        self.closed = True


class EvidenceController:
    def __init__(self) -> None:
        self.current_writes: list[bytes] = []
        self.current_reads: list[bytes | None] = []
        self.calls: list[str] = []
        self.fail_ctx_high = True

    def _record(self, name: str, result=1, writes=None, reads=None):
        self.calls.append(name)
        self.current_writes = list(writes or [bytes([len(self.calls), 0xAA])])
        self.current_reads = list(reads if reads is not None else [bytes([0x10, len(self.calls)])])
        return result

    def get_last_io_events(self):
        return list(self.current_writes), list(self.current_reads)

    def read_battery_info(self):
        return self._record("read_battery", {"battery_mv": 3800})

    def read_serial_number(self):
        return self._record("read_serial_number", "SERIAL01")

    def set_charging(self, enabled):
        return self._record(f"charging:{enabled}")

    def set_ctx(self, high):
        self._record(f"ctx:{high}", writes=[b"\x0f\x0e", b"\x0f\x02"], reads=[None, b""])
        if high and self.fail_ctx_high:
            self.fail_ctx_high = False
            raise RuntimeError("injected failure")
        return 2

    def flash_led(self, color):
        return self._record(f"flash:{color}")

    def turn_off_all_leds(self):
        return self._record("leds_off")

    def stop_rf(self):
        return self._record("stop_rf")

    def start_rf(self, channel, power):
        return self._record(f"start_rf:{channel}:{power}")


class TestTransportCapture(unittest.TestCase):
    def test_operation_order_raw_boundaries_errors_continuation_and_cleanup(self) -> None:
        controller = EvidenceController()
        capture = run_transport_capture(
            "hendrix-tx",
            "usb",
            controller,
            {"connected": True, "hid_ready": True, "vid": 0x19F7, "pid": 0x008A, "name": "Hendrix TX"},
            None,
            now=datetime(2026, 8, 11, 18, 45, tzinfo=timezone.utc),
        )

        names = [item["operation"] for item in capture["operations"]]
        expected = [item[0] for item in operation_matrix("hendrix-tx", EvidenceController())[0]]
        assert names == expected
        failed = capture["operations"][4]
        assert failed["operation"] == "set_ctx"
        assert failed["writes"] == [
            {"bytes": [15, 14], "length": 2},
            {"bytes": [15, 2], "length": 2},
        ]
        assert failed["reads"] == [
            {"bytes": None, "length": None, "result": "none"},
            {"bytes": [], "length": 0, "result": "bytes"},
        ]
        assert "injected failure" in failed["error"]
        assert capture["operations"][5]["error"] is None
        assert capture["operations"][0]["parsed_result"] == {"battery_mv": 3800}
        assert [item["operation"] for item in capture["cleanup_operations"]] == [
            "stop_rf", "turn_off_all_leds", "set_charging"
        ]
        assert capture["download_filename"] == "hendrix_tx_usb_2026-08-11_184500.json"

    def test_controller_trace_preserves_multiple_writes_and_raw_read(self) -> None:
        factory = SmartFactory()
        controller = HendrixController(product_id=0x008A, device_factory=factory, backend_name="test")
        with patch("damspy_rpicontrol.hendrix_device.time.sleep", return_value=None):
            controller.flash_led(0)
        writes, reads = controller.get_last_io_events()
        assert len(writes) == 4
        assert writes[0] == bytes([21, 78, 0, 1, 255] + [0] * 12)
        assert writes[1] == bytes([21, 78, 0, 0, 0] + [0] * 12)
        assert reads == [COMMAND_RESPONSE]
        assert controller.get_last_hid_events() == [
            *([("write", report) for report in writes]),
            ("read", COMMAND_RESPONSE),
        ]

    def test_none_battery_response_is_preserved_without_inventing_bytes(self) -> None:
        class NoneDevice(SmartDevice):
            def read(self, length: int, timeout_ms: int):
                return None

        controller = HendrixController(
            product_id=0x008A,
            device_factory=lambda: NoneDevice([]),
            backend_name="test",
        )
        with patch("damspy_rpicontrol.hendrix_device.time.sleep", return_value=None):
            try:
                controller.read_battery_info()
            except Exception:
                pass
        assert controller.get_last_io_events()[1] == [None]

    def test_usb_api_uses_usb_controller_and_keeps_profile_and_identity_separate(self) -> None:
        m5_instances = []

        def m5_factory(port):
            transport = FakeM5Transport(port)
            m5_instances.append(transport)
            return transport

        app = create_app(
            controller=RxccController(device_factory=SmartFactory(), backend_name="usb"),
            m5_transport_factory=m5_factory,
            usb_identity_provider=lambda profile: {
                "connected": True, "hid_ready": True, "vid": 0x19F7, "pid": 0x008C, "name": "RODE RXCC"
            },
        )
        evidence = EvidenceController()
        app.state.usb_controllers["tx_via_rxcc_controller"] = evidence
        capture_route = next(route for route in app.routes if route.path == "/api/transport-capture")
        page_route = next(route for route in app.routes if route.path == "/diagnostics/transport-capture")
        body = capture_route.endpoint(TransportCaptureRequest(profile="hendrix-tx-via-rxcc", transport="usb"))
        page = page_route.endpoint()
        json.dumps(body)
        assert body["selected_profile"] == "hendrix-tx-via-rxcc"
        assert body["physical_usb_device"]["pid"] == 0x008C
        assert "mismatch" not in body
        assert not m5_instances
        assert page.status_code == 200 and b"Run Capture" in page.body
        assert b"Download JSON" in page.body
        assert body["download_filename"].endswith(".json")

    def test_m5_api_uses_existing_m5_transport_path_and_returns_json(self) -> None:
        instances: list[FakeM5Transport] = []

        def factory(port: str) -> FakeM5Transport:
            result = FakeM5Transport(port)
            instances.append(result)
            return result

        app = create_app(
            controller=RxccController(device_factory=SmartFactory(), backend_name="usb"),
            m5_transport_factory=factory,
        )
        capture_route = next(route for route in app.routes if route.path == "/api/transport-capture")
        with patch("damspy_rpicontrol.hendrix_device.time.sleep", return_value=None), patch(
            "damspy_rpicontrol.rxcc_device.time.sleep", return_value=None
        ):
            body = capture_route.endpoint(TransportCaptureRequest(profile="hendrix-rx", transport="m5"))
        json.dumps(body)
        assert body["transport"] == "m5"
        assert body["m5_serial_port"] == "/dev/ttyACM0"
        assert body["physical_usb_device"]["pid"] == 0x008C
        assert instances[0].status_calls == 1
        assert instances[0].factory.writes
        assert instances[0].closed is True
