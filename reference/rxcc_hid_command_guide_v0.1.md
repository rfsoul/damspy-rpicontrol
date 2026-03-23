# RXCC HID Command Guide

This document defines the RXCC HID commands needed to control front-end mode, antenna path, RF start, and RF stop.

## Device identity

- Vendor ID: `0x19F7`
- Product ID: `0x008C`

## Report structure

Each command is sent as a HID report with:

- Report ID: `0x0F` (`15`)
- Payload bytes following the report ID

General form:

```text
[0x0F, ...payload...]
```

Equivalent Python form:

```python
report = bytes([0x0F] + payload)
dev.write(report)
```

## GPIO command family

GPIO writes use this payload structure:

```text
[0x14, 0x00, 0x02, pin, level]
```

Full HID report form:

```text
[0x0F, 0x14, 0x00, 0x02, pin, level]
```

Simple decimal form for the same command family is:

```text
15 14 0 2 pin level
```

Use that form when describing RXCC control states.

## Front-end mode selection

### Transmitting-PA mode

All three commands must be sent:

```text
15 14 0 2 0 1
15 14 0 2 1 0
15 14 0 2 2 0
```

Meaning:

- pin 0 = 1
- pin 1 = 0
- pin 2 = 0

### Bypass mode

```text
15 14 0 2 0 0
15 14 0 2 1 1
15 14 0 2 2 0
```

Meaning:

- pin 0 = 0
- pin 1 = 1
- pin 2 = 0

### Receiving mode

```text
15 14 0 2 0 0
15 14 0 2 1 0
15 14 0 2 2 1
```

Meaning:

- pin 0 = 0
- pin 1 = 0
- pin 2 = 1

## Antenna selection

GPIO pin `3` selects the antenna path.

### Main antenna

```text
15 14 0 2 3 0
```

### Secondary antenna

```text
15 14 0 2 3 1
```

## RF start command

CW transmit is started with this payload structure:

```text
[0x03, 0x00, channel, 0x00, power]
```

Full HID report form:

```text
[0x0F, 0x03, 0x00, channel, 0x00, power]
```

Decimal form:

```text
15 3 0 channel, 0, power
```

Parameters:

- `channel`: channel index
- `power`: TX power level

Intended operating ranges:

- `channel`: `0` to `80`
- `power`: `0` to `10`

## RF stop command

RF stop uses this payload:

```text
[0x0D, 0x00]
```

Full HID report form:

```text
[0x0F, 0x0D, 0x00]
```

Decimal form:

```text
15 13 0
```

## Required command ordering

For normal transmit setup, use this order:

1. Set Transmitting-PA mode
2. Select antenna
3. Start CW with chosen channel and power

### Example: transmit on main antenna

```text
15 14 0 2 0 1
15 14 0 2 1 0
15 14 0 2 2 0
15 14 0 2 3 0
15 3 0 channel 0 power
```

### Example: transmit on secondary antenna

```text
15 14 0 2 0 1
15 14 0 2 1 0
15 14 0 2 2 0
15 14 0 2 3 1
15 3 0 channel 0 power
```

### Stop RF

```text
15 13 0

```


## Minimal Python example

```python
import hidapi

VENDOR_ID = 0x19F7
PRODUCT_ID = 0x008C

dev = hidapi.Device(vendor_id=VENDOR_ID, product_id=PRODUCT_ID)

def send(payload):
    dev.write(bytes([0x0F] + payload))

# Set Transmitting-PA mode
send([0x14, 0x00, 0x02, 0x00, 0x01])
send([0x14, 0x00, 0x02, 0x01, 0x00])
send([0x14, 0x00, 0x02, 0x02, 0x00])

# Select main antenna
send([0x14, 0x00, 0x02, 0x03, 0x00])

# Start CW on channel 10, power 5
send([0x03, 0x00, 10, 0x00, 5])

# Stop RF
send([0x0D, 0x00])

dev.close()
```