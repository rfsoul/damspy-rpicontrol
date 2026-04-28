from __future__ import annotations

from contextlib import contextmanager
import threading
import time
from typing import Callable, Iterator, Protocol, Sequence

import importlib

VENDOR_ID = 0x19F7
TX_PRODUCT_ID = 0x008A
RX_PRODUCT_ID = 0x008B
REPORT_ID = 0x0F
BATTERY_REQUEST_REPORT_ID = 0x01
BATTERY_RESPONSE_REPORT_ID = 0x02
BATTERY_COMMAND_ID = 0x61
BATTERY_STATUS_OK = ord("A")
BATTERY_REQUEST_LENGTH = 17
BATTERY_RESPONSE_MIN_LENGTH = 5
BATTERY_READ_TIMEOUT_MS = 1000
COMMAND_RESPONSE_LENGTH = 64
COMMAND_READ_TIMEOUT_MS = 200
COMMAND_READ_POLL_INTERVAL_S = 0.01
LED_TEST_REPORT_ID = 21
LED_TEST_COMMAND_ID = 0x4E
LED_TEST_RESERVED_LENGTH = 12
LED_FLASH_STEP_DELAY_S = 0.25
LED_FLASH_COUNT = 2
LED_MAX_BRIGHTNESS = 0xFF

INTER_WRITE_DELAY_S = 0.10
POST_OPEN_DELAY_S = 0.02


class DeviceUnavailableError(RuntimeError):
    """Raised when the HID backend is unavailable."""


class DeviceCommunicationError(RuntimeError):
    """Raised when HID I/O fails."""


class HidDevice(Protocol):
    def write(self, data: bytes) -> int | None:
        ...

    def read(self, length: int, timeout_ms: int) -> bytes | Sequence[int] | None:
        ...

    def close(self) -> None:
        ...


DeviceFactory = Callable[[], HidDevice]


def detect_hid_backend(product_id: int) -> tuple[DeviceFactory | None, str]:
    try:
        hidapi_module = importlib.import_module("hidapi")
    except Exception:
        return None, "unavailable"

    return (
        lambda: hidapi_module.Device(vendor_id=VENDOR_ID, product_id=product_id),
        "hidapi.Device",
    )


def build_report(payload: Sequence[int]) -> bytes:
    return bytes([REPORT_ID] + list(payload))


def build_ctx_high_report() -> bytes:
    return build_report([0x0E, 0x00, 0x02, 0x00, 0x01])


def build_ctx_low_report() -> bytes:
    return build_report([0x0E, 0x00, 0x02, 0x00, 0x00])


def build_rf_start_report(channel: int, power: int) -> bytes:
    return build_report([0x03, 0x00, channel, 0x00, power])


def build_rf_stop_report() -> bytes:
    return build_report([0x0D, 0x00])


def build_led_test_report(color_index: int, enabled: bool, brightness: int) -> bytes:
    if color_index not in {0, 1, 2, 3}:
        raise ValueError("LED colour index must be 0 (red), 1 (green), 2 (blue), or 3 (white).")
    if brightness < 0 or brightness > LED_MAX_BRIGHTNESS:
        raise ValueError("LED brightness must be between 0 and 255.")

    return bytes(
        [
            LED_TEST_REPORT_ID,
            LED_TEST_COMMAND_ID,
            color_index,
            0x01 if enabled else 0x00,
            brightness,
        ]
        + [0x00] * LED_TEST_RESERVED_LENGTH
    )


def build_led_off_reports() -> list[bytes]:
    return [build_led_test_report(color_index=color_index, enabled=False, brightness=0) for color_index in (0, 1, 2, 3)]


def build_battery_info_request() -> bytes:
    return bytes([BATTERY_REQUEST_REPORT_ID, BATTERY_COMMAND_ID] + [0x00] * (BATTERY_REQUEST_LENGTH - 2))


def parse_battery_info_response(data: bytes | Sequence[int]) -> int:
    response = bytes(data)
    if len(response) < BATTERY_RESPONSE_MIN_LENGTH:
        raise DeviceCommunicationError(
            f"Battery response was too short: expected at least {BATTERY_RESPONSE_MIN_LENGTH} bytes, got {len(response)}."
        )
    if response[0] != BATTERY_RESPONSE_REPORT_ID:
        raise DeviceCommunicationError(
            f"Unexpected battery response report ID 0x{response[0]:02X}; expected 0x{BATTERY_RESPONSE_REPORT_ID:02X}."
        )
    if response[1] != BATTERY_COMMAND_ID:
        raise DeviceCommunicationError(
            f"Unexpected battery response command ID 0x{response[1]:02X}; expected 0x{BATTERY_COMMAND_ID:02X}."
        )
    if response[2] != BATTERY_STATUS_OK:
        raise DeviceCommunicationError(
            f"Battery response status was 0x{response[2]:02X}; expected 0x{BATTERY_STATUS_OK:02X}."
        )
    return response[3] | (response[4] << 8)


class HendrixController:
    def __init__(
        self,
        product_id: int,
        device_factory: DeviceFactory | None = None,
        backend_name: str | None = None,
    ) -> None:
        self.product_id = product_id
        if device_factory is None:
            device_factory, detected_backend = detect_hid_backend(product_id)
            self._device_factory = device_factory
            self.backend_name = backend_name or detected_backend
        else:
            self._device_factory = device_factory
            self.backend_name = backend_name or "custom"

        self._lock = threading.Lock()
        self._last_written_reports: list[bytes] = []
        self._last_response: bytes | None = None

    @property
    def is_available(self) -> bool:
        return self._device_factory is not None

    def start_rf(self, channel: int, power: int) -> int:
        return self._execute([build_rf_start_report(channel=channel, power=power)])

    def set_ctx(self, high: bool) -> int:
        report = build_ctx_high_report() if high else build_ctx_low_report()
        return self._execute([report])

    def stop_rf(self) -> int:
        return self._execute([build_rf_stop_report()])

    def flash_led(self, color_index: int, flashes: int = LED_FLASH_COUNT) -> int:
        if flashes < 1:
            raise ValueError("LED flash count must be at least 1.")

        reports: list[bytes] = []
        for _ in range(flashes):
            reports.append(build_led_test_report(color_index=color_index, enabled=True, brightness=LED_MAX_BRIGHTNESS))
            reports.append(build_led_test_report(color_index=color_index, enabled=False, brightness=0))

        return self._execute(reports, inter_write_delay_s=LED_FLASH_STEP_DELAY_S)

    def turn_off_all_leds(self) -> int:
        return self._execute(build_led_off_reports())

    def read_battery_mv(self) -> int:
        battery_mv, _ = self.read_battery_info()
        return battery_mv

    def read_battery_info(self) -> tuple[int, bytes]:
        with self._lock:
            self._reset_io_trace()
            with self._open_device() as device:
                self._write_reports(device, [build_battery_info_request()])
                return self._read_battery_info(device)

    def _execute(self, reports: Sequence[bytes], inter_write_delay_s: float = INTER_WRITE_DELAY_S) -> int:
        with self._lock:
            self._reset_io_trace()
            with self._open_device() as device:
                reports_sent = self._write_reports(device, reports, inter_write_delay_s=inter_write_delay_s)
                self._read_command_response(device)
                return reports_sent

    def get_last_io_trace(self) -> tuple[list[bytes], bytes | None]:
        return list(self._last_written_reports), self._last_response

    @contextmanager
    def _open_device(self) -> Iterator[HidDevice]:
        if self._device_factory is None:
            raise DeviceUnavailableError(
                "No supported HID backend is available. Install python hidapi."
            )

        try:
            device = self._device_factory()
            set_nonblocking = getattr(device, "set_nonblocking", None)
            if callable(set_nonblocking):
                set_nonblocking(True)
            time.sleep(POST_OPEN_DELAY_S)
        except Exception as exc:
            raise DeviceCommunicationError(
                f"Unable to open the Hendrix HID device ({exc})."
            ) from exc

        try:
            yield device
        finally:
            try:
                device.close()
            except Exception:
                pass

    def _write_reports(
        self,
        device: HidDevice,
        reports: Sequence[bytes],
        inter_write_delay_s: float = INTER_WRITE_DELAY_S,
    ) -> int:
        reports_sent = 0

        for report in reports:
            try:
                result = device.write(report)
            except Exception as exc:
                raise DeviceCommunicationError(
                    f"Failed while writing HID report {list(report)} ({exc})."
                ) from exc

            if isinstance(result, int) and result < 0:
                raise DeviceCommunicationError(
                    f"HID write failed for report {list(report)}."
                )

            self._last_written_reports.append(bytes(report))
            reports_sent += 1
            time.sleep(inter_write_delay_s)

        return reports_sent

    def _read_battery_mv(self, device: HidDevice) -> int:
        battery_mv, _ = self._read_battery_info(device)
        return battery_mv

    def _read_command_response(self, device: HidDevice) -> bytes | None:
        deadline = time.monotonic() + (COMMAND_READ_TIMEOUT_MS / 1000)

        while True:
            try:
                response = device.read(COMMAND_RESPONSE_LENGTH, COMMAND_READ_TIMEOUT_MS)
            except Exception:
                self._last_response = None
                return None

            if response is not None:
                response_bytes = bytes(response)
                if response_bytes:
                    self._last_response = response_bytes
                    return response_bytes

            if time.monotonic() >= deadline:
                self._last_response = None
                return None

            time.sleep(COMMAND_READ_POLL_INTERVAL_S)

    def _read_battery_info(self, device: HidDevice) -> tuple[int, bytes]:
        try:
            response = device.read(BATTERY_REQUEST_LENGTH, BATTERY_READ_TIMEOUT_MS)
        except Exception as exc:
            raise DeviceCommunicationError(
                f"Failed while reading Hendrix battery response ({exc})."
            ) from exc

        if response is None:
            self._last_response = None
            raise DeviceCommunicationError("Hendrix battery response was empty.")

        response_bytes = bytes(response)
        self._last_response = response_bytes
        return parse_battery_info_response(response_bytes), response_bytes

    def _reset_io_trace(self) -> None:
        self._last_written_reports = []
        self._last_response = None
