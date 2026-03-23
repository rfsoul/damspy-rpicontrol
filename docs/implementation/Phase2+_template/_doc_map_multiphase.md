# _Documentation Map - Phase2+

This document provides an overview of the documentation structure for a **multi-phase repository**.

It is intended to live with the Phase2+ template pack and should be used once a project has moved beyond the default single-phase path.

It serves as the entry point for both humans and AI agents to understand:

- where documentation is located
- when each document should be consulted
- how the repository is organised once deeper structured development is active

Use this doc map only after the liveplan has recorded the decision to continue into Phase2+ development.

---

# Repository Structure

```text
repo/
 ├─ AGENTS.md
 ├─ README.md
 ├─ doc_map.md
 ├─ Makefile
 ├─ tests/
 ├─ reference/
 └─ docs/
     ├─ agent_commands.md
     ├─ implementation/
     │   ├─ _getting_started_phase2+.md
     │   ├─ ai_contract.md
     │   ├─ architecture.md
     │   ├─ decisions.md
     │   ├─ external_interfaces.md
     │   ├─ future_directions.md
     │   ├─ implementation_strategy.md
     │   ├─ liveplan.md
     │   ├─ memory.md
     │   ├─ prompts.md
     │   ├─ runbook.md
     │   ├─ system_invariants.md
     │   ├─ test_strategy.md
     │   ├─ tests_regression.md
     │   └─ whatsonyourmind_WOYM.md
     └─ setup/
         ├─ gettingstartednew.md
         ├─ project_definition.md
         └─ short_description.md
```

---

# Root Files

### AGENTS.md

Purpose  
Defines the AI development contract and Prompt-Driven Development workflow used when generating code, reviewing work, and preparing pull requests.

Read when:

- determining agent workflow rules
- preparing to create a pull request
- validating repository changes
- coordinating structured multi-step development work

---

### README.md

Purpose  
High-level description of the project including what it is, what it does, and how the repository should be used.

Read when:

- understanding the overall project purpose
- onboarding to the repository
- checking that deeper architectural or interface work still serves the intended user-facing system

---

### doc_map.md

Purpose  
Provides the navigation guide for the active repository documentation.

Read when:

- determining which documents are relevant
- locating planning, architecture, testing, or operations documents
- orienting a new human or AI contributor

---

### Makefile

Purpose  
Defines repository commands used for development and validation.

Primary validation command:

`make ci`

Read when:

- repository validation must be executed
- determining how to run automated checks
- preparing to validate source code changes

Agents should run `make ci` before creating pull requests that modify source code, unless the repository documents specify another required validation entrypoint.

---

### tests/

Purpose  
Contains automated tests for the repository.

Actual test implementations live here.

Tests are typically executed through the repository validation command:

`make ci`

Read when:

- examining or updating automated test coverage
- validating implementation behaviour
- implementing regression protection described by `test_strategy.md` and `tests_regression.md`

---

### reference/

Purpose  
Reference material only.

Contains historical scripts, examples, notes, or source material preserved for context.

Read when:

- background context is needed
- earlier implementations or source material may inform ongoing design

Do not treat `reference/` as the source of truth for active implementation unless another document explicitly directs this.

---

# docs/

The `docs/` directory contains project documentation for the active multi-phase workflow.

Documentation is divided into two major areas:

- **setup/** — original project-definition documents from the single-phase start
- **implementation/** — active planning, architecture, testing, interface, and operations documents used after continuing into Phase2+

---

### agent_commands.md

Purpose  
Defines repository command keywords that may be invoked directly in prompts.

This document is part of the repository control system and is read-only for agents.

Agents must never modify this document.

Read when:

- the prompt consists solely of a single keyword
- directed by the command dispatch rule in `AGENTS.md`

---

# docs/setup/

The original startup documents remain part of the repository and still provide important context.

---

### short_description.md

Purpose  
Captures the original project idea in short, high-level form.

Read when:

- checking the original intent of the project
- confirming that later phases still serve the original purpose

---

### gettingstartednew.md

Purpose  
Defines the original single-phase startup workflow.

Read when:

- understanding how the project began
- reviewing what had to be completed before the first implementation

Once the project has formally continued into Phase2+, the active continuation workflow is defined in `_getting_started_phase2+.md`.

---

### project_definition.md

Purpose  
Defines the concrete project boundary.

This typically includes:

- the problem being solved
- intended users or operators
- scope and non-goals
- runtime environment
- important constraints

Read when:

- clarifying what remains in scope
- evaluating whether a proposed expansion belongs in the project
- checking later architectural decisions against intended boundaries

---

# docs/implementation/

These documents define how the project is continued, structured, validated, and operated once it becomes a multi-phase system.

---

### _getting_started_phase2+.md

Purpose  
Defines the standard order for activating and filling in the Phase2+ document set.

Read when:

- the project has formally continued beyond single-phase development
- determining the order to deepen the docs before more major implementation work

---

### implementation_strategy.md

Purpose  
Defines how the current implementation phase is being built.

In a multi-phase repo this remains the practical implementation-planning document for the currently active phase.

Read when:

- planning implementation work
- checking whether code changes still match the intended build strategy

---

### liveplan.md

Purpose  
Engineering ledger tracking the Minimum Viable Steps (MVS) used to build and evolve the project.

In a multi-phase repo the liveplan records the structured continuation of work beyond the original single-phase path.

Read when:

- determining the next development task
- checking project status
- sequencing deeper documentation, architecture, test, and implementation work

---

### system_invariants.md

Purpose  
Defines the rules that must remain true as the system evolves.

These are the non-negotiable constraints that later design and implementation must preserve.

Read when:

- expanding or refactoring the system
- evaluating whether a proposed change violates core system rules

---

### architecture.md

Purpose  
High-level system architecture including major components and how they interact.

Read when:

- implementing new system components
- restructuring major areas of the system
- understanding overall system shape

---

### external_interfaces.md

Purpose  
Defines external services, APIs, message boundaries, webhooks, protocols, or integration contracts used by the system.

Read when:

- implementing integrations
- modifying external communications
- checking interface assumptions during refactor work

---

### decisions.md

Purpose  
Architecture Decision Records (ADRs) or other major technical decisions.

Captures important technical decisions and the reasoning behind them.

Read when:

- understanding why architectural decisions were made
- evaluating potential architectural changes
- deciding whether to preserve or reverse prior choices

---

### ai_contract.md

Purpose  
Defines repository-specific instructions and guardrails for AI-driven development work.

Read when:

- using AI agents for substantial implementation work
- aligning prompts and expectations with repo-specific constraints

---

### prompts.md

Purpose  
Records prompt identifiers and prompt text associated with planned coding work.

Read when:

- coordinating Prompt-Driven Development work
- mapping liveplan items to prompt content

---

### test_strategy.md

Purpose  
Defines the testing harness and validation philosophy used by the repository.

This document describes how the system is validated, including:

- manual testing approaches
- automated testing layers
- simulation testing
- CI validation

Read when:

- implementing automated tests
- configuring CI validation
- understanding how repository behaviour is validated

---

### tests_regression.md

Purpose  
Catalogues behaviours that must not break as the system evolves.

Read when:

- designing or expanding test coverage
- verifying that refactors preserve critical behaviour
- identifying regression risks before major changes

---

### runbook.md

Purpose  
Operational procedures including deployment steps, debugging procedures, recovery instructions, and maintenance workflows.

Read when:

- deploying the system
- diagnosing operational issues
- handling production or field failures

---

### memory.md

Purpose  
Operational knowledge, lessons learned, and important repository-specific observations gathered over time.

Read when:

- investigating past issues
- understanding historical context
- avoiding repeated mistakes

---

### future_directions.md

Purpose  
Captures ideas, possible future work, or deferred capabilities that are not part of the currently active implementation path.

Read when:

- considering future expansions
- deciding whether a new idea belongs in the active liveplan or should remain deferred

---

### whatsonyourmind_WOYM.md

Purpose  
Defines the WOYM route or equivalent “thinking/output without action” behaviour if the project uses that pattern.

Read when:

- the project includes WOYM functionality
- implementing or validating safe non-action diagnostic or preview behaviour

---

# Activation Rule

This doc map belongs to the Phase2+ structure.

It should only become active after the repository has already:

- completed the default single-phase path
- passed initial testing
- recorded the decision to continue into Phase2+ development in `liveplan.md`

Until then, the single-phase doc map should remain the active documentation map for the repository.
