# implementation_strategy.md

## Content

### Phase 1 Build Goal

Phase 1 should produce a small, working Raspberry Pi-hosted FastAPI service that can control a connected RØDE RXCC over HID from the local network.

The first implementation should prove three things:

- the Pi can reliably issue the documented RXCC HID commands
- a stable HTTP/JSON interface can drive the supported operations
- a lightweight browser page can trigger the same supported operations without separate tooling

This phase should favor operational correctness and a clear control path over architectural completeness.

### Chosen Technical Approach

- Python service using FastAPI, as stated in `docs/setup/short_description.md`
- Direct HID communication from the service to the RXCC using a Python HID library compatible with the reference guide example
- One FastAPI process on the Raspberry Pi, serving both JSON endpoints and the manual control page
- No database, background worker, message queue, or multi-service split in Phase 1

The implementation should stay close to the reference command guide and avoid unnecessary abstraction in the first pass.

### Intended Runtime Structure

The runtime should be a single LAN-local web service running on the Raspberry Pi connected to the RXCC.

The service should have three layers:

1. HTTP layer: FastAPI routes for JSON control operations, health/status, and the manual browser page
2. Validation/orchestration layer: request validation, supported-operation mapping, and command ordering rules
3. Device layer: HID device open/write/close logic and construction of the exact RXCC reports defined in `reference/rxcc_hid_command_guide_v0.1.md`

The device layer should be treated as the only place allowed to emit raw HID reports.

For Phase 1, device access should be serialized inside the process with a lock so that overlapping requests cannot interleave writes to the RXCC.

For simplicity and reliability, each control request should:

- open the RXCC by the documented vendor/product IDs
- send the required ordered command sequence
- report success or failure clearly
- close the device handle

Phase 1 should not depend on a long-lived HID session or hidden background state.

### First Practical Implementation Shape

Runtime code should live under `src/`.

The initial implementation should be small and explicit. A suitable first shape is:

- `src/damspy_rpicontrol/main.py`: FastAPI app, route registration, and startup wiring
- `src/damspy_rpicontrol/models.py`: request/response models and supported enum values
- `src/damspy_rpicontrol/rxcc_device.py`: HID transport, report construction, and ordered RXCC operations
- `src/damspy_rpicontrol/templates/index.html` or equivalent minimal web page template for manual control

If the first pass is easier to make correct with fewer files, combining `main.py`, models, and route logic is acceptable. The HID report-building and send logic should still remain clearly separated from HTML and request parsing.

### Supported Phase 1 Behaviour

Phase 1 should implement only the supported control set implied by the project docs and explicitly documented in the reference guide:

- set front-end mode: `transmitting-pa`, `bypass`, `receiving`
- set antenna path: `main`, `secondary`
- start RF using channel and power values within the documented operating ranges
- stop RF

The JSON API should be explicit rather than generic. A practical minimum API shape is:

- `GET /health`
- `GET /` for the manual control page
- `POST /api/frontend/mode`
- `POST /api/antenna`
- `POST /api/rf/start`
- `POST /api/rf/stop`

`POST /api/rf/start` should accept the parameters needed for transmit start and should internally enforce the documented normal ordering:

1. set `transmitting-pa` mode
2. set antenna path
3. send RF start with channel and power

This keeps the API stable for callers and avoids forcing DAMSpy tooling or browser users to reproduce low-level command sequencing themselves.

The manual browser page should call the same backend operations as the JSON API. It should remain lightweight: plain forms or minimal JavaScript is sufficient.

### Reference-Driven Implementation Rules

The RXCC HID command guide should be used as the command source for Phase 1.

Key implementation rules taken from the reference guide are:

- use vendor ID `0x19F7` and product ID `0x008C`
- send HID reports with report ID `0x0F`
- use the documented GPIO report family for mode and antenna selection
- use the documented RF start report form with `channel` and `power`
- use the documented RF stop report
- preserve the documented command ordering for normal transmit setup

The reference guide is protocol guidance, not a service design. It should define how commands are sent, not expand the project beyond the LAN API plus lightweight browser control described in the project docs.

### Validation Approach

Phase 1 validation should start with correctness of command construction and hardware behaviour, then expand into repeatable repository validation.

The first implementation should be validated in three ways:

1. local code-level tests for request validation and HID report construction
2. hands-on manual testing on a Raspberry Pi with a connected RXCC
3. repository validation through `make ci` for checks that do not require the physical device

The minimum manual hardware checklist should confirm:

- the service starts on the Pi and is reachable over the LAN
- the manual browser page loads and can trigger supported actions
- each mode command sends the expected GPIO sequence
- antenna selection sends the correct pin write
- RF start sends the ordered mode, antenna, then start sequence
- RF stop sends the documented stop command
- invalid channel or power inputs are rejected before HID writes occur

Hardware-dependent tests should not be required for default CI. CI should focus on unit-level validation of the API layer and command-building logic, while manual hardware verification remains the acceptance check for actual device behaviour.

### Constraints, Tradeoffs, and Forbidden Shortcuts

The Phase 1 implementation must stay within the documented project scope.

Important constraints:

- keep the service LAN-local in intent and deployment model
- support only the documented RXCC command set used by this project
- keep the API stable and explicit for the supported operations
- prefer a small correct service over an over-abstracted design

Forbidden shortcuts:

- do not expose arbitrary HID passthrough or a raw command execution endpoint
- do not silently widen the supported feature set beyond the documented commands
- do not move core control behaviour into browser-only logic
- do not treat reference snippets as production code to run unchanged
- do not claim success before the HID command sequence has actually been attempted
- do not add persistence, queues, or multi-process orchestration without a documented need
- do not rely on undocumented RXCC state readback or inferred device behaviour

Tradeoffs accepted in Phase 1:

- a simple in-process controller is preferred over a more layered architecture
- HTML can be minimal if the core operations are clear and reliable
- the service may start with limited observability as long as failures are surfaced clearly
- the first pass may be implemented in a small number of files if that improves delivery of a working control path

### Phase 1 Outcome

At the end of this phase, the repository should have a working FastAPI-based RXCC control service on Raspberry Pi with:

- a stable LAN JSON API for the supported control operations
- a lightweight browser page using the same backend operations
- direct HID communication aligned with the reference guide
- a validation path that separates hardware-free checks from hardware-backed acceptance

That is the correct minimum working implementation for this project. Additional structure should only be added later if the first working version proves insufficient.



## DO NOT MODIFY BELOW THIS LINE

### Purpose of This Document

`implementation_strategy.md` defines **how the system will be built** during its initial implementation phase.

It translates the intent described in:

- `docs/setup/short_description.md`
- `README.md`
- relevant guide documents in `reference/`

into a **practical construction plan** for the repository.

This document is used by both humans and automated agents to understand:

- the selected technical approach
- the intended runtime structure
- the first implementation shape
- validation expectations
- constraints that must not be violated

---

### Relationship to Other Documents

Default Phase 1 flow:

`short_description → reference/ → README → implementation_strategy → liveplan → code`

Each stage becomes progressively more concrete.

`implementation_strategy.md` bridges **project intent and implementation**.

`project_definition.md` is not part of the default Phase 1 path. If it exists later, it may provide additional structure, but this document must remain valid without it.

---

### What Belongs in the Content Section

The content section should include:

- chosen technology stack
- intended runtime architecture approach
- first implementation shape
- validation strategy
- important constraints or forbidden shortcuts
- any implementation guidance taken from relevant `reference/` documents

The goal is to make the **first coding pass clear and well-directed**.

---

### First Implementation Expectations

The strategy should explicitly define, where applicable:

- what files or components should be created first
- what libraries or frameworks may be used
- the minimal required behaviour
- what runtime pattern is intended
- what shortcuts are not acceptable

This ensures the **initial code establishes the correct foundation**.

Later refactoring may improve structure, but should not drift away from the intended approach without the document being updated.

---

### Use of Reference Material

Relevant documents in `reference/` may contain:

- prior scripts
- operating notes
- protocol details
- examples of known-good behaviour
- constraints from existing systems

These documents may strongly inform the implementation strategy.

However:

- `short_description.md` remains the source of truth for project intent
- `README.md` remains the user-facing interpretation
- `reference/` should guide implementation, not silently redefine the project

If a reference guide conflicts with the active setup documents, the conflict should be resolved explicitly in the Content section.

---

### Relationship to Liveplan

`liveplan.md` breaks the strategy into concrete implementation steps.

Each active liveplan step should remain aligned with the strategy.

If the strategy changes significantly, the liveplan should be updated to match.

---

### Editing Rules

When editing the **Content section**:

- keep it concise and directive
- avoid speculation or brainstorming
- avoid historical notes unless they directly affect implementation
- avoid vague future-roadmap language
- avoid deep architecture discussion beyond what is needed for the first implementation

The document should describe **what will be built first and how**.

---

### Important Constraint

The strategy should **prevent architectural drift** during early coding.

If an implementation rule is important, it should be written explicitly in the strategy.

Examples:

- runtime code must live in a specific location
- reference materials must not be executed directly
- the service must remain LAN-local
- interfaces must remain stable during the first implementation

---

### Phase 1 Scope Reminder

For involved projects, the strategy should describe a **minimum working first implementation**.

This does not need to solve everything.

It should define a practical first build that proves the core concept and provides a clean foundation for later expansion.
