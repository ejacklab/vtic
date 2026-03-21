# Simplified TDD Workflow (LLM-Optimized)

**Version:** 1.0
**Created:** 2026-03-21
**Status:** Validated on Phase 3.1 (shared.auth, 75 tests, 100% pass)

---

## Overview

Traditional TDD assumes incremental discovery of requirements. With LLMs, we can enumerate all behaviors upfront, reducing 4 stages to 3 and 4 enhancement cycles to 1.

### Traditional TDD vs Simplified TDD

| Aspect | Traditional TDD | Simplified TDD |
|--------|-----------------|----------------|
| Stages | 4 | 3 |
| Enhancement cycles | 4 | 1 |
| Test categories | Discovered incrementally | Enumerated upfront |
| Turns required | 8-12 | 3-4 |
| Best for | Human developers | LLM agents |

---

## Stage 1: SPEC (Behavior Definition)

**Duration:** ~5 minutes
**Agent:** Any (cclow, GLM-5, Claude Code)

### Purpose

Define ALL behaviors upfront before writing any code.

### Input

- Module requirements
- Design documents
- Existing code (if enhancing)

### Output

`SPEC.md` with complete behavior specification:

```markdown
# [Module Name] Behavior Specification

## 1. POSITIVE BEHAVIORS (Happy Path)
| ID | Behavior | Input | Expected Output |
|----|----------|-------|-----------------|
| P1 | ... | ... | ... |

## 2. NEGATIVE BEHAVIORS (Error Cases)
| ID | Behavior | Input | Expected Error |
|----|----------|-------|----------------|
| N1 | ... | ... | ... |

## 3. EDGE CASES (Boundaries)
| ID | Behavior | Input | Expected Output |
|----|----------|-------|-----------------|
| E1 | ... | ... | ... |

## 4. INTEGRATION POINTS
- External dependencies
- API contracts
- Data flow

## 5. SECURITY CONSIDERATIONS
- Auth requirements
- Data validation
- Information disclosure

## 6. PUBLIC INTERFACE
- Function signatures
- Type definitions
- Exported classes

## 7. TEST COVERAGE TARGETS
- Positive tests: X-Y
- Negative tests: X-Y
- Edge cases: X-Y
- Integration tests: X-Y
- Total: X-Y tests
```

### Guidelines

1. **Be exhaustive** - List every behavior you can think of
2. **Use IDs** - P1, N1, E1 format for traceability
3. **Include security** - Don't forget auth, validation, logging
4. **Define interface** - Function signatures before implementation

### Example (shared.auth)

```
38 behaviors defined:
- 11 positive (happy path)
- 14 negative (error cases)
- 13 edge cases (boundaries)
- 3 integration points
- 14 security considerations

Target: 50-70 tests
```

---

## Stage 2: GENERATE (Code + Tests Together)

**Duration:** ~15 minutes
**Agents:** GLM-5 (implementation) + MiMo (test generation)

### Purpose

Generate implementation AND test suite in ONE shot.

### Parallel Execution

| Agent | Task | Output |
|-------|------|--------|
| GLM-5 | Generate tests | `test_auth.py` (63 tests) |
| MiMo | Generate tests | `test_auth.py` (~55 tests) |
| GLM-5 | Implement code | `auth.py` + merge best tests |

### Test Structure

```python
"""Tests for [module] module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

# ===== POSITIVE TESTS =====
class TestPositiveBehaviors:
    """Happy path tests."""
    
    async def test_P1_valid_input(self):
        """P1: Valid input returns expected output."""
        pass

# ===== NEGATIVE TESTS =====
class TestNegativeBehaviors:
    """Error case tests."""
    
    async def test_N1_invalid_input(self):
        """N1: Invalid input raises expected error."""
        pass

# ===== EDGE CASES =====
class TestEdgeCases:
    """Boundary condition tests."""
    
    async def test_E1_boundary(self):
        """E1: Behavior at boundary."""
        pass

# ===== INTEGRATION TESTS =====
class TestIntegration:
    """Integration tests."""
    pass

# ===== SECURITY TESTS =====
class TestSecurity:
    """Security-related tests."""
    pass
```

### Requirements

1. **Use pytest** with async support
2. **Mock external dependencies** (Firebase, HTTP, etc.)
3. **Cover ALL spec behaviors** (P1-Pn, N1-Nn, E1-En)
4. **Include docstrings** referencing behavior IDs
5. **Target coverage** per spec

### Implementation Requirements

1. **Implement all public functions** from spec
2. **Handle all error cases** from spec
3. **Include type hints** for all functions
4. **Add docstrings** (Google style)
5. **Run tests** and fix until passing

### Success Criteria

- All generated tests pass
- All spec behaviors covered
- No skipped tests

---

## Stage 3: VERIFY (External Review + Fix)

**Duration:** ~10 minutes
**Agents:** Codex (review) → GLM-5 (fix) → MiMo (quality) → Codex (final)

### Purpose

Independent verification and fix cycle until production-ready.

### Sub-stages

#### 3.1 External Review (Codex/GPT-5.4)

**Agent:** External (no skill context, fresh eyes)

**Task:**
1. Read implementation
2. Read tests
3. Check for issues (functional, security, edge cases)
4. Create enhancement plan

**Output:** `ENHANCEMENT_PLAN.md`

```markdown
# Enhancement Plan

## Issues Found

### 1. [Issue Title]
- **Problem**: [description]
- **Fix**: [solution]
- **Priority**: High/Medium/Low

## Test Coverage Gaps
- [Missing test cases]

## Security Issues
- [Security concerns]

## FINAL VERDICT
- [ ] APPROVED
- [ ] NEEDS WORK
```

#### 3.2 Fix Implementation (GLM-5)

**Agent:** GLM-5

**Task:**
1. Read enhancement plan
2. Fix issues identified
3. Run tests
4. Verify fixes

**Success Criteria:**
- All tests passing
- All issues from review addressed

#### 3.3 Code Quality Review (MiMo)

**Agent:** MiMo

**Task:**
1. Review code quality (not functionality)
2. Check style, docs, types
3. Rate 1-10

**Output:** `CODE_REVIEW.md`

```markdown
# Code Quality Review

## Overall Quality: [1-10]

## Issues
- [Style issues]
- [Docstring issues]
- [Type hint issues]

## Verdict
- [ ] APPROVED
- [ ] NEEDS POLISH
```

#### 3.4 Final Review (Codex)

**Agent:** Codex

**Task:**
1. Final verification
2. Confirm production-ready
3. Sign off

**Output:** `FINAL_VERDICT.md`

```markdown
# Final Verdict

## Test Coverage
- Total: X tests
- Passing: X (100%)
- Coverage: X%

## FINAL VERDICT
- [x] APPROVED - Production ready
- [ ] NEEDS WORK
```

---

## Iteration Rules

### When to Iterate

1. **Tests failing:** GLM-5 fixes → Re-verify
2. **External review finds issues:** GLM-5 fixes → MiMo reviews → Codex re-reviews
3. **Code quality issues:** Polish → MiMo re-reviews

### Iteration Limit

- Maximum 3 fix cycles
- After 3 cycles, escalate to human

### Success Gate

```
ALL conditions must be met:
✅ 100% tests passing
✅ External review APPROVED
✅ Code quality 7+/10
✅ Security review passed
```

---

## Agent Assignments

| Role | Agent | Reason |
|------|-------|--------|
| **Spec Definition** | Any | Low-risk, can be done by any capable agent |
| **Test Generation** | GLM-5 + MiMo | Different perspectives, merge best |
| **Implementation** | GLM-5 | Fast, comprehensive |
| **External Review** | Codex/Claude | Fresh eyes, no skill context |
| **Fix Implementation** | GLM-5 | Fast iteration |
| **Code Quality** | MiMo | Thorough, detail-oriented |
| **Final Approval** | Codex/Claude | Independent verification |

---

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: SPEC                                                │
│ Define all behaviors (positive, negative, edge, security)   │
│ Output: SPEC.md (38 behaviors for auth)                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: GENERATE                                            │
│ ┌─────────────────┐  ┌─────────────────┐                    │
│ │ GLM-5: Tests    │  │ MiMo: Tests     │                    │
│ │ (63 tests)      │  │ (~55 tests)     │                    │
│ └────────┬────────┘  └────────┬────────┘                    │
│          │                     │                             │
│          └──────────┬──────────┘                             │
│                     │                                        │
│                     ▼                                        │
│          ┌─────────────────┐                                 │
│          │ GLM-5: Impl     │                                 │
│          │ + Merge tests   │                                 │
│          │ (75 tests)      │                                 │
│          └────────┬────────┘                                 │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3: VERIFY                                              │
│                                                               │
│  ┌─────────────────┐                                         │
│  │ Codex: Review   │ ──→ Enhancement Plan                    │
│  │ (External)      │                                         │
│  └────────┬────────┘                                         │
│           │ Issues found?                                    │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │ GLM-5: Fix      │ ──→ Tests 100% passing                  │
│  └────────┬────────┘                                         │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │ MiMo: Quality   │ ──→ 8/10 rating                         │
│  └────────┬────────┘                                         │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │ Codex: Final    │ ──→ ✅ APPROVED                         │
│  └─────────────────┘                                         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                    │
                    ▼
              Push to GitHub
```

---

## Test Case Categories

### 1. Positive Tests (Happy Path)

Tests that verify expected behavior with valid inputs.

**Example:**
```python
async def test_P1_valid_token():
    """P1: Valid token returns user info."""
    token = create_valid_token()
    result = await verify_token(token)
    assert result["uid"] == "user123"
```

**Write first:** Defines what success looks like.

### 2. Negative Tests (Error Cases)

Tests that verify proper error handling.

**Example:**
```python
async def test_N1_missing_header():
    """N1: Missing Authorization header returns 401."""
    with pytest.raises(HTTPException) as exc:
        await verify_token("")
    assert exc.value.status_code == 401
```

**Write second:** Defines failure boundaries.

### 3. Edge Cases (Boundaries)

Tests at the boundaries of valid/invalid.

**Example:**
```python
async def test_E1_token_at_expiry():
    """E1: Token expiring in 1 second still valid."""
    token = create_token(expires_in=1)
    result = await verify_token(token)
    assert result is not None
```

**Write third:** Catches off-by-one errors.

### 4. Integration Tests

Tests for component interaction.

**Example:**
```python
async def test_fastapi_dependency():
    """Integration: Works as FastAPI dependency."""
    app = FastAPI()
    
    @app.get("/protected")
    async def protected(user = Depends(verify_token)):
        return {"user": user}
    
    # Test the endpoint
```

**Write fourth:** Validates system behavior.

### 5. Security Tests

Tests for security considerations.

**Example:**
```python
async def test_S1_no_token_in_logs():
    """S1: Tokens are masked in logs."""
    token = "secret-token-12345"
    log_output = capture_logs(lambda: verify_token(token))
    assert "secret-token" not in log_output
```

**Write fifth:** Catches security issues.

---

## Metrics

### Per-Module Targets

| Module Size | Tests | Coverage | Time |
|-------------|-------|----------|------|
| Small (<200 LOC) | 30-40 | 90%+ | 15 min |
| Medium (200-500 LOC) | 50-75 | 92%+ | 30 min |
| Large (>500 LOC) | 75-100 | 95%+ | 45 min |

### Quality Gates

| Stage | Gate |
|-------|------|
| Generate | All tests passing |
| External Review | No critical issues |
| Code Quality | 7+/10 rating |
| Final Review | APPROVED |

---

## Lessons Learned

### From Phase 2 (Contracts)

- **141 tests still had bugs** - Tests alone not sufficient
- **External reviewers catch different issues** - Fresh eyes essential
- **Cosmetic fixes problem** - Agent claimed fix but didn't implement
- **Verification required** - Run specific edge case tests before approval

### From Phase 3.1 (Auth)

- **38 behaviors → 75 tests** - More tests than behaviors (good)
- **3 test bugs, 0 implementation bugs** - Tests needed fixes
- **Codex identified root cause** - External review valuable
- **1 fix cycle to 100%** - Efficient

### Key Insight

> **Tests = "We tested what we thought of"**
> **External Review = "We checked what we noticed"**
> **Bugs exist in: "What we didn't think of AND didn't notice"**

This is why both tests AND external review are required.

---

## Anti-Patterns to Avoid

### ❌ Don't

1. **Skip spec stage** - Leads to incomplete coverage
2. **Generate code without tests** - No verification
3. **Self-review only** - Misses issues
4. **Accept "I fixed it" without verification** - Cosmetic fixes
5. **Skip external review** - Fresh eyes catch different issues

### ✅ Do

1. **Define ALL behaviors upfront**
2. **Generate code AND tests together**
3. **Use external reviewers (no skill context)**
4. **Verify fixes actually work**
5. **Iterate until 100% tests passing**

---

## File Structure

```
/tmp/{module}/
├── SPEC.md                    # Stage 1 output
├── backend/
│   └── shared/
│       └── {module}.py        # Implementation
├── tests/
│   └── test_{module}.py       # Tests
├── ENHANCEMENT_PLAN.md        # Stage 3.1 output
├── CODE_REVIEW.md             # Stage 3.3 output
└── FINAL_VERDICT.md           # Stage 3.4 output
```

---

## Checklist

### Before Starting

- [ ] Requirements understood
- [ ] Design documents read
- [ ] Dependencies identified

### Stage 1 Complete

- [ ] All positive behaviors listed
- [ ] All negative behaviors listed
- [ ] All edge cases listed
- [ ] Integration points identified
- [ ] Security considerations documented
- [ ] Test targets defined

### Stage 2 Complete

- [ ] Implementation created
- [ ] Tests created
- [ ] All tests passing
- [ ] All spec behaviors covered

### Stage 3 Complete

- [ ] External review done
- [ ] Issues fixed
- [ ] Code quality reviewed
- [ ] Final approval received
- [ ] 100% tests passing

### Ready for Production

- [ ] All quality gates passed
- [ ] Documentation complete
- [ ] Pushed to GitHub

---

## References

- **Phase 2.4 Contracts:** 141 tests, 6 fix cycles
- **Phase 3.1 Auth:** 75 tests, 1 fix cycle
- **Design Document:** `docs/design/UNIFIED-DESIGN.md`
- **Agent Preferences:** `AGENTS.md`

---

*Last updated: 2026-03-21*
*Author: cclow*
*Status: Validated in production*
