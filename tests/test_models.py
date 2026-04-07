import unittest

from pydantic import ValidationError

from damspy_rpicontrol.models import AntennaPath, FrontendMode, StartRfRequest


class StartRfRequestTest(unittest.TestCase):
    def test_accepts_documented_ranges(self) -> None:
        request = StartRfRequest(device="rxcc", antenna=AntennaPath.MAIN, channel=79, power=10)

        self.assertEqual(request.antenna, AntennaPath.MAIN)
        self.assertEqual(request.channel, 79)
        self.assertEqual(request.power, 10)

    def test_rejects_channel_above_documented_range(self) -> None:
        with self.assertRaises(ValidationError):
            StartRfRequest(device="tx", channel=80, power=5)

    def test_rejects_power_above_documented_range(self) -> None:
        with self.assertRaises(ValidationError):
            StartRfRequest(antenna=AntennaPath.MAIN, channel=10, power=11)

    def test_frontend_mode_values_match_reference(self) -> None:
        self.assertEqual(FrontendMode.TRANSMITTING_PA.value, "transmitting-pa")
        self.assertEqual(FrontendMode.BYPASS.value, "bypass")
        self.assertEqual(FrontendMode.RECEIVING.value, "receiving")


if __name__ == "__main__":
    unittest.main()
