from __future__ import annotations

from contextlib import contextmanager
import threading
import time
from typing import Callable, Iterator, Protocol, Sequence

import importlib

from damspy_rpicontrol.models import AntennaPath, FrontendMode

VENDOR_ID = 0x19F7
PRODUCT_ID = 0x008C
REPORT_ID = 0x0F
COMMAND_RESPONSE_LENGTH = 64
COMMAND_READ_TIMEOUT_MS = 200
COMMAND_READ_POLL_INTERVAL_S = 0.01

# Small settle delays to match the known-good standalone scripts more closely.
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


_FRONTEND_MODE_LEVELS: dict[FrontendMode, tuple[int, int, int]] = {
    FrontendMode.TRANSMITTING_PA: (1, 0, 0),
    FrontendMode.BYPASS: (0, 1, 0),
    FrontendMode.RECEIVING: (0, 0, 1),
}

_ANTENNA_LEVELS: dict[AntennaPath, int] = {
    AntennaPath.MAIN: 0,
    AntennaPath.SECONDARY: 1,
}


def detect_hid_backend() -> tuple[DeviceFactory | None, str]:
    """
    Force the exact backend family that the known-good standalone scripts use:
    hidapi.Device(vendor_id=..., product_id=...)
    """
    try:
        hidapi_module = importlib.import_module("hidapi")
    except Exception:
        return None, "unavailable"

    return (
        lambda: hidapi_module.Device(vendor_id=VENDOR_ID, product_id=PRODUCT_ID),
        "hidapi.Device",
    )


def build_report(payload: Sequence[int]) -> bytes:
    """
    RXCC report format from the command guide:
        bytes([0x0F] + payload)
    """
    return bytes([REPORT_ID] + list(payload))


def build_gpio_report(pin: int, level: int) -> bytes:
    return build_report([0x0E, 0x00, 0x02, pin, level])


def build_rf_start_report(channel: int, power: int) -> bytes:
    return build_report([0x03, 0x00, channel, 0x00, power])


def build_rf_stop_report() -> bytes:
    return build_report([0x0D, 0x00])


def frontend_mode_reports(mode: FrontendMode) -> list[bytes]:
    levels = _FRONTEND_MODE_LEVELS[mode]
    return [
        build_gpio_report(pin=0, level=levels[0]),
        build_gpio_report(pin=1, level=levels[1]),
        build_gpio_report(pin=2, level=levels[2]),
    ]


def antenna_reports(path: AntennaPath) -> list[bytes]:
    return [build_gpio_report(pin=3, level=_ANTENNA_LEVELS[path])]


class RxccController:
    def __init__(
        self,
        device_factory: DeviceFactory | None = None,
        backend_name: str | None = None,
    ) -> None:
        if device_factory is None:
            device_factory, detected_backend = detect_hid_backend()
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

    def apply_frontend_mode(self, mode: FrontendMode) -> int:
        return self._execute(frontend_mode_reports(mode))

    def apply_gpio(self, pin: int, level: int) -> int:
        return self._execute([build_gpio_report(pin=pin, level=level)])

    def apply_antenna(self, path: AntennaPath) -> int:
        return self._execute(antenna_reports(path))

    def start_rf(self, antenna: AntennaPath, channel: int, power: int) -> int:
        reports = [
            *frontend_mode_reports(FrontendMode.TRANSMITTING_PA),
            *antenna_reports(antenna),
            build_rf_start_report(channel=channel, power=power),
        ]
        return self._execute(reports)

    def start_rf_raw(self, channel: int, power: int) -> int:
        return self._execute([build_rf_start_report(channel=channel, power=power)])

    def stop_rf(self) -> int:
        return self._execute([build_rf_stop_report()])

    def _execute(self, reports: Sequence[bytes]) -> int:
        with self._lock:
            self._reset_io_trace()
            with self._open_device() as device:
                reports_sent = self._write_reports(device, reports)
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
                f"Unable to open the RXCC HID device ({exc})."
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
                # IMPORTANT:
                # Use bytes only, matching the guide and the known-good standalone scripts.
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
            time.sleep(INTER_WRITE_DELAY_S)

        return reports_sent

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

    def _reset_io_trace(self) -> None:
        self._last_written_reports = []
        self._last_response = None
