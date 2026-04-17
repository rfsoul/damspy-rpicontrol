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

INTER_WRITE_DELAY_S = 0.10
POST_OPEN_DELAY_S = 0.02


class DeviceUnavailableError(RuntimeError):
    """Raised when the HID backend is unavailable."""


class DeviceCommunicationError(RuntimeError):
    """Raised when HID I/O fails."""


class HidDevice(Protocol):
    def write(self, data: bytes) -> int | None:
        ...

    def read(self, length: int, timeout_ms: int) -> bytes | Sequence[int]:
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
    return build_report([0x14, 0x00, 0x02, 0x00, 0x01])


def build_ctx_low_report() -> bytes:
    return build_report([0x14, 0x00, 0x02, 0x00, 0x00])


def build_rf_start_report(channel: int, power: int) -> bytes:
    return build_report([0x03, 0x00, channel, 0x00, power])


def build_rf_stop_report() -> bytes:
    return build_report([0x0D, 0x00])


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

    @property
    def is_available(self) -> bool:
        return self._device_factory is not None

    def start_rf(self, channel: int, power: int) -> int:
        reports = [
            build_ctx_high_report(),
            build_rf_start_report(channel=channel, power=power),
        ]
        return self._execute(reports)

    def set_ctx(self, high: bool) -> int:
        report = build_ctx_high_report() if high else build_ctx_low_report()
        return self._execute([report])

    def stop_rf(self) -> int:
        return self._execute([build_rf_stop_report()])

    def read_battery_mv(self) -> int:
        with self._lock:
            with self._open_device() as device:
                self._write_reports(device, [build_battery_info_request()])
                return self._read_battery_mv(device)

    def _execute(self, reports: Sequence[bytes]) -> int:
        with self._lock:
            with self._open_device() as device:
                return self._write_reports(device, reports)

    @contextmanager
    def _open_device(self) -> Iterator[HidDevice]:
        if self._device_factory is None:
            raise DeviceUnavailableError(
                "No supported HID backend is available. Install python hidapi."
            )

        try:
            device = self._device_factory()
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

    def _write_reports(self, device: HidDevice, reports: Sequence[bytes]) -> int:
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

            reports_sent += 1
            time.sleep(INTER_WRITE_DELAY_S)

        return reports_sent

    def _read_battery_mv(self, device: HidDevice) -> int:
        try:
            response = device.read(BATTERY_REQUEST_LENGTH, BATTERY_READ_TIMEOUT_MS)
        except Exception as exc:
            raise DeviceCommunicationError(
                f"Failed while reading Hendrix battery response ({exc})."
            ) from exc

        return parse_battery_info_response(response)
