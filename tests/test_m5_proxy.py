import unittest

from damspy_rpicontrol.m5_proxy import M5ProxyBroker


class FakeSerial:
    def __init__(self):
        self.writes = []

    def read(self, _size=1):
        return b""

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)

    def close(self):
        return None


class FakeHid:
    def __init__(self):
        self.writes = []
        self.reads = [b"\x02\x61\x41"]
        self.closed = False

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)

    def read(self, _length, _timeout_ms):
        return self.reads.pop(0) if self.reads else b""

    def close(self):
        self.closed = True


class M5ProxyBrokerTest(unittest.TestCase):
    def setUp(self):
        self.serial = FakeSerial()
        self.hid = FakeHid()
        self.broker = M5ProxyBroker(
            "/dev/core",
            lambda: self.hid,
            lambda: {"connected": True, "hid_ready": True, "vid": 0x19F7, "pid": 0x008C},
            serial_factory=lambda _port, _baud: self.serial,
        )

    def tearDown(self):
        self.broker.close()

    def test_status_returns_direct_usb_identity(self):
        response = self.broker._handle_line(b"@M5PX1,REQ,00000001,05,")
        self.assertEqual(response, b"@M5PX1,RSP,00000001,06,0101f7198c00")

    def test_write_and_read_share_one_open_hid_device(self):
        write = self.broker._handle_line(b"@M5PX1,REQ,00000002,01,016100")
        read = self.broker._handle_line(b"@M5PX1,REQ,00000003,03,1100c8000000")
        self.assertEqual(write, b"@M5PX1,RSP,00000002,02,000300")
        self.assertEqual(read, b"@M5PX1,RSP,00000003,04,000300026141")
        self.assertEqual(self.hid.writes, [b"\x01\x61\x00"])
        self.assertFalse(self.hid.closed)

    def test_empty_read_maps_to_tunnel_timeout(self):
        self.hid.reads = []
        response = self.broker._handle_line(b"@M5PX1,REQ,00000004,03,1100c8000000")
        self.assertEqual(response, b"@M5PX1,RSP,00000004,04,010000")


if __name__ == "__main__":
    unittest.main()
