# Project Definition

## Content

### Problem
DAMSpy lab workflows currently rely on ad-hoc HID proof-of-concept scripts to control supported RF settings on a connected RØDE RXCC device. This creates inconsistency in operation, increases setup friction for both manual use and automation, and makes repeatable LAN-based control harder than it should be.

### Target User
Primary users are:

- **Lab operators** who need simple, repeatable manual control from a browser on the local network
- **Developers/integrators** who need a predictable HTTP/JSON interface for DAMSpy-linked automation

### Core Capability
Provide a repository-owned Raspberry Pi-hosted control service that exposes a stable LAN interface for a constrained set of RXCC controls (mode, antenna selection, RF start, RF stop), replacing one-off scripts with consistent, repeatable behavior.

### System Scope
#### Included
- Running as a local service on a Raspberry Pi connected to an RXCC
- Exposing a stable HTTP/JSON API for supported control operations
- Providing a lightweight browser-based control page for manual operation
- Applying only the documented and supported RXCC command set for:
  - front-end mode selection
  - antenna path selection
  - RF start (with channel and power parameters)
  - RF stop
- Enforcing input bounds and returning clear errors for invalid requests or device communication failures

#### Excluded
- General-purpose or arbitrary HID command passthrough
- Full RXCC feature coverage beyond the documented supported control set
- Cloud-first, internet-exposed, or multi-tenant deployment requirements
- User accounts, role-based access control, or enterprise authentication flows
- Broader DAMSpy orchestration logic outside this control-layer responsibility
- Long-term data storage, analytics, or reporting systems

### Inputs
- HTTP API requests from LAN clients
- Browser form submissions from the local manual control page
- Required control parameters for supported operations (including channel and power where applicable)
- RXCC device availability via direct HID connection on the Raspberry Pi

### Outputs
- Deterministic control actions applied to the connected RXCC for supported operations
- HTTP/JSON responses indicating success/failure and validation errors
- Browser-visible status/feedback for manual operations

### Non-Goals
- Acting as a full RF planning or spectrum-management platform
- Replacing DAMSpy end-to-end workflow orchestration
- Supporting undocumented, inferred, or experimental RXCC commands in the primary interface
- Delivering a feature-rich front-end application beyond a minimal operator control page

### Success Criteria
- Operators and integrators can reliably perform the supported RXCC control operations over the LAN
- The same constrained operations are accessible via both API and manual web page
- Requests with out-of-bounds or invalid parameters are rejected consistently
- The service replaces ad-hoc control scripts as the normal operating path for the supported controls

### Constraints
- Must run on Raspberry Pi in the intended lab environment
- Must communicate directly with the RXCC through HID
- Must keep the control surface intentionally narrow to preserve repeatability and operational safety
- Must stay aligned with documented RXCC command behavior from repository reference material

---

## Editing Guidelines (Do Not Modify Below This Line)

This document describes the problem the system solves.

It intentionally avoids implementation details.

Architecture and technology choices are described elsewhere.

---

# Problem

Describe the real-world problem the system solves.

Focus on the user's perspective.

---

# Target User

Describe who the system is for.

Examples:

• contractors  
• developers  
• Etsy sellers  
• RF engineers  

---

# Core Capability

Describe the primary capability of the system.

The system should ideally do **one thing extremely well**.

---

# System Scope

Define the **boundary of responsibility** for the system.

This section clarifies what the system **includes** and what it **intentionally excludes**.

### Included

Describe the responsibilities the system **does perform**.

Examples:

• generating invoices from user input  
• storing collected data  
• triggering notifications  

### Excluded

Describe capabilities that are **explicitly outside the scope** of the system.

Examples:

• enterprise billing systems  
• full accounting software  
• user account management  
• large-scale analytics  

Items listed here may appear in `futuredirections.md` but are not part of the current system.

---

# Inputs

What information enters the system?

Examples:

• emails  
• API requests  
• files  
• sensor readings  

---

# Outputs

What does the system produce?

Examples:

• invoices  
• reports  
• alerts  
• stored data  

---

# Non-Goals

What the system explicitly does **not** attempt to do.

This prevents scope creep.

---

# Success Criteria

How we know the system is working.

Examples:

• an invoice is generated within 10 seconds  
• data is stored reliably  
• users receive expected output  

---

# Constraints

Known limitations.

Examples:

• must run on Vercel  
• must use Gmail API  
• must run on Raspberry Pi  
• must operate without user accounts
