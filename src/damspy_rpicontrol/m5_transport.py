from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import threading
import time
from typing import Callable, Protocol


PROTOCOL_MAGIC = 0xD1
DEFAULT_BAUD_RATE = 115200
DEFAULT_REQUEST_TIMEOUT_S = 6.0
READ_TRANSPORT_MARGIN_S = 1.0
MAX_BODY_LENGTH = 242
MAX_HID_PAYLOAD_LENGTH = 239


class M5TransportError(RuntimeError):
    """Raised when the serial HID tunnel cannot complete an operation."""


class MessageType(IntEnum):
    WRITE_REQUEST = 0x01
    WRITE_RESPONSE = 0x02
    READ_REQUEST = 0x03
    READ_RESPONSE = 0x04
    STATUS_REQUEST = 0x05
    STATUS_RESPONSE = 0x06


class Result(IntEnum):
    OK = 0x00
    TIMEOUT = 0x01
    NO_DEVICE = 0x02
    BUSY = 0x03
    INVALID_REQUEST = 0x04
    USB_ERROR = 0x05


@dataclass(frozen=True)
class Frame:
    message_type: MessageType
    request_id: int
    body: bytes = b""


@dataclass(frozen=True)
class RemoteDeviceInfo:
    connected: bool
    hid_ready: bool
    vendor_id: int | None = None
    product_id: int | None = None


class SerialEndpoint(Protocol):
    def write(self, data: bytes) -> int | None: ...

    def read(self, size: int = 1) -> bytes: ...

    def close(self) -> None: ...


SerialFactory = Callable[[str, int], SerialEndpoint]


def cobs_encode(data: bytes) -> bytes:
    output = bytearray([0])
    code_index = 0
    code = 1
    for byte in data:
        if byte == 0:
            output[code_index] = code
            code_index = len(output)
            output.append(0)
            code = 1
        else:
            output.append(byte)
            code += 1
            if code == 0xFF:
                output[code_index] = code
                code_index = len(output)
                output.append(0)
                code = 1
    output[code_index] = code
    return bytes(output)


def cobs_decode(data: bytes) -> bytes:
    if not data:
        raise M5TransportError("Received an empty COBS frame.")
    output = bytearray()
    index = 0
    while index < len(data):
        code = data[index]
        if code == 0:
            raise M5TransportError("COBS frame contains an unexpected zero byte.")
        index += 1
        end = index + code - 1
        if end > len(data):
            raise M5TransportError("COBS frame is truncated.")
        output.extend(data[index:end])
        index = end
        if code != 0xFF and index < len(data):
            output.append(0)
    return bytes(output)


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def encode_frame(frame: Frame) -> bytes:
    body = bytes(frame.body)
    if len(body) > MAX_BODY_LENGTH:
        raise M5TransportError(f"M5 body exceeds {MAX_BODY_LENGTH} bytes.")
    inner = struct.pack(
        "<BBIH",
        PROTOCOL_MAGIC,
        int(frame.message_type),
        frame.request_id,
        len(body),
    ) + body
    crc = struct.pack("<H", crc16_ccitt_false(inner))
    return cobs_encode(inner + crc) + b"\x00"


def decode_frame(encoded: bytes) -> Frame:
    decoded = cobs_decode(encoded)
    if len(decoded) < 10:
        raise M5TransportError("M5 frame is too short.")
    magic, raw_type, request_id, body_length = struct.unpack("<BBIH", decoded[:8])
    if magic != PROTOCOL_MAGIC:
        raise M5TransportError(f"Invalid M5 protocol magic 0x{magic:02X}.")
    if body_length > MAX_BODY_LENGTH or len(decoded) != 8 + body_length + 2:
        raise M5TransportError("M5 frame body length is invalid.")
    expected_crc = struct.unpack("<H", decoded[-2:])[0]
    if expected_crc != crc16_ccitt_false(decoded[:-2]):
        raise M5TransportError("M5 frame CRC16 check failed.")
    try:
        message_type = MessageType(raw_type)
    except ValueError as exc:
        raise M5TransportError(f"Unknown M5 message type {raw_type}.") from exc
    return Frame(message_type, request_id, decoded[8:-2])


def _decode_result(raw_result: int, operation: str) -> Result:
    try:
        return Result(raw_result)
    except ValueError as exc:
        raise M5TransportError(
            f"M5 {operation} response has unknown result 0x{raw_result:02X}."
        ) from exc


class M5SerialHidDevice:
    def __init__(self, transport: "M5SerialHidTransport") -> None:
        self._transport = transport

    def write(self, data: bytes) -> int:
        report = bytes(data)
        if not report:
            raise M5TransportError("M5 HID writes must not be empty.")
        if len(report) > MAX_HID_PAYLOAD_LENGTH:
            raise M5TransportError(
                f"M5 HID write exceeds the {MAX_HID_PAYLOAD_LENGTH}-byte maximum."
            )
        response = self._transport.request(
            MessageType.WRITE_REQUEST,
            report,
            MessageType.WRITE_RESPONSE,
        )
        if len(response) != 3:
            raise M5TransportError("M5 write response has an invalid length.")
        result = _decode_result(response[0], "write")
        bytes_written = struct.unpack("<H", response[1:])[0]
        if result != Result.OK:
            raise M5TransportError(f"M5 HID write failed: {result.name}.")
        return bytes_written

    def read(self, length: int, timeout_ms: int) -> bytes:
        if length <= 0 or length > MAX_HID_PAYLOAD_LENGTH or timeout_ms <= 0:
            raise M5TransportError("M5 HID read parameters are invalid.")
        response = self._transport.request(
            MessageType.READ_REQUEST,
            struct.pack("<HI", length, timeout_ms),
            MessageType.READ_RESPONSE,
            timeout_s=(timeout_ms / 1000) + READ_TRANSPORT_MARGIN_S,
        )
        if len(response) < 3:
            raise M5TransportError("M5 read response is too short.")
        result = _decode_result(response[0], "read")
        response_length = struct.unpack("<H", response[1:3])[0]
        if len(response) != 3 + response_length or response_length > length:
            raise M5TransportError("M5 read response length is invalid.")
        if result == Result.TIMEOUT:
            if response_length != 0:
                raise M5TransportError("M5 timed-out read included unexpected HID data.")
            return b""
        if result != Result.OK:
            raise M5TransportError(f"M5 HID read failed: {result.name}.")
        return response[3:]

    def close(self) -> None:
        # The shared serial connection remains open across controller operations.
        return None


class M5SerialHidTransport:
    def __init__(
        self,
        port: str,
        baud_rate: int = DEFAULT_BAUD_RATE,
        request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S,
        serial_factory: SerialFactory | None = None,
    ) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.request_timeout_s = request_timeout_s
        self._serial_factory = serial_factory or self._default_serial_factory
        self._serial: SerialEndpoint | None = None
        self._lock = threading.Lock()
        self._receive_buffer = bytearray()
        self._next_request_id = 1

    @property
    def backend_name(self) -> str:
        return f"m5-serial:{self.port}"

    def device_factory(self) -> M5SerialHidDevice:
        return M5SerialHidDevice(self)

    def get_remote_device_info(self) -> RemoteDeviceInfo:
        body = self.request(
            MessageType.STATUS_REQUEST,
            b"",
            MessageType.STATUS_RESPONSE,
        )
        if len(body) != 6 or body[0] not in {0, 1} or body[1] not in {0, 1}:
            raise M5TransportError("M5 status response has an invalid body.")
        vendor_id, product_id = struct.unpack("<HH", body[2:])
        connected = body[0] == 1
        hid_ready = body[1] == 1
        return RemoteDeviceInfo(
            connected,
            hid_ready,
            vendor_id,
            product_id,
        )

    def request(
        self,
        message_type: MessageType,
        body: bytes,
        expected_response_type: MessageType,
        timeout_s: float | None = None,
    ) -> bytes:
        with self._lock:
            request_id = self._allocate_request_id()
            endpoint = self._ensure_serial()
            self._write_all(endpoint, encode_frame(Frame(message_type, request_id, body)))
            deadline = time.monotonic() + (timeout_s or self.request_timeout_s)
            while True:
                frame = self._read_frame(endpoint, deadline)
                if frame.request_id != request_id:
                    continue
                if frame.message_type != expected_response_type:
                    raise M5TransportError(
                        f"Unexpected M5 response type {frame.message_type.name}; "
                        f"expected {expected_response_type.name}."
                    )
                return frame.body

    def close(self) -> None:
        with self._lock:
            if self._serial is not None:
                try:
                    self._serial.close()
                finally:
                    self._serial = None
                    self._receive_buffer.clear()

    def _allocate_request_id(self) -> int:
        request_id = self._next_request_id
        self._next_request_id = 1 if request_id == 0xFFFFFFFF else request_id + 1
        return request_id

    def _ensure_serial(self) -> SerialEndpoint:
        if self._serial is None:
            try:
                self._serial = self._serial_factory(self.port, self.baud_rate)
            except Exception as exc:
                raise M5TransportError(f"Unable to open M5 serial port {self.port} ({exc}).") from exc
        return self._serial

    def _write_all(self, endpoint: SerialEndpoint, data: bytes) -> None:
        offset = 0
        try:
            while offset < len(data):
                written = endpoint.write(data[offset:])
                if written is None:
                    written = len(data) - offset
                if written <= 0:
                    raise M5TransportError("M5 serial write returned no progress.")
                offset += written
        except M5TransportError:
            raise
        except Exception as exc:
            raise M5TransportError(f"Failed writing to M5 serial port {self.port} ({exc}).") from exc

    def _read_frame(self, endpoint: SerialEndpoint, deadline: float) -> Frame:
        while time.monotonic() < deadline:
            delimiter = self._receive_buffer.find(0)
            if delimiter >= 0:
                encoded = bytes(self._receive_buffer[:delimiter])
                del self._receive_buffer[: delimiter + 1]
                if not encoded:
                    continue
                try:
                    return decode_frame(encoded)
                except M5TransportError:
                    # A delimiter gives us a clean resynchronisation point.
                    continue
            try:
                chunk = endpoint.read(256)
            except Exception as exc:
                raise M5TransportError(f"Failed reading M5 serial port {self.port} ({exc}).") from exc
            if chunk:
                self._receive_buffer.extend(chunk)
                if len(self._receive_buffer) > MAX_BODY_LENGTH + 32:
                    self._receive_buffer.clear()
            else:
                time.sleep(0.001)
        raise M5TransportError(f"Timed out waiting for an M5 response on {self.port}.")

    @staticmethod
    def _default_serial_factory(port: str, baud_rate: int) -> SerialEndpoint:
        try:
            import serial
        except ImportError as exc:
            raise M5TransportError("pyserial is not installed.") from exc
        return serial.Serial(port=port, baudrate=baud_rate, timeout=0.05, write_timeout=1.0)
