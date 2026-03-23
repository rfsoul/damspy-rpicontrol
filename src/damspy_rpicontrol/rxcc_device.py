from __future__ import annotations

from contextlib import contextmanager
import importlib
import importlib.util
import threading
from typing import Callable, Iterator, Protocol, Sequence

from damspy_rpicontrol.models import AntennaPath, FrontendMode

VENDOR_ID = 0x19F7
PRODUCT_ID = 0x008C
REPORT_ID = 0x0F


class DeviceUnavailableError(RuntimeError):
    """Raised when no supported HID backend is available."""


class DeviceCommunicationError(RuntimeError):
    """Raised when HID I/O fails."""


class HidDevice(Protocol):
    def write(self, data: bytes | list[int]) -> int | None:
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


def build_report(payload: Sequence[int]) -> bytes:
    return bytes([REPORT_ID, *payload])


def build_gpio_report(pin: int, level: int) -> bytes:
    return build_report([0x14, 0x00, 0x02, pin, level])


def build_rf_start_report(channel: int, power: int) -> bytes:
    return build_report([0x03, 0x00, channel, 0x00, power])


def build_rf_stop_report() -> bytes:
    return build_report([0x0D, 0x00])


def frontend_mode_reports(mode: FrontendMode) -> list[bytes]:
    levels = _FRONTEND_MODE_LEVELS[mode]
    return [build_gpio_report(pin=index, level=level) for index, level in enumerate(levels)]


def antenna_reports(path: AntennaPath) -> list[bytes]:
    return [build_gpio_report(pin=3, level=_ANTENNA_LEVELS[path])]


def detect_hid_backend() -> tuple[DeviceFactory | None, str]:
    if importlib.util.find_spec("hidapi") is not None:
        try:
            hidapi = importlib.import_module("hidapi")
            if hasattr(hidapi, "Device"):
                return (
                    lambda: hidapi.Device(vendor_id=VENDOR_ID, product_id=PRODUCT_ID),
                    "hidapi.Device",
                )
        except Exception:
            pass

    if importlib.util.find_spec("hid") is not None:
        try:
            hid = importlib.import_module("hid")
            if hasattr(hid, "Device"):
                return (
                    lambda: hid.Device(vendor_id=VENDOR_ID, product_id=PRODUCT_ID),
                    "hid.Device",
                )
            if hasattr(hid, "device"):
                def open_hid_device() -> HidDevice:
                    device = hid.device()
                    device.open(VENDOR_ID, PRODUCT_ID)
                    return device

                return open_hid_device, "hid.device"
        except Exception:
            pass

    return None, "unavailable"


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

    @property
    def is_available(self) -> bool:
        return self._device_factory is not None

    def apply_frontend_mode(self, mode: FrontendMode) -> int:
        return self._execute(frontend_mode_reports(mode))

    def apply_antenna(self, path: AntennaPath) -> int:
        return self._execute(antenna_reports(path))

    def start_rf(self, antenna: AntennaPath, channel: int, power: int) -> int:
        reports = [
            *frontend_mode_reports(FrontendMode.TRANSMITTING_PA),
            *antenna_reports(antenna),
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
                "No supported HID backend is installed. Install `hidapi` on the Raspberry Pi."
            )

        try:
            device = self._device_factory()
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
                result = device.write(report)
            except TypeError:
                result = device.write(list(report))
            except Exception as exc:
                raise DeviceCommunicationError(
                    f"Failed while writing HID report {list(report)} ({exc})."
                ) from exc

            if isinstance(result, int) and result < 0:
                raise DeviceCommunicationError(
                    f"HID write failed for report {list(report)}."
                )

            reports_sent += 1

        return reports_sent
