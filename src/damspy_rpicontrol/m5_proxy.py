from __future__ import annotations

import logging
import struct
import threading
from typing import Callable, Protocol

from damspy_rpicontrol.m5_transport import MessageType, Result


logger = logging.getLogger(__name__)
PREFIX = b"@M5PX1,"


class HidDevice(Protocol):
    def write(self, data: bytes) -> int | None: ...
    def read(self, length: int, timeout_ms: int) -> bytes: ...
    def close(self) -> None: ...


class M5ProxyBroker:
    """Execute Core proxy requests against a Pi-attached HID device."""

    def __init__(
        self,
        core_port: str,
        device_factory: Callable[[], HidDevice],
        identity_provider: Callable[[], dict],
        serial_factory=None,
    ) -> None:
        self.core_port = core_port
        self._device_factory = device_factory
        self._identity_provider = identity_provider
        self._serial_factory = serial_factory or self._default_serial_factory
        self._serial = self._serial_factory(core_port, 115200)
        # Terminate any bytes left by Gateway probing so the Core line parser
        # starts the first proxy response at a clean record boundary.
        self._serial.write(b"\n")
        self._device: HidDevice | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="m5-proxy", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        if self._device is not None:
            try:
                self._device.close()
            finally:
                self._device = None
        self._serial.close()

    def _run(self) -> None:
        buffer = bytearray()
        while not self._stop.is_set():
            chunk = self._serial.read(256)
            if not chunk:
                continue
            buffer.extend(chunk)
            while b"\n" in buffer:
                raw_line, _, remainder = buffer.partition(b"\n")
                buffer = bytearray(remainder)
                if not raw_line.startswith(PREFIX + b"REQ,"):
                    continue
                try:
                    response = self._handle_line(raw_line.rstrip(b"\r"))
                    self._serial.write(response + b"\n")
                except Exception:
                    logger.exception("M5 Proxy request failed")

    def _handle_line(self, line: bytes) -> bytes:
        parts = line.split(b",", 4)
        if len(parts) != 5 or parts[:2] != [b"@M5PX1", b"REQ"]:
            raise ValueError("invalid M5 Proxy record")
        request_id = int(parts[2], 16)
        request_type = MessageType(int(parts[3], 16))
        body = bytes.fromhex(parts[4].decode("ascii"))
        response_type, response_body = self._execute(request_type, body)
        return (
            f"@M5PX1,RSP,{request_id:08x},{int(response_type):02x},".encode("ascii")
            + response_body.hex().encode("ascii")
        )

    def _execute(self, request_type: MessageType, body: bytes) -> tuple[MessageType, bytes]:
        if request_type == MessageType.STATUS_REQUEST:
            identity = self._identity_provider()
            connected = bool(identity.get("connected"))
            ready = bool(identity.get("hid_ready"))
            vendor_id = int(identity.get("vid") or 0)
            product_id = int(identity.get("pid") or 0)
            return MessageType.STATUS_RESPONSE, struct.pack(
                "<BBHH", connected, ready, vendor_id, product_id
            )

        try:
            device = self._ensure_device()
            if request_type == MessageType.WRITE_REQUEST:
                if not body:
                    return MessageType.WRITE_RESPONSE, self._result(Result.INVALID_REQUEST)
                written = device.write(body)
                count = len(body) if written is None else int(written)
                return MessageType.WRITE_RESPONSE, self._result(Result.OK, count)

            if request_type == MessageType.READ_REQUEST:
                if len(body) != 6:
                    return MessageType.READ_RESPONSE, self._result(Result.INVALID_REQUEST)
                length, timeout_ms = struct.unpack("<HI", body)
                if not 0 < length <= 239 or timeout_ms <= 0:
                    return MessageType.READ_RESPONSE, self._result(Result.INVALID_REQUEST)
                data = bytes(device.read(length, timeout_ms) or b"")
                if not data:
                    return MessageType.READ_RESPONSE, self._result(Result.TIMEOUT)
                return MessageType.READ_RESPONSE, self._result(Result.OK, len(data), data)
        except Exception:
            logger.exception("Direct HID operation for M5 Proxy failed")
            self._close_device()
            response = (
                MessageType.WRITE_RESPONSE
                if request_type == MessageType.WRITE_REQUEST
                else MessageType.READ_RESPONSE
            )
            return response, self._result(Result.USB_ERROR)

        raise ValueError(f"unsupported M5 Proxy request {request_type}")

    def _ensure_device(self) -> HidDevice:
        if self._device is None:
            self._device = self._device_factory()
            set_nonblocking = getattr(self._device, "set_nonblocking", None)
            if callable(set_nonblocking):
                set_nonblocking(True)
        return self._device

    def _close_device(self) -> None:
        if self._device is not None:
            try:
                self._device.close()
            finally:
                self._device = None

    @staticmethod
    def _result(result: Result, length: int = 0, data: bytes = b"") -> bytes:
        return struct.pack("<BH", int(result), length) + data

    @staticmethod
    def _default_serial_factory(port: str, baud_rate: int):
        import serial
        return serial.Serial(port=port, baudrate=baud_rate, timeout=0.05, write_timeout=1.0)
