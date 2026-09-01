from __future__ import annotations

from types import SimpleNamespace
from typing import Callable


def load_hidapi(import_module: Callable[[str], object]):
    """Load either supported Python binding shape for the hidapi library."""
    try:
        return import_module("hidapi")
    except ModuleNotFoundError as error:
        if error.name != "hidapi":
            raise

    hid_module = import_module("hid")
    if hasattr(hid_module, "Device"):
        return hid_module

    class Device:
        def __init__(self, *, vendor_id: int, product_id: int):
            self._device = hid_module.device()
            self._device.open(vendor_id, product_id)

        def __getattr__(self, name: str):
            return getattr(self._device, name)

    return SimpleNamespace(Device=Device, enumerate=hid_module.enumerate)
