# Implementation Plan: Spec Alignment Checker

## Overview

**Total Time**: 6 weeks (240 hours)  
**Team**: 1-2 developers  
**Approach**: Iterative delivery with working MVP at week 3

---

## Timeline Overview

```
Week 1-2: Foundation (Parsing)
Week 3:   Core Logic (Comparison Engine)
Week 4:   Reporting (Human + Machine)
Week 5:   CLI & UX
Week 6:   CI Integration & Release

MVP Checkpoint: End of Week 3
Release Candidate: End of Week 5
v1.0 Release: End of Week 6
```

---

## Phase 1: Foundation (Week 1-2)

### Week 1: Schema Model + OpenAPI Parser

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | Project setup, dependencies | 4 | `pyproject.toml`, structure |
| 1-2 | Design canonical schema model | 12 | `schema.py` with dataclasses |
| 2-3 | Implement OpenAPI parser | 16 | `parsers/openapi.py` |
| 4 | Write tests for OpenAPI parser | 8 | `tests/test_parsers/` |
| 5 | Integration: parse sample specs | 4 | Working parser |

**Dependencies**:
```toml
openapi-spec-validator = "^0.6.0"
pyyaml = "^6.0"
pytest = "^7.0"
```

**Milestone**: Can parse OpenAPI spec into canonical model

### Week 2: Pydantic + TypeScript Parsers

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1-2 | Pydantic parser (AST-based) | 16 | `parsers/pydantic.py` |
| 3 | Pydantic parser tests | 8 | `tests/test_parsers/` |
| 4 | TypeScript parser | 8 | `parsers/typescript.py` |
| 5 | Integration tests | 8 | E2E parsing |

**Dependencies**:
```toml
pydantic = "^2.0"
# TypeScript parser via subprocess to tsc
```

**Milestone**: Multi-format parsing complete

---

## Phase 2: Core Logic (Week 3)

### Week 3: Comparison Engine

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | Design comparison algorithm | 4 | Design doc |
| 1-2 | Model comparison | 12 | `comparison/engine.py` |
| 3 | Field comparison | 8 | Type/required/enum checks |
| 3-4 | Contradiction classification | 8 | Severity system |
| 4-5 | Comprehensive tests | 12 | `tests/test_comparison/` |

**Milestone**: MVP - Detects contradictions between sources

**End of Week 3 Checkpoint**:
```bash
# This should work:
spec-align check openapi.yaml models/ src/
# Output: List of contradictions with severity
```

---

## Phase 3: Reporting (Week 4)

### Week 4: Report Generators

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | Human-readable reporter | 8 | `reporting/console.py` |
| 2 | JSON reporter | 4 | `reporting/json_report.py` |
| 2-3 | SARIF reporter (GitHub) | 8 | `reporting/sarif.py` |
| 4 | Suggestion generation | 8 | Actionable fixes |
| 5 | Integration testing | 12 | E2E tests |

**Milestone**: Rich reporting with actionable suggestions

---

## Phase 4: CLI & UX (Week 5)

### Week 5: Command Line Interface

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | CLI with typer | 8 | `cli.py` with commands |
| 2 | Output format flags | 4 | `--format json/yaml/text` |
| 2-3 | Severity filters | 8 | `--fail-on critical` |
| 3-4 | Watch mode | 12 | `--watch` continuous |
| 4-5 | Config file support | 8 | `.spec-align.yaml` |
| 5 | Error messages | 4 | User-friendly errors |

**Dependencies**:
```toml
typer = "^0.9.0"
rich = "^13.0"
watchfiles = "^0.20"
```

**Milestone**: Full-featured CLI tool

**End of Week 5 Checkpoint**:
```bash
# All these should work:
spec-align check openapi.yaml models/ src/
spec-align check openapi.yaml models/ --output json
spec-align check openapi.yaml models/ --fail-on critical
spec-align check openapi.yaml models/ --watch
spec-align init  # Generate config
```

---

## Phase 5: Integration & Polish (Week 6)

### Week 6: CI Integration & Documentation

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | GitHub Action | 8 | `action.yml` |
| 1-2 | Pre-commit hook | 4 | `.pre-commit-config.yaml` |
| 2-3 | README + docs | 8 | Usage examples |
| 3-4 | Example projects | 8 | `examples/` directory |
| 4-5 | Performance optimization | 8 | Meet <5s target |
| 5 | Bug fixes & edge cases | 8 | Robust handling |

**Milestone**: Release-ready v1.0

---

## Detailed Task Breakdown

### Phase 1 Tasks

#### Project Setup
```bash
mkdir spec-alignment-checker && cd spec-alignment-checker
poetry init --name spec-alignment-checker --python "^3.10"
poetry add openapi-spec-validator pyyaml typer rich pydantic
poetry add --group dev pytest pytest-cov mypy ruff black

# Structure
mkdir -p spec_align/{parsers,comparison,reporting,utils}
mkdir -p tests/{test_parsers,test_comparison,test_reporting}
mkdir examples
```

#### Canonical Schema Model
```python
# Must deliver: spec_align/schema.py
# - FieldType enum
# - TypeRef dataclass
# - FieldSpec dataclass
# - EndpointSpec dataclass
# - SchemaModel dataclass
# - SourceLocation dataclass
# - matches() method for comparison
```

#### Parsers
```python
# Must deliver:
# - spec_align/parsers/openapi.py
#   - Handle OpenAPI 3.0.x and 3.1.x
#   - YAML and JSON formats
#   - $ref resolution
#   - components/schemas
#   - paths (endpoints)
#
# - spec_align/parsers/pydantic.py
#   - Pydantic v2 BaseModel classes
#   - Field annotations
#   - Default values
#   - Nested models
#   - Enums
```

### Phase 2 Tasks

#### Comparison Engine
```python
# Must deliver: spec_align/comparison/engine.py
# - Compare models
# - Compare fields
# - Type mismatch detection
# - Required/optional detection
# - Enum drift detection
# - Severity classification
```

### Phase 3 Tasks

#### Reporters
```python
# Must deliver:
# - reporting/console.py - Human-readable with colors
# - reporting/json_report.py - Machine-readable
# - reporting/sarif.py - GitHub Advanced Security
# - Suggestion engine - Actionable fixes
```

### Phase 4 Tasks

#### CLI Commands
```python
# spec-align check <openapi> <models> [code]
# spec-align check --output json
# spec-align check --fail-on critical,high
# spec-align check --watch
# spec-align init
# spec-align --version
```

#### Configuration
```yaml
# .spec-align.yaml
openapi: openapi.yaml
models:
  - src/models/
code:
  - src/
output: console
fail_on: critical
ignore:
  - src/models/legacy.py
```

---

## Milestones

### Milestone 1: MVP (Week 3)
- [ ] Parse OpenAPI specs
- [ ] Parse Pydantic models
- [ ] Detect type mismatches
- [ ] Detect required field mismatches
- [ ] Basic text output

### Milestone 2: Alpha (Week 4)
- [ ] All comparison rules
- [ ] Severity classification
- [ ] Human-readable reports
- [ ] JSON output
- [ ] SARIF output

### Milestone 3: Beta (Week 5)
- [ ] Full CLI
- [ ] Watch mode
- [ ] Config file support
- [ ] Performance targets met

### Milestone 4: Release (Week 6)
- [ ] GitHub Action
- [ ] Pre-commit hook
- [ ] Documentation
- [ ] PyPI package

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Complex $ref resolution | Medium | High | Use mature library |
| Pydantic v2 changes | Low | Medium | Pin version, test |
| Performance issues | Medium | Medium | Caching, parallel |
| False positives | High | Critical | Conservative defaults |
| Type mapping edge cases | Medium | Medium | Extensive testing |

---

## Testing Strategy

### Unit Tests
- Each parser independently testable
- Comparison engine with fixtures
- Report generation with known contradictions

### Integration Tests
- Parse real OpenAPI specs (Pet Store, GitHub API)
- Parse real FastAPI/Pydantic codebases
- End-to-end: spec → parse → compare → report

### Performance Tests
- Benchmark against vtic-sized codebase (100+ files)
- Target: <5s total runtime
- Memory profiling

---

## Success Criteria

### Phase 1 Success
```bash
python -c "
from spec_align.parsers.openapi import OpenAPIParser
from spec_align.parsers.pydantic import PydanticParser

oas = OpenAPIParser('examples/petstore.yaml').parse()
assert len(oas.models) > 0

pyd = PydanticParser(['examples/models/']).parse()
assert len(pyd.models) > 0
"
```

### Phase 3 Success
```bash
spec-align check examples/openapi.yaml examples/models/
# Should output contradictions with severity
```

### Phase 5 Success
```bash
# CI mode
spec-align check openapi.yaml models/ --fail-on critical
echo $?  # 0 = no critical, 1 = found

# Watch mode
spec-align check openapi.yaml models/ --watch &
# Change file → auto-recheck
```

---

## Post-v1.0 Roadmap

### v1.1 (Week 7-8)
- Auto-fix with --dry-run
- TypeScript support (full)
- JSON Schema support

### v1.2 (Week 9-10)
- VS Code extension
- PyCharm plugin
- GitLab CI template

### v2.0 (Future)
- GraphQL schema support
- Database schema alignment
- Semantic analysis
