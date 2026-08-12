import struct
import unittest
from unittest.mock import patch

from damspy_rpicontrol.m5_transport import (
    DEFAULT_REQUEST_TIMEOUT_S,
    Frame,
    M5SerialHidTransport,
    M5TransportError,
    MessageType,
    RemoteDeviceInfo,
    Result,
    cobs_decode,
    crc16_ccitt_false,
    decode_frame,
    encode_frame,
)


class FakeSerial:
    def __init__(self, responder, chunk_size: int = 3) -> None:
        self.responder = responder
        self.chunk_size = chunk_size
        self.writes = bytearray()
        self.pending = bytearray()
        self.closed = False

    def write(self, data: bytes) -> int:
        self.writes.extend(data)
        while b"\x00" in self.writes:
            encoded, _, remainder = self.writes.partition(b"\x00")
            self.writes = bytearray(remainder)
            response = self.responder(decode_frame(bytes(encoded)))
            if response is not None:
                self.pending.extend(response)
        return len(data)

    def read(self, size: int = 1) -> bytes:
        amount = min(size, self.chunk_size, len(self.pending))
        result = bytes(self.pending[:amount])
        del self.pending[:amount]
        return result

    def close(self) -> None:
        self.closed = True


class M5TransportTest(unittest.TestCase):
    def test_non_read_operations_use_six_second_default_timeout(self) -> None:
        transport = M5SerialHidTransport("/dev/fake")

        self.assertEqual(DEFAULT_REQUEST_TIMEOUT_S, 6.0)
        self.assertEqual(transport.request_timeout_s, 6.0)

        with patch.object(
            transport,
            "request",
            return_value=bytes([Result.OK]) + struct.pack("<H", 3),
        ) as request:
            self.assertEqual(transport.device_factory().write(b"\x01\x02\x03"), 3)

        self.assertNotIn("timeout_s", request.call_args.kwargs)

    def test_read_uses_requested_timeout_plus_existing_margin(self) -> None:
        transport = M5SerialHidTransport("/dev/fake")

        with patch.object(
            transport,
            "request",
            return_value=bytes([Result.TIMEOUT]) + struct.pack("<H", 0),
        ) as request:
            self.assertEqual(transport.device_factory().read(64, 200), b"")

        self.assertAlmostEqual(request.call_args.kwargs["timeout_s"], 1.2)

    def test_crc16_ccitt_false_matches_reference_vector(self) -> None:
        self.assertEqual(crc16_ccitt_false(b"123456789"), 0x29B1)

    def test_frame_uses_canonical_inner_message_and_little_endian_crc(self) -> None:
        frame = Frame(MessageType.WRITE_REQUEST, 0x12345678, bytes([0x00, 0x0F, 0xFF]))

        encoded = encode_frame(frame)
        decoded_serial = cobs_decode(encoded[:-1])

        inner = bytes([0xD1, 0x01, 0x78, 0x56, 0x34, 0x12, 0x03, 0x00, 0x00, 0x0F, 0xFF])
        self.assertEqual(decoded_serial[:-2], inner)
        self.assertEqual(decoded_serial[-2:], struct.pack("<H", crc16_ccitt_false(inner)))
        self.assertEqual(decode_frame(encoded[:-1]), frame)

    def test_separate_write_and_read_use_canonical_bodies(self) -> None:
        requests = []

        def respond(frame):
            requests.append(frame)
            if frame.message_type == MessageType.WRITE_REQUEST:
                body = bytes([Result.OK]) + struct.pack("<H", len(frame.body))
                return encode_frame(Frame(MessageType.WRITE_RESPONSE, frame.request_id, body))
            data = bytes([0x10, 0xAA, 0x00, 0x55])
            body = bytes([Result.OK]) + struct.pack("<H", len(data)) + data
            return encode_frame(Frame(MessageType.READ_RESPONSE, frame.request_id, body))

        endpoint = FakeSerial(respond, chunk_size=1)
        transport = M5SerialHidTransport("/dev/fake", serial_factory=lambda _port, _baud: endpoint)
        device = transport.device_factory()

        written = device.write(bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]))
        response = device.read(64, 200)

        self.assertEqual(written, 6)
        self.assertEqual(response, bytes([0x10, 0xAA, 0x00, 0x55]))
        self.assertEqual([request.message_type for request in requests], [MessageType.WRITE_REQUEST, MessageType.READ_REQUEST])
        self.assertEqual(requests[0].body, bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]))
        self.assertEqual(requests[1].body, struct.pack("<HI", 64, 200))

    def test_correlated_remote_read_timeout_returns_empty_bytes(self) -> None:
        def respond(frame):
            body = bytes([Result.TIMEOUT]) + struct.pack("<H", 0)
            return encode_frame(Frame(MessageType.READ_RESPONSE, frame.request_id, body))

        transport = M5SerialHidTransport("/dev/fake", serial_factory=lambda _port, _baud: FakeSerial(respond))

        self.assertEqual(transport.device_factory().read(64, 200), b"")

    def test_no_correlated_response_raises_transport_timeout(self) -> None:
        endpoint = FakeSerial(lambda _frame: None)
        transport = M5SerialHidTransport(
            "/dev/fake", request_timeout_s=0.01, serial_factory=lambda _port, _baud: endpoint
        )

        with self.assertRaisesRegex(M5TransportError, "Timed out"):
            transport.get_remote_device_info()

    def test_recovery_defaults_only_for_stable_espressif_by_id_port(self) -> None:
        stable = (
            "/dev/serial/by-id/"
            "usb-Espressif_USB_JTAG_serial_debug_unit_11:22-if00"
        )

        self.assertTrue(M5SerialHidTransport(stable).recovery_enabled)
        self.assertFalse(M5SerialHidTransport("/dev/ttyACM0").recovery_enabled)
        self.assertFalse(M5SerialHidTransport("/dev/serial/by-id/usb-other").recovery_enabled)

    def test_status_timeout_resets_reopens_and_returns_verified_status(self) -> None:
        reset_ports = []
        endpoints = [
            FakeSerial(lambda _frame: None),
            FakeSerial(
                lambda frame: encode_frame(
                    Frame(
                        MessageType.STATUS_RESPONSE,
                        frame.request_id,
                        bytes([1, 1]) + struct.pack("<HH", 0x19F7, 0x0058),
                    )
                )
            ),
        ]

        transport = M5SerialHidTransport(
            "/tmp/fake-stick",
            request_timeout_s=0.01,
            serial_factory=lambda _port, _baud: endpoints.pop(0),
            stick_resetter=reset_ports.append,
            recovery_enabled=True,
        )

        with patch("damspy_rpicontrol.m5_transport.RECOVERY_BOOT_DELAY_S", 0), \
             patch("damspy_rpicontrol.m5_transport.Path.exists", return_value=True):
            info = transport.get_remote_device_info()

        self.assertEqual(reset_ports, ["/tmp/fake-stick"])
        self.assertTrue(info.hid_ready)
        self.assertEqual(info.product_id, 0x0058)

    def test_uncertain_write_is_not_retried_after_successful_recovery(self) -> None:
        first_requests = []
        recovery_requests = []

        def first_responder(frame):
            first_requests.append(frame)
            return None

        def recovery_responder(frame):
            recovery_requests.append(frame)
            return encode_frame(
                Frame(
                    MessageType.STATUS_RESPONSE,
                    frame.request_id,
                    bytes([1, 1]) + struct.pack("<HH", 0x19F7, 0x0058),
                )
            )

        endpoints = [FakeSerial(first_responder), FakeSerial(recovery_responder)]
        transport = M5SerialHidTransport(
            "/tmp/fake-stick",
            request_timeout_s=0.01,
            serial_factory=lambda _port, _baud: endpoints.pop(0),
            stick_resetter=lambda _port: None,
            recovery_enabled=True,
        )

        with patch("damspy_rpicontrol.m5_transport.RECOVERY_BOOT_DELAY_S", 0), \
             patch("damspy_rpicontrol.m5_transport.Path.exists", return_value=True):
            with self.assertRaisesRegex(M5TransportError, "outcome is uncertain"):
                transport.device_factory().write(b"\x0f\x0d\x00")

        self.assertEqual(
            [frame.message_type for frame in first_requests],
            [MessageType.WRITE_REQUEST],
        )
        self.assertEqual(
            [frame.message_type for frame in recovery_requests],
            [MessageType.STATUS_REQUEST],
        )

    def test_no_device_usb_error_busy_and_invalid_request_are_errors(self) -> None:
        for result in (Result.NO_DEVICE, Result.BUSY, Result.INVALID_REQUEST, Result.USB_ERROR):
            with self.subTest(result=result):
                def respond(frame, current_result=result):
                    body = bytes([current_result]) + struct.pack("<H", 0)
                    return encode_frame(Frame(MessageType.READ_RESPONSE, frame.request_id, body))

                transport = M5SerialHidTransport(
                    "/dev/fake", serial_factory=lambda _port, _baud: FakeSerial(respond)
                )
                with self.assertRaisesRegex(M5TransportError, result.name):
                    transport.device_factory().read(64, 200)

    def test_rejects_write_over_239_bytes_before_opening_serial(self) -> None:
        serial_opened = False

        def serial_factory(_port, _baud):
            nonlocal serial_opened
            serial_opened = True
            raise AssertionError("serial should not open")

        transport = M5SerialHidTransport("/dev/fake", serial_factory=serial_factory)

        with self.assertRaisesRegex(M5TransportError, "239-byte maximum"):
            transport.device_factory().write(bytes(240))
        self.assertFalse(serial_opened)

    def test_ignores_uncorrelated_response_before_matching_u32_request_id(self) -> None:
        def respond(frame):
            body = bytes([1, 1]) + struct.pack("<HH", 0x19F7, 0x008C)
            return (
                encode_frame(Frame(MessageType.STATUS_RESPONSE, frame.request_id + 1, body))
                + encode_frame(Frame(MessageType.STATUS_RESPONSE, frame.request_id, body))
            )

        transport = M5SerialHidTransport("/dev/fake", serial_factory=lambda _port, _baud: FakeSerial(respond))

        self.assertTrue(transport.get_remote_device_info().hid_ready)

    def test_status_response_reports_usb_hid_state(self) -> None:
        def respond(frame):
            body = bytes([1, 1]) + struct.pack("<HH", 0x19F7, 0x008C)
            return encode_frame(Frame(MessageType.STATUS_RESPONSE, frame.request_id, body))

        transport = M5SerialHidTransport("/dev/fake", serial_factory=lambda _port, _baud: FakeSerial(respond))

        self.assertEqual(
            transport.get_remote_device_info(),
            RemoteDeviceInfo(True, True, 0x19F7, 0x008C),
        )


if __name__ == "__main__":
    unittest.main()
