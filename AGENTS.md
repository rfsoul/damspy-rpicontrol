# AGENTS.md

This repository controls real hardware from a Raspberry Pi.

The codebase is mature enough that agents should prefer narrow, practical
changes over large process-driven rewrites.

## Working Style

Make the smallest useful change.

Do not introduce new architecture, documentation structure, CI, test framework,
or repository process unless explicitly asked.

Do not perform broad refactors while changing device-control behaviour.

When modifying code, explain:
- what changed
- which command path is affected
- whether real-device testing is required

## Hardware-Control Changes

Treat these as hardware-control changes:
- HID bytes or payload construction
- report IDs
- VID/PID selection
- hidraw/device discovery
- command timing
- response parsing
- device mode changes

For hardware-control changes:
- show the relevant changed bytes or payloads where practical
- do not claim automated checks prove real hardware behaviour
- provide a simple Raspberry Pi test command or manual test step
- clearly state what terminal output or device behaviour to look for

## Validation

Run lightweight checks if they already exist and are quick.

Do not add, expand, or require CI unless explicitly asked.

Do not require real hardware for automated tests.

If hardware validation is needed, say so plainly and leave that test to the
human operator.

## Repository Context

Only read extra documentation when it is directly relevant to the requested
change.

Avoid editing docs unless the user specifically asks for documentation changes.

## Commit Message

When changes are complete, provide a suggested git commit message.

The commit message should include:
- a concise subject line
- a short body explaining what changed
- any hardware validation still required

For hardware-control changes, mention the affected device or command path.

Example:

```text
Print Hendrix TX HID response bytes

Update the Hendrix TX send path to read and print any response bytes after
writing a HID report. This makes Pi-side hardware testing easier when checking
whether the device acknowledges a command.

Hardware validation is still required on the Raspberry Pi with the Hendrix TX
connected.