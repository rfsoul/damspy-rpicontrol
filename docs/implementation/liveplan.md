# Live Plan — Phase 1

This document tracks the minimum viable steps for a project starting in Phase 1.

Phase 1 is about getting to a working first implementation, checking that it is the right approach, then deciding whether the project is already good enough to deploy/use or whether it needs more phases.

Default Phase 1 flow:

`short_desc → reference/ → README → implementation_strategy → first working code → hands-on review → CI working → decide deploy/use vs continue`

`project_definition.md` is not part of the default Phase 1 startup flow. It is usually introduced only if the project continues into Phase2+ and needs deeper structure.

Future ideas that are not part of the active implementation path belong in `docs/implementation/future_directions.md`.

---

| Step | Type | Item | Description | Prompt Ref | Status | Notes |
|-----|-----|-----|-----|-----|-----|-----|
| **1** | **goal** | **GOAL: Phase 1 setup docs complete** | **Create the minimum documentation needed to start coding in the right direction.** |  | **pending** | **Goal complete when the startup docs are written and aligned.** |
| 1.1 | doc | Prepare short description | Write `docs/setup/short_description.md`. |  | Done | This is the main project prompt. Capture what the project is, what it does, why it exists, key constraints, preferred stack, and what success looks like. |
| 1.2 | doc | Prepare reference folder | Add or clean up `reference/` material. |  | Done | Only include technical guides or known-good material you want the code to follow. Anything vague or wrong here can get baked into the implementation. |
| 1.3 | doc | Create README | Write `README.md`. | `1.3_create_readme.md` | pending | Usability check. Confirms that the short description has been correctly interpreted from the user or operator point of view. |
| 1.4 | doc | Create implementation strategy | Write `docs/implementation/implementation_strategy.md`. | `1.4_create_implementation_strategy.md` | pending | Turn the short description, README, and relevant reference material into a practical first-pass coding plan. Keep it focused on implementation, not theory. |
| 1.5 | review | Review startup doc alignment | Check that `short_description`, `reference/`, `README`, and `implementation_strategy` agree. |  | pending | Final pre-code sanity check. Fix misunderstandings here instead of later in code. |
| **2** | **goal** | **GOAL: First working code exists** | **Create the first working implementation and check that it is functionally the right approach.** |  | **pending** | **Goal complete when the core behaviour works and has been reviewed hands-on.** |
| 2.1 | code | Create first code pass | Generate the first working code pass. | `2.1_create_first_code_pass.md` | pending | Working code matters more than architectural purity at this stage. It should run, do the core job, and stay within the chosen scope and stack. |
| 2.2 | review | Hands-on review of first code | Review the implementation by actually inspecting or trying the behaviour. |  | pending | Decide whether it works functionally and whether it feels like the right approach from a user or operator point of view. |
| 2.3 | review | Confirm Phase 1 direction | Record whether the current implementation is the right vehicle to continue with. |  | pending | Minor roughness is fine. This check is about correctness and direction, not polish. |
| **3** | **goal** | **GOAL: Validation entrypoint working** | **Put repo validation in place once the implementation has earned it.** |  | **pending** | **Goal complete when the repo has a working validation entrypoint appropriate to the current codebase.** |
| 3.1 | code | Bootstrap CI | Set up the validation entrypoint and supporting files. | `bootstrapci` | pending | Usually this means a bootstrap CI flow and `make ci`. Do this after the first code pass is accepted. |
| 3.2 | code | Get CI passing | Make the validation command pass cleanly. |  | pending | Add or refine tests, startup checks, and any lightweight validation needed for the current implementation. |
| **4** | **goal** | **GOAL: Phase 1 decision recorded** | **Decide whether the project is already good enough to deploy/use or whether it needs more phases.** |  | **pending** | **Goal complete when one of the allowed outcomes is explicitly recorded.** |
| 4.1 | review | Assess whether Phase 1 is enough | Decide whether the current repo is sufficient with only minor follow-up changes, or whether it requires further structured development. |  | pending | Some projects can stop here. Others will need more structured development. |
