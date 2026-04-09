---
name: self-harness
description: Design and use a workspace-local self-harness for multi-step work, planning, tracking, verification, and continuity. Use when setting up or refining how cclow works in a workspace, when tasks span files or replies, when context loss is a risk, or when the user asks how work should be organized, tracked, or resumed.
---

# Self Harness

Use this skill to **implement or use** a lightweight harness inside the current workspace.

This is not a ceremony skill. It is a **router + operating guide** for structured work.

## When to Use

Use for:
- multi-step tasks
- work spanning multiple files
- tasks likely to take more than one reply/session
- work that needs explicit tracking or resumption
- fixing drift in how the workspace is organized

Skip it for:
- tiny one-shot answers
- trivial edits with no continuity risk
- casual conversation

## Minimal Harness

The minimum useful harness is:

```text
state.md        # what is active, blocked, backlog, done
plans/          # session/task handoff and active work notes
memory/         # continuity and durable lessons
rules/workflow/ # planning, verification, cleanup, diary discipline
skills/         # local guides for how to work
```

## Quick Start

1. Read `state.md`
2. Read the relevant workflow rule from `rules/workflow/`
3. If the task is non-trivial, create or update a plan in `plans/`
4. Execute step-by-step with verification
5. Record decisions / dead ends / next steps

## Routing Guide

Read these local skills as needed:

- `skills/scrum-master-lite/SKILL.md`
  - use for the overall operating loop
  - triggers: start / review / retro
- `skills/planning/SKILL.md`
  - use before implementation or broad edits
  - creates the actual plan shape
- `skills/task-manager/SKILL.md`
  - use when work needs explicit state tracking

Read these workflow rules as needed:

- `rules/workflow/planning.md` — plan-first discipline
- `rules/workflow/planning_execution_protocol.md` — 10-step execution sequence
- `rules/workflow/verification.md` — how to verify instead of guessing
- `rules/workflow/cleanup.md` — end-of-task cleanup discipline
- `rules/workflow/diary.md` — how to log what matters

For more detail, use:
- `references/workspace-anatomy.md` — what lives where
- `references/planning-patterns.md` — small vs larger planning shapes
- `references/state-tracking.md` — how to track active work
- `references/verification-recipes.md` — verification by task type
- `references/evolution-workflow.md` — how to improve the harness without over-engineering it

## Operating Rules

- Plan before non-trivial execution
- Verify real outcomes, not vibes
- Write down failed approaches
- Use the lightest structure that prevents chaos
- Evolve incrementally; do not bureaucratize the workspace

## Failure Protocol

If parts of the harness are missing, stale, or contradictory:
1. fall back to the minimum loop: **plan → execute → verify → log**
2. note the breakage in `plans/diary.md` or `memory/YYYY-MM-DD.md`
3. fix the harness after the active task is stabilized

Do not halt useful work just because the harness is imperfect.

## Anti-Patterns

- making a plan for a 2-minute fix
- updating state files for every tiny move
- declaring done without a check
- adding files no one will read
- turning the harness into a shrine instead of a tool
- creating recursive meta-instructions with no concrete next step

## Evolution Signals

Add or refine structure when:
- the same mistake repeats
- context gets lost between turns
- tasks stall because next steps are unclear
- verification is repeatedly skipped or vague

Simplify when:
- files are unused
- tracking overhead exceeds value
- the process is slowing real delivery
