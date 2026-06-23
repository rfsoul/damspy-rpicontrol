from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

WIRELESS_PRO_RX_POWER_LEVELS = frozenset({4, 3, 0, -4, -8, -12, -16, -20, -40})


class FrontendMode(str, Enum):
    TRANSMITTING_PA = "transmitting-pa"
    BYPASS = "bypass"
    RECEIVING = "receiving"


class AntennaPath(str, Enum):
    MAIN = "main"
    SECONDARY = "secondary"


class FrontendModeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: FrontendMode


class AntennaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: AntennaPath


class StartRfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device: str = Field(..., pattern="^(rxcc|tx|rx|wireless-pro-rx)$")
    antenna: AntennaPath | None = None
    channel: int | None = Field(default=None, ge=0, le=80)
    wirepro_freq: int | None = Field(default=None, ge=0, le=80)
    power: int | None = Field(default=None, ge=0, le=10)
    wirepro_power: int | None = Field(default=None, ge=-40, le=10)

    @model_validator(mode="after")
    def validate_device_specific_power(self) -> "StartRfRequest":
        if self.device == "wireless-pro-rx":
            if self.antenna is None:
                raise ValueError("`antenna` is required for wireless-pro-rx RF start.")
            if self.wirepro_freq is None:
                raise ValueError("`wirepro_freq` is required for wireless-pro-rx RF start.")
            if self.channel is not None:
                raise ValueError("`channel` is not supported for wireless-pro-rx RF start. Use `wirepro_freq`.")
            if self.wirepro_power is None:
                raise ValueError("`wirepro_power` is required for wireless-pro-rx RF start.")
            if self.power is not None:
                raise ValueError("`power` is not supported for wireless-pro-rx RF start. Use `wirepro_power`.")
            if self.wirepro_power not in WIRELESS_PRO_RX_POWER_LEVELS:
                allowed_values = ", ".join(str(value) for value in sorted(WIRELESS_PRO_RX_POWER_LEVELS, reverse=True))
                raise ValueError(
                    "wireless-pro-rx power must be one of: "
                    f"{allowed_values}."
                )
            return self

        if self.channel is None:
            raise ValueError("`channel` is required for this device.")
        if self.wirepro_freq is not None:
            raise ValueError("`wirepro_freq` is only supported for wireless-pro-rx.")
        if self.wirepro_power is not None:
            raise ValueError("`wirepro_power` is only supported for wireless-pro-rx.")
        if self.power is None:
            raise ValueError("`power` is required for this device.")
        return self


class DeviceType(str, Enum):
    RXCC = "rxcc"
    TX = "tx"
    RX = "rx"
    WIRELESS_PRO_RX = "wireless-pro-rx"


class DeviceCommand(str, Enum):
    START_RF = "start-rf"
    STOP_RF = "stop-rf"
    SET_FRONTEND_MODE = "set-frontend-mode"
    SET_ANTENNA = "set-antenna"


class DeviceCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: int | None = Field(default=None, ge=0, le=80)
    wirepro_freq: int | None = Field(default=None, ge=0, le=80)
    power: int | None = Field(default=None, ge=0, le=10)
    wirepro_power: int | None = Field(default=None, ge=-40, le=10)
    antenna: AntennaPath | None = None
    mode: FrontendMode | None = None


class OperationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str
    status: str = "ok"
    detail: str
    reports_sent: int
    command_sent: list[str] = Field(default_factory=list)
    device_response: str | None = None
    read_attempted: bool = False


class BatteryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str = "read_battery"
    status: str = "ok"
    detail: str
    device: DeviceType
    battery_mv: int
    temperature_c: int
    charge_state: str
    charge_state_code: int
    charge_current_ma: int
    reports_sent: int = 1
    command_sent: list[str] = Field(default_factory=list)
    device_response: str | None = None
    read_attempted: bool = False


class SerialNumberResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str = "read_serial_number"
    status: str = "ok"
    detail: str
    device: DeviceType
    serial_number: str
    reports_sent: int = 1
    command_sent: list[str] = Field(default_factory=list)
    device_response: str | None = None
    read_attempted: bool = False


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    service: str = "damspy-rpicontrol"
    hid_backend: str
    device: str = "RODE RXCC"
    vendor_id: str = "0x19F7"
    product_id: str = "0x008C"


class HealthcheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str
    status: str = "ok"
    passed: bool
    exit_code: int
    output: str
