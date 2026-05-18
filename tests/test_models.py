import unittest

from pydantic import ValidationError

from damspy_rpicontrol.models import (
    AntennaPath,
    DeviceCommand,
    DeviceCommandRequest,
    DeviceType,
    FrontendMode,
    StartRfRequest,
)


class StartRfRequestTest(unittest.TestCase):
    def test_accepts_documented_ranges(self) -> None:
        request = StartRfRequest(device="rxcc", antenna=AntennaPath.MAIN, channel=80, power=10)

        self.assertEqual(request.antenna, AntennaPath.MAIN)
        self.assertEqual(request.channel, 80)
        self.assertEqual(request.power, 10)

    def test_accepts_wireless_pro_rx_device(self) -> None:
        request = StartRfRequest(device="wireless-pro-rx", antenna=AntennaPath.SECONDARY, wirepro_freq=12, wirepro_power=4)

        self.assertEqual(request.device, "wireless-pro-rx")
        self.assertEqual(request.antenna, AntennaPath.SECONDARY)
        self.assertEqual(request.wirepro_freq, 12)
        self.assertEqual(request.wirepro_power, 4)

    def test_accepts_wireless_pro_negative_power_level(self) -> None:
        request = StartRfRequest(device="wireless-pro-rx", antenna=AntennaPath.MAIN, wirepro_freq=12, wirepro_power=-4)

        self.assertEqual(request.wirepro_power, -4)

    def test_rejects_channel_above_documented_range(self) -> None:
        with self.assertRaises(ValidationError):
            StartRfRequest(device="tx", channel=81, power=5)

    def test_rejects_power_above_documented_range(self) -> None:
        with self.assertRaises(ValidationError):
            StartRfRequest(antenna=AntennaPath.MAIN, channel=10, power=11)

    def test_rejects_unsupported_wireless_pro_power_level(self) -> None:
        with self.assertRaises(ValidationError):
            StartRfRequest(device="wireless-pro-rx", antenna=AntennaPath.MAIN, wirepro_freq=10, wirepro_power=2)

    def test_rejects_wireless_pro_channel_parameter(self) -> None:
        with self.assertRaises(ValidationError):
            StartRfRequest(device="wireless-pro-rx", antenna=AntennaPath.MAIN, channel=10, wirepro_power=4)

    def test_rejects_wireless_pro_power_parameter(self) -> None:
        with self.assertRaises(ValidationError):
            StartRfRequest(device="wireless-pro-rx", antenna=AntennaPath.MAIN, wirepro_freq=10, power=4)

    def test_frontend_mode_values_match_reference(self) -> None:
        self.assertEqual(FrontendMode.TRANSMITTING_PA.value, "transmitting-pa")
        self.assertEqual(FrontendMode.BYPASS.value, "bypass")
        self.assertEqual(FrontendMode.RECEIVING.value, "receiving")

    def test_device_command_values_are_stable(self) -> None:
        self.assertEqual(DeviceType.RXCC.value, "rxcc")
        self.assertEqual(DeviceType.TX.value, "tx")
        self.assertEqual(DeviceType.RX.value, "rx")
        self.assertEqual(DeviceType.WIRELESS_PRO_RX.value, "wireless-pro-rx")
        self.assertEqual(DeviceCommand.START_RF.value, "start-rf")
        self.assertEqual(DeviceCommand.STOP_RF.value, "stop-rf")

    def test_device_command_request_accepts_optional_fields(self) -> None:
        request = DeviceCommandRequest(
            mode=FrontendMode.BYPASS,
            antenna=AntennaPath.SECONDARY,
            channel=10,
            wirepro_freq=78,
            power=5,
            wirepro_power=-4,
        )
        self.assertEqual(request.mode, FrontendMode.BYPASS)
        self.assertEqual(request.antenna, AntennaPath.SECONDARY)
        self.assertEqual(request.channel, 10)
        self.assertEqual(request.wirepro_freq, 78)
        self.assertEqual(request.power, 5)
        self.assertEqual(request.wirepro_power, -4)


if __name__ == "__main__":
    unittest.main()
