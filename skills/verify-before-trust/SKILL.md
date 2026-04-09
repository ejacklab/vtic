---
name: verify-before-trust
description: "Verification protocol for agent outputs. Use when: (1) a subagent or ACP agent claims to have completed a fix or implementation, (2) reviewing agent results before committing, (3) checking if reported changes were actually applied. NOT for: initial implementation (before any agent runs)."
---

# Verify Before Trust

## Core Rule

**Never trust an agent's completion report.** Read the actual files.

## When to Verify

1. **After every fix agent** — especially GLM-5, which has been caught claiming fixes it never applied
2. **After every ACP agent** — Claude Code and Codex can get stuck in fix loops and report incomplete work as done
3. **Before every commit** — confirm files match what agents reported

## Verification Protocol

### For fixes
```
1. Agent reports: "Fixed TERMINAL_STATUSES to include FIXED"
2. READ the actual file: read(src/vtic/models/enums.py)
3. Search for the specific change: grep "FIXED" in TERMINAL_STATUSES
4. Run tests: uv run pytest tests/ -v
5. Only accept if ALL of: file changed + tests pass
```

### For new code
```
1. Agent reports: "Implemented SearchEngine with 5 methods"
2. READ the file: read(src/vtic/search/engine.py)
3. Check method signatures match the design doc
4. Check for stubs (pass, NotImplementedError, TODO)
5. Run tests
```

### For reviews
```
1. Reviewer reports: "All tests pass, no issues"
2. Run the full test suite yourself
3. Spot-check 2-3 files the reviewer said were fine
4. Check the review file was actually written
```

## Red Flags

- Agent says "fixed" but doesn't show a diff
- Agent says "all tests pass" but didn't include test output
- Agent completed in unusually short time (may not have actually done the work)
- Agent completed in unusually long time (may be stuck in a loop, partial output)

## Lessons from vtic

- **GLM-5 claimed TERMINAL_STATUSES was fixed** — file was unchanged. Caught by cross-check reviewer.
- **Mock-based tests passed** but integration tests failed — verify against real services, not mocks.
- **Claude Code ACP ran 1h15m** — claimed to be working but was stuck. File was written at 14:23 but process ran until 15:19.
