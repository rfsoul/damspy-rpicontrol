# Prompt Library

##Content

(Add content here)

---
## Editing Guidelines (Do Not Modify Below This Line)


This file stores Codex task prompts keyed by Prompt-ID.

Rules:
- `liveplan.md` is the source of truth for step status and execution sequencing.
- `prompts.md` stores prompt text only.
- Every `type=code` liveplan step should have a Prompt-ID and matching prompt entry here.
- Goals do not receive Prompt-IDs.
- Once a Prompt-ID has been used to drive implementation, that Prompt-ID must never change.
- Prompt-IDs for steps not yet run may be changed, but `liveplan.md` and `prompts.md` must be updated together.
- Used Prompt-IDs are permanent historical identifiers.
