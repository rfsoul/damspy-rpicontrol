import struct
import unittest
from unittest.mock import patch

from damspy_rpicontrol.m5_transport import (
    M5SerialHidTransport,
    M5TransportError,
    SURVEY_HOST_TIMEOUT_S,
    SURVEY_PROTOCOL_MAGIC,
    SURVEY_SET_REQUEST,
    SURVEY_SET_RESPONSE,
    cobs_decode,
    cobs_encode,
    crc16_ccitt_false,
    decode_survey_set_response,
    encode_survey_set_request,
)


def encode_survey_response(request_id: int, result: int = 0) -> bytes:
    inner = struct.pack(
        "<BBIHB",
        SURVEY_PROTOCOL_MAGIC,
        SURVEY_SET_RESPONSE,
        request_id,
        1,
        result,
    )
    return cobs_encode(inner + struct.pack("<H", crc16_ccitt_false(inner))) + b"\x00"


class SurveySerial:
    def __init__(self, responder) -> None:
        self.responder = responder
        self.pending = bytearray()
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> int:
        self.writes.append(bytes(data))
        response = self.responder(bytes(data))
        if response:
            self.pending.extend(response)
        return len(data)

    def read(self, size: int = 1) -> bytes:
        amount = min(size, len(self.pending))
        result = bytes(self.pending[:amount])
        del self.pending[:amount]
        return result

    def close(self) -> None:
        return None


class M5SurveyTest(unittest.TestCase):
    def test_exact_diagnostic_request_bytes_framing_and_crc(self) -> None:
        self.assertEqual(SURVEY_HOST_TIMEOUT_S, 6.0)
        encoded = encode_survey_set_request(0x12345678)
        decoded = cobs_decode(encoded[:-1])
        inner = bytes(
            [0xD2, 0x01, 0x78, 0x56, 0x34, 0x12, 0x01, 0x00, 0x01]
        )

        self.assertEqual(encoded[-1:], b"\x00")
        self.assertEqual(decoded[:-2], inner)
        self.assertEqual(decoded[-2:], struct.pack("<H", crc16_ccitt_false(inner)))

    def test_success_requires_correlated_response(self) -> None:
        def respond(request: bytes) -> bytes:
            decoded = cobs_decode(request[:-1])
            request_id = struct.unpack("<I", decoded[2:6])[0]
            return encode_survey_response(request_id + 1) + encode_survey_response(request_id)

        endpoint = SurveySerial(respond)
        transport = M5SerialHidTransport(
            "/dev/fake", serial_factory=lambda _port, _baud: endpoint
        )

        transport.start_standalone_survey()

        self.assertEqual(len(endpoint.writes), 1)

    def test_timeout_without_correlated_response(self) -> None:
        endpoint = SurveySerial(lambda _request: None)
        transport = M5SerialHidTransport(
            "/dev/fake", serial_factory=lambda _port, _baud: endpoint
        )

        with patch("damspy_rpicontrol.m5_transport.SURVEY_HOST_TIMEOUT_S", 0.01):
            with self.assertRaisesRegex(M5TransportError, "Timed out"):
                transport.start_standalone_survey()

    def test_malformed_response_is_transport_error(self) -> None:
        endpoint = SurveySerial(lambda _request: b"\x02\xD2\x00")
        transport = M5SerialHidTransport(
            "/dev/fake", serial_factory=lambda _port, _baud: endpoint
        )

        with self.assertRaisesRegex(M5TransportError, "invalid length"):
            transport.start_standalone_survey()

    def test_nonzero_result_is_transport_error(self) -> None:
        def respond(request: bytes) -> bytes:
            decoded = cobs_decode(request[:-1])
            request_id = struct.unpack("<I", decoded[2:6])[0]
            return encode_survey_response(request_id, result=3)

        transport = M5SerialHidTransport(
            "/dev/fake", serial_factory=lambda _port, _baud: SurveySerial(respond)
        )

        with self.assertRaisesRegex(M5TransportError, "result 0x03"):
            transport.start_standalone_survey()

    def test_diagnostic_decoder_rejects_bad_crc(self) -> None:
        response = bytearray(encode_survey_response(7))
        decoded = bytearray(cobs_decode(response[:-1]))
        decoded[-1] ^= 0xFF

        with self.assertRaisesRegex(M5TransportError, "CRC16"):
            decode_survey_set_response(cobs_encode(bytes(decoded)))


if __name__ == "__main__":
    unittest.main()
