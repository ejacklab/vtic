# Coding Standards

_These rules are enforced on ALL delegated coding work — subagents, coding agents, ACP sessions, everything._

---

## 1. Workspace-Local Temp Files

**Never use `/tmp` for anything you need to keep.** System cleanup can wipe it anytime.

### Rules
- Use workspace-relative temp dirs: `{workspace}/tmp/{project}/`
- Example: `/home/smoke01/.openclaw/workspace-cclow/tmp/vtic/`
- For subagent output files, use numbered variants: `vtic-1/`, `vtic-2/` to avoid conflicts
- `/tmp` is fine for truly disposable one-off scripts, never for design docs or agent output

### Lesson learned
- Lost 10+ hours of reconciled vtic design docs when `/tmp/vtic/` was cleaned
- Workspace tmp is git-trackable and survives reboots/sessions

---

## 2. Unit Tests (Non-Negotiable)

Every piece of new code **must** have unit tests.

### Before Writing Tests
- Check for existing test files in the project (look for `**/*.test.*`, `**/*.spec.*`, `**/tests/**`, `**/__tests__/**`)
- Read existing test patterns, frameworks, and conventions already in use
- Match the project's testing style — don't introduce a new framework unless asked

### After Writing Tests
- Run the full test suite
- Generate a **test report**: summary of tests run, passed, failed, skipped
- If any tests fail, fix them before finishing

### Coverage
- Test happy paths, edge cases, and error handling
- Mock external dependencies (APIs, databases, filesystem)
- No `// TODO: add tests later` — write them now

---

## 3. Project Structure (Max 5 Levels Deep)

Files must not be placed randomly at the project root. Use a clean, logical folder structure.

### Rules
- Maximum **5 levels** from project root: `project/src/tools/my-tool/handlers/create.ts` ✅ (5 levels)
- Group by **domain/feature**, not by file type
- Put tests **next to the code they test** (co-located) or in a dedicated `tests/` mirror — follow the project convention
- Shared utilities go in `lib/`, `utils/`, or `shared/`
- Config files stay at root or in `config/`

### Example Structure
```
project/
├── src/
│   ├── core/           # level 2
│   │   ├── engine/     # level 3
│   │   │   ├── index.ts
│   │   │   └── engine.test.ts
│   ├── tools/          # level 2
│   │   ├── calculator/ # level 3
│   │   │   ├── calc.ts
│   │   │   └── calc.test.ts
│   └── utils/          # level 2
├── tests/              # integration/e2e (level 2)
├── config/             # level 2
└── package.json
```

### Anti-Patterns
```
❌ project/handler.ts
❌ project/test_handler.ts
❌ project/utils/utils_math/math_utils/basic_math.ts  (6 levels)
```

---

## 4. Code Quality

- **Type-safe**: Use TypeScript with strict types, or Python with type hints
- **No secrets**: API keys, tokens, passwords → environment variables only
- **No `any`/`unknown`**: Use proper types or Zod schemas for validation
- **Error handling**: Every function that can fail should handle errors explicitly
- **No dead code**: Remove unused imports, variables, and commented-out blocks
- **Meaningful names**: `getUserById()` not `getData()` or `fn()`

---

## 5. Git Discipline

- Commit with meaningful messages (conventional commits preferred: `feat:`, `fix:`, `test:`, `refactor:`)
- One logical change per commit — don't mix features
- Don't commit failing tests
- Run tests before committing

---

## 6. Test Hygiene

- **Run tests early** — don't write 100 lines then test. Run after each logical change.
- **Verify test validity** — before debugging code, check if the test itself is correct. Common test bugs:
  - Zero-duration date ranges (`startDate === endDate`)
  - Missing mocks or stubs
  - Incorrect expected values
  - Tests testing the wrong thing
- **Don't over-debug a single test** — if a test keeps failing after 2 attempts, step back and question the test itself, not just the code.

---

## 7. Process Discipline

- **Report progress early** — don't go silent for minutes. Report what you found, what you're doing next.
- **Monitor long-running tasks** — if you're stuck on something for more than a few minutes, report it. Don't silently timeout.
- **Validate tests before fixing code** — distinguishing test bugs from code bugs saves enormous time.

---

## 8. Vector Database: Zvec

When a task requires vector storage, semantic search, or embeddings — **use [Zvec](https://github.com/alibaba/zvec)** by default.

**Why:** In-process (no Docker/server), file-based persistence, lightweight, fast (8500+ QPS), Alibaba-backed (Proxima engine), Python + npm packages.

```bash
pip install zvec
```

**Don't use** Qdrant, Pinecone, Weaviate, ChromaDB, or similar unless the use case specifically requires a client-server vector DB.

---

## 9. Design Doc Hierarchy

When multiple design documents exist (OpenAPI spec, data models, data flows, breakdowns), **one is canonical** — all others must align to it.

### Rules
- **Define the canonical source** before spawning parallel agents to write design docs
- If OpenAPI exists, it is canonical — data models, flows, and breakdowns match its schemas exactly
- Field names, types, enums, defaults, patterns must be identical across all docs
- After parallel generation, always run cross-reference reviews before coding
- Never let different agents independently define the same concept (enums, models, error codes)

### First-draft reconciliation workflow
1. Spawn agents to generate design docs in parallel (fast)
2. Run GLM-5 cross-review agents to find contradictions
3. Reconcile all docs to the canonical source
4. Only then start coding

**Lesson learned:** vtic's first draft had 58 contradictions across OpenAPI, data models, and flows because 6+ agents wrote independently without a shared canonical source.

---

## 10. Parallel Agent File Ownership

When spawning multiple agents to work in parallel, **every file must have exactly one owner**. No two agents may write to the same file.

### Rules
- Each agent's task prompt **must list the exact files it owns** — and only those files
- Agents may **read** any file (specs, other source, tests), but must only **write** to their owned files
- If two agents logically need to modify the same file, one owns it and the other provides patches/instructions
- Shared interfaces (imports, method signatures) must be defined **before** parallel work begins
- Use a table in the task prompt:

| Agent | Owns Files | May Read |
|-------|-----------|----------|
| agent-1 | `src/models/enums.py`, `tests/test_enums.py` | all specs, other source |

### Anti-Patterns
- ❌ "Fix the enums module" → vague, two agents might touch it
- ❌ "Update the models" → too broad
- ✅ "You own ONLY these 3 files: [list]. Do not modify any other file."

### Interface contracts
- Before parallel work, define shared method signatures: `async def create_ticket(data: TicketCreate) -> Ticket`
- Specify sync vs async, parameter types, return types
- Agents implement against the contract — mismatches surface in integration tests

### Lesson learned
- vtic Wave 1: T2 and T3 both wrote `enums.py` independently → merge conflicts
- vtic Wave 2: T7 wrote sync service, T8 wrote async routes → integration tests broke
- vtic fix round: GLM-5 claimed "TERMINAL_STATUSES fixed" but never actually changed the file — always verify fixes

---

## 11. Phase Separation (Design → Plan → Develop → Test → Review → Fix)

Never combine phases in a single agent. Each phase is a separate agent spawn with a focused, narrow task. The context window dilutes when tasks are too complex — separation improves quality.

### Minimum 6 phases per feature

| # | Phase | Agent | Input | Output | Max Time |
|---|-------|-------|-------|--------|----------|
| 1 | **Design** | GLM-5 | Spec, requirements | Interface definitions, data contracts, method signatures | 20 min |
| 2 | **Plan** | Kimi 2.5 | Design output | Task breakdown, file ownership table, test plan | 20 min |
| 3 | **Develop** | Kimi 2.5 / GLM-5 | Plan output | Source code implementation | 20 min |
| 4 | **Test** | Kimi 2.5 | Developed source + plan | Test code, run tests, test report | 20 min |
| 5 | **Review** | GLM-5 | Source + tests + spec | Review report with issues, spec compliance check | 20 min |
| 6 | **Fix** | GLM-5 | Review report + source | Fixes applied, re-run tests, verification | 20 min |

### Rules
- Each phase is a **separate agent spawn** — never combine phases
- **No phase exceeds 20 minutes** — if it does, the task wasn't scoped small enough
- Context window is limited — a focused agent with one clear job outperforms a loaded agent with 5 jobs
- Each phase reads only what it needs: design reads specs, develop reads plan, test reads source, review reads source + spec
- Output of phase N becomes input of phase N+1 (pass as file paths, not inline content)
- If any phase fails, loop back — don't carry bad output forward
- Use **session mode** for tightly coupled phases (Design→Plan, Review→Fix) to carry context forward
- Use **run mode** for independent phases (Develop, Test) to keep context windows clean

### Hybrid session approach

Not all phases need fresh starts. Use session-bound agents for tightly coupled work:

```
Phase 1+2: Same session (Design → Plan)
  spawn(mode="session", label="search-design")
  → agent designs interfaces
  sessions_send(label="search-design", message="Now plan implementation")
  → agent plans with full design context, no loss

Phase 3: New session (Develop)
  spawn(mode="run", task="Implement based on plan at /path/to/plan.md")
  → clean context, focused on code

Phase 4: New session (Test)
  spawn(mode="run", task="Write tests for source at /path/")

Phase 5+6: Same session (Review → Fix)
  spawn(mode="session", label="search-review")
  → agent reviews source + tests against spec
  sessions_send(label="search-review", message="Now fix the issues you found")
  → agent knows exactly what it flagged, fixes precisely
```

**Why hybrid:** Design→Plan and Review→Fix are tightly coupled — context carry-forward prevents miscommunication. But Develop and Test are heavy (lots of code/tokens) and benefit from clean context windows.

### Why separation matters
- Context window dilution: a 70k-token prompt with design + code + tests = confused agent, missed details
- Complexity hurts quality: each additional responsibility reduces correctness
- Focused agents produce cleaner output that's easier to verify

### Anti-patterns
- ❌ "Design and implement the search engine" → design quality suffers
- ❌ "Write code and tests" → tests miss edge cases because context is full of implementation details
- ❌ "Review and fix" → reviewer becomes biased by its own fix suggestions
- ✅ Phase 1: design interfaces → Phase 3: implement against interfaces → Phase 4: write tests → Phase 5: review independently

### Lesson learned
- vtic Wave 1: agents designed + coded + tested in one shot → 58 spec contradictions, async/sync mismatch
- vtic Wave 2: T7 (Kimi) wrote sync service, T8 (Kimi) wrote async routes → no shared interface contract upfront
- vtic fix round: GLM-5 claimed "fixed" but wasn't — reviewer and fixer should be separate agents
- Combining phases in one agent = lower quality per phase, harder to debug

---

## 12. Completion Checklist

Before declaring a task done, verify:
- [ ] Unit tests written and passing
- [ ] Test report generated
- [ ] Code follows project structure (≤5 levels)
- [ ] No secrets or hardcoded values
- [ ] Existing tests still pass
- [ ] No `any` types or untyped code
- [ ] Clean git state (no uncommitted mess)
- [ ] No file ownership conflicts (each file written by exactly one agent)
- [ ] Fixes verified by reading actual file content (not just agent's report)
