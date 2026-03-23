# AI Contract

## Content
(Add content here)

### Purpose

This document defines how AI agents (such as Codex, Dexie, ChatGPT, or similar tools) must behave when modifying this repository.

Its purpose is to ensure AI-generated changes remain:

- safe
- minimal
- traceable
- aligned with the documented project intent

AI agents should treat this document as the authoritative guide for development behaviour in this repository.

---

### Primary Rule

Follow `docs/implementation/liveplan.md`.

Only implement the step currently being worked on.

Do not implement features, refactors, or improvements that are not explicitly part of the current step.

If a useful improvement is discovered but is not part of the current step, it should be recorded in `docs/implementation/future_directions.md` rather than implemented immediately.

---

### 1. Respect System Invariants

The rules defined in `docs/setup/system_invariants.md` are safety guarantees.

AI agents must not introduce changes that violate these invariants.

If a requested change conflicts with an invariant, the AI agent must:

- explain the conflict
- propose an alternative design
- avoid silently bypassing the invariant

Invariants must always take priority over convenience.

---

### 2. Follow the Architecture

The system design is documented in:

`docs/implementation/architecture.md`

AI agents must understand the documented architecture before making significant modifications.

Architectural shortcuts that bypass the intended component boundaries, data flow, or integration model are not allowed unless the current step explicitly changes the architecture.

If the architecture appears incomplete or in conflict with the requested work, the AI agent should flag that issue rather than inventing a new architecture silently.

---

### 3. Implement Only the Current Step

Development work is controlled through `docs/implementation/liveplan.md`.

Each task is broken into minimal steps.

AI agents must:

- implement only the current step
- avoid implementing future steps
- avoid combining multiple steps into one change unless explicitly requested

The preferred workflow is:

Goal → Minimal Step → Test → Review → Merge

---

### 4. Keep Changes Small

Each code change or pull request should implement one minimal viable step.

AI agents must not:

- refactor unrelated files
- reorganise the repository without need
- introduce broad architectural changes without explicit instruction
- modify working components unnecessarily

If a change affects many files or concerns, it should usually be split into smaller steps.

---

### 5. Preserve Working Behaviour

Existing functionality must remain stable unless the current step explicitly changes it.

If the repository already contains working behaviour, AI agents should preserve it while implementing the requested step.

If a requested change may affect other behaviour, the AI agent should make that risk explicit.

Avoid changing unrelated behaviour just because a better design seems possible.

---

### 6. Prefer Extension Over Unnecessary Refactor

When adding new behaviour:

- extend existing modules where reasonable
- avoid rewriting working components without need
- avoid introducing new abstractions unless they clearly improve the current step

Large refactors must be justified by the current goal, not by general preference.

---

### 7. Validate the Change

Before proposing completion of a coding step, the AI agent should confirm the change has been validated appropriately.

Validation may include:

- running `make ci`
- executing automated tests
- checking linting or type checks
- exercising the changed path locally
- verifying behaviour in the real target environment where relevant

The validation method should match the repo and the type of change.

The goal is to reduce regressions and keep progress trustworthy.

---

### 8. Update Documentation When Behaviour Changes

If system behaviour, interfaces, constraints, or operational expectations change, the relevant documentation must be updated.

Possible documents to update include:

- `README.md`
- `docs/setup/project_definition.md`
- `docs/setup/system_invariants.md`
- `docs/implementation/architecture.md`
- `docs/implementation/external_interfaces.md`
- `docs/implementation/runbook.md`
- `docs/implementation/decisions.md`
- `docs/implementation/memory.md`
- `docs/implementation/liveplan.md`

Documentation must remain consistent with the codebase and with the actual current system behaviour.

---

### 9. Prefer Safe Failure

If an AI agent cannot safely implement a requested change, it should:

- explain the uncertainty
- identify the missing information or conflict
- avoid producing unsafe or misleading changes

Producing incorrect or risky behaviour is worse than pausing for clarification or narrowing the change.

---

### 10. Respect Repository Boundaries

AI agents must respect the defined scope of the repository.

They must not casually absorb responsibilities that belong to:

- another repository
- another service
- external infrastructure
- manual operator processes
- future planned systems

If a useful capability appears to belong elsewhere, it should be documented as a possible future integration or upstream responsibility rather than implemented here by default.

---

### 11. Keep Work Traceable

Where the repository uses Prompt-ID, liveplan steps, or PR-linked workflow tracking, AI agents must preserve that traceability.

Changes should remain attributable to:

- the current goal
- the current minimal step
- the prompt or task that triggered the work

Traceability is part of the development system, not optional extra process.

---

### 12. Repository Documentation Map

AI agents should understand the purpose of the core repository documents.

`README.md`  
Project overview and user/operator view.

`docs/setup/short_description.md`  
Original high-level project idea.

`docs/setup/project_definition.md`  
Problem, scope, users, non-goals, and constraints.

`docs/setup/system_invariants.md`  
Core truths that must not be violated.

`docs/implementation/architecture.md`  
Major components, interactions, and system boundaries.

`docs/implementation/external_interfaces.md`  
How other systems, users, or hardware interact with the system.

`docs/implementation/liveplan.md`  
Current goals and minimal implementation steps.

`docs/implementation/decisions.md`  
Recorded architectural decisions.

`docs/implementation/memory.md`  
Operational lessons and debugging insights.

`docs/implementation/runbook.md`  
Operational procedures and troubleshooting.

`docs/implementation/future_directions.md`  
Ideas that are intentionally out of scope for the current step.

---

### Development Philosophy

This repository should be built incrementally.

Changes should prioritise:

- safety
- clarity
- small steps
- predictable behaviour
- architectural discipline
- documentation consistency

Small, controlled improvements are preferred over large speculative changes.

---

## Editing Guidelines (Do Not Modify Below This Line)

This document defines the **behavioural rules for AI agents** working in the repository.

It acts as the operational contract between the documented repository design and AI-assisted implementation.

The contract should remain:

- durable
- repo-agnostic where possible
- aligned with the repository’s documented workflow
- strict enough to prevent drift
- practical enough to guide day-to-day work

It should reinforce:

- liveplan-driven execution
- respect for invariants
- architectural discipline
- small-step implementation
- documentation consistency
- traceable changes

Avoid including:

- project-specific business logic
- temporary feature instructions
- narrow implementation details
- one-off task guidance that belongs in `liveplan.md`
- content that should live in architecture, runbook, or system invariants instead