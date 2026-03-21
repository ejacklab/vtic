# Skill Audit — Workflow Skills

**Date:** 2026-03-19  
**Auditor:** workflow auditor subagent  
**Scope:** harness-workflow, self-harness, planning, task-manager, scrum-master-lite

---

## Gaps Found

### 1. Multi-Agent Orchestration Patterns
- **Problem:** No skill explains the decision framework for subagent vs ACP. AGENTS.md mentions both but doesn't clarify when each is appropriate (e.g., "subagent = execute precise instructions" vs "ACP = delegate open tasks" exists only in memory/2026-03-19.md, not in any skill).
- **Impact:** Agents may choose the wrong tool, leading to inefficiency (Claude Code ACP 1h15m vs subagent 30s for same task).

### 2. Agent Lifecycle Management
- **Problem:** No skill covers how to spawn, monitor, timeout, or kill agents. The 20-minute phase limit from Rule #11 is documented but not enforced. No guidance on handling hung agents or partial completions.
- **Impact:** Wave 3 (46f62ab) succeeded because phases were time-boxed, but this was learned through pain in Waves 1-2. Without enforcement, agents run long and burn tokens.

### 3. Phase Separation Enforcement
- **Problem:** Rule #11 describes the 6-phase workflow (Design → Plan → Develop → Test → Review → Fix) but it's buried in coding-standards.md, not in any workflow skill. No mechanism exists to actually enforce the 20-minute limit per phase.
- **Impact:** Agents combine phases (design+coding+testing in one), leading to 58 spec contradictions in vtic Wave 1, async/sync mismatches in Wave 2.

### 4. Task Scoping Guidance
- **Problem:** Skills say "split large tasks" but don't define "large." No heuristics for when to spawn vs when to do inline. "Non-trivial" is subjective.
- **Impact:** Inconsistent task sizing — some tasks spawn for 5-minute fixes, others try to do 2-hour waves in one agent.

### 5. Cross-Agent Communication Patterns
- **Problem:** Rule #10 covers file ownership but not inter-agent communication. No skill explains interface contracts, shared state, or how agents should pass context (file paths vs inline content).
- **Impact:** T7 wrote sync service while T8 wrote async routes — no shared contract upfront. Integration tests broke.

### 6. Cost/Token Tracking
- **Problem:** No skill tracks costs across waves. GLM-5 fix agents "lie about applying fixes" (memory/2026-03-19.md) but there's no verification skill to catch this systematically.
- **Impact:** Repeated fix cycles, wasted tokens, fake "done" states.

### 7. Verification of Agent Claims
- **Problem:** AGENTS.md says "verify subagent output against completion checklist" but verification.md only covers implementation verification, not agent-claim verification.
- **Impact:** GLM-5 claimed TERMINAL_STATUSES fixed but never changed the file. Cross-check reviewer (agent 8) caught it — but this was ad-hoc, not systematic.

---

## Skill Consolidation

### Overlap: harness-workflow (global) vs self-harness (local)
- **Current:** 
  - `harness-workflow` (global): 4-step loop (Plan → Track → Execute → Close), minimal harness structure, 3 triggers
  - `self-harness` (local): Nearly identical description, references scrum-master-lite and planning skills, adds routing layer
- **Proposed:** Merge into a single skill. The global skill should reference local workspace files if they exist, otherwise provide defaults. Remove duplication — having two "default operating loops" is confusing.

### Overlap: planning skill vs planning.md rule
- **Current:**
  - `skills/planning/SKILL.md`: Planning checklist, good plan shape, session state guidance
  - `rules/workflow/planning.md`: Pre-execution planning, mandatory order, session state
- **Proposed:** Consolidate into planning skill. The rule file duplicates content. Skills should be the source of truth; rules should reference them.

### Overlap: task-manager vs state.md pattern
- **Current:** task-manager describes state.md format, but state.md is also referenced in harness-workflow and self-harness.
- **Proposed:** Keep task-manager as the canonical reference for state tracking. Other skills should link to it rather than duplicating the state.md format.

---

## New Workflow Skills Needed

### 1. multi-agent-orchestration
- **Purpose:** Decision framework for when to spawn subagents vs use ACP, how many to spawn, how to coordinate them.
- **Contents:**
  - Subagent vs ACP decision matrix (from memory/2026-03-19.md lessons)
  - When to parallelize vs serialize
  - File ownership rules (migrate Rule #10 here)
  - Interface contract templates
  - Cross-agent communication patterns (file-based vs message-based)
- **Prevents:** Wrong tool selection, file conflicts, integration mismatches.

### 2. phase-separation
- **Purpose:** Enforce the 6-phase workflow with actual time limits.
- **Contents:**
  - The 6 phases: Design → Plan → Develop → Test → Review → Fix
  - Max 20 min per phase (hard limit)
  - Hybrid session approach (Design→Plan same session, Develop/Test fresh sessions, Review→Fix same session)
  - Phase inputs/outputs (what each phase reads and produces)
  - Loopback rules (when to restart a phase)
- **Prevents:** Phase combining, context window dilution, quality degradation.

### 3. agent-lifecycle
- **Purpose:** Spawn, monitor, timeout, and kill agents properly.
- **Contents:**
  - Spawn patterns (run vs session mode)
  - Timeout handling (default 20 min, extend conditions)
  - Kill conditions (infinite loops, fix loops like Claude Code ACP)
  - Monitoring in-flight agents (check status without polling)
  - Handling partial completions
  - Retry with backoff
- **Prevents:** Runaway agents, hung sessions, token waste.

### 4. wave-planning
- **Purpose:** Plan multi-wave development (like vtic v0.1).
- **Contents:**
  - Wave definition (vertical slice vs horizontal layer)
  - Wave sizing (how many tasks per wave)
  - Cross-wave dependencies
  - Wave retro template (what to capture)
  - When to split a wave
- **Prevents:** Waves that are too big, unclear dependencies, missing retros.

### 5. agent-verification
- **Purpose:** Verify agent claims ("I fixed it") against actual file content.
- **Contents:**
  - Never trust agent reports — always read files
  - Cross-check reviewer pattern (separate agent verifies)
  - Fix verification checklist
  - Handling "fake fixes" (claimed but not applied)
- **Prevents:** Fake done states, repeated fix cycles.

### 6. cost-tracking
- **Purpose:** Track token usage and costs across waves/phases.
- **Contents:**
  - Model cost per token (reference table)
  - Wave cost logging template
  - Cost optimization heuristics
  - When cheaper models are acceptable (Rule #11 Kimi vs GLM-5 split)
- **Prevents:** Unnecessary expensive model usage, budget overruns.

---

## Existing Skill Enhancements

### harness-workflow
- **Add:** Reference to the 6-phase workflow (from Rule #11)
- **Add:** Explicit time limits (20 min per phase)
- **Add:** Subagent vs inline decision heuristics (when to spawn)
- **Add:** Link to new multi-agent-orchestration skill
- **Remove:** Duplication with self-harness (merge or differentiate clearly)

### self-harness
- **Add:** Clarify it's the "router" — harness-workflow is the "engine"
- **Add:** Reference to phase-separation skill
- **Add:** Explicit statement: "If a task exceeds 20 min, you didn't scope it small enough"
- **Add:** Reference to agent-lifecycle for spawning patterns

### planning
- **Add:** Task sizing heuristics ("if you can't verify in 2 steps, split it")
- **Add:** Pre-spawn checklist (should this be inline or delegated?)
- **Add:** Reference to wave-planning for multi-wave work
- **Add:** Phase input/output template (what does this plan feed into?)

### task-manager
- **Add:** Token cost field in state.md template
- **Add:** Agent assignment field (which agent owns this task)
- **Add:** Phase tracking (which phase is this task in?)
- **Add:** Blocked reason taxonomy (dependency, approval needed, etc.)

### scrum-master-lite
- **Add:** Phase gates (Design gate, Review gate, etc.)
- **Add:** CEO_CHECK for wave planning ("is this the smallest useful wave?")
- **Add:** Retro template with cost tracking section

### coding-standards
- **Remove:** Rule #10 and Rule #11 (migrate to new multi-agent-orchestration and phase-separation skills)
- **Add:** References to new skills instead of inline rules
- **Keep:** The completion checklist (it's coding-specific)

---

## Summary

The workflow skills work for single-agent tasks but lack structure for multi-agent orchestration. The vtic v0.1 success (600 tests, all passing) came from hard-won lessons that aren't captured in skills yet:

1. **Phase separation with 20-min limits** → needs phase-separation skill
2. **Subagent vs ACP decision framework** → needs multi-agent-orchestration skill
3. **Agent spawn/monitor/timeout/kill** → needs agent-lifecycle skill
4. **Verify fixes by reading files** → needs agent-verification skill
5. **Wave planning with retros** → needs wave-planning skill

Without these skills, future multi-agent work will repeat the same mistakes: phase combining, fake fixes, wrong tool selection, runaway agents.
