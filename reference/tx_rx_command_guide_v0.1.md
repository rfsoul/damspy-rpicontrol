# Hendrix TX/RX Command Guide v0.1

## Content

This document defines the currently validated HID commands needed to control plain Hendrix TX and Hendrix RX devices for channel selection, RF start, and RF stop.

It is intentionally separate from the RXCC guide. RXCC includes additional front-end mode and antenna-path control that should not be assumed for plain TX/RX devices.

## Device identity

- Vendor ID: `0x19F7`
- Hendrix TX Product ID: `0x008A`
- Hendrix RX Product ID: `0x008B`

## Validation status

The following is currently validated:

- Hendrix RX works with the documented RF start and RF stop command pattern.
- Hendrix TX works with the same command pattern as Hendrix RX when the product ID is changed from `0x008B` to `0x008A`.

This guide only covers that validated subset.

## Report structure

Each command is sent as a HID report with:

- Report ID: `0x0F` (`15`)
- Payload bytes following the report ID

General form:

```text
[0x0F, ...payload...]
```

Equivalent write form:

```python
dev.write(bytes([0x0F] + payload))
```

## Channel model

The validated control command sets a **channel**, not a frequency.

Current validated channel range:

- `0` to `79`

Where a frequency conversion is needed outside the HID command itself, use:

- channel `0` = `2400 MHz`
- each channel step = `1 MHz`

So:

```text
frequency_mhz = 2400 + channel
```

Examples:

- channel `0` -> `2400 MHz`
- channel `10` -> `2410 MHz`
- channel `79` -> `2479 MHz`

This frequency conversion note is provided for operator understanding only. The HID command itself carries a channel number.

## RF context-high command

Before RF start, the currently validated command sequence sends:

```text
15 14 0 2 0 1
```

Equivalent payload:

```text
[0x14, 0x00, 0x02, 0x00, 0x01]
```

This is the same command shape previously used in the working RX script and also works on TX for the tested path.

This document does not assign a deeper protocol meaning beyond the currently validated name:

- CTX HIGH

## RF start command

RF start uses this payload structure:

```text
[0x03, 0x00, channel, 0x00, power]
```

Full HID report form:

```text
[0x0F, 0x03, 0x00, channel, 0x00, power]
```

Decimal form:

```text
15 3 0 channel 0 power
```

Parameters:

- `channel`: channel index
- `power`: TX power level

Current validated ranges:

- `channel`: `0` to `79`
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

For the currently validated RF start path, use this order:

1. Send CTX HIGH
2. Send RF start with chosen channel and power

### Example

```text
15 14 0 2 0 1
15 3 0 channel 0 power
```

### Stop RF

```text
15 13 0
```

## Linux permissions

On Linux or Raspberry Pi, successful operation depends on correct `hidraw` permissions for the matching device node.

Typical approach:

- add `udev` rules for `19f7:008a`
- add `udev` rules for `19f7:008b`
- reload rules or reboot
- verify `/dev/hidraw*` permissions

## Scope and limits

This guide only covers the currently validated TX/RX control subset:

- open device by VID/PID
- send CTX HIGH
- start RF with channel and power
- stop RF

It does not define:

- RXCC front-end mode control
- RXCC antenna selection
- any unvalidated TX/RX command families

## Editing Guidelines (Do Not Modify Below This Line)

Keep this document focused on validated Hendrix TX/RX HID control behaviour.

Include:
- device identity
- HID report structure
- exact tested command bytes
- channel and power parameter meaning
- scope limits
- Linux permission notes when relevant

Do not include:
- RXCC-only front-end mode or antenna-path behaviour
- speculative protocol claims beyond what has been tested
- script implementation copied verbatim unless there is a specific need

Prefer exact command bytes and validated behaviour over inferred protocol meaning.
