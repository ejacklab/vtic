---
name: design-doc-reconciliation
description: "Workflow for generating, reviewing, and reconciling design documents across multiple agents. Use when: (1) starting a new project with multiple design docs (OpenAPI, data models, data flows), (2) multiple agents need to produce design artifacts, (3) checking design docs for contradictions. NOT for: implementation (that's multi-agent-orchestration)."
---

# Design Doc Reconciliation

## The Problem

When multiple agents write design docs independently, contradictions accumulate:
- vtic Wave 1: **58 contradictions** across 6+ independently-written docs
- Enums defined differently in OpenAPI vs data models
- Field types mismatched between specs

## The Solution: Canonical Source First

**Before any parallel generation, define the canonical source.**

1. **Choose canonical** — Usually OpenAPI spec (API-first) or data models
2. **Write canonical first** — One agent, one doc, reviewed
3. **Generate rest** — Parallel agents produce supporting docs
4. **Cross-review** — Separate agents check alignment to canonical
5. **Reconcile** — Fix contradictions BEFORE coding starts

## Workflow

### Phase 1: Canonical Source (Sequential)
```
1. One agent writes the OpenAPI spec (or chosen canonical)
2. One agent reviews it
3. Commit as canonical
```

### Phase 2: Parallel Generation
```
1. Spawn 3-4 agents, each producing one doc:
   - Data models (align to OpenAPI)
   - Data flows (align to OpenAPI + data models)
   - Breakdown (align to all above)
   - Config schema (align to all above)
2. Each agent READS the canonical before writing
```

### Phase 3: Cross-Review
```
1. Spawn 2-3 review agents (GLM-5)
2. Each reviewer checks one doc against canonical
3. Output: numbered list of contradictions
```

### Phase 4: Reconcile
```
1. One agent reads all review reports
2. Fixes contradictions by aligning to canonical
3. The canonical doc is NEVER changed to match others
```

### Phase 5: Lock
```
1. Final review confirms zero contradictions
2. Commit all design docs
3. Design docs are now LOCKED — no changes without re-review
```

## Reconciliation Rules

- **Canonical is king** — All other docs align to it, never the reverse
- **One field = one definition** — Same field must have same name, type, and constraints everywhere
- **Zero tolerance for contradictions** — Even minor mismatches cause bugs downstream
- **Review agents must READ the canonical** — Don't trust that generation agents got it right

## What Gets Reconciled

| Doc | Aligns To | Common Issues |
|-----|-----------|---------------|
| OpenAPI spec | Self (canonical) | — |
| Data models | OpenAPI | Field names, types, required/optional |
| Data flows | OpenAPI + data models | Endpoint paths, request/response shapes |
| Breakdown | All above | Module paths, function signatures |
| Config schema | All above | Key names, defaults, types |

## Lesson: Cost of Skipping Reconciliation

- vtic Wave 1 without reconciliation: 58 contradictions → 3 days of fix cycles
- vtic Wave 1 with reconciliation: Zero contradictions → clean implementation
- **Time saved by reconciling: >10x the time spent reconciling**
