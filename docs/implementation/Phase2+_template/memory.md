# Memory

## Content

(Add content here)
---

## Editing Guidelines (Do Not Modify Below This Line)

This document captures **operational knowledge and lessons learned while building and running the system**.

It preserves insights that are easy to forget but valuable for future debugging and maintenance.

Entries should capture behaviors that were **not obvious from documentation**, especially when working with external systems such as:

• webhooks
• message queues
• scheduled jobs
• email ingestion pipelines
• third-party APIs

Each entry should briefly describe:

• what happened
• how it was confirmed
• the impact on the system
• what was changed or learned

Example entry structure:

### Observation: <short title>

**What happened**

Describe the behavior that was observed.

**How it was confirmed**

Explain how the issue or behavior was verified.

**Impact**

Describe the effect on the system or workflow.

**Resolution / Lesson**

Describe what was learned or changed.

Use this document to record:

• unexpected system behaviors
• integration quirks
• debugging discoveries
• operational lessons

Avoid including:

• architecture design decisions
• implementation details
• speculative ideas

Architecture decisions belong in `decisions.md`.
Future ideas belong in `futuredirections.md`.

Only edit the **Content section above** unless the documentation system itself is being changed.
