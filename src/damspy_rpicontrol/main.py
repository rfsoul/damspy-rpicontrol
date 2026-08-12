from __future__ import annotations

from pathlib import Path
import importlib
import threading
import subprocess
import sys
from typing import Callable, Sequence

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from damspy_rpicontrol.models import (
    AntennaRequest,
    BatteryResponse,
    DeviceCommand,
    DeviceCommandRequest,
    DeviceType,
    FrontendModeRequest,
    HealthResponse,
    HealthcheckResponse,
    OperationResponse,
    RawCommandRequest,
    SerialNumberResponse,
    StartRfRequest,
    SurveyModeResponse,
    TransportCaptureRequest,
    TransportConfigRequest,
    TransportMode,
    TransportStatusResponse,
)
from damspy_rpicontrol.m5_transport import M5SerialHidTransport, M5TransportError
from damspy_rpicontrol.transport_capture import run_transport_capture
from damspy_rpicontrol.hendrix_device import (
    DeviceCommunicationError as HendrixDeviceCommunicationError,
    DeviceUnavailableError as HendrixDeviceUnavailableError,
    HendrixController,
    RX_PRODUCT_ID,
    TX_PRODUCT_ID,
    VENDOR_ID as HENDRIX_VENDOR_ID,
)
from damspy_rpicontrol.rxcc_device import (
    DeviceCommunicationError,
    DeviceUnavailableError,
    RXCC_DEVICE_IDS,
    RxccController,
    WIRELESS_PRO_PRODUCT_IDS,
    WirelessProRxController,
)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
HEALTHCHECK_SCRIPT_PATH = Path(__file__).resolve().parent / "healthcheck.py"
SUPPORTED_WEB_DEVICES: dict[str, str] = {
    "rxcc": "RODE RXCC 008C",
    "tx": "Hendrix TX 008A",
    "rx": "Hendrix RX 008B",
    "wireless-pro-rx": "RODE Wireless PRO RX 0058",
    "test-command": "Test Command",
}
DEVICE_TEMPLATE_FILES: dict[str, str] = {
    "rxcc": "rxcc.html",
    "tx": "tx.html",
    "rx": "rx.html",
    "wireless-pro-rx": "wireless_pro_rx.html",
    "test-command": "test_command.html",
}
TX_LED_FLASH_COLORS: dict[str, int] = {
    "red": 0,
    "green": 1,
}
TEST_COMMAND_DEVICE_IDS = (
    *RXCC_DEVICE_IDS,
    (HENDRIX_VENDOR_ID, RX_PRODUCT_ID),
    (HENDRIX_VENDOR_ID, TX_PRODUCT_ID),
)

USB_PROFILE_DEVICE_IDS = {
    "hendrix-rx": ((HENDRIX_VENDOR_ID, RX_PRODUCT_ID),),
    "hendrix-tx": ((HENDRIX_VENDOR_ID, TX_PRODUCT_ID),),
    "wireless-pro-rx": tuple((HENDRIX_VENDOR_ID, pid) for pid in WIRELESS_PRO_PRODUCT_IDS),
    "rxcc": RXCC_DEVICE_IDS,
    "hendrix-tx-via-rxcc": RXCC_DEVICE_IDS,
}


def _device_info_value(entry, field: str):
    if isinstance(entry, dict):
        return entry.get(field)
    return getattr(entry, field, None)

def _detect_usb_identity(profile: str) -> dict:
    expected_ids = USB_PROFILE_DEVICE_IDS[profile]
    try:
        hidapi_module = importlib.import_module("hidapi")
        entries = hidapi_module.enumerate()
    except Exception as exc:
        return {
            "connected": False, "hid_ready": False, "vid": None, "pid": None, "name": None,
            "status_error": f"Unable to enumerate USB HID devices: {exc}",
        }
    for entry in entries:
        vendor_id = _device_info_value(entry, "vendor_id")
        product_id = _device_info_value(entry, "product_id")
        if (vendor_id, product_id) not in expected_ids:
            continue
        raw_name = _device_info_value(entry, "product_string") or _device_info_value(entry, "manufacturer_string")
        name = raw_name.decode(errors="replace") if isinstance(raw_name, bytes) else raw_name
        return {
            "connected": True, "hid_ready": True, "vid": vendor_id, "pid": product_id,
            "name": name or REMOTE_DEVICE_NAMES.get((vendor_id, product_id)),
        }
    return {"connected": False, "hid_ready": False, "vid": None, "pid": None, "name": None}


REMOTE_DEVICE_NAMES = {
    (0x19F7, 0x0056): "RODE Wireless PRO TX",
    (0x19F7, 0x0058): "RODE Wireless PRO RX",
    (0x19F7, 0x008A): "Hendrix TX",
    (0x19F7, 0x008B): "Hendrix RX",
    (0x19F7, 0x008C): "RODE RXCC",
    (0x1A86, 0x8091): "RODE RXCC (QinHeng USB HUB alias)",
}

def _render_transport_controls() -> str:
    return """
<div id="transport-controls" style="display:flex;gap:.6rem;align-items:end;flex-wrap:wrap;margin-top:.8rem">
  <label>Connection
    <select id="transport-mode"><option value="usb">USB</option><option value="m5">M5</option></select>
  </label>
  <label>M5 serial port
    <input id="transport-port" list="transport-ports" value="/dev/ttyACM0" disabled>
    <datalist id="transport-ports"></datalist>
  </label>
  <button id="transport-apply" type="button">Apply connection</button>
  <span id="transport-status" role="status">Loading connection status...</span>
</div>
<div style="margin-top:.8rem">
  <button id="survey-start" type="button" disabled>Start Standalone Range Survey</button>
  <p id="survey-warning" style="margin:.45rem 0 0;color:#991b1b">
    Warning: starting survey mode stops normal HID control until the Stick is reset.
  </p>
</div>
"""

def _format_report(report: Sequence[int]) -> str:
    return " ".join(str(int(byte)) for byte in report)


def _format_trace(
    written_reports: Sequence[bytes],
    response_bytes: bytes | None,
) -> tuple[list[str], str | None]:
    command_sent = [_format_report(report) for report in written_reports]
    if response_bytes is None:
        return command_sent, None
    return command_sent, _format_report(response_bytes)


def _parse_raw_command(command: str) -> bytes:
    tokens = command.split()
    if not tokens:
        raise HTTPException(status_code=422, detail="Enter at least one byte.")

    parsed_bytes: list[int] = []
    for token in tokens:
        try:
            value = int(token, 10)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid byte `{token}`. Use space-separated decimal values such as `15 13 0`.",
            ) from exc
        if value < 0 or value > 255:
            raise HTTPException(status_code=422, detail=f"Byte `{token}` is out of range. Use values from 0 to 255.")
        parsed_bytes.append(value)

    return bytes(parsed_bytes)


def create_app(
    controller: RxccController | None = None,
    m5_transport_factory: Callable[[str], M5SerialHidTransport] | None = None,
    usb_identity_provider: Callable[[str], dict] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="damspy-rpicontrol",
        summary="LAN-local FastAPI service for RODE RXCC control.",
        version="0.1.0",
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")
    app.state.controller = controller or RxccController()
    app.state.wireless_pro_rx_controller = WirelessProRxController(product_id=WIRELESS_PRO_PRODUCT_IDS)
    app.state.tx_controller = HendrixController(product_id=TX_PRODUCT_ID)
    app.state.rx_controller = HendrixController(product_id=RX_PRODUCT_ID)
    app.state.test_command_controller = RxccController(product_id=TEST_COMMAND_DEVICE_IDS)
    app.state.tx_via_rxcc_controller = HendrixController(
        product_id=TX_PRODUCT_ID,
        device_factory=app.state.controller._device_factory,
        backend_name=app.state.controller.backend_name,
    )
    app.state.usb_controllers = {
        "controller": app.state.controller,
        "wireless_pro_rx_controller": app.state.wireless_pro_rx_controller,
        "tx_controller": app.state.tx_controller,
        "rx_controller": app.state.rx_controller,
        "test_command_controller": app.state.test_command_controller,
        "tx_via_rxcc_controller": app.state.tx_via_rxcc_controller,
    }
    app.state.transport_mode = TransportMode.USB
    app.state.serial_port = "/dev/ttyACM0"
    app.state.transport_connected = app.state.controller.is_available
    app.state.transport_detail = "Using direct USB HID."
    app.state.m5_transport = None
    app.state.m5_transport_factory = m5_transport_factory or M5SerialHidTransport
    app.state.usb_identity_provider = usb_identity_provider or _detect_usb_identity
    app.state.capture_lock = threading.Lock()

    def _serial_ports() -> list[str]:
        try:
            from serial.tools import list_ports
        except ImportError:
            return []
        return sorted(port.device for port in list_ports.comports())

    def _transport_status() -> TransportStatusResponse:
        return TransportStatusResponse(
            mode=app.state.transport_mode,
            serial_port=app.state.serial_port,
            available_serial_ports=_serial_ports(),
            connected=app.state.transport_connected,
            detail=app.state.transport_detail,
        )

    @app.get("/api/transport", response_model=TransportStatusResponse)
    def get_transport() -> TransportStatusResponse:
        return _transport_status()

    @app.put("/api/transport", response_model=TransportStatusResponse)
    def set_transport(payload: TransportConfigRequest) -> TransportStatusResponse:
        old_m5_transport = app.state.m5_transport
        if payload.mode == TransportMode.USB:
            for name, current_controller in app.state.usb_controllers.items():
                setattr(app.state, name, current_controller)
            app.state.transport_mode = TransportMode.USB
            app.state.serial_port = payload.serial_port
            app.state.transport_connected = app.state.controller.is_available
            app.state.transport_detail = "Using direct USB HID."
            app.state.m5_transport = None
            if old_m5_transport is not None:
                old_m5_transport.close()
            return _transport_status()

        transport = app.state.m5_transport_factory(payload.serial_port)
        device_factory = transport.device_factory
        app.state.controller = RxccController(device_factory=device_factory, backend_name=transport.backend_name)
        app.state.wireless_pro_rx_controller = WirelessProRxController(
            device_factory=device_factory, backend_name=transport.backend_name
        )
        app.state.tx_controller = HendrixController(
            product_id=TX_PRODUCT_ID, device_factory=device_factory, backend_name=transport.backend_name
        )
        app.state.rx_controller = HendrixController(
            product_id=RX_PRODUCT_ID, device_factory=device_factory, backend_name=transport.backend_name
        )
        app.state.test_command_controller = RxccController(
            product_id=TEST_COMMAND_DEVICE_IDS, device_factory=device_factory, backend_name=transport.backend_name
        )
        app.state.tx_via_rxcc_controller = HendrixController(
            product_id=TX_PRODUCT_ID, device_factory=device_factory, backend_name=transport.backend_name
        )
        app.state.transport_mode = TransportMode.M5
        app.state.serial_port = payload.serial_port
        app.state.m5_transport = transport
        try:
            status = transport.get_remote_device_info()
            app.state.transport_connected = True
            app.state.transport_detail = (
                "Connected to the M5 bridge; remote HID is ready."
                if status.connected and status.hid_ready
                else "Connected to the M5 bridge; remote HID is not ready."
            )
        except M5TransportError as exc:
            app.state.transport_connected = False
            app.state.transport_detail = str(exc)
        if old_m5_transport is not None and old_m5_transport is not transport:
            old_m5_transport.close()
        return _transport_status()

    @app.post("/api/m5/survey/start", response_model=SurveyModeResponse)
    def start_standalone_range_survey() -> SurveyModeResponse:
        failure_detail = (
            "Survey mode was not started. Keep the Stick connected; normal operation "
            "was not intentionally stopped."
        )
        if app.state.transport_mode != TransportMode.M5 or app.state.m5_transport is None:
            raise HTTPException(
                status_code=409,
                detail=f"Select and apply the M5 connection first. {failure_detail}",
            )
        try:
            app.state.m5_transport.start_standalone_survey()
        except M5TransportError as exc:
            app.state.transport_detail = str(exc)
            raise HTTPException(
                status_code=502,
                detail=f"{failure_detail} Transport error: {exc}",
            ) from exc
        app.state.transport_connected = False
        app.state.transport_detail = (
            "Standalone range survey is active; reset the Stick to restore bridge mode."
        )
        return SurveyModeResponse(
            detail=(
                "Survey mode started successfully. You may now disconnect the Stick "
                "from the Pi. Reset the Stick to return to normal bridge mode."
            )
        )

    def _capture_controllers(device_factory, backend_name):
        return {
            "rxcc": RxccController(device_factory=device_factory, backend_name=backend_name),
            "wireless-pro-rx": WirelessProRxController(device_factory=device_factory, backend_name=backend_name),
            "hendrix-tx": HendrixController(product_id=TX_PRODUCT_ID, device_factory=device_factory, backend_name=backend_name),
            "hendrix-rx": HendrixController(product_id=RX_PRODUCT_ID, device_factory=device_factory, backend_name=backend_name),
            "hendrix-tx-via-rxcc": HendrixController(
                product_id=TX_PRODUCT_ID, device_factory=device_factory, backend_name=backend_name
            ),
        }

    def _capture_controller_map(mode: TransportMode):
        if mode == TransportMode.USB:
            return {
                "rxcc": app.state.usb_controllers["controller"],
                "wireless-pro-rx": app.state.usb_controllers["wireless_pro_rx_controller"],
                "hendrix-tx": app.state.usb_controllers["tx_controller"],
                "hendrix-rx": app.state.usb_controllers["rx_controller"],
                "hendrix-tx-via-rxcc": app.state.usb_controllers["tx_via_rxcc_controller"],
            }, None
        if app.state.transport_mode == TransportMode.M5 and app.state.m5_transport is not None:
            return _capture_controllers(
                app.state.m5_transport.device_factory, app.state.m5_transport.backend_name
            ), None
        transport = app.state.m5_transport_factory(app.state.serial_port)
        return _capture_controllers(transport.device_factory, transport.backend_name), transport

    @app.get("/diagnostics/transport-capture", response_class=HTMLResponse)
    def transport_capture_page() -> HTMLResponse:
        return HTMLResponse((TEMPLATE_DIR / "transport_capture.html").read_text(encoding="utf-8"))

    @app.post("/api/transport-capture")
    def capture_transport(payload: TransportCaptureRequest) -> dict:
        temporary_transport = None
        with app.state.capture_lock:
            controllers, temporary_transport = _capture_controller_map(payload.transport)
            try:
                if payload.transport == TransportMode.USB:
                    physical_info = app.state.usb_identity_provider(payload.profile)
                    serial_port = None
                else:
                    transport = temporary_transport or app.state.m5_transport
                    serial_port = app.state.serial_port
                    try:
                        info = transport.get_remote_device_info()
                        physical_info = {
                            "connected": info.connected,
                            "hid_ready": info.hid_ready,
                            "vid": info.vendor_id,
                            "pid": info.product_id,
                            "name": REMOTE_DEVICE_NAMES.get((info.vendor_id, info.product_id)),
                        }
                    except Exception as exc:
                        physical_info = {
                            "connected": False, "hid_ready": False, "vid": None, "pid": None, "name": None,
                            "status_error": f"{type(exc).__name__}: {exc}",
                        }
                return run_transport_capture(
                    profile=payload.profile,
                    transport=payload.transport.value,
                    controller=controllers[payload.profile],
                    physical_usb_device=physical_info,
                    m5_serial_port=serial_port,
                )
            finally:
                if temporary_transport is not None:
                    temporary_transport.close()

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        active_controller: RxccController = request.app.state.controller
        backend_name = active_controller.backend_name
        backend_status = backend_name if active_controller.is_available else "unavailable"
        return HealthResponse(hid_backend=backend_status)

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return _render_device_page("rxcc")

    @app.get("/devices/{device_type}", response_class=HTMLResponse)
    def device_page(device_type: str) -> HTMLResponse:
        return _render_device_page(device_type)

    def _render_device_page(device_type: str) -> HTMLResponse:
        if device_type not in SUPPORTED_WEB_DEVICES:
            raise HTTPException(status_code=404, detail="Unknown device page.")

        nav_links = []
        for key, label in SUPPORTED_WEB_DEVICES.items():
            href = "/" if key == "rxcc" else f"/devices/{key}"
            is_active = " aria-current='page'" if key == device_type else ""
            nav_links.append(f"<a href='{href}'{is_active}>{label}</a>")
        nav_links.append("<a href='/diagnostics/transport-capture'>Transport Capture</a>")

        html = (TEMPLATE_DIR / DEVICE_TEMPLATE_FILES[device_type]).read_text(encoding="utf-8")
        html = html.replace("__DEVICE_NAV__", " · ".join(nav_links))
        html = html.replace("</nav>", "</nav>" + _render_transport_controls(), 1)
        html = html.replace("</body>", "<script src=\"/static/transport.js\"></script></body>")
        if device_type == DeviceType.RXCC.value:
            html = html.replace("__RXCC_GUIDE__", _render_rxcc_guide())
        return HTMLResponse(html)

    @app.post("/api/frontend/mode", response_model=OperationResponse)
    def set_frontend_mode(
        payload: FrontendModeRequest,
        request: Request,
    ) -> OperationResponse:
        return _execute_device_command(
            request=request,
            device_type=DeviceType.RXCC,
            command=DeviceCommand.SET_FRONTEND_MODE,
            payload=DeviceCommandRequest(mode=payload.mode),
        )

    @app.post("/api/antenna", response_model=OperationResponse)
    def set_antenna(
        payload: AntennaRequest,
        request: Request,
    ) -> OperationResponse:
        return _execute_device_command(
            request=request,
            device_type=DeviceType.RXCC,
            command=DeviceCommand.SET_ANTENNA,
            payload=DeviceCommandRequest(antenna=payload.path),
        )

    @app.post("/api/rxcc/gpio/{pin}/{level}", response_model=OperationResponse)
    def set_rxcc_gpio(pin: int, level: int, request: Request) -> OperationResponse:
        return _set_rxcc_family_gpio(DeviceType.RXCC, pin, level, request)

    def _set_rxcc_family_gpio(
        device_type: DeviceType,
        pin: int,
        level: int,
        request: Request,
    ) -> OperationResponse:
        if pin not in {0, 1, 2, 3}:
            raise HTTPException(status_code=422, detail="`pin` must be 0, 1, 2, or 3.")
        if level not in {0, 1}:
            raise HTTPException(status_code=422, detail="`level` must be 0 or 1.")

        controller = _resolve_rxcc_family_controller(request, device_type)
        try:
            reports_sent = controller.apply_gpio(pin=pin, level=level)
        except (DeviceUnavailableError, DeviceCommunicationError) as exc:
            raise _translate_device_error(exc) from exc
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return OperationResponse(
            operation="set_gpio",
            detail=f"Sent GPIO command for `{device_type.value}` pin {pin} level {level}.",
            reports_sent=reports_sent,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    @app.post("/api/rf/start", response_model=OperationResponse)
    def start_rf(
        payload: StartRfRequest,
        request: Request,
    ) -> OperationResponse:
        return _execute_device_command(
            request=request,
            device_type=DeviceType(payload.device),
            command=DeviceCommand.START_RF,
            payload=DeviceCommandRequest(
                antenna=payload.antenna,
                channel=payload.channel,
                wirepro_freq=payload.wirepro_freq,
                power=payload.power,
                wirepro_power=payload.wirepro_power,
            ),
        )

    @app.post("/api/rf/start/rxcc/raw", response_model=OperationResponse)
    def start_rf_rxcc_raw(
        payload: DeviceCommandRequest,
        request: Request,
    ) -> OperationResponse:
        return _start_rxcc_family_raw_rf(DeviceType.RXCC, payload, request)

    @app.post("/api/rf/start/wireless-pro-rx/raw", response_model=OperationResponse)
    def start_rf_wireless_pro_rx_raw(
        payload: DeviceCommandRequest,
        request: Request,
    ) -> OperationResponse:
        return _start_rxcc_family_raw_rf(DeviceType.WIRELESS_PRO_RX, payload, request)

    def _start_rxcc_family_raw_rf(
        device_type: DeviceType,
        payload: DeviceCommandRequest,
        request: Request,
    ) -> OperationResponse:
        if device_type == DeviceType.RXCC:
            if payload.channel is None or payload.power is None:
                raise HTTPException(
                    status_code=422,
                    detail="`channel` and `power` are required for raw RXCC RF start.",
                )
            controller = _resolve_rxcc_family_controller(request, device_type)
            try:
                reports_sent = controller.start_rf_raw(channel=payload.channel, power=payload.power)
            except (DeviceUnavailableError, DeviceCommunicationError) as exc:
                raise _translate_device_error(exc) from exc
            command_sent, device_response = _format_trace(*controller.get_last_io_trace())

            return OperationResponse(
                operation="start_rf_raw",
                detail=f"Sent raw RXCC RF start on channel {payload.channel} at power {payload.power}.",
                reports_sent=reports_sent,
                command_sent=command_sent,
                device_response=device_response,
                read_attempted=True,
            )

        if payload.antenna is None:
            raise HTTPException(
                status_code=422,
                detail="`antenna` is required for raw Wireless PRO RX RF start.",
            )
        if payload.wirepro_freq is None or payload.wirepro_power is None:
            raise HTTPException(
                status_code=422,
                detail="`wirepro_freq` and `wirepro_power` are required for raw Wireless PRO RX RF start.",
            )

        controller = request.app.state.wireless_pro_rx_controller
        try:
            reports_sent = controller.start_rf_raw(
                antenna=payload.antenna,
                wirepro_freq=payload.wirepro_freq,
                wirepro_power=payload.wirepro_power,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (DeviceUnavailableError, DeviceCommunicationError) as exc:
            raise _translate_device_error(exc) from exc
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return OperationResponse(
            operation="start_rf_raw",
            detail=(
                f"Sent raw RF start for `wireless-pro-rx` with wirepro_freq {payload.wirepro_freq} "
                f"using `{payload.antenna.value}` antenna at wirepro_power {payload.wirepro_power} dBm."
            ),
            reports_sent=reports_sent,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    @app.post("/api/healthcheck", response_model=HealthcheckResponse, response_model_exclude_none=True)
    def run_healthcheck() -> HealthcheckResponse:
        if app.state.transport_mode == TransportMode.M5:
            transport = app.state.m5_transport
            try:
                info = transport.get_remote_device_info()
                app.state.transport_connected = True
                app.state.transport_detail = "Connected to the M5 bridge."
            except M5TransportError as exc:
                app.state.transport_connected = False
                app.state.transport_detail = str(exc)
                return HealthcheckResponse(operation="healthcheck", transport=TransportMode.M5, passed=False, exit_code=1, connected=False, output=f"FAIL: {exc}")
            if not info.connected or not info.hid_ready:
                state = "no USB HID device is attached" if not info.connected else "the USB HID device is not ready"
                return HealthcheckResponse(operation="healthcheck", transport=TransportMode.M5, passed=False, exit_code=1, connected=info.connected, hid_ready=info.hid_ready, output=f"M5 bridge connected; {state} on the remote Core.")
            device_name = REMOTE_DEVICE_NAMES.get((info.vendor_id, info.product_id))
            vendor_id = f"0x{info.vendor_id:04X}"
            product_id = f"0x{info.product_id:04X}"
            friendly = device_name or "Unknown USB HID device"
            return HealthcheckResponse(
                operation="healthcheck", transport=TransportMode.M5, passed=True, exit_code=0, connected=True, hid_ready=True,
                vendor_id=vendor_id, product_id=product_id, device_name=device_name,
                output=f"PASS: Remote USB HID device connected: {friendly} ({vendor_id}:{product_id}).",
            )

        result = subprocess.run([sys.executable, str(HEALTHCHECK_SCRIPT_PATH)], capture_output=True, text=True, check=False)
        output = result.stdout
        if result.stderr:
            output = f"{output}\n{result.stderr}" if output else result.stderr
        return HealthcheckResponse(operation="healthcheck", passed=result.returncode == 0, exit_code=result.returncode, output=output.strip())

    @app.post("/api/test-command", response_model=OperationResponse)
    def send_test_command(payload: RawCommandRequest, request: Request) -> OperationResponse:
        controller = request.app.state.test_command_controller
        report = _parse_raw_command(payload.command)

        try:
            reports_sent = controller.send_raw_report(report)
        except (DeviceUnavailableError, DeviceCommunicationError) as exc:
            raise _translate_device_error(exc) from exc
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return OperationResponse(
            operation="send_raw_command",
            detail="Sent raw HID bytes to the first available supported test device (`rxcc`, `rx`, or `tx`).",
            reports_sent=reports_sent,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    @app.post("/api/battery/{device_type}", response_model=BatteryResponse)
    def read_battery(device_type: str, request: Request) -> BatteryResponse:
        resolved_device_type = DeviceType(device_type)
        if resolved_device_type in {DeviceType.RXCC, DeviceType.WIRELESS_PRO_RX}:
            controller = request.app.state.wireless_pro_rx_controller
            if resolved_device_type == DeviceType.RXCC:
                controller = _resolve_rxcc_family_controller(request, resolved_device_type)
            try:
                battery_info = controller.read_battery_info()
            except (DeviceUnavailableError, DeviceCommunicationError) as exc:
                raise _translate_device_error(exc) from exc
        elif resolved_device_type in {DeviceType.TX, DeviceType.RX}:
            controller = (
                request.app.state.tx_controller
                if resolved_device_type == DeviceType.TX
                else request.app.state.rx_controller
            )
            try:
                battery_info = controller.read_battery_info()
            except (
                HendrixDeviceUnavailableError,
                HendrixDeviceCommunicationError,
            ) as exc:
                raise _translate_device_error(exc) from exc
        else:
            raise HTTPException(
                status_code=404,
                detail="Battery read is only supported for RXCC, Hendrix TX/RX, and Wireless PRO RX.",
            )
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return BatteryResponse(
            detail=f"Read battery telemetry for `{resolved_device_type.value}`.",
            device=resolved_device_type,
            battery_mv=battery_info.battery_mv,
            temperature_c=battery_info.temperature_c,
            charge_state=battery_info.charge_state,
            charge_state_code=battery_info.charge_state_code,
            charge_current_ma=battery_info.charge_current_ma,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    @app.post("/api/serial-number/{device_type}", response_model=SerialNumberResponse)
    def read_serial_number(device_type: str, request: Request) -> SerialNumberResponse:
        resolved_device_type = DeviceType(device_type)
        if resolved_device_type == DeviceType.RXCC:
            controller = _resolve_rxcc_family_controller(request, resolved_device_type)
            try:
                serial_number = controller.read_serial_number()
            except (
                DeviceUnavailableError,
                DeviceCommunicationError,
            ) as exc:
                raise _translate_device_error(exc) from exc
        elif resolved_device_type == DeviceType.TX:
            controller = request.app.state.tx_controller
            try:
                serial_number = controller.read_serial_number()
            except (
                HendrixDeviceUnavailableError,
                HendrixDeviceCommunicationError,
            ) as exc:
                raise _translate_device_error(exc) from exc
        else:
            raise HTTPException(status_code=404, detail="Serial-number read is only supported for Hendrix TX and RXCC.")
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return SerialNumberResponse(
            detail=f"Read serial number for `{resolved_device_type.value}` using NVM key `NORDIC_ID`.",
            device=resolved_device_type,
            serial_number=serial_number,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    @app.post("/api/ctx/{device_type}/{level}", response_model=OperationResponse)
    def set_ctx_level(device_type: str, level: str, request: Request) -> OperationResponse:
        if device_type not in {DeviceType.TX.value, DeviceType.RX.value}:
            raise HTTPException(status_code=404, detail="CTX control is only supported for Hendrix TX/RX.")
        if level not in {"low", "high"}:
            raise HTTPException(status_code=404, detail="Unknown CTX level.")

        resolved_device_type = DeviceType(device_type)
        controller = (
            request.app.state.tx_controller
            if resolved_device_type == DeviceType.TX
            else request.app.state.rx_controller
        )
        try:
            reports_sent = controller.set_ctx(high=level == "high")
        except (
            HendrixDeviceUnavailableError,
            HendrixDeviceCommunicationError,
        ) as exc:
            raise _translate_device_error(exc) from exc
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return OperationResponse(
            operation="set_ctx",
            detail=f"Sent CTX {level.upper()} for `{resolved_device_type.value}`.",
            reports_sent=reports_sent,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    @app.post("/api/charging/{device_type}/{state}", response_model=OperationResponse)
    def set_device_charging(device_type: str, state: str, request: Request) -> OperationResponse:
        resolved_device_type = DeviceType(device_type)
        if resolved_device_type not in {DeviceType.TX, DeviceType.RXCC}:
            raise HTTPException(status_code=404, detail="Charging control is only supported for Hendrix TX and RXCC.")
        if state not in {"enable", "disable"}:
            raise HTTPException(status_code=404, detail="Unknown charging control state.")

        enabled = state == "enable"
        if resolved_device_type == DeviceType.RXCC:
            controller = _resolve_rxcc_family_controller(request, resolved_device_type)
            try:
                reports_sent = controller.set_charging(enabled=enabled)
            except (
                DeviceUnavailableError,
                DeviceCommunicationError,
            ) as exc:
                raise _translate_device_error(exc) from exc
        else:
            controller = request.app.state.tx_controller
            try:
                reports_sent = controller.set_charging(enabled=enabled)
            except (
                HendrixDeviceUnavailableError,
                HendrixDeviceCommunicationError,
            ) as exc:
                raise _translate_device_error(exc) from exc
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return OperationResponse(
            operation="set_charging",
            detail=f"Sent charging {'enable' if enabled else 'disable'} command for `{resolved_device_type.value}`.",
            reports_sent=reports_sent,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    @app.post("/api/led/{device_type}/flash/{color}", response_model=OperationResponse)
    def flash_tx_led(device_type: str, color: str, request: Request) -> OperationResponse:
        if device_type != DeviceType.TX.value:
            raise HTTPException(status_code=404, detail="LED test control is only supported for Hendrix TX.")
        if color not in TX_LED_FLASH_COLORS:
            raise HTTPException(status_code=404, detail="Unknown TX LED colour.")

        controller = request.app.state.tx_controller
        try:
            reports_sent = controller.flash_led(color_index=TX_LED_FLASH_COLORS[color])
        except (
            HendrixDeviceUnavailableError,
            HendrixDeviceCommunicationError,
        ) as exc:
            raise _translate_device_error(exc) from exc
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return OperationResponse(
            operation="flash_led",
            detail=f"Flashed the {color} LED on `tx` twice over one second.",
            reports_sent=reports_sent,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    @app.post("/api/led/{device_type}/off/all", response_model=OperationResponse)
    def turn_off_tx_leds(device_type: str, request: Request) -> OperationResponse:
        if device_type != DeviceType.TX.value:
            raise HTTPException(status_code=404, detail="LED test control is only supported for Hendrix TX.")

        controller = request.app.state.tx_controller
        try:
            reports_sent = controller.turn_off_all_leds()
        except (
            HendrixDeviceUnavailableError,
            HendrixDeviceCommunicationError,
        ) as exc:
            raise _translate_device_error(exc) from exc
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return OperationResponse(
            operation="turn_off_leds",
            detail="Turned off all LEDs on `tx`.",
            reports_sent=reports_sent,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    @app.post("/api/rf/stop", response_model=OperationResponse)
    def stop_rf(request: Request) -> OperationResponse:
        return _execute_device_command(
            request=request,
            device_type=DeviceType.RXCC,
            command=DeviceCommand.STOP_RF,
            payload=DeviceCommandRequest(),
        )

    @app.post("/api/rf/stop/{device_type}", response_model=OperationResponse)
    def stop_rf_device(device_type: str, request: Request) -> OperationResponse:
        if device_type not in {device.value for device in DeviceType}:
            raise HTTPException(status_code=404, detail="Unknown device type.")
        return _execute_device_command(
            request=request,
            device_type=DeviceType(device_type),
            command=DeviceCommand.STOP_RF,
            payload=DeviceCommandRequest(),
        )

    @app.post("/api/devices/{device_type}/commands/{command}", response_model=OperationResponse)
    def device_command(
        device_type: DeviceType,
        command: DeviceCommand,
        payload: DeviceCommandRequest,
        request: Request,
    ) -> OperationResponse:
        return _execute_device_command(
            request=request,
            device_type=device_type,
            command=command,
            payload=payload,
        )

    def _execute_device_command(
        request: Request,
        device_type: DeviceType,
        command: DeviceCommand,
        payload: DeviceCommandRequest,
    ) -> OperationResponse:
        if device_type == DeviceType.RXCC:
            controller = _resolve_rxcc_family_controller(request, device_type)
            try:
                if command == DeviceCommand.SET_FRONTEND_MODE:
                    if payload.mode is None:
                        raise HTTPException(status_code=422, detail="`mode` is required.")
                    reports_sent = controller.apply_frontend_mode(payload.mode)
                    detail = f"Applied frontend mode `{payload.mode.value}`."
                    operation = "set_frontend_mode"
                elif command == DeviceCommand.SET_ANTENNA:
                    if payload.antenna is None:
                        raise HTTPException(status_code=422, detail="`antenna` is required.")
                    reports_sent = controller.apply_antenna(payload.antenna)
                    detail = f"Selected `{payload.antenna.value}` antenna path."
                    operation = "set_antenna"
                elif command == DeviceCommand.START_RF:
                    if payload.antenna is None:
                        raise HTTPException(status_code=422, detail="`antenna` is required when starting RF for RXCC.")
                    if payload.channel is None or payload.power is None:
                        raise HTTPException(
                            status_code=422,
                            detail="`channel` and `power` are required for RF start.",
                        )
                    reports_sent = controller.start_rf(
                        antenna=payload.antenna,
                        channel=payload.channel,
                        power=payload.power,
                    )
                    detail = (
                        "Applied transmitting-pa mode, selected "
                        f"`{payload.antenna.value}` antenna, and started RF on "
                        f"channel {payload.channel} at power {payload.power}."
                    )
                    operation = "start_rf"
                elif command == DeviceCommand.STOP_RF:
                    reports_sent = controller.stop_rf()
                    detail = "Sent RF stop command."
                    operation = "stop_rf"
                else:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Command `{command.value}` is not supported for RXCC.",
                    )
            except (DeviceUnavailableError, DeviceCommunicationError) as exc:
                raise _translate_device_error(exc) from exc
            command_sent, device_response = _format_trace(*controller.get_last_io_trace())
            return OperationResponse(
                operation=operation,
                detail=detail,
                reports_sent=reports_sent,
                command_sent=command_sent,
                device_response=device_response,
                read_attempted=True,
            )

        if device_type == DeviceType.WIRELESS_PRO_RX:
            controller = request.app.state.wireless_pro_rx_controller
            try:
                if command == DeviceCommand.START_RF:
                    if payload.antenna is None:
                        raise HTTPException(
                            status_code=422,
                            detail="`antenna` is required when starting RF for Wireless PRO RX.",
                        )
                    if payload.wirepro_freq is None or payload.wirepro_power is None:
                        raise HTTPException(
                            status_code=422,
                            detail="`wirepro_freq` and `wirepro_power` are required for Wireless PRO RX RF start.",
                        )
                    reports_sent = controller.start_rf(
                        antenna=payload.antenna,
                        wirepro_freq=payload.wirepro_freq,
                        wirepro_power=payload.wirepro_power,
                    )
                    detail = (
                        f"Sent RF start for `wireless-pro-rx` with wirepro_freq {payload.wirepro_freq} "
                        f"using `{payload.antenna.value}` antenna at wirepro_power {payload.wirepro_power} dBm."
                    )
                    operation = "start_rf"
                elif command == DeviceCommand.STOP_RF:
                    reports_sent = controller.stop_rf()
                    detail = "Sent RF stop command for `wireless-pro-rx`."
                    operation = "stop_rf"
                else:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Command `{command.value}` is not supported for Wireless PRO RX. "
                            "This device uses antenna selection inside the RF start command and has no separate PA-mode control."
                        ),
                    )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except (DeviceUnavailableError, DeviceCommunicationError) as exc:
                raise _translate_device_error(exc) from exc
            command_sent, device_response = _format_trace(*controller.get_last_io_trace())
            return OperationResponse(
                operation=operation,
                detail=detail,
                reports_sent=reports_sent,
                command_sent=command_sent,
                device_response=device_response,
                read_attempted=True,
            )

        if command in {DeviceCommand.SET_FRONTEND_MODE, DeviceCommand.SET_ANTENNA}:
            raise HTTPException(
                status_code=422,
                detail=f"Command `{command.value}` is only supported for RXCC.",
            )

        controller = (
            request.app.state.tx_controller
            if device_type == DeviceType.TX
            else request.app.state.rx_controller
        )
        try:
            if command == DeviceCommand.START_RF:
                if payload.channel is None or payload.power is None:
                    raise HTTPException(
                        status_code=422,
                        detail="`channel` and `power` are required for RF start.",
                    )
                reports_sent = controller.start_rf(channel=payload.channel, power=payload.power)
                detail = (
                    f"Sent RF start for `{device_type.value}` on channel "
                    f"{payload.channel} at power {payload.power}."
                )
                operation = "start_rf"
            else:
                reports_sent = controller.stop_rf()
                detail = f"Sent RF stop command for `{device_type.value}`."
                operation = "stop_rf"
        except (
            HendrixDeviceUnavailableError,
            HendrixDeviceCommunicationError,
        ) as exc:
            raise _translate_device_error(exc) from exc
        command_sent, device_response = _format_trace(*controller.get_last_io_trace())

        return OperationResponse(
            operation=operation,
            detail=detail,
            reports_sent=reports_sent,
            command_sent=command_sent,
            device_response=device_response,
            read_attempted=True,
        )

    return app


def _resolve_rxcc_family_controller(request: Request, device_type: DeviceType) -> RxccController:
    if device_type == DeviceType.RXCC:
        return request.app.state.controller
    raise HTTPException(status_code=422, detail=f"Device `{device_type.value}` is not RXCC.")


def _render_rxcc_guide() -> str:
    figures = [
        (
            "Port mapping",
            "/static/rxcc/GPIO-ports.png",
            "Pins of interest from the RXCC schematic. This maps the software pin number to the named control line.",
            "Add `static/rxcc/GPIO-ports.png` to show the port mapping figure.",
        ),
        (
            "Antenna paths",
            "/static/rxcc/antenna-paths.png",
            "Primary and secondary antenna routing, including `ANT_SEL`.",
            "Add `static/rxcc/antenna-paths.png` to show the antenna-path schematic.",
        ),
        (
            "SKY FEM mode table",
            "/static/rxcc/sky66112-mode-table.png",
            "Reference truth table for the SKY front-end module control lines.",
            "Add `static/rxcc/sky66112-mode-table.png` to show the FEM mode table.",
        ),
    ]

    figure_markup: list[str] = []
    for heading, src, caption, fallback in figures:
        figure_markup.append(
            "\n".join(
                [
                    "<figure class='guide-figure'>",
                    f"  <figcaption><strong>{heading}</strong> {caption}</figcaption>",
                    f"  <img src='{src}' alt='{heading}' onerror=\"this.hidden=true; this.nextElementSibling.hidden=false;\">",
                    f"  <div class='guide-missing' hidden>{fallback}</div>",
                    "</figure>",
                ]
            )
        )

    return "\n".join(
        [
            "<section>",
            "  <details class='guide-panel'>",
            "    <summary>RXCC GPIO Guide: ports, pins, and mode presets</summary>",
            "    <div class='guide-content'>",
            "      <p><strong>Command format:</strong> <code>15 14 0 2 pin level</code>. Each command writes one GPIO line; the named modes are presets built from the combined states of multiple GPIOs.</p>",
            "      <div class='guide-columns'>",
            "        <div class='guide-card'>",
            "          <h3>Pin Map</h3>",
            "          <ul>",
            "            <li><code>pin 0</code> = <code>CTX</code></li>",
            "            <li><code>pin 1</code> = <code>CPS</code></li>",
            "            <li><code>pin 2</code> = <code>CRX</code></li>",
            "            <li><code>pin 3</code> = <code>ANT_SEL</code></li>",
            "          </ul>",
            "        </div>",
            "        <div class='guide-card'>",
            "          <h3>Mode Presets</h3>",
            "          <ul>",
            "            <li><strong>Transmitting PA:</strong> <code>CTX=1</code>, <code>CPS=0</code>, <code>CRX=0</code></li>",
            "            <li><strong>Bypass:</strong> <code>CTX=0</code>, <code>CPS=1</code>, <code>CRX=0</code></li>",
            "            <li><strong>Receiving:</strong> <code>CTX=0</code>, <code>CPS=0</code>, <code>CRX=1</code></li>",
            "          </ul>",
            "        </div>",
            "      </div>",
            "      <div class='guide-figures'>",
            *figure_markup,
            "      </div>",
            "    </div>",
            "  </details>",
            "</section>",
        ]
    )


def _translate_device_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (DeviceUnavailableError, HendrixDeviceUnavailableError)):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("damspy_rpicontrol.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
