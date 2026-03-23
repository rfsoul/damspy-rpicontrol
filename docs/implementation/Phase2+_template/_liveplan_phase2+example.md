# _Live Plan Example — Phase2+

This document shows an example continuation of the single-phase liveplan after the project has already passed through Goals 1–5 and has been formally assessed as requiring continued structured development.

It assumes:

- Phase 1 documentation is complete
- Phase 1 code exists
- Phase 1 testing has been completed
- the project has been judged to require further structured development rather than simple maintenance

This example begins at Goal 6 because Goals 1–5 belong to the default single-phase startup path.

Future ideas that are not part of the active implementation path belong in `docs/implementation/future_directions.md`.

---

| Step | Type | Item | Description | Prompt-ID | Codex prompt | Status | Notes |
|-----|-----|-----|-----|-----|--|-----|-----|
| **6** | **goal** | **GOAL: Phase2+ continuation is formally activated** | **Confirm that the repository is continuing beyond Phase 1 and activate the Phase2+ documentation set.** |  |  | **pending** | **Goal complete when the continuation rationale is recorded and the Phase2+ docs are active in their normal repo locations.** |
| 6.1 | review | Confirm continuation beyond Phase 1 | Record why Phase 1 is not sufficient and why the repo now needs further structured development. |  |  | pending | Expansion, hardening, refactor, multi-component growth, or stronger production needs may justify continuation. |
| 6.2 | human-op | Activate Phase2+ docs | Unzip or move the Phase2+ template docs into their normal active repo locations as defined by `doc_map.md`. |  |  | pending | This is the transition point from the single-phase doc set to the expanded doc set. |
| 6.3 | review | Verify active doc map is correct | Check that the activated docs are in the intended locations and that the repository documentation map still makes sense. |  |  | pending | Prevents path drift and template confusion before filling in deeper docs. |
| **7** | **goal** | **GOAL: Phase2+ repository reality is reviewed** | **Re-anchor the next phase in the real state of the working repo rather than in an imagined redesign.** |  |  | **pending** | **Goal complete when the current implementation, constraints, and reasons for continuation are clearly understood.** |
| 7.1 | review | Review implemented Phase 1 system | Review what was actually built, what works, what is fragile, and what is already proven. |  |  | pending | Phase2+ should begin from reality, not from assumptions. |
| 7.2 | review | Review observed constraints and lessons | Review what was learned during implementation, testing, and real usage that affects the next phase. |  |  | pending | Inputs for this may come from implementation notes, manual testing, and operator knowledge. |
| 7.3 | review | Define continuation focus | State whether the next phase is primarily expansion, refactor, hardening, interface growth, or system decomposition. |  |  | pending | This helps later documents stay aligned. |
| **8** | **goal** | **GOAL: Core system constraints are defined** | **Write down the durable rules that the next phase must not violate.** |  |  | **pending** | **Goal complete when the repository invariants are explicit and usable as a design and review constraint.** |
| 8.1 | doc | Create system invariants | Fill in `docs/implementation/system_invariants.md`. |  |  | pending | Record the core truths and non-negotiable rules that must survive future changes. |
| 8.2 | review | Review invariants for durability | Check that the invariants are specific, durable, and not merely temporary implementation details. |  |  | pending | Invariants should constrain future work without becoming noisy or fragile. |
| **9** | **goal** | **GOAL: Phase2+ design structure is documented** | **Describe the system structure and boundaries needed for continued development.** |  |  | **pending** | **Goal complete when architecture and external interfaces are documented clearly enough to guide future work.** |
| 9.1 | doc | Create architecture document | Fill in `docs/implementation/architecture.md`. |  |  | pending | Describe major components, responsibilities, interactions, and important boundaries. |
| 9.2 | doc | Create external interfaces document | Fill in `docs/implementation/external_interfaces.md`. |  |  | pending | Describe APIs, files, hardware links, jobs, services, operator entry points, and other repo boundaries. |
| 9.3 | review | Review design boundary alignment | Check that invariants, architecture, and interfaces agree with each other and with the existing repository. |  |  | pending | Prevents architectural drift before more coding resumes. |
| **10** | **goal** | **GOAL: Development control rules are explicit** | **Define how AI, testing, and operations should be handled in the more complex repo.** |  |  | **pending** | **Goal complete when the repo has clear rules for AI behaviour, validation strategy, and operational handling.** |
| 10.1 | doc | Create AI contract | Fill in `docs/implementation/ai_contract.md`. |  |  | pending | Define safe AI behaviour for the deeper system. |
| 10.2 | doc | Create test strategy | Fill in `docs/implementation/test_strategy.md`. |  |  | pending | Define the validation philosophy, layers, and environments for the repo. |
| 10.3 | doc | Create regression tests catalogue | Fill in `docs/implementation/tests_regression.md`. |  |  | pending | Record the important behaviours that future changes must not break. |
| 10.4 | doc | Create runbook | Fill in `docs/implementation/runbook.md`. |  |  | pending | Record startup, operation, monitoring, troubleshooting, and recovery guidance. |
| 10.5 | review | Review AI/testing/ops alignment | Check that AI contract, test strategy, regression expectations, and runbook agree with the architecture and repo reality. |  |  | pending | This creates a coherent operating model before further development. |
| **11** | **goal** | **GOAL: Repo memory and decision records are in place** | **Create the durable supporting documents that preserve important choices and observations.** |  |  | **pending** | **Goal complete when decisions, memory, and WOYM stance are explicitly recorded.** |
| 11.1 | doc | Create decisions log | Fill in `docs/implementation/decisions.md`. |  |  | pending | Record important technical and architectural decisions and why they were made. |
| 11.2 | doc | Create memory log | Fill in `docs/implementation/memory.md`. |  |  | pending | Record quirks, observations, and lessons learned from implementation and operation. |
| 11.3 | doc | Decide WOYM approach | Fill in `docs/implementation/whatsonyourmind_WOYM.md`. |  |  | pending | Always record the decision, even if WOYM is not needed. |
| 11.4 | review | Review decision and memory docs | Check that these records are useful, specific, and aligned with the real repository. |  |  | pending | Avoid generic filler. |
| **12** | **goal** | **GOAL: Prompt and planning control are expanded for Phase2+** | **Move from the simple single-phase control model to an expanded multi-goal planning model.** |  |  | **pending** | **Goal complete when prompt storage and the liveplan are ready to drive the next structured development phase.** |
| 12.1 | doc | Create prompt library | Fill in `docs/implementation/prompts.md`. |  |  | pending | Add Prompt-ID keyed prompts for future `type=code` work where appropriate. |
| 12.2 | doc | Expand liveplan for next development phase | Add the next serious implementation goals and steps after Goal 12. |  |  | pending | This is where repo-specific continued development planning begins. |
| 12.3 | review | Review Phase2+ planning baseline | Confirm the activated docs and expanded liveplan are coherent enough to begin the next coding cycle. |  |  | pending | Final doc alignment gate before major further implementation work. |
| **13** | **goal** | **GOAL: Repository ready for next major coding phase** | **Prepare the repo to resume implementation under the expanded Phase2+ documentation system.** |  |  | **pending** | **Goal complete when the next coding phase can begin in a controlled and well-documented way.** |
| 13.1 | human-op | Commit Phase2+ planning baseline | Create a clean repository commit after the Phase2+ doc set and liveplan expansion are complete. |  |  | pending | Establishes the baseline for the next deeper coding cycle. |
| 13.2 | review | Confirm validation entrypoint still works | Re-run the repo validation entrypoint after documentation activation and repo planning changes. |  |  | pending | Helps confirm the repo remains stable before more code changes. |
| 13.3 | outcome | Begin Phase2+ implementation cycle | Start the next coding phase using the expanded liveplan, prompts, and Phase2+ doc set. |  |  | pending | This is the handoff into the next serious implementation stage. |
