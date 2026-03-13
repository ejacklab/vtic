---
name: planning
description: Workspace-local planning guide for cclow. Use before edits, coding, research, debugging, or any multi-step task that needs a clear approach and verification plan.
---

# Planning

Create plans before implementation.

## Planning Checklist

1. **Context** — what files, systems, or prior decisions matter?
2. **Goal** — what outcome is actually needed?
3. **Scope** — what is included and excluded?
4. **Steps** — ordered, testable checklist items
5. **Verification** — how each step will be checked
6. **Risks** — what could go wrong or need approval?

## Good Plan Shape

```markdown
# Plan: [task]

## Goal
- [one sentence]

## Scope
- In: ...
- Out: ...

## Steps
- [ ] Step 1 ...
  - Verify: ...
- [ ] Step 2 ...
  - Verify: ...

## Risks / Approval Points
- ...
```

## When to Stop for Approval

Always pause before:
- destructive changes
- schema or public API changes
- adding secrets or credentials
- editing broad/shared behavior with unclear impact

## Session State

If a task may span multiple turns, create or update a session-state file in `plans/` using `plans/SESSION_STATE.template.md`.

## Context Budget Rule

If a task feels too broad, split it before implementation. Prefer a small passing slice over a giant speculative change.
