# Getting Started


## Content

(Add content here)

---

## Editing Guidelines (Do Not Modify Below This Line)

This document defines the **default startup process** for a new repository.

All projects begin as **Phase 1 projects**.

Phase 1 aims to produce the **first working implementation** of the system, verify that the approach is correct, and then bring repository validation into place.

If the project is complete after Phase 1, it may proceed to deployment with only minor follow-up changes.

If the project needs additional development phases, it becomes a **Phase 2+ project**, and additional documentation may then be activated.

---

## Documentation Model

### Phase 1

Phase 1 documentation lives directly in its normal active locations in the repository.

These documents are not templates in `reference/`.
They are already where they need to be and are filled in during the normal startup flow.

Core Phase 1 documents are:

- `docs/setup/short_description.md`
- `reference/`
- `README.md`
- `docs/implementation/implementation_strategy.md`

Phase 1 may also create initial code, initial tests, and later the first working `Makefile` / `make ci` flow.

`project_definition.md` is **not required in Phase 1 by default**.
It may be introduced later if the project continues beyond the initial working implementation.

---

### Phase 2+

Phase 2+ documentation does **not** exist in the active repository by default.

Instead, dormant templates live in the Phase 2+ template area.

These templates are only brought into the active documentation structure if the project proves it requires more than Phase 1.

Examples of Phase 2+ documents may include:

- `docs/setup/project_definition.md`
- `system_invariants.md`
- `architecture.md`
- `external_interfaces.md`
- expanded `liveplan.md`
- protocol or interface specifications
- testing strategy documents
- deployment or operational hardening documents

These documents should only be activated when justified by the project.

---

## Standard Phase 1 Startup Process

The default Phase 1 flow is:

`short_description → reference/ → README → implementation_strategy → first working code → hands-on review → make ci → assess deploy vs further phases`

This is the normal path for all new projects.

---

### Step 1 — Create Short Description

Fill in:

`docs/setup/short_description.md`

This is the main startup document.
It should act like a strong extended prompt for the repository.

It should clearly describe:
- what the project is
- what it does
- why it exists
- who it is for if already known
- what it does not need to do in the first phase
- major constraints or fixed choices already known at project start
- preferred libraries, frameworks, runtime model, or tech stack when those are already intentional

Include specific implementation or interface choices when they are already intentional and important to the project shape.

The short description should make the first implementation direction clear enough that the project does not drift unnecessarily.

---

### Step 2 — Prepare the Reference Folder

Review and curate:

`reference/`

The reference folder contains technical truth, guide material, protocol notes, example behaviour, or other source material that may be used during implementation.

Anything placed in `reference/` may strongly influence the generated code.
Therefore the reference material should be:

- accurate
- deliberate
- current
- aligned with real terminology used by the project or lab
- free of misleading or accidental behaviour unless intentionally included

For hardware and protocol work especially, the reference folder should be treated as high-authority input.

---

### Step 3 — Create README

Generate:

`README.md`

The README should describe the project from the perspective of the user or operator.

Its purpose in Phase 1 is primarily as a **usability and understanding check**.
It should confirm that the short description has been interpreted correctly.

Review the README before proceeding.
If the README does not feel right, fix the short description or reference material first.

---

### Step 4 — Create Implementation Strategy

Fill in:

`docs/implementation/implementation_strategy.md`

This document turns the short description and README into a coding plan.

It should define:

- the chosen technical approach
- the intended runtime structure
- the preferred libraries and stack
- the major components or files expected in the first implementation
- the first-pass scope
- any important constraints or forbidden shortcuts

For Phase 1, the implementation strategy should optimize for a **working first implementation**.
It should guide the architecture, but it must not encourage a polished-looking repo at the expense of operational correctness.

Review the implementation strategy before proceeding.

---

### Step 5 — Implement First Working Code

Using the short description, reference material, README, and implementation strategy, produce the first working code for the repository.

The first code pass should prioritize, in this order:

1. operational correctness for the core use case
2. correct user or operator behaviour
3. staying within the intended stack and scope
4. reasonable structure
5. later refinement readiness

The first implementation may be:

- small
- rough
- less featured
- less modular than the final desired shape
- initially in a single file or a small number of files if that improves reliability

This is acceptable **if it works and proves the right approach**.

A working first pass is more important than architectural neatness.

---

### Step 6 — Hands-On Review

Before formal CI is established, the project owner should review the first working code directly.

This review should answer:

- does the code actually work
- does it do the right thing from the user or operator point of view
- is the technical approach fundamentally correct
- is the project on the right track
- are there major scope or behaviour changes needed before hardening the repo

This is the key Phase 1 checkpoint.

If the answer is no, continue iterating on the implementation before moving on.

---

### Step 7 — Get CI Working

Once the first implementation has been reviewed and accepted as directionally correct, bring the repository validation flow into place.

Typical validation entrypoint:

`make ci`

This may be introduced or expanded using the repository bootstrap CI commands.

At this stage, CI should confirm at an appropriate level that:

- the code imports or starts correctly
- the core tests run
- the minimum required behaviour is validated
- the repository has a stable validation entrypoint

CI should be added **after** the first working implementation has earned trust, not before.

---

### Step 8 — Assess Whether Phase 1 Is Enough

After the code works and CI is in place, decide which of the following applies.

#### Outcome 1 — Ready to Deploy After Phase 1

If the project’s required functionality is satisfied and only minor follow-up changes remain, the project may proceed to deployment from Phase 1.

In this case:

- no additional phase documentation is required by default
- future work may be handled as small incremental improvements
- the project remains intentionally simple

This is a normal and acceptable outcome.

#### Outcome 2 — Project Requires Additional Phases

If the project still needs significant refinement, restructuring, expansion, or hardening, it becomes a **Phase 2+ project**.

At that point:

- the relevant Phase 2+ template docs may be activated
- `docs/setup/project_definition.md` may be introduced
- the liveplan may be expanded to include multiple goals or phases
- the repository may adopt more explicit architectural, interface, testing, or deployment documentation

A project should only move into additional phases when there is a clear reason to do so.

---

## Important Principles

1. All projects begin as Phase 1 projects.
2. Phase 1 is about producing a working implementation first.
3. Operational correctness is more important than architectural neatness in the first code pass.
4. The short description is the main startup driver.
5. The reference folder must be curated carefully because it strongly shapes generated code.
6. The README is an understanding and usability check.
7. The implementation strategy is a bridge from intent to code.
8. Hands-on human review happens before CI formalization.
9. CI is introduced once the first implementation is proven directionally correct.
10. `project_definition.md` is normally deferred until Phase 2+.
11. Additional documentation should only be introduced when justified.

---

## Summary

Default Phase 1 flow:

`short_description → reference/ → README → implementation_strategy → first working code → hands-on review → make ci → assess deploy vs further phases`

If the project is complete after that, it may deploy from Phase 1 with only minor follow-up changes.

If the project continues beyond that, it becomes a Phase 2+ project and the additional docs may be activated from the dormant template area.
