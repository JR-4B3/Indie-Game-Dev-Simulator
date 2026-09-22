---
description: Plan, delegate, review, and verify a task end to end
agent: lead
subagent: false
---

Carry out this task end to end:

$ARGUMENTS

Inspect the repository and current work first, then plan before implementing.
Break non-trivial work into bounded work packages and delegate to the right
subagents (`explore` for research, `builder` for substantial work, `micro` for
tiny edits, `reviewer` for read-only review). Put every implementation through
the review loop.

Do not declare completion on passing tests alone: run the affected application
or page, use browser tools to exercise the real flow, capture desktop and narrow
screenshots, inspect them yourself, and confirm the result is visibly finished
and usable. Report what changed, what ran, what you saw, and anything unverified.
