---
name: task-manager
description: Lightweight task tracking for cclow. Use when work becomes multi-step, spans files, or should survive context loss.
---

# Task Manager

Track non-trivial work in simple files, not in your head.

## Files

- `state.md` — global task index
- `plans/SESSION_STATE.template.md` — template for task/session handoff
- `plans/diary.md` — append-only project/workspace diary
- `tasks/` — optional place for task-specific notes or artifacts

## Minimal Status Flow

```text
backlog → ready → in_progress → review → done
                 └────────────→ blocked
```

## Rules

- Use one clear task name
- Keep next step explicit
- Record failed approaches so they are not repeated
- Mark blocked work honestly
- Close tasks only after verification

## State.md Shape

```markdown
# Workspace State

## In Progress
- TASK-001 — title — next step

## Backlog
- TASK-002 — title

## Done
- TASK-000 — title
```
