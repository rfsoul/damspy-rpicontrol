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

INTER_WRITE_DELAY_S = 0.10
POST_OPEN_DELAY_S = 0.02


class DeviceUnavailableError(RuntimeError):
    """Raised when the HID backend is unavailable."""


class DeviceCommunicationError(RuntimeError):
    """Raised when HID I/O fails."""


class HidDevice(Protocol):
    def write(self, data: bytes) -> int | None:
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


def build_rf_start_report(channel: int, power: int) -> bytes:
    return build_report([0x03, 0x00, channel, 0x00, power])


def build_rf_stop_report() -> bytes:
    return build_report([0x0D, 0x00])


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

    def stop_rf(self) -> int:
        return self._execute([build_rf_stop_report()])

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
