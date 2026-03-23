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

    antenna: AntennaPath
    channel: int = Field(..., ge=0, le=80)
    power: int = Field(..., ge=0, le=10)


class OperationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str
    status: str = "ok"
    detail: str
    reports_sent: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    service: str = "damspy-rpicontrol"
    hid_backend: str
    device: str = "RODE RXCC"
    vendor_id: str = "0x19F7"
    product_id: str = "0x008C"
