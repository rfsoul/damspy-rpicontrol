# _Getting Started — Phase2+

## Content

This document defines the default startup process for a repository that has already completed Phase 1 and has explicitly been assessed as needing further structured development.

Phase2+ starts from an existing working repository.

It assumes:

- Phase 1 code exists
- Phase 1 testing has been completed
- the repository has already proven useful enough to continue
- the next work is larger than a minor incremental change

The purpose of Phase2+ is to move the repository from a simple first implementation into a more explicitly structured system.

This usually means introducing the deeper documentation needed to support:

- larger scope
- multiple components or interfaces
- significant refactoring
- production hardening
- stronger validation expectations
- more disciplined AI-assisted development

Phase2+ should only begin after the liveplan records the decision to continue beyond Phase 1.

---

## Documentation Model

Phase2+ documents are activated after the project has already passed through the initial single-phase path.

By the start of Phase2+, the root and core Phase 1 documents should already exist in active form, including:

- `README.md`
- `docs/setup/short_description.md`
- `docs/setup/project_definition.md`
- `docs/implementation/implementation_strategy.md`
- `docs/implementation/liveplan.md`

Phase2+ then activates the deeper implementation documents needed for continued structured development.

Typical Phase2+ documents include:

- `docs/implementation/system_invariants.md`
- `docs/implementation/architecture.md`
- `docs/implementation/external_interfaces.md`
- `docs/implementation/ai_contract.md`
- `docs/implementation/test_strategy.md`
- `docs/implementation/tests_regression.md`
- `docs/implementation/runbook.md`
- `docs/implementation/decisions.md`
- `docs/implementation/memory.md`
- `docs/implementation/prompts.md`
- `docs/implementation/whatsonyourmind_WOYM.md`

Additional Phase2+ documents may also be activated if present in the template set.

---

## Standard Phase2+ Startup Process

The default Phase2+ flow is:

`review Phase 1 reality → activate deeper docs → define invariants → define architecture → define interfaces → define AI/testing/ops rules → expand prompts/liveplan → continue coding`

This is the normal path for a repository that has moved beyond simple single-phase development.

---

### Step 1 — Review Why The Repository Is Continuing

Before activating deeper documentation, review the result of Phase 1.

Confirm:

- what was built
- what actually works now
- what was learned during implementation and testing
- why Phase 1 is no longer sufficient
- whether the next work is expansion, refactor, hardening, or multi-component growth

This review should anchor all later Phase2+ documents in the reality of the existing repo, not in an imagined greenfield design.

---

### Step 2 — Activate The Phase2+ Documents

Bring the Phase2+ template documents into their normal active locations in the repository as defined by `doc_map.md`.

At this point, the repository is no longer operating with only the Phase 1 document set.

The deeper documentation structure is now active and should be treated as part of the working repo.

---

### Step 3 — Define System Invariants

Fill in:

`docs/implementation/system_invariants.md`

This document records the core truths that must remain true as the system evolves.

It should capture non-negotiable rules such as:

- safety boundaries
- scope boundaries
- architectural boundaries
- data integrity rules
- operational guarantees
- behaviours that must never be broken by refactor or expansion

This should be done early in Phase2+ because it constrains all later design and implementation work.

---

### Step 4 — Define Architecture

Fill in:

`docs/implementation/architecture.md`

This document explains the high-level structure of the system as it now exists or is intended to evolve.

It should include:

- the major components
- their responsibilities
- how they interact
- important boundaries
- the intended direction of future structural change where relevant

This should reflect the real repository and the actual next phase of development.

---

### Step 5 — Define External Interfaces

Fill in:

`docs/implementation/external_interfaces.md`

This document describes how the repository interacts with the outside world.

Examples may include:

- APIs
- web endpoints
- hardware interfaces
- scheduled jobs
- file inputs and outputs
- external services
- user/operator entry points

This document becomes increasingly important once the project grows beyond a small self-contained Phase 1 build.

---

### Step 6 — Define AI Development Rules

Fill in:

`docs/implementation/ai_contract.md`

This document defines how AI agents should safely work in the repository now that the system is more complex.

It should align AI behaviour with:

- the liveplan
- the invariants
- the architecture
- repo validation expectations
- documentation update requirements

This is especially important once the repository has enough depth that casual AI changes could cause drift or breakage.

---

### Step 7 — Define Testing Strategy

Fill in:

`docs/implementation/test_strategy.md`

This document explains how the repository should be validated at the new level of complexity.

It should describe:

- the testing philosophy
- validation layers
- environments used
- how regressions are prevented
- what kinds of checks belong in CI versus manual validation

This should describe the strategy, not the full catalogue of critical behaviours.

---

### Step 8 — Define Critical Regression Expectations

Fill in:

`docs/implementation/tests_regression.md`

This document lists the important behaviours that must not be broken as the repository evolves.

It should describe the critical workflows and expected outcomes that future changes must preserve.

This gives the system a durable reference point for future test expansion.

---

### Step 9 — Define Operational Guidance

Fill in:

`docs/implementation/runbook.md`

This document describes how the repository is operated, monitored, troubleshot, and recovered.

It is especially useful once the repo:

- runs continuously
- has production or semi-production use
- interacts with hardware or external services
- needs repeatable operational knowledge

---

### Step 10 — Record Important Decisions And Learnings

Fill in or begin using:

- `docs/implementation/decisions.md`
- `docs/implementation/memory.md`

Use `decisions.md` for durable technical or architectural decisions.

Use `memory.md` for observed behaviour, quirks, and lessons learned during implementation or operation.

These documents help the repo accumulate useful understanding without burying it in code or chat history.

---

### Step 11 — Decide On WOYM

Fill in:

`docs/implementation/whatsonyourmind_WOYM.md`

This document records whether the repository should expose a meaningful runtime introspection surface and, if so, what shape it should take.

Even if WOYM is not needed, the decision should still be recorded.

For more involved systems, this is also the point to decide whether a safe dry-run / calculate-but-don’t-act view would be valuable.

---

### Step 12 — Expand Prompt And Liveplan Control

Fill in or activate:

- `docs/implementation/prompts.md`
- expanded `docs/implementation/liveplan.md`

At this point the repository should move from a simple Phase 1 path into a more explicit multi-goal liveplan that reflects the next serious development phase.

The expanded liveplan should:

- continue from the existing single-phase liveplan
- begin at Goal 6 or later
- define the next implementation goals in a controlled order
- connect code steps to Prompt-ID where appropriate

---

### Step 13 — Review The Full Phase2+ Doc Set

Before continuing with major new coding work, review the activated Phase2+ documents together.

Check that they agree on:

- what the system is now
- what must remain true
- how the system is structured
- what interfaces matter
- how changes should be tested
- how AI agents should behave
- what the next liveplan goals are

This is the final doc-alignment step before deeper development continues.

---

## Important Principles

1. Phase2+ begins from a working repository, not from a blank slate.
2. Phase2+ docs should reflect reality and the next justified stage of development.
3. System invariants should be defined before major expansion or refactor work continues.
4. Architecture and interfaces should be documented before significant new structure is added.
5. AI development rules matter more once the system becomes more complex.
6. Testing strategy and regression expectations should become more explicit in Phase2+.
7. Operational knowledge, decisions, and learned behaviour should be written down rather than left implicit.
8. The liveplan should expand only after the deeper documentation base is in place.
9. Phase2+ is for substantial continued development, not for trivial incremental edits.

---

## Summary

Default Phase2+ flow:

`review Phase 1 reality → activate deeper docs → define invariants → define architecture → define interfaces → define AI/testing/ops rules → expand prompts/liveplan → continue coding`

Phase2+ exists to support the next serious stage of repository growth after Phase 1 has already produced a working implementation.
