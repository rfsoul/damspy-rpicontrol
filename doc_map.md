# Documentation Map

This document describes the documentation structure for a **single-phase repository**.

It is the main navigation guide for humans and AI agents to understand:

- where documentation lives
- when each document should be read
- how the repository is organised during default Phase 1 development

This doc map intentionally does **not** describe any Phase2+ documentation.

If the project later continues beyond Phase 1, use the separate multi-phase doc map stored with the dormant Phase2+ template pack under:

`docs/implementation/Phase2+_template/`

Until then, those documents are dormant and can be ignored.

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
     │   ├─ implementation_strategy.md
     │   └─ liveplan.md
     └─ setup/
         ├─ _getting_started.md
         └─ short_description.md
```

---

# Root Files

### AGENTS.md

Purpose  
Defines the AI development contract and repository behaviour rules.

Read when:

- determining agent workflow rules
- preparing code changes or pull requests
- checking Prompt-ID, branch, or reporting requirements

---

### README.md

Purpose  
Describes the project from the perspective of a user, operator, or first-time repository reader.

Read when:

- understanding what the project is
- checking the intended user-facing purpose
- confirming that the implementation still matches the project intent

---

### doc_map.md

Purpose  
Provides the navigation guide for the repository documentation.

Read when:

- determining which documents are relevant
- locating setup or implementation documents
- orienting a new human or AI contributor

---

### Makefile

Purpose  
Defines repository commands used for development and validation.

Primary validation command:

`make ci`

Read when:

- repository validation must be executed
- determining how automated checks are run
- preparing to validate source code changes

Agents should run `make ci` before creating pull requests that modify source code, unless repository documentation explicitly defines a different validation entrypoint.

---

### tests/

Purpose  
Contains automated tests and validation scripts for the repository.

Read when:

- examining automated test coverage
- validating implementation behaviour
- updating tests to match code changes

Tests are typically executed through:

`make ci`

---

### reference/

Purpose  
Contains technical guides, prior art, known-good examples, or supporting source material used to help shape the implementation.

Read when:

- implementation details need guidance
- historical scripts or prior examples may be useful
- the setup docs direct you to use reference material

`reference/` may contain high-authority implementation guidance for the repository. It should not silently override the active setup documents, but it is a normal input during Phase 1 planning and implementation.

---

# docs/

The `docs/` directory contains the active project documentation used during the default single-phase workflow.

Documentation is divided into two areas:

- **setup/** — documents that define the project before coding begins
- **implementation/** — documents that define how the initial implementation will be built and tracked

---

### agent_commands.md

Purpose  
Defines repository command keywords that may be invoked directly in prompts.

This document is part of the repository control system and is read-only for agents.

Read when:

- a prompt consists solely of a supported command keyword
- directed by command dispatch rules in `AGENTS.md`

Agents must not modify this document unless explicitly instructed by a human.

---

# docs/setup/

Documents used to define and align the project before coding begins.

---

### _getting_started.md

Purpose  
Defines the default Phase 1 startup flow for the repository.

Read when:

- starting a new repository
- determining the order of documentation work
- checking what should be done before coding begins

This is the main guide for the Phase 1 setup process.

---

### short_description.md

Purpose  
Captures the original project idea in concise high-level form.

Read when:

- beginning a new project
- checking the original intent of the repository
- confirming that later docs still align with the starting idea

This is the main source document for initial project intent.

---

# docs/implementation/

Documents used to define and track the initial implementation.

---

### implementation_strategy.md

Purpose  
Defines how the project will be built in its initial implementation phase.

This typically includes:

- the chosen technical approach
- intended runtime structure
- first implementation shape
- validation approach
- important constraints or forbidden shortcuts

Read when:

- preparing to begin implementation
- checking whether code changes still match the intended build approach
- planning the first working version

---

### liveplan.md

Purpose  
Tracks the minimum viable steps for the repository’s active implementation path.

Read when:

- determining the current project step
- checking what should happen next
- finding the prompt reference for a code step
- recording whether the project finishes as single-phase or continues into Phase2+

The liveplan is the execution map for active work.
