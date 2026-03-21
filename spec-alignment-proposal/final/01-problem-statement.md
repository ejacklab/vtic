# Problem Statement: Spec Alignment Crisis

## The Hidden Killer of Multi-Agent Development

When multiple AI agents collaborate on a codebase, they operate independently. Each agent reads specs, interprets requirements, and writes code in isolation. This creates a silent catastrophe: **specification drift**.

---

## The vtic Incident: A Case Study

### Background

During development of **vtic** (AI-first ticketing system), we had multiple agents working in parallel:

| Agent | Task | Output |
|-------|------|--------|
| A | OpenAPI specifications | `openapi.yaml` |
| B | Pydantic models | `src/models/*.py` |
| C | API handlers | `src/api/routes/*.py` |
| D | Integration tests | `tests/*.py` |
| E | Documentation | `docs/*.md` |
| F | Client SDKs | Generated from OpenAPI |

Each agent was competent. Each produced reasonable output. **But nobody was checking for alignment.**

---

## The 58 Contradictions

After weeks of independent work, we discovered **58 contradictions** across 6+ documents:

```
Document Analysis Summary:
├── openapi.yaml          (v1.2.0)
├── models/pydantic/      (v1.1.0 - unofficial)
├── docs/api-design.md    (v2.0.0 - draft)
├── docs/data-model.md    (v1.3.0)
├── src/schemas/          (mixed versions)
└── tests/fixtures/       (outdated)

Total Contradictions Found: 58
├── Type mismatches:        23  (40%)
├── Required field conflicts: 15  (26%)
├── Enum value drift:       11  (19%)
├── Naming inconsistencies:  6  (10%)
└── Default value conflicts: 3   (5%)
```

---

## Contradiction Breakdown

### Type Mismatches (23 instances)

**Example 1: Ticket ID format**

| Source | Type | Format |
|--------|------|--------|
| OpenAPI | `string` | Pattern: `^[CFGHST]\d+$` |
| Pydantic | `str` | No validation |
| TypeScript | `string \| number` | Accepts both |

**Impact:** TypeScript clients could pass `123` (number), breaking API validation.

**Example 2: Timestamp fields**

| Source | Field | Type |
|--------|-------|------|
| OpenAPI | `created` | `string` (date-time) |
| Pydantic | `created` | `datetime` |
| Code | `created` | `int` (Unix timestamp) |

**Impact:** API returns ISO string, code expects Unix int → runtime error.

---

### Required Field Conflicts (15 instances)

**Example: `TicketUpdate` schema**

| Source | Required Fields |
|--------|-----------------|
| OpenAPI | None (all optional) |
| Pydantic | At least one field required |
| Tests | Requires `title` and `status` |

**Impact:** API accepts empty PATCH, but tests fail on valid requests.

---

### Enum Value Drift (11 instances)

**Example: `Severity` enum**

| Source | Values | Count |
|--------|--------|-------|
| OpenAPI | `[low, medium, high, critical]` | 4 |
| Pydantic | `[low, medium, high]` | 3 |
| TypeScript | `[low, med, high, critical]` | 4 (typo: "med") |
| Database | `[1, 2, 3, 4]` | Mapped differently |

**Impact:** 
- OpenAPI accepts "critical"
- Pydantic rejects it
- TypeScript sends "med" (typo)
- Database stores as number

---

## The Impact

### Wasted Time

| Phase | Time Lost | Why |
|-------|-----------|-----|
| Debug mysterious failures | 3.5 hours | "API returns X but code expects Y" |
| Find the contradiction | 30 min | Manual diff between specs |
| Understand the impact | 15 min | Which systems affected? |
| Fix the code/spec | 30 min | Update one source |
| Update tests | 30 min | Tests assumed wrong format |
| Review and verify | 30 min | Manual check |
| **Total per contradiction** | **~6 hours** | |
| **Total for 58 contradictions** | **~350 hours** | 44 person-days |

### Quality Impact

| Metric | Before | After Fixes |
|--------|--------|-------------|
| Test pass rate | 78% | 95% |
| Production bugs (spec-related) | 12 | 2 |
| Developer trust in specs | Low | Medium |
| Onboarding time | 2 weeks | 1 week |

---

## Why Manual Review Fails

### Problem 1: Scale

```
vtic codebase:
├── 1 OpenAPI spec (3,000 lines)
├── 15 Pydantic models (500 lines each)
├── 30 API endpoints
├── 100+ field definitions
└── 5 developers changing things independently

Manual cross-check: Impossible to do thoroughly
```

### Problem 2: Timing

```
Timeline:
Week 1: Agent A writes OpenAPI
Week 2: Agent B writes Pydantic (based on Week 1 OpenAPI)
Week 3: Agent A updates OpenAPI (Agent B not notified)
Week 4: Integration testing → contradictions discovered

Problem: Drift happens BETWEEN spec creation and integration
```

### Problem 3: Human Factors

- **Assumption of correctness**: "The spec must be right"
- **Confirmation bias**: "I tested it, so it works"
- **Context switching**: Forgetting what the spec said
- **Fatigue**: 58 contradictions = manual review fatigue

---

## The Real Cost

For a team of 5 developers working on vtic for 6 months:

| Cost Category | Calculation | Total |
|---------------|-------------|-------|
| Debug time | 58 contradictions × 6 hours × $50/hr | $17,400 |
| Rework | 30% of features rebuilt | $15,000 |
| Delayed delivery | 3 weeks × 5 devs × $40/hr | $24,000 |
| Production incidents | 12 bugs × 2 hours × $75/hr | $1,800 |
| **Total** | | **$58,200** |

**ROI of automated checking**: Prevent 90% of contradictions = save **$52,380** per project.

---

## The Missing Tool

What we needed:

1. **Automatic detection** of contradictions as they happen
2. **Clear reporting** with specific file:line locations
3. **CI integration** to block merges with contradictions
4. **Actionable fixes** not just error messages

This is the `spec-alignment-checker`.
