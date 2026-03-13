---
name: scrum-master-lite
description: Lightweight self-orchestration for cclow. Use for any non-trivial task: multi-step work, coding, debugging, research, cleanup, or anything likely to span more than one reply.
---

# Scrum Master Lite

Default operating loop for this workspace.

## The 3 Triggers

```text
ON_FEATURE_START → PLAN
ON_FEATURE_END   → REVIEW
ON_TASK_COMPLETE → RETRO
```

Plus: **CEO_CHECK** anytime when direction feels muddy.

## Trigger 1: ON_FEATURE_START → PLAN

Use when starting any non-trivial task.

Do this:
1. Gather context from the relevant files
2. Create a short implementation plan with testable items
3. If the task looks large, split it
4. Present the plan before major edits when review is needed

## Trigger 2: ON_FEATURE_END → REVIEW

When implementation is done:
1. Verify acceptance criteria
2. Check for stale docs or obvious cleanup
3. Summarize what changed and any remaining risks

## Trigger 3: ON_TASK_COMPLETE → RETRO

When the task is actually complete:
1. Record what worked / what failed
2. Update `plans/diary.md`
3. Update `memory/YYYY-MM-DD.md` if the lesson matters beyond the task
4. Update docs/rules if a repeatable lesson was learned

## CEO_CHECK

Ask this whenever a task is ambiguous:
- Is this aligned with what Ejack actually wants?
- Is this the smallest useful step?
- Am I optimizing the artifact instead of the real goal?

## Anti-Patterns

- Starting long work without a plan
- Declaring done before verification
- Hiding uncertainty instead of surfacing it
- Skipping the retro because the task “basically worked”
