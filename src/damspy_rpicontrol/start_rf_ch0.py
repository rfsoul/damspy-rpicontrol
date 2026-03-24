from __future__ import annotations

from damspy_rpicontrol.models import AntennaPath
from damspy_rpicontrol.rxcc_device import RxccController


FIXED_CHANNEL = 0
FIXED_POWER = 10


def run() -> int:
    """Start RF using fixed test settings: main antenna, channel 0, power 10."""
    controller = RxccController()
    return controller.start_rf(
        antenna=AntennaPath.MAIN,
        channel=FIXED_CHANNEL,
        power=FIXED_POWER,
    )


if __name__ == "__main__":
    run()
