from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import threading
import time
from typing import Callable, Protocol
import zlib


PROTOCOL_VERSION = 1
DEFAULT_BAUD_RATE = 115200
DEFAULT_REQUEST_TIMEOUT_S = 1.5
MAX_PAYLOAD_LENGTH = 4096


class M5TransportError(RuntimeError):
    """Raised when the serial HID tunnel cannot complete an operation."""


class MessageType(IntEnum):
    PING_REQUEST = 1
    PING_RESPONSE = 2
    WRITE_REQUEST = 3
    WRITE_RESPONSE = 4
    READ_REQUEST = 5
    READ_RESPONSE = 6
    DEVICE_INFO_REQUEST = 7
    DEVICE_INFO_RESPONSE = 8
    ERROR_RESPONSE = 255


@dataclass(frozen=True)
class Frame:
    message_type: MessageType
    transaction_id: int
    payload: bytes = b""


@dataclass(frozen=True)
class RemoteDeviceInfo:
    connected: bool
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


def encode_frame(frame: Frame) -> bytes:
    payload = bytes(frame.payload)
    if len(payload) > MAX_PAYLOAD_LENGTH:
        raise M5TransportError(f"M5 payload exceeds {MAX_PAYLOAD_LENGTH} bytes.")
    header = struct.pack(
        "<BBHH",
        PROTOCOL_VERSION,
        int(frame.message_type),
        frame.transaction_id,
        len(payload),
    )
    body = header + payload
    checksum = struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)
    return cobs_encode(body + checksum) + b"\x00"


def decode_frame(encoded: bytes) -> Frame:
    decoded = cobs_decode(encoded)
    if len(decoded) < 10:
        raise M5TransportError("M5 frame is too short.")
    version, raw_type, transaction_id, payload_length = struct.unpack("<BBHH", decoded[:6])
    if version != PROTOCOL_VERSION:
        raise M5TransportError(f"Unsupported M5 protocol version {version}.")
    if payload_length > MAX_PAYLOAD_LENGTH or len(decoded) != 6 + payload_length + 4:
        raise M5TransportError("M5 frame payload length is invalid.")
    expected_crc = struct.unpack("<I", decoded[-4:])[0]
    actual_crc = zlib.crc32(decoded[:-4]) & 0xFFFFFFFF
    if expected_crc != actual_crc:
        raise M5TransportError("M5 frame CRC check failed.")
    try:
        message_type = MessageType(raw_type)
    except ValueError as exc:
        raise M5TransportError(f"Unknown M5 message type {raw_type}.") from exc
    return Frame(message_type, transaction_id, decoded[6:-4])


class M5SerialHidDevice:
    def __init__(self, transport: "M5SerialHidTransport") -> None:
        self._transport = transport

    def write(self, data: bytes) -> int:
        response = self._transport.request(MessageType.WRITE_REQUEST, bytes(data), MessageType.WRITE_RESPONSE)
        if not response:
            return len(data)
        if len(response) != 2:
            raise M5TransportError("M5 write response has an invalid length.")
        return struct.unpack("<H", response)[0]

    def read(self, length: int, timeout_ms: int) -> bytes:
        payload = struct.pack("<HI", length, timeout_ms)
        return self._transport.request(MessageType.READ_REQUEST, payload, MessageType.READ_RESPONSE)

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
        self._next_transaction_id = 1

    @property
    def backend_name(self) -> str:
        return f"m5-serial:{self.port}"

    def device_factory(self) -> M5SerialHidDevice:
        return M5SerialHidDevice(self)

    def ping(self) -> None:
        self.request(MessageType.PING_REQUEST, b"", MessageType.PING_RESPONSE)

    def get_remote_device_info(self) -> RemoteDeviceInfo:
        payload = self.request(
            MessageType.DEVICE_INFO_REQUEST,
            b"",
            MessageType.DEVICE_INFO_RESPONSE,
        )
        if payload == b"\x00":
            return RemoteDeviceInfo(connected=False)
        if len(payload) != 5 or payload[0] != 1:
            raise M5TransportError("M5 device-info response has an invalid payload.")
        vendor_id, product_id = struct.unpack("<HH", payload[1:])
        return RemoteDeviceInfo(True, vendor_id, product_id)

    def request(
        self,
        message_type: MessageType,
        payload: bytes,
        expected_response_type: MessageType,
    ) -> bytes:
        with self._lock:
            transaction_id = self._allocate_transaction_id()
            endpoint = self._ensure_serial()
            self._write_all(endpoint, encode_frame(Frame(message_type, transaction_id, payload)))
            deadline = time.monotonic() + self.request_timeout_s
            while True:
                frame = self._read_frame(endpoint, deadline)
                if frame.transaction_id != transaction_id:
                    continue
                if frame.message_type == MessageType.ERROR_RESPONSE:
                    detail = frame.payload.decode("utf-8", errors="replace") or "unspecified remote error"
                    raise M5TransportError(f"M5 remote error: {detail}")
                if frame.message_type != expected_response_type:
                    raise M5TransportError(
                        f"Unexpected M5 response type {frame.message_type.name}; expected {expected_response_type.name}."
                    )
                return frame.payload

    def close(self) -> None:
        with self._lock:
            if self._serial is not None:
                try:
                    self._serial.close()
                finally:
                    self._serial = None
                    self._receive_buffer.clear()

    def _allocate_transaction_id(self) -> int:
        transaction_id = self._next_transaction_id
        self._next_transaction_id = 1 if transaction_id == 0xFFFF else transaction_id + 1
        return transaction_id

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
                if len(self._receive_buffer) > MAX_PAYLOAD_LENGTH + 64:
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
