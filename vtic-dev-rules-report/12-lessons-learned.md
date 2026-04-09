# Lessons Learned

**Project:** vtic — AI-first ticketing system  
**Source:** MEMORY.md, coding-standards.md, vtic development history

---

## 1. The Big Lessons

### Lesson 1: Design Doc Hierarchy is Non-Negotiable

**Problem:**  
Wave 1 had **58 contradictions** across 6+ independently-written design documents. Enums defined differently in OpenAPI vs data models. Field types mismatched. Multiple agents wrote conflicting specs.

**Solution:**  
Define one canonical source (usually OpenAPI) before any parallel work. All other docs must align to it exactly.

**Rule:**  
> Before spawning parallel agents to write design docs, one agent writes the canonical source. All others read it first and align to it.

**Verification:**  
Run cross-reference reviews with GLM-5 to find contradictions BEFORE coding starts.

---

### Lesson 2: File Ownership Prevents Chaos

**Problem:**  
Wave 1: T2 and T3 both wrote `enums.py` independently → merge conflicts.  
Wave 2: T7 wrote sync service, T8 wrote async routes → integration broke.

**Solution:**  
Every file has exactly one owner. Define file ownership in a table before spawning parallel agents.

**Rule:**  
> Each agent's task prompt MUST list the exact files it owns — and only those files. Agents may READ any file but must only WRITE to their owned files.

**Table Format:**
```markdown
| Agent | Owns Files | May Read |
|-------|-----------|----------|
| agent-1 | `src/models/enums.py`, `tests/test_enums.py` | all specs |
| agent-2 | `src/models/ticket.py`, `tests/test_ticket.py` | all specs |
```

---

### Lesson 3: Phase Separation Beats All-in-One

**Problem:**  
Agents designed + coded + tested in one shot → missed details, wrong types, broken contracts. Context window dilutes when tasks are too complex.

**Solution:**  
Split into 6 phases: Design → Plan → Develop → Test → Review → Fix

**Rule:**  
> Never combine phases in a single agent. Each phase is a separate agent spawn with a focused, narrow task.

**Benefits:**
- Focused agents produce cleaner output
- Easier to verify each phase
- Context window stays clean
- Issues caught early, not at integration

---

### Lesson 4: Verify Before Trust

**Problem:**  
GLM-5 claimed "TERMINAL_STATUSES fixed" but never actually changed the file. Agent completed task but didn't do the work.

**Solution:**  
Never trust completion reports. Read actual files. Run actual tests.

**Rule:**  
> After every fix agent, read the actual file content. Search for the specific change. Run tests. Only accept if ALL of: file changed + tests pass.

**Red Flags:**
- Agent says "fixed" but doesn't show diff
- Agent says "all tests pass" but didn't include test output
- Agent completed in unusually short time (may not have done the work)
- Agent completed in unusually long time (may be stuck in a loop)

---

### Lesson 5: Mocks Give False Confidence

**Problem:**  
Mock-based API route tests all passed ✅. Integration tests with real TicketService caught an async/await bug ❌.

**Solution:**  
Real services catch real bugs. Use mocks only for external APIs.

**Rule:**  
> Mock-based tests: medium confidence. Integration tests: highest confidence. Always test with real TicketService.

**When to Mock:**
| Dependency | Mock? |
|------------|-------|
| External API (OpenAI) | ✅ Yes |
| Internal service | ❌ No |
| Database (Zvec) | ❌ No |
| File system | ❌ No |

---

### Lesson 6: Temp Files Must Survive

**Problem:**  
Lost 10+ hours of reconciled vtic design docs when `/tmp/vtic/` was wiped by system cleanup.

**Solution:**  
Never use `/tmp` for anything you need to keep.

**Rule:**  
> Use workspace-relative temp dirs: `{workspace}/tmp/{project}/`. Workspace tmp is git-trackable and survives reboots/sessions.

---

### Lesson 7: Test Hygiene Matters

**Problem:**  
Spent hours debugging a test that was wrong (zero-duration date range). Test looked correct but tested the wrong thing.

**Solution:**  
Verify test validity before debugging code.

**Rule:**  
> Before debugging code, check if the test itself is correct. Common test bugs: zero-duration date ranges, missing mocks, incorrect expected values.

**Rule:**  
> Don't over-debug a single test. If a test keeps failing after 2 attempts, step back and question the TEST, not just the code.

---

## 2. Process Lessons

### Lesson 8: 20-Minute Limit Prevents Waste

**Problem:**  
Agents would spin for 30+ minutes on complex tasks, often getting stuck in loops or producing poor output.

**Solution:**  
Hard 20-minute limit per agent spawn.

**Rule:**  
> No agent task exceeds 20 minutes. If it can't fit, scope it smaller.

**Enforcement:**
- Set explicit timeout in spawn
- If agent exceeds 20 min: kill it, assess what was produced, spawn smaller tasks
- If task can't fit in 20 min → it wasn't scoped small enough

---

### Lesson 9: Report Progress or Stay Silent

**Problem:**  
Agents would go silent for minutes. When they finally reported, they had gone down wrong paths.

**Solution:**  
Report findings and next steps regularly.

**Rule:**  
> Don't go silent for minutes. Report what you found, what you're doing next.

**Rule:**  
> Monitor long-running tasks. If you're stuck on something for more than a few minutes, report it. Don't silently timeout.

---

### Lesson 10: Model Selection Matters

**Problem:**  
Used the wrong model for the wrong task → poor output, wasted time.

**Solution:**  
Match model to task type.

**Assignment Strategy:**

| Role | Model | Task |
|------|-------|------|
| **Coder** | Kimi 2.5 | Implementation |
| **Reviewer** | GLM-5 | Review + fix |
| **Architect** | GLM-5 | Complex design |

**Why:**
- Kimi: Good Python, cost-effective for bulk work
- GLM-5: Catches gaps, strong analysis, good for reviews

---

## 3. Technical Lessons

### Lesson 11: PyYAML Creates Anchors

**Problem:**  
PyYAML auto-creates YAML anchors on duplicate objects. This breaks OpenAPI tooling.

**Solution:**  
Post-process YAML output to remove anchors.

**Rule:**  
> Always post-process PyYAML output:
```python
import re
content = yaml.dump(data)
content = re.sub(r'&id\d+', '', content)
content = re.sub(r'\*id\d+', 'value', content)
```

---

### Lesson 12: YAML Round-Trip Loses Data

**Problem:**  
YAML round-trip (`yaml.dump(yaml.safe_load(content))`) drops non-standard keys like `webhooks` from OpenAPI specs.

**Solution:**  
Re-insert dropped keys manually after round-trip.

**Rule:**  
> After YAML round-trip, check for missing keys. Re-insert `webhooks` and other non-standard sections manually.

---

### Lesson 13: `$ref: null` is Silent Killer

**Problem:**  
A `$ref: null` somewhere in the spec breaks code generation and Swagger UI with no error message.

**Solution:**  
Validate specs with a linter before generation.

**Rule:**  
> Run `swagger-cli validate openapi.yaml` before any code generation. Check for `$ref: null` and other schema issues.

---

### Lesson 14: Zvec RocksDB Stderr

**Problem:**  
Zvec (uses RocksDB internally) prints cosmetic cleanup errors to stderr during tests. These are Zvec's behavior, not a vtic bug.

**Solution:**  
Ignore RocksDB stderr warnings in tests. Don't waste time trying to fix them.

**Rule:**  
> Zvec uses RocksDB internally. Cosmetic cleanup errors in tests are Zvec's behavior, NOT a vtic bug. Do NOT waste time trying to fix them.

---

## 4. Architecture Lessons

### Lesson 15: Markdown is Source of Truth

**Decision:**  
Store tickets as Markdown files with YAML frontmatter. Zvec index is derived.

**Rationale:**
- Git-friendly, human-readable
- Can rebuild index from files
- Simple backup/restore

**Trade-offs:**
- (+) Git diff works naturally
- (+) Human can read/edit files
- (-) Dual write required

---

### Lesson 16: In-Process Vector DB

**Decision:**  
Use Zvec instead of Qdrant/Pinecone/Chroma.

**Rationale:**
- No Docker/server needed
- File-based persistence
- 8500+ QPS performance
- Alibaba-backed

**Trade-offs:**
- (+) No infrastructure overhead
- (+) Fast for local-first
- (-) Single-process only

---

### Lesson 17: Async All the Way

**Decision:**  
Async file I/O, async FastAPI handlers, async everything.

**Rationale:**
- Non-blocking I/O
- Higher throughput
- Consistent with FastAPI patterns

---

## 5. Anti-Patterns to Avoid

### ❌ Reinventing the Wheel

**Rule:**  
Before building any component, search GitHub for existing solutions.

---

### ❌ Specs in Code Comments

**Rule:**  
Design decisions belong in design docs, not inline comments that drift from reality.

---

### ❌ Dual-Source Truth

**Rule:**  
If markdown and Zvec disagree, markdown wins. Rebuild Zvec from markdown.

---

### ❌ Combining Phases

**Rule:**  
Design/Plan/Develop/Test/Review/Fix are separate spawns. Never combine.

---

### ❌ Trusting Agent Reports

**Rule:**  
Read actual files. Run actual tests. Never trust completion reports.

---

## 6. Summary: The 12 Non-Negotiable Rules

1. **Workspace-local temp files** — Never use `/tmp` for anything you need to keep
2. **Unit tests required** — Every new code path has tests. No exceptions.
3. **Max 5 levels deep** — Files must not be buried more than 5 levels from project root
4. **Type-safe code** — No `any`/`unknown`. Use proper types or Zod schemas.
5. **No secrets in code** — API keys → environment variables only
6. **Meaningful git commits** — Conventional commits, one logical change per commit
7. **Test early, test often** — Run tests after each logical change, not after 100 lines
8. **Report progress** — Don't go silent. Report findings and next steps regularly.
9. **Zvec for vectors** — Use Zvec (not Qdrant/Pinecone/Chroma) for vector storage
10. **Design doc hierarchy** — One canonical source. All docs align to it.
11. **Phase separation** — Design/Plan/Develop/Test/Review/Fix are separate spawns
12. **Verify before trust** — Never trust agent reports. Read files. Run tests.

---

## References

- `MEMORY.md` — Long-term lessons
- `rules/coding-standards.md` — All 12 rules
- `tmp/vtic/` — Reference implementation
- `tmp/vtic/FEATURES.md` — Feature specs
