import struct
import unittest

from damspy_rpicontrol.m5_transport import (
    Frame,
    M5SerialHidTransport,
    M5TransportError,
    MessageType,
    RemoteDeviceInfo,
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
    def test_frame_round_trip_preserves_zero_and_opaque_hid_bytes(self) -> None:
        frame = Frame(MessageType.WRITE_REQUEST, 42, bytes([0x00, 0x0F, 0xFF, 0x00, 0x55]))

        decoded = decode_frame(encode_frame(frame)[:-1])

        self.assertEqual(decoded, frame)

    def test_separate_write_and_read_requests_survive_fragmented_serial_reads(self) -> None:
        requests = []

        def respond(frame):
            requests.append(frame)
            if frame.message_type == MessageType.WRITE_REQUEST:
                return encode_frame(Frame(MessageType.WRITE_RESPONSE, frame.transaction_id, struct.pack("<H", len(frame.payload))))
            return encode_frame(Frame(MessageType.READ_RESPONSE, frame.transaction_id, bytes([0x10, 0xAA, 0x00, 0x55])))

        endpoint = FakeSerial(respond, chunk_size=1)
        transport = M5SerialHidTransport("/dev/fake", serial_factory=lambda _port, _baud: endpoint)
        device = transport.device_factory()

        written = device.write(bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]))
        response = device.read(64, 200)

        self.assertEqual(written, 6)
        self.assertEqual(response, bytes([0x10, 0xAA, 0x00, 0x55]))
        self.assertEqual([request.message_type for request in requests], [MessageType.WRITE_REQUEST, MessageType.READ_REQUEST])
        self.assertEqual(requests[0].payload, bytes([0x0F, 0x03, 0x00, 10, 0x00, 5]))
        self.assertEqual(requests[1].payload, struct.pack("<HI", 64, 200))

    def test_ignores_unrelated_transaction_before_correlated_response(self) -> None:
        def respond(frame):
            return (
                encode_frame(Frame(MessageType.PING_RESPONSE, frame.transaction_id + 1))
                + encode_frame(Frame(MessageType.PING_RESPONSE, frame.transaction_id))
            )

        transport = M5SerialHidTransport("/dev/fake", serial_factory=lambda _port, _baud: FakeSerial(respond))

        transport.ping()

    def test_remote_device_info_is_diagnostic_data(self) -> None:
        def respond(frame):
            payload = bytes([1]) + struct.pack("<HH", 0x19F7, 0x008C)
            return encode_frame(Frame(MessageType.DEVICE_INFO_RESPONSE, frame.transaction_id, payload))

        transport = M5SerialHidTransport("/dev/fake", serial_factory=lambda _port, _baud: FakeSerial(respond))

        self.assertEqual(transport.get_remote_device_info(), RemoteDeviceInfo(True, 0x19F7, 0x008C))

    def test_remote_error_surfaces_cleanly(self) -> None:
        def respond(frame):
            return encode_frame(Frame(MessageType.ERROR_RESPONSE, frame.transaction_id, b"Core HID disconnected"))

        transport = M5SerialHidTransport("/dev/fake", serial_factory=lambda _port, _baud: FakeSerial(respond))

        with self.assertRaisesRegex(M5TransportError, "Core HID disconnected"):
            transport.device_factory().read(64, 200)

    def test_timeout_when_no_correlated_response_arrives(self) -> None:
        endpoint = FakeSerial(lambda _frame: None)
        transport = M5SerialHidTransport(
            "/dev/fake",
            request_timeout_s=0.01,
            serial_factory=lambda _port, _baud: endpoint,
        )

        with self.assertRaisesRegex(M5TransportError, "Timed out"):
            transport.ping()


if __name__ == "__main__":
    unittest.main()
