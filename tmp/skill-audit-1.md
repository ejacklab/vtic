# Skill Audit — Coding Rules

## New Skills Proposed

### 1. parallel-agent-orchestrator
- **What:** How to spawn and coordinate multiple agents working in parallel without conflicts. Covers file ownership tables, interface contracts, session vs run mode selection, and the hybrid session approach (Design→Plan shares session; Develop/Test get fresh sessions).
- **Prevents:** 
  - Two agents writing the same file (vtic T2/T3 both wrote enums.py)
  - Async/sync mismatches (vtic T7 wrote sync service, T8 wrote async routes)
  - Interface contract violations
  - Context window pollution from combining phases
- **Covers rules:** #10 (Parallel Agent File Ownership), #11 (Phase Separation)
- **Concrete mistakes prevented:**
  - vtic Wave 1: 58 contradictions from 6+ agents writing design docs independently
  - vtic Wave 2: Integration tests broke due to sync/async mismatch
  - Fix round: GLM-5 claimed "TERMINAL_STATUSES fixed" but file was unchanged

### 2. verify-before-trust
- **What:** Mandates reading actual file content to verify fixes. Agents often report success without actually applying changes. This skill provides the verification protocol: always `read` the file after a fix agent claims completion.
- **Prevents:** False "fixed" reports from agents who only claimed to fix but didn't.
- **Covers rules:** #12 (Completion Checklist - "Fixes verified by reading actual file content")
- **Concrete mistakes prevented:**
  - vtic: GLM-5 claimed TERMINAL_STATUSES included FIXED — file unchanged
  - vtic: Multiple fix rounds where agents reported success but nothing changed

### 3. test-hygiene
- **What:** Distinguishes real integration tests from mock-based tests that give false confidence. Covers when to use mocks (external APIs only) vs real services, and the rule that unit tests must run against actual implementations where possible.
- **Prevents:** Mock-based tests passing while real code fails in production.
- **Covers rules:** #2 (Unit Tests), #6 (Test Hygiene)
- **Concrete mistakes prevented:**
  - vtic early tests used mocks that hid async/await bugs
  - Real-service tests caught integration issues mocks missed

### 4. acp-subagent-router
- **What:** Decision matrix for when to use ACP (Claude Code, Codex CLI) vs subagents. Subagents = precise instructions, fast, cheap. ACP = open-ended exploration, autonomous, slower. Includes the 20-minute phase limit applies to both.
- **Prevents:** Using ACP for well-defined tasks (overkill) or subagents for exploration (underpowered).
- **Covers rules:** Implicit in AGENTS.md task routing table
- **Concrete mistakes prevented:**
  - Claude Code ACP session stuck for 1h15m in fix loop (should have used subagent)
  - GPT-5.4 subagent: 30 seconds vs Codex ACP: ~30 minutes for same task

### 5. design-doc-reconciliation
- **What:** The first-draft reconciliation workflow for when multiple agents generate design docs in parallel. Steps: 1) Define canonical source, 2) Parallel generation, 3) Cross-reference review agents (GLM-5), 4) Reconcile to canonical, 5) Only then start coding.
- **Prevents:** Contradictions across OpenAPI specs, data models, data flows, and breakdowns.
- **Covers rules:** #9 (Design Doc Hierarchy)
- **Concrete mistakes prevented:**
  - vtic first draft: 58 contradictions across 6+ independently-written docs
  - Enums defined differently in OpenAPI vs data models
  - Field types mismatched between specs

### 6. temp-file-manager
- **What:** Workspace-relative temp directory convention. Never use `/tmp/` for design docs or agent output — use `{workspace}/tmp/{project}/` with numbered variants for parallel work.
- **Prevents:** Lost work when system cleans `/tmp/`.
- **Covers rules:** #1 (Workspace-Local Temp Files)
- **Concrete mistakes prevented:**
  - Lost 10+ hours of reconciled vtic design docs when `/tmp/vtic/` cleaned

### 7. code-quality-guardrails
- **What:** Pre-commit checklist for TypeScript/Python quality: strict types, no secrets, no `any`/`unknown`, explicit error handling, meaningful names. Includes automated checks where possible.
- **Prevents:** Tech debt accumulation, security leaks, unmaintainable code.
- **Covers rules:** #4 (Code Quality), #5 (Git Discipline)
- **Concrete mistakes prevented:**
  - Hardcoded API keys in source
  - `any` types propagating through codebase
  - Dead code and unused imports accumulating

### 8. project-structure-validator
- **What:** Validates file placement against max 5-level depth rule, domain-based grouping, and co-located tests. Prevents root-level clutter and excessive nesting.
- **Prevents:** messy project roots, 6+ level deep file paths, test files scattered randomly.
- **Covers rules:** #3 (Project Structure)
- **Concrete mistakes prevented:**
  - Files dumped at project root
  - `project/utils/utils_math/math_utils/basic_math.ts` (6 levels)

## Existing Skills to Enhance

### harness-workflow / self-harness
- **Missing:** 
  - Phase separation guidance (Rule #11) — the 6-phase workflow isn't mentioned
  - 20-minute timebox rule per phase
  - Parallel agent orchestration patterns
  - Hybrid session approach (when to use session mode vs run mode)
  - File ownership table template

### coding-agent
- **Missing:**
  - The 20-minute phase limit (agents exceeded this and got stuck in vtic)
  - Phase boundaries — when to kill and respawn vs continue
  - File ownership constraints when spawning multiple coding agents
  - Integration with design-doc-reconciliation skill

### planning
- **Missing:**
  - The full 6-phase pipeline (Design→Plan→Develop→Test→Review→Fix)
  - Canonical source definition for multi-doc projects
  - Pre-implementation reconciliation step
  - Test plan requirements from Rule #2

### task-manager
- **Missing:**
  - Timebox tracking (20 min per phase)
  - File ownership column in task tracking
  - Verification status (not just completion)

## Rules to Promote to Skills

### Rule #10 — Parallel Agent File Ownership
- **Why it's a skill:** This is a workflow procedure for multi-agent coordination, not a coding standard. It requires:
  - File ownership table format
  - Interface contract definition
  - Read vs write permissions
  - Conflict resolution when two agents need the same file

### Rule #11 — Phase Separation
- **Why it's a skill:** This is a complete workflow methodology with:
  - 6 defined phases with inputs/outputs/max times
  - Hybrid session approach (which phases share sessions)
  - Phase transition protocols
  - Failure loops (when to go back to previous phase)
  - Time enforcement (20 min max)

### Rule #9 — Design Doc Hierarchy
- **Why it's a skill:** This is a document management workflow:
  - Canonical source definition
  - Parallel generation coordination
  - Cross-reference review process
  - Reconciliation workflow
  - Alignment verification

### Rule #1 — Workspace-Local Temp Files
- **Why it's a skill:** This is a workspace management procedure:
  - Directory naming convention
  - Numbered variants for parallel work
  - Git-trackable temp vs system temp
  - Migration path from `/tmp/` to workspace temp

## Summary: Priority Order for Skill Creation

1. **parallel-agent-orchestrator** — Highest impact, addresses root cause of most vtic issues
2. **verify-before-trust** — Simple, high leverage, prevents false progress
3. **acp-subagent-router** — Needed now that ACP is being configured
4. **design-doc-reconciliation** — Prevents 58-contradiction scenarios
5. **test-hygiene** — Quality gate for the testing rule
6. **temp-file-manager** — Simple utility skill
7. **code-quality-guardrails** — Could be bundled references
8. **project-structure-validator** — Could be a script in code-quality-guardrails
