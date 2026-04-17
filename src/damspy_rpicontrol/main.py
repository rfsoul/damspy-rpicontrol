from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

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
    StartRfRequest,
)
from damspy_rpicontrol.hendrix_device import (
    DeviceCommunicationError as HendrixDeviceCommunicationError,
    DeviceUnavailableError as HendrixDeviceUnavailableError,
    HendrixController,
    RX_PRODUCT_ID,
    TX_PRODUCT_ID,
)
from damspy_rpicontrol.rxcc_device import (
    DeviceCommunicationError,
    DeviceUnavailableError,
    RxccController,
)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
HEALTHCHECK_SCRIPT_PATH = Path(__file__).resolve().parent / "healthcheck.py"
SUPPORTED_WEB_DEVICES: dict[str, str] = {
    "rxcc": "RODE RXCC 008C",
    "tx": "Hendrix TX 008A",
    "rx": "Hendrix RX 008B",
}
DEVICE_TEMPLATE_FILES: dict[str, str] = {
    "rxcc": "rxcc.html",
    "tx": "tx.html",
    "rx": "rx.html",
}


def create_app(controller: RxccController | None = None) -> FastAPI:
    app = FastAPI(
        title="damspy-rpicontrol",
        summary="LAN-local FastAPI service for RODE RXCC control.",
        version="0.1.0",
    )
    app.state.controller = controller or RxccController()
    app.state.tx_controller = HendrixController(product_id=TX_PRODUCT_ID)
    app.state.rx_controller = HendrixController(product_id=RX_PRODUCT_ID)

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

        html = (TEMPLATE_DIR / DEVICE_TEMPLATE_FILES[device_type]).read_text(encoding="utf-8")
        html = html.replace("__DEVICE_NAV__", " · ".join(nav_links))
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
                power=payload.power,
            ),
        )

    @app.post("/api/healthcheck", response_model=HealthcheckResponse)
    def run_healthcheck() -> HealthcheckResponse:
        result = subprocess.run(
            [sys.executable, str(HEALTHCHECK_SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout
        if result.stderr:
            output = f"{output}\n{result.stderr}" if output else result.stderr

        passed = result.returncode == 0
        return HealthcheckResponse(
            operation="healthcheck",
            passed=passed,
            exit_code=result.returncode,
            output=output.strip(),
        )

    @app.post("/api/battery/{device_type}", response_model=BatteryResponse)
    def read_battery(device_type: str, request: Request) -> BatteryResponse:
        if device_type not in {DeviceType.TX.value, DeviceType.RX.value}:
            raise HTTPException(status_code=404, detail="Battery read is only supported for Hendrix TX/RX.")

        resolved_device_type = DeviceType(device_type)
        controller = (
            request.app.state.tx_controller
            if resolved_device_type == DeviceType.TX
            else request.app.state.rx_controller
        )
        try:
            battery_mv = controller.read_battery_mv()
        except (
            HendrixDeviceUnavailableError,
            HendrixDeviceCommunicationError,
        ) as exc:
            raise _translate_device_error(exc) from exc

        return BatteryResponse(
            detail=f"Read battery voltage for `{resolved_device_type.value}`.",
            device=resolved_device_type,
            battery_mv=battery_mv,
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

        return OperationResponse(
            operation="set_ctx",
            detail=f"Sent CTX {level.upper()} for `{resolved_device_type.value}`.",
            reports_sent=reports_sent,
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
            controller = request.app.state.controller
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
                        raise HTTPException(
                            status_code=422,
                            detail="`antenna` is required when starting RF for RXCC.",
                        )
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
            return OperationResponse(operation=operation, detail=detail, reports_sent=reports_sent)

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
                    f"Sent CTX HIGH and RF start for `{device_type.value}` "
                    f"on channel {payload.channel} at power {payload.power}."
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

        return OperationResponse(operation=operation, detail=detail, reports_sent=reports_sent)

    return app


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
