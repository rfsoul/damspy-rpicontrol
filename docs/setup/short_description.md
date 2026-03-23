# Short Description

## Content

`damspy-rpicontrol` is a Raspberry Pi-hosted FastAPI control service for a RØDE RXCC device used in DAMSpy workflows.

It provides a simple, repeatable LAN interface for applying a small set of RF output parameters to the RXCC connected to the Pi, supporting both future DAMSpy automation and manual lab operation.

The service must expose a stable HTTP/JSON API for programmatic control and a lightweight browser-based web page for manual control over the LAN.

The project replaces ad-hoc HID proof-of-concept scripts with a repo-owned control layer that directly manages device behaviour through a clear and repeatable interface.

Use the HID command guide in the \`reference\` folder to understand how to communicate with the RØDE RXCC.


---

## Editing Guidelines (Do Not Modify Below This Line)

This document contains the **original idea for the project**.

Capture the intended project in a concise but specific form.

This should clearly describe:
- what the project is
- what it does
- why it exists
- any major constraints or fixed choices already known at project start

Include specific implementation or interface choices when they are already intentional and important to the project shape.

If proof-of-concept scripts or loose experimental code already exist, extract any durable behavioural or protocol knowledge from them into markdown guides in `reference/`. Remove temporary executable POC code from the repo unless it is intentionally being promoted into production-owned implementation.