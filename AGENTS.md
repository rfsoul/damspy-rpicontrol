# AGENTS.md

This repository follows a **Prompt-Driven Development workflow**.

---

# Prompt-ID Rule

If a prompt contains a line of the form:

Prompt-ID: <value>

`<value>` may be any non-empty string (for example: `Prompt-ID: onboarding-v2`, `Prompt-ID: abc123`, or `Prompt-ID: 42`).

Placeholder substitution rule

Before executing a command or interpreting a task, the agent must resolve any supported placeholder tokens found in the instruction text.

Supported placeholders:
- `reponame` → resolve as `cwdname`
- `cwdname` → the final path component of the current working directory

If `reponame` appears, the agent must treat it as an alias for `cwdname`.

If the current working directory name cannot be resolved confidently, the placeholder should be omitted rather than guessed.

Then the agent must:

1. Determine the current **base PR number** of the repository.
2. Determine the **base short commit SHA**.
3. Include the **Prompt-ID value**, **Base-PR**, and **Base-SHA** in:
   - the Codex output
   - the Pull Request description

Include `CWD-Name` only when it was successfully resolved.

Required output fields:

Prompt-ID: <value>
Base-PR: <value>
Base-SHA: <short_sha>

Optional output field:

CWD-Name: <cwdname>

---

# Repository Context

When additional repository context is required, read the repository file:

doc_map.md

to determine which documents are relevant.

If the prompt explicitly instructs the agent to read specific files, follow the prompt instructions instead.

---

# Documentation Structure

Documentation files contain two sections:

Content
Editing Guidelines

Agents should normally **modify only the Content section**.

Editing Guidelines should not be modified unless explicitly instructed.

---

# Validation Policy

Changes fall into two categories.

## Documentation Changes

Documentation-only changes include:

* `README.md`
* files under `docs/`
* `*.md`
* architecture documents
* planning documents

For documentation-only changes:

* CI validation is **not required**
* A Pull Request may be created directly.

---

## Source Code Changes

Source code changes include modifications to:

* `src/`
* `app/`
* `api/`
* `lib/`
* `components/`
* `package.json`
* `tsconfig.json`
* build scripts
* runtime configuration
* any executable code

If source code is modified, repository validation **must be run before creating a Pull Request**.

---

# Validation Command

The validation command for this repository is:

make ci

Agents must run this command before opening any Pull Request that modifies source code.

Validation typically performs:

* dependency installation
* type checking
* linting
* automated tests
* build verification

All failures must be fixed before submitting a Pull Request.

---

# CI Requirement

If source code changes are requested but repository validation cannot be executed because:

* a `Makefile` does not exist
* the `ci` target is missing
* validation scripts are not configured
* required tooling is unavailable

then **do not create the Pull Request**.

Instead return the following message:

You have asked me to change source code, but CI validation is not configured for this repository.

This repository must define a validation command:

make ci

Please add CI configuration before code changes can be safely merged.

---

# Pull Request Rule

Before creating a Pull Request that modifies source code:

1. Run `make ci`
2. Confirm validation passes
3. Only then open the Pull Request.

Pull Requests must not be created if validation fails.

---

# Principle

Prefer the **minimum validation required for the change type**:

* documentation changes → no CI required
* source code changes → CI validation required

# Agent Command Dispatch

If a prompt consists solely of a single keyword, the agent should check
`docs/agent_commands.md` to determine whether that keyword is a defined
repository command.

If the prompt is not a single keyword, do not read this document.

