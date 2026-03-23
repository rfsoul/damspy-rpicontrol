# Agent Commands

## Content

This document defines repository command keywords that may be invoked directly in prompts.

These commands provide deterministic shortcuts for performing common repository tasks.

---

### Command Summary

bootstrapci

If a prompt consists solely of a single keyword and that keyword is **not present in the Command Summary above**, the agent should **stop reading this document immediately** and continue normal prompt processing.

If the keyword **is present in the Command Summary**, the agent should locate the corresponding command definition below and execute the described behaviour.

---

### bootstrapci

Trigger

bootstrapci

Purpose

Configure the repository validation harness.

This command ensures that the repository has a working `make ci` validation command so that source code changes can be validated before Pull Requests are created.

---

Actions

The agent should:

1. Inspect the repository to determine the technology stack.
2. Locate the existing `Makefile`.
3. Update the `Makefile` so that the `make ci` command performs appropriate validation for the repository.
4. Replace any placeholder `make ci` implementation with a working validation command.
5. If no automated tests exist, create a minimal smoke test inside the `tests/` directory.
6. Execute `make ci` to confirm that validation completes successfully.

After these steps the repository should support validation using:

make ci

---

Bootstrap Guard

If the repository already contains a functioning `make ci` validation command and repository validation appears correctly configured, the agent should **not modify the repository**.

Instead the agent should report that CI validation already exists and no changes are required.

---

Response Format

When executing this command the agent should include the following summary in both the Codex response and the Pull Request description.

Bootstrap command detected: `bootstrapci`

Executed the Bootstrap CI Command defined in `docs/agent_commands.md`.

Prompt-ID: bootstrapci
Base-PR: <number>
Base-SHA: <short_sha>

Actions performed:

• Updated Makefile to implement a working `make ci` validation command
• Configured validation steps based on the detected technology stack
• Created initial smoke test in the tests/ directory
• Verified that `make ci` completes successfully

The repository can now validate source code changes using:

make ci

---

## Editing Guidelines (Do Not Modify Below This Line)

This document defines **repository control commands** used by AI agents.

Agents must treat this file as **read-only**.

Agents should never modify command definitions in this document.

New commands or modifications to existing commands must be performed **only by a human maintainer**.

If a prompt keyword does not appear in the **Command Summary**, the agent should stop reading this document and continue normal prompt processing.
