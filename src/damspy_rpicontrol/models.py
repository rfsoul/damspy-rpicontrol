from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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

    device: str = Field(..., pattern="^(rxcc|tx|rx)$")
    antenna: AntennaPath | None = None
    channel: int = Field(..., ge=0, le=80)
    power: int = Field(..., ge=0, le=10)


class DeviceType(str, Enum):
    RXCC = "rxcc"
    TX = "tx"
    RX = "rx"


class DeviceCommand(str, Enum):
    START_RF = "start-rf"
    STOP_RF = "stop-rf"
    SET_FRONTEND_MODE = "set-frontend-mode"
    SET_ANTENNA = "set-antenna"


class DeviceCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: int | None = Field(default=None, ge=0, le=80)
    power: int | None = Field(default=None, ge=0, le=10)
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
