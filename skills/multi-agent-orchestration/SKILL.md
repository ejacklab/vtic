---
name: multi-agent-orchestration
description: "Orchestrate multiple coding agents (subagents and ACP harnesses) for parallel development. Use when: (1) spawning 2+ agents for a coding task, (2) deciding between subagent vs ACP, (3) defining file ownership and interface contracts, (4) coordinating agent lifecycle (spawn, monitor, timeout, kill). NOT for: single-agent tasks, simple edits."
---

# Multi-Agent Orchestration

## Subagent vs ACP Decision Matrix

| Factor | Subagent | ACP (Claude Code/Codex) |
|--------|----------|------------------------|
| Task clarity | Precise instructions available | Open-ended, needs exploration |
| Speed | Fast (30s-5min typical) | Slow (5-30min typical) |
| File access | read/write/exec tools | Full CLI with TTY |
| Autonomy | Linear execution | Self-directed loops |
| Cost | Lower (API only) | Higher (CLI process) |
| Stuck risk | Low (single turn) | High (can loop forever) |

**Rule: If you can write a 3-line spec, use subagent. If you need to say 'figure it out', use ACP.**

## 20-Minute Hard Limit

Every agent spawn (subagent or ACP) must complete within **20 minutes**. If a task can't fit in 20 min, it wasn't scoped small enough.

**Enforcement:**
- Set explicit timeout in spawn: `runTimeoutSeconds: 1200`
- Use cron watchdog for ACP: `openclaw cron add --at "20m" --delete-after-run`
- If an agent exceeds 20 min: kill it, assess what was produced, spawn smaller tasks

## Phase Separation (6 Phases)

| Phase | Session | Model | Input | Output |
|-------|---------|-------|-------|--------|
| 1. Design | Shared | GLM-5 | Specs, existing code | Design doc with interfaces |
| 2. Plan | Shared | Kimi 2.5 | Design doc | Task breakdown + file ownership |
| 3. Develop | Fresh per agent | Kimi 2.5/GLM-5 | Plan + file assignments | Source code |
| 4. Test | Fresh | Kimi 2.5 | Source code + tests spec | Passing tests |
| 5. Review | Shared | GLM-5 | Source + tests + specs | Review report |
| 6. Fix | Shared with Review | GLM-5 | Review report | Fixed code |

**Session sharing:** Design→Plan and Review→Fix share context. Develop and Test get fresh sessions.

## File Ownership

Every file has exactly **one owner** when parallel agents work. Define before spawning:

```markdown
| Agent | Files | Model |
|-------|-------|-------|
| A | search/__init__.py, search/engine.py | Kimi 2.5 |
| B | api/routes/search.py | Kimi 2.5 |
| C | services/, api/routes/system.py, api/deps.py, api/app.py | Kimi 2.5 |
```

**Rules:**
- Agents can READ anything
- Agents WRITE only their owned files
- Shared files (deps.py, app.py) → assign to one agent or do sequentially
- Interface contracts defined in plan phase BEFORE parallel spawn

## Interface Contracts

When two agents produce code that integrates, define the contract first:

```python
# In plan phase, define exact signatures:
class SearchEngine:
    def search(self, query: SearchQuery, request_id: str | None = None) -> SearchResult
    def suggest(self, partial: str, limit: int = 5) -> list[SuggestResult]
```

Both agents implement against this contract. No ambiguity.

## Spawn Template

```
Phase 3 — Develop (parallel):
Agent A (Kimi 2.5): {task description}
  Files: {owned files}
  Reads: {spec files, contract definitions}
  Timeout: 20 min

Agent B (Kimi 2.5): {task description}
  Files: {owned files}
  Reads: {spec files, contract definitions}
  Timeout: 20 min
```

## Verify Before Trust

**Never trust an agent's completion report.** Always verify by reading actual file content.

After a fix agent claims "I fixed X":
1. Read the actual file: `read(path)`
2. Check the specific change was applied
3. Run tests to confirm
4. GLM-5 fix agents have been caught claiming fixes they never made

## Agent Lifecycle

- **Spawn:** `sessions_spawn` for subagents, `runtime="acp"` for ACP
- **Monitor:** Wait for push-based completion. Do NOT poll.
- **Timeout:** Kill at 20 min. Check what was produced before killing.
- **Partial completion:** If agent produced files but didn't finish tests, spawn a fresh test agent.
- **Retry:** If agent failed completely, re-scope the task smaller and retry once.
