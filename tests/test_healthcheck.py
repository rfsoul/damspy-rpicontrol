import unittest

from damspy_rpicontrol.healthcheck import SUPPORTED_PRODUCTS


class HealthcheckSupportTest(unittest.TestCase):
    def test_wireless_pro_product_ids_are_supported(self) -> None:
        self.assertEqual(SUPPORTED_PRODUCTS["0056"], "RODE Wireless PRO TX")
        self.assertEqual(SUPPORTED_PRODUCTS["0058"], "RODE Wireless PRO RX")

    def test_rxcc_usb_hub_alias_is_supported(self) -> None:
        self.assertEqual(SUPPORTED_PRODUCTS["008c"], "RODE RXCC")
        self.assertEqual(SUPPORTED_PRODUCTS["8091"], "RODE RXCC (QinHeng USB HUB alias)")


if __name__ == "__main__":
    unittest.main()
