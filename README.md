# README.md

## Content

# damspy-rpicontrol

`damspy-rpicontrol` is a Raspberry Pi-hosted control service for a Rode RXCC device used in DAMSpy workflows.

It provides a stable LAN-accessible interface for setting a small set of RF output parameters on the connected device. The service is intended to support both programmatic control from DAMSpy-related tooling and simple manual control from a browser on the local network.

## What This Project Does

- Exposes an HTTP/JSON control interface over the LAN
- Provides a lightweight browser-based page for manual operation
- Applies supported RF output settings to a Rode RXCC connected to the Raspberry Pi

## Why It Exists

This project replaces ad-hoc HID proof-of-concept scripts with a repo-owned control layer that is easier to operate, reuse, and maintain.

The goal is to make RXCC control repeatable and clear in lab and workflow-driven environments, rather than relying on one-off local scripts or manual device handling.

## Who It Is For

This repository is for people working with DAMSpy workflows and for operators who need a simple way to control an RXCC device over a local network.

It is most relevant to:

- developers integrating RXCC control into DAMSpy automation
- lab users who need a simple browser-based control surface
- maintainers who need a clear, repo-owned interface to the device

## How It Is Used

At a high level, the expected workflow is:

1. Host the service on a Raspberry Pi connected to the RXCC device.
2. Access the service over the local network.
3. Use either the HTTP/JSON API or the browser page to apply the supported RF output parameters.

## Reference Material

The HID command guide in the [`reference/`](reference/) folder is the starting point for understanding how the service communicates with the RXCC device.
---

## Editing Guidelines (Do Not Modify Below This Line)

This document describes the project from the perspective of a **user, operator, or first-time repository reader**.

It should explain:

- what the system is
- what it broadly does
- why it exists
- who it is for, if that is known
- the general workflow of use, if that is known

Keep the README:

- clear
- practical
- easy to scan
- aligned with `docs/setup/short_description.md`

Use the README as a **usability and interpretation check** for the project idea.

It should help confirm that the intended project has been understood correctly before implementation moves too far.

Avoid including:

- low-level architecture
- detailed implementation decisions
- deep engineering discussion
- speculative future features
- internal planning detail better suited to implementation docs

The README should describe the project in a way that is useful to someone opening the repository for the first time.
