#!/usr/bin/env python3
import glob
import importlib
import os
import subprocess
import sys
from pathlib import Path


SUPPORTED_DEVICE_IDS = {
    ("19f7", "0056"): "RODE Wireless PRO TX",
    ("19f7", "0058"): "RODE Wireless PRO RX",
    ("19f7", "008a"): "Hendrix TX",
    ("19f7", "008b"): "Hendrix RX",
    ("19f7", "008c"): "RODE RXCC",
    ("1a86", "8091"): "RODE RXCC (QinHeng USB HUB alias)",
}
SUPPORTED_PRODUCTS = {product_id: label for (_, product_id), label in SUPPORTED_DEVICE_IDS.items()}


def run_command(cmd):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as exc:
        return 1, "", str(exc)


def print_section(title):
    print(f"===== {title} =====")


def find_supported_lsusb_lines():
    code, stdout, stderr = run_command(["lsusb"])
    if code != 0:
        print("FAIL: Could not run lsusb")
        if stderr:
            print(stderr)
        sys.exit(1)

    lines = []
    for line in stdout.splitlines():
        lowered_line = line.lower()
        for vendor_id, product_id in SUPPORTED_DEVICE_IDS:
            if f"id {vendor_id}:{product_id}" in lowered_line:
                lines.append(line)
                break

    return lines


def list_hidraw_nodes():
    return sorted(glob.glob("/dev/hidraw*"))


def resolve_usb_device_from_hidraw(hidraw_node):
    sys_node = Path("/sys/class/hidraw") / Path(hidraw_node).name
    try:
        real_path = sys_node.resolve()
    except Exception:
        return None, None

    usb_dev = None
    interface_path = None

    for part in real_path.parts:
        if part.startswith("1-") and ":" not in part:
            usb_dev = part
        if part.startswith("1-") and ":" in part:
            interface_path = part

    return usb_dev, str(real_path)


def read_sysfs_text(path):
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


def get_usb_device_info(usb_dev):
    usb_sys = Path("/sys/bus/usb/devices") / usb_dev
    if not usb_sys.exists():
        return None

    vendor = read_sysfs_text(usb_sys / "idVendor")
    product_id = read_sysfs_text(usb_sys / "idProduct")

    if vendor is None or product_id is None:
        return None

    return {
        "usb_path": usb_dev,
        "vendor": vendor.lower(),
        "product_id": product_id.lower(),
        "product": read_sysfs_text(usb_sys / "product") or "",
        "manufacturer": read_sysfs_text(usb_sys / "manufacturer") or "",
        "speed": read_sysfs_text(usb_sys / "speed") or "",
        "version": read_sysfs_text(usb_sys / "version") or "",
    }


def test_open(path):
    try:
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        os.close(fd)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def load_hidapi_module():
    try:
        return importlib.import_module("hidapi"), ""
    except Exception as exc:
        return None, str(exc)


def test_hidapi_open(vendor_id, product_id):
    hidapi_module, error = load_hidapi_module()
    if hidapi_module is None:
        return False, f"hidapi import failed ({error})"

    device = None
    try:
        device = hidapi_module.Device(vendor_id=int(vendor_id, 16), product_id=int(product_id, 16))
        set_nonblocking = getattr(device, "set_nonblocking", None)
        if callable(set_nonblocking):
            set_nonblocking(True)
        return True, ""
    except Exception as exc:
        return False, str(exc)
    finally:
        if device is not None:
            try:
                device.close()
            except Exception:
                pass


def main():
    print_section("HID HEALTH CHECK")
    code, date_out, _ = run_command(["date"])
    print(f"Time: {date_out if date_out else 'Unknown'}")
    print()

    print_section("SUPPORTED USB DEVICES")
    lsusb_lines = find_supported_lsusb_lines()
    if not lsusb_lines:
        supported_list = ", ".join(f"{vendor}:{product}" for vendor, product in SUPPORTED_DEVICE_IDS)
        print(f"FAIL: No supported USB devices found in lsusb ({supported_list})")
        sys.exit(1)

    for line in lsusb_lines:
        print(line)
    print()

    print_section("HIDRAW NODES")
    hidraw_nodes = list_hidraw_nodes()
    if hidraw_nodes:
        for node in hidraw_nodes:
            try:
                st = os.stat(node)
                mode = oct(st.st_mode)[-3:]
                print(f"{node}  mode={mode}  uid={st.st_uid}  gid={st.st_gid}")
            except Exception as exc:
                print(f"{node}  stat failed: {exc}")
    else:
        print("No /dev/hidraw* nodes found")
    print()

    print_section("HID MAPPING")
    found_any_supported_hid = False
    mapped_supported_devices = []

    if not hidraw_nodes:
        print("No hidraw nodes found")
    else:
        for node in hidraw_nodes:
            usb_dev, resolved_path = resolve_usb_device_from_hidraw(node)
            if not usb_dev:
                continue

            info = get_usb_device_info(usb_dev)
            if not info:
                continue

            device_key = (info["vendor"], info["product_id"])
            if device_key not in SUPPORTED_DEVICE_IDS:
                continue

            found_any_supported_hid = True
            mapped_supported_devices.append(device_key)
            print(node)
            print(f"  usb path: {info['usb_path']}")
            print(f"  vid:pid: {info['vendor']}:{info['product_id']}")
            print(f"  label: {SUPPORTED_DEVICE_IDS[device_key]}")
            if info["manufacturer"]:
                print(f"  manufacturer: {info['manufacturer']}")
            if info["product"]:
                print(f"  product: {info['product']}")
            if info["speed"]:
                print(f"  speed: {info['speed']}M")
            if info["version"]:
                print(f"  usb version: {info['version']}")
            if resolved_path:
                print(f"  sysfs: {resolved_path}")

            ok, err = test_open(node)
            if ok:
                print("  open test: PASS")
            else:
                print(f"  open test: FAIL ({err})")
            print()

    if not found_any_supported_hid:
        print("No hidraw nodes mapped to supported device identities")
        print()

    print_section("HIDAPI OPEN TESTS")
    if not mapped_supported_devices:
        print("FAIL: No supported Hendrix/RXCC/Wireless PRO devices were mapped to hidraw nodes")
        sys.exit(1)

    hidapi_failures = []
    for vendor_id, product_id in sorted(set(mapped_supported_devices)):
        label = SUPPORTED_DEVICE_IDS[(vendor_id, product_id)]
        ok, err = test_hidapi_open(vendor_id, product_id)
        if ok:
            print(f"{label} ({vendor_id}:{product_id})  hidapi open: PASS")
        else:
            hidapi_failures.append(((vendor_id, product_id), err))
            print(f"{label} ({vendor_id}:{product_id})  hidapi open: FAIL ({err})")
    print()

    if hidapi_failures:
        print_section("RESULT")
        print("FAIL: USB presence is OK, but the hidapi open path used by the server is failing.")
        sys.exit(1)

    print_section("RESULT")
    print("PASS: Supported device nodes are present and hidapi can open them.")


if __name__ == "__main__":
    main()
