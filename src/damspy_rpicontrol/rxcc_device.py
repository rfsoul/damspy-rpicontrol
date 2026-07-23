from __future__ import annotations

from contextlib import contextmanager
import threading
import time
from typing import Callable, Iterator, Protocol, Sequence

import importlib

from damspy_rpicontrol.hendrix_device import (
    BATTERY_READ_TIMEOUT_MS,
    BATTERY_REQUEST_LENGTH,
    BatteryInfo,
    DeviceCommunicationError as HendrixDeviceCommunicationError,
    build_battery_info_request,
    build_charging_control_report,
    build_read_item_report,
    parse_battery_info_response,
    parse_read_item_response,
    READ_ITEM_RESPONSE_LENGTH,
    READ_ITEM_TIMEOUT_MS,
)
from damspy_rpicontrol.models import (
    AntennaPath,
    FrontendMode,
    WIRELESS_PRO_RX_POWER_LEVELS,
)

VENDOR_ID = 0x19F7
RXCC_PRODUCT_ID = 0x008C
RXCC_USB_HUB_ALIAS_VENDOR_ID = 0x1A86
RXCC_USB_HUB_ALIAS_PRODUCT_ID = 0x8091
RXCC_DEVICE_IDS = (
    (VENDOR_ID, RXCC_PRODUCT_ID),
    (RXCC_USB_HUB_ALIAS_VENDOR_ID, RXCC_USB_HUB_ALIAS_PRODUCT_ID),
)
WIRELESS_PRO_RX_PRODUCT_ID = 0x0058
WIRELESS_PRO_TX_PRODUCT_ID = 0x0056
WIRELESS_PRO_PRODUCT_IDS = (
    WIRELESS_PRO_RX_PRODUCT_ID,
    WIRELESS_PRO_TX_PRODUCT_ID,
)
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
DeviceIdentity = tuple[int, int]


_FRONTEND_MODE_LEVELS: dict[FrontendMode, tuple[int, int, int]] = {
    FrontendMode.TRANSMITTING_PA: (1, 0, 0),
    FrontendMode.BYPASS: (0, 1, 0),
    FrontendMode.RECEIVING: (0, 0, 1),
}

_ANTENNA_LEVELS: dict[AntennaPath, int] = {
    AntennaPath.MAIN: 0,
    AntennaPath.SECONDARY: 1,
}


def _normalise_device_ids(
    product_id: int | Sequence[int] | Sequence[DeviceIdentity],
) -> tuple[DeviceIdentity, ...]:
    if isinstance(product_id, int):
        return ((VENDOR_ID, product_id),)

    device_entries = tuple(product_id)
    if not device_entries:
        raise ValueError("At least one HID product ID is required.")

    first_entry = device_entries[0]
    if isinstance(first_entry, int):
        return tuple((VENDOR_ID, current_product_id) for current_product_id in device_entries)

    normalised_device_ids: list[DeviceIdentity] = []
    for entry in device_entries:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise ValueError("HID device IDs must be provided as (vendor_id, product_id) pairs.")
        vendor_id, current_product_id = entry
        normalised_device_ids.append((vendor_id, current_product_id))
    return tuple(normalised_device_ids)


def _open_hidapi_device(hidapi_module, device_ids: Sequence[DeviceIdentity]) -> HidDevice:
    last_error: Exception | None = None

    for current_vendor_id, current_product_id in device_ids:
        try:
            return hidapi_module.Device(vendor_id=current_vendor_id, product_id=current_product_id)
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("No HID product IDs were provided.")


def detect_hid_backend(
    product_id: int | Sequence[int] | Sequence[DeviceIdentity] = RXCC_DEVICE_IDS,
) -> tuple[DeviceFactory | None, str]:
    """
    Force the exact backend family that the known-good standalone scripts use:
    hidapi.Device(vendor_id=..., product_id=...)
    """
    try:
        hidapi_module = importlib.import_module("hidapi")
    except Exception:
        return None, "unavailable"

    device_ids = _normalise_device_ids(product_id)
    return (
        lambda: _open_hidapi_device(hidapi_module, device_ids),
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


def _encode_signed_byte(value: int) -> int:
    return value & 0xFF


def build_wireless_pro_rf_start_report(wirepro_freq: int, antenna: AntennaPath, wirepro_power: int) -> bytes:
    if wirepro_power not in WIRELESS_PRO_RX_POWER_LEVELS:
        raise ValueError(
            "Wireless PRO RX power must be one of: "
            + ", ".join(str(value) for value in sorted(WIRELESS_PRO_RX_POWER_LEVELS, reverse=True))
            + "."
        )
    antenna_id = 0 if antenna == AntennaPath.MAIN else 1
    return build_report([0x03, 0x00, wirepro_freq, antenna_id, _encode_signed_byte(wirepro_power)])


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
        product_id: int | Sequence[int] | Sequence[DeviceIdentity] = RXCC_DEVICE_IDS,
        device_factory: DeviceFactory | None = None,
        backend_name: str | None = None,
    ) -> None:
        self.device_ids = _normalise_device_ids(product_id)
        self.product_ids = tuple(current_product_id for _, current_product_id in self.device_ids)
        self.product_id = self.product_ids[0]
        if device_factory is None:
            device_factory, detected_backend = detect_hid_backend(product_id=self.device_ids)
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

    def send_raw_report(self, report: bytes) -> int:
        return self._execute([bytes(report)])

    def set_charging(self, enabled: bool) -> int:
        return self._execute([build_charging_control_report(enabled)])

    def read_battery_mv(self) -> int:
        return self.read_battery_info().battery_mv

    def read_battery_info(self) -> BatteryInfo:
        with self._lock:
            self._reset_io_trace()
            with self._open_device() as device:
                self._write_reports(device, [build_battery_info_request()])
                return self._read_battery_info(device)

    def read_serial_number(self) -> str:
        return self.read_nvm_item("NORDIC_ID")

    def read_nvm_item(self, key: str) -> str:
        with self._lock:
            self._reset_io_trace()
            with self._open_device() as device:
                self._write_reports(device, [build_read_item_report(key)])
                return self._read_nvm_item(device, key)

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

    def _read_battery_info(self, device: HidDevice) -> BatteryInfo:
        try:
            response = device.read(BATTERY_REQUEST_LENGTH, BATTERY_READ_TIMEOUT_MS)
        except Exception as exc:
            raise DeviceCommunicationError(
                f"Failed while reading RXCC battery response ({exc})."
            ) from exc

        if response is None:
            self._last_response = None
            raise DeviceCommunicationError("RXCC battery response was empty.")

        response_bytes = bytes(response)
        self._last_response = response_bytes
        try:
            return parse_battery_info_response(response_bytes)
        except HendrixDeviceCommunicationError as exc:
            raise DeviceCommunicationError(str(exc)) from exc

    def _read_nvm_item(self, device: HidDevice, key: str) -> str:
        try:
            response = device.read(READ_ITEM_RESPONSE_LENGTH, READ_ITEM_TIMEOUT_MS)
        except Exception as exc:
            raise DeviceCommunicationError(
                f"Failed while reading RXCC NVM item `{key}` ({exc})."
            ) from exc

        if response is None:
            self._last_response = None
            raise DeviceCommunicationError(f"RXCC NVM item response for `{key}` was empty.")

        response_bytes = bytes(response)
        if not response_bytes:
            self._last_response = response_bytes
            raise DeviceCommunicationError(f"RXCC NVM item response for `{key}` was empty.")

        self._last_response = response_bytes
        try:
            return parse_read_item_response(response_bytes, key)
        except HendrixDeviceCommunicationError as exc:
            raise DeviceCommunicationError(str(exc)) from exc

    def _reset_io_trace(self) -> None:
        self._last_written_reports = []
        self._last_response = None


class WirelessProRxController(RxccController):
    def __init__(
        self,
        product_id: int | Sequence[int] = WIRELESS_PRO_PRODUCT_IDS,
        device_factory: DeviceFactory | None = None,
        backend_name: str | None = None,
    ) -> None:
        super().__init__(product_id=product_id, device_factory=device_factory, backend_name=backend_name)

    def start_rf(self, antenna: AntennaPath, wirepro_freq: int, wirepro_power: int) -> int:
        return self._execute(
            [
                build_wireless_pro_rf_start_report(
                    wirepro_freq=wirepro_freq,
                    antenna=antenna,
                    wirepro_power=wirepro_power,
                )
            ]
        )

    def start_rf_raw(self, antenna: AntennaPath, wirepro_freq: int, wirepro_power: int) -> int:
        return self._execute(
            [
                build_wireless_pro_rf_start_report(
                    wirepro_freq=wirepro_freq,
                    antenna=antenna,
                    wirepro_power=wirepro_power,
                )
            ]
        )

    def read_battery_mv(self) -> int:
        return self.read_battery_info().battery_mv

    def read_battery_info(self) -> BatteryInfo:
        with self._lock:
            self._reset_io_trace()
            with self._open_device() as device:
                self._write_reports(device, [build_battery_info_request()])
                return self._read_battery_info(device)

    def _read_battery_info(self, device: HidDevice) -> BatteryInfo:
        try:
            response = device.read(BATTERY_REQUEST_LENGTH, BATTERY_READ_TIMEOUT_MS)
        except Exception as exc:
            raise DeviceCommunicationError(
                f"Failed while reading Wireless PRO RX battery response ({exc})."
            ) from exc

        if response is None:
            self._last_response = None
            raise DeviceCommunicationError("Wireless PRO RX battery response was empty.")

        response_bytes = bytes(response)
        self._last_response = response_bytes
        return parse_battery_info_response(response_bytes)
