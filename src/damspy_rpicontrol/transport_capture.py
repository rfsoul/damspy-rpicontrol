from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Callable

from damspy_rpicontrol.models import AntennaPath, FrontendMode

CAPTURE_VERSION = 1
RF_CHANNEL = 10
RF_POWER = 5
WIRELESS_PRO_FREQUENCY = 78
WIRELESS_PRO_POWER = -4

PROFILE_LABELS = {
    "hendrix-rx": "Hendrix RX",
    "hendrix-tx": "Hendrix TX direct/beltpack",
    "wireless-pro-rx": "Wireless PRO RX",
    "rxcc": "RXCC",
    "hendrix-tx-via-rxcc": "Hendrix TX via RXCC",
}

Operation = tuple[str, dict[str, Any], Callable[[], Any]]


def _hendrix_operations(controller: Any, include_tx_operations: bool) -> tuple[list[Operation], list[Operation]]:
    operations: list[Operation] = [("read_battery", {}, controller.read_battery_info)]
    if include_tx_operations:
        operations.extend(
            [
                ("read_serial_number", {"nvm_key": "NORDIC_ID"}, controller.read_serial_number),
                ("set_charging", {"enabled": True}, lambda: controller.set_charging(True)),
                ("set_charging", {"enabled": False}, lambda: controller.set_charging(False)),
            ]
        )
    operations.extend(
        [
            ("set_ctx", {"high": True}, lambda: controller.set_ctx(True)),
            ("set_ctx", {"high": False}, lambda: controller.set_ctx(False)),
        ]
    )
    operations.extend(
        [
            ("stop_rf", {}, controller.stop_rf),
            ("start_rf", {"channel": RF_CHANNEL, "power": RF_POWER}, lambda: controller.start_rf(RF_CHANNEL, RF_POWER)),
            ("stop_rf", {}, controller.stop_rf),
        ]
    )
    cleanup: list[Operation] = [("stop_rf", {}, controller.stop_rf)]
    if include_tx_operations:
        cleanup.extend(
            [
                ("set_charging", {"enabled": False}, lambda: controller.set_charging(False)),
            ]
        )
    return operations, cleanup


def _rxcc_operations(controller: Any) -> tuple[list[Operation], list[Operation]]:
    operations: list[Operation] = [
        ("read_battery", {}, controller.read_battery_info),
        ("read_serial_number", {"nvm_key": "NORDIC_ID"}, controller.read_serial_number),
        ("set_charging", {"enabled": True}, lambda: controller.set_charging(True)),
        ("set_charging", {"enabled": False}, lambda: controller.set_charging(False)),
    ]
    for mode in FrontendMode:
        operations.append(("set_frontend_mode", {"mode": mode.value}, lambda mode=mode: controller.apply_frontend_mode(mode)))
    for path in AntennaPath:
        operations.append(("set_antenna", {"path": path.value}, lambda path=path: controller.apply_antenna(path)))
    for pin in range(4):
        for level in (0, 1):
            operations.append(("set_gpio", {"pin": pin, "level": level}, lambda pin=pin, level=level: controller.apply_gpio(pin, level)))
    operations.extend(
        [
            ("stop_rf", {}, controller.stop_rf),
            (
                "start_rf",
                {"antenna": AntennaPath.MAIN.value, "channel": RF_CHANNEL, "power": RF_POWER},
                lambda: controller.start_rf(AntennaPath.MAIN, RF_CHANNEL, RF_POWER),
            ),
            ("stop_rf", {}, controller.stop_rf),
        ]
    )
    cleanup = [
        ("stop_rf", {}, controller.stop_rf),
        ("set_charging", {"enabled": False}, lambda: controller.set_charging(False)),
        ("set_frontend_mode", {"mode": FrontendMode.BYPASS.value}, lambda: controller.apply_frontend_mode(FrontendMode.BYPASS)),
    ]
    return operations, cleanup


def _wireless_pro_operations(controller: Any) -> tuple[list[Operation], list[Operation]]:
    parameters = {
        "antenna": AntennaPath.MAIN.value,
        "wirepro_freq": WIRELESS_PRO_FREQUENCY,
        "wirepro_power": WIRELESS_PRO_POWER,
    }
    operations = [
        ("read_battery", {}, controller.read_battery_info),
        ("stop_rf", {}, controller.stop_rf),
        (
            "start_rf",
            parameters,
            lambda: controller.start_rf(AntennaPath.MAIN, WIRELESS_PRO_FREQUENCY, WIRELESS_PRO_POWER),
        ),
        ("stop_rf", {}, controller.stop_rf),
    ]
    return operations, [("stop_rf", {}, controller.stop_rf)]


def operation_matrix(profile: str, controller: Any) -> tuple[list[Operation], list[Operation]]:
    if profile == "hendrix-rx":
        return _hendrix_operations(controller, include_tx_operations=False)
    if profile in {"hendrix-tx", "hendrix-tx-via-rxcc"}:
        return _hendrix_operations(controller, include_tx_operations=True)
    if profile == "wireless-pro-rx":
        return _wireless_pro_operations(controller)
    if profile == "rxcc":
        return _rxcc_operations(controller)
    raise ValueError(f"Unknown transport capture profile `{profile}`.")


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return list(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _io_records(controller: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    writes, reads = controller.get_last_io_events()
    write_records = [{"bytes": list(report), "length": len(report)} for report in writes]
    read_records = []
    for response in reads:
        if response is None:
            read_records.append({"bytes": None, "length": None, "result": "none"})
        else:
            read_records.append({"bytes": list(response), "length": len(response), "result": "bytes"})
    hid_events = []
    raw_events = controller.get_last_hid_events() if hasattr(controller, "get_last_hid_events") else (
        [("write", item) for item in writes] + [("read", item) for item in reads]
    )
    for index, (direction, data) in enumerate(raw_events, start=1):
        hid_events.append({
            "sequence": index,
            "direction": direction,
            "bytes": None if data is None else list(data),
            "length": None if data is None else len(data),
            "result": "none" if data is None else "bytes",
        })
    return write_records, read_records, hid_events


def _run_operation(sequence: int, operation: Operation, controller: Any, cleanup: bool = False) -> dict[str, Any]:
    name, parameters, call = operation
    started = time.monotonic()
    parsed_result = None
    error = None
    try:
        parsed_result = _json_value(call())
    except Exception as exc:  # Captures transport and controller errors as evidence and continues.
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = round((time.monotonic() - started) * 1000, 3)
    try:
        writes, reads, io_events = _io_records(controller)
    except Exception as exc:
        writes, reads, io_events = [], [], []
        if error is None:
            error = f"Unable to retrieve HID trace: {type(exc).__name__}: {exc}"
    return {
        "sequence": sequence,
        "operation": name,
        "parameters": parameters,
        "cleanup": cleanup,
        "elapsed_ms": elapsed_ms,
        "writes": writes,
        "reads": reads,
        "io_events": io_events,
        "parsed_result": parsed_result,
        "error": error,
    }


def run_transport_capture(
    profile: str,
    transport: str,
    controller: Any,
    physical_usb_device: dict[str, Any],
    m5_serial_port: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    timestamp = now or datetime.now(timezone.utc).astimezone()
    operations, cleanup = operation_matrix(profile, controller)
    captured = [_run_operation(index, operation, controller) for index, operation in enumerate(operations, start=1)]
    cleanup_captured = [
        _run_operation(index, operation, controller, cleanup=True)
        for index, operation in enumerate(cleanup, start=len(captured) + 1)
    ]
    filename_stamp = timestamp.strftime("%Y-%m-%d_%H%M%S")
    filename = f"{profile.replace('-', '_')}_{transport}_{filename_stamp}.json"
    return {
        "capture_version": CAPTURE_VERSION,
        "timestamp": timestamp.isoformat(),
        "selected_profile": profile,
        "selected_profile_name": PROFILE_LABELS[profile],
        "transport": transport,
        "m5_serial_port": m5_serial_port,
        "physical_usb_device": physical_usb_device,
        "operations": captured,
        "cleanup_operations": cleanup_captured,
        "download_filename": filename,
    }
