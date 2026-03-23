# WhatsOnYourMind (WOYM)

## Content

(Add content here)
---

## Editing Guidelines (Do Not Modify Below This Line)

This document records the repository’s decision about **WhatsOnYourMind (WOYM)**.

Focus on whether the repository should expose a **runtime introspection surface**, not on detailed implementation tasks.

Explain whether WOYM is needed for this repository and, if so, what shape it should take.

Typical things described here include:

• whether WOYM is needed now, later, or not at all
• why WOYM is or is not appropriate for this repo
• what form WOYM would take in this repo
• what kind of state or decisions WOYM should expose
• whether WOYM should support dry-run / calculate-but-don’t-act behaviour
• whether CI or automated testing should inspect WOYM

WOYM is generally a quiet, curated explanation of system state, not a raw log.

It should usually prefer:

• current meaningful state
• important recent inputs or commands
• key events that contributed to the current state
• warnings or errors
• summaries of important derived values or telemetry

When updating this document:

• always fill in the Content section, even if the conclusion is that WOYM is not needed yet
• make the repository’s decision explicit
• describe the intended WOYM shape if it is needed
• prefer concise, repo-specific guidance over generic theory
• describe summaries rather than raw logs where appropriate
• state whether dry-run / safe action preview would be useful for this repo

Avoid including:

• detailed implementation code
• step-by-step engineering tasks
• full test scripts
• general task tracking

Engineering work and task tracking belong in `liveplan.md`.

Only edit the **Content section above** unless the documentation system itself is being changed.
