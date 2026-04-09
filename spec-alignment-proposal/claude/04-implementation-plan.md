# Implementation Plan: Spec Alignment Checker

## Overview

**Total Estimated Time**: 6 weeks (240 hours)
**Team Size**: 1-2 developers
**Approach**: Iterative delivery with working MVP at week 3

---

## Phase 1: Foundation (Week 1-2)

**Goal**: Core parsing and comparison infrastructure

### Week 1: Schema Model + OpenAPI Parser

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | Project setup, dependencies | 4 | pyproject.toml, basic structure |
| 1-2 | Design and implement canonical schema model | 12 | `schema.py` with all dataclasses |
| 2-3 | Implement OpenAPI parser | 16 | `parsers/openapi.py` |
| 4 | Write tests for OpenAPI parser | 8 | `tests/test_parsers/test_openapi.py` |
| 5 | Integration: parse sample OpenAPI specs | 4 | Working parser |

**Dependencies**:
- openapi-spec-validator>=0.6.0
- pyyaml>=6.0
- pytest>=7.0

**Milestone**: Can parse OpenAPI spec into canonical model

### Week 2: Pydantic Parser + Code Parser

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1-2 | Implement Pydantic parser (AST-based) | 16 | `parsers/pydantic.py` |
| 3 | Write tests for Pydantic parser | 8 | `tests/test_parsers/test_pydantic.py` |
| 4 | Implement basic code parser (type hints) | 8 | `parsers/code.py` |
| 5 | Integration: parse sample Python code | 8 | Working parsers |

**Dependencies**:
- pydantic>=2.0
- ast (stdlib)

**Milestone**: Can parse OpenAPI + Pydantic + code into canonical models

---

## Phase 2: Core Logic (Week 3)

**Goal**: Comparison engine and contradiction detection

### Week 3: Comparison Engine

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | Design comparison algorithm | 4 | Design doc |
| 1-2 | Implement model comparison | 12 | `comparison/engine.py` |
| 3 | Implement endpoint comparison | 8 | Enhanced engine |
| 3-4 | Implement contradiction classification | 8 | Severity system |
| 4-5 | Write comprehensive tests | 12 | `tests/test_comparison/` |

**Milestone**: MVP - Can detect contradictions between sources

**End of Week 3 Checkpoint**:
```bash
# This should work:
spec-check openapi.yaml models/ src/
# Output: List of contradictions
```

---

## Phase 3: Reporting (Week 4)

**Goal**: Human and machine-readable reports

### Week 4: Report Generation

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | Implement human-readable reporter | 8 | `reporting/human.py` |
| 2 | Implement JSON reporter | 4 | `reporting/json_report.py` |
| 2-3 | Implement SARIF reporter (for GitHub) | 8 | `reporting/sarif.py` |
| 4 | Add suggestion generation | 8 | Actionable fixes |
| 5 | Integration testing | 12 | End-to-end tests |

**Milestone**: Rich reporting with actionable suggestions

---

## Phase 4: CLI & UX (Week 5)

**Goal**: Production-ready CLI tool

### Week 5: Command Line Interface

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | Implement CLI with typer | 8 | `cli.py` with basic commands |
| 2 | Add --output, --format flags | 4 | JSON/YAML/text output |
| 2-3 | Add --fail-on, --severity filters | 8 | Configurable thresholds |
| 3-4 | Add --watch mode | 12 | Continuous checking |
| 4-5 | Add --config file support | 8 | `.spec-check.yaml` |
| 5 | Polish error messages | 4 | User-friendly errors |

**Dependencies**:
- typer>=0.9.0
- rich>=13.0
- watchfiles>=0.20 (for --watch)

**Milestone**: Full-featured CLI tool

**End of Week 5 Checkpoint**:
```bash
# All these should work:
spec-check openapi.yaml models/ src/
spec-check openapi.yaml models/ src/ --output json > report.json
spec-check openapi.yaml models/ src/ --fail-on critical
spec-check openapi.yaml models/ src/ --watch
```

---

## Phase 5: CI Integration & Polish (Week 6)

**Goal**: Production-ready, CI-friendly tool

### Week 6: Integration & Documentation

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | Create GitHub Action | 8 | `action.yml` |
| 1-2 | Create pre-commit hook example | 4 | `.pre-commit-config.yaml` |
| 2-3 | Write comprehensive README | 8 | Usage docs, examples |
| 3-4 | Create examples/ with sample projects | 8 | Working examples |
| 4-5 | Performance optimization | 8 | Meet targets (<5s runtime) |
| 5 | Bug fixes and edge cases | 8 | Robust handling |

**Milestone**: Release-ready v1.0

---

## Detailed Task Breakdown

### Phase 1 Tasks (32 hours)

#### Project Setup
```bash
# Tasks:
mkdir spec-alignment-checker
cd spec-alignment-checker
poetry init --name spec-alignment-checker --python "^3.10"
poetry add openapi-spec-validator pyyaml typer rich
poetry add --group dev pytest pytest-cov mypy ruff

# Create structure:
mkdir -p spec_alignment_checker/{parsers,comparison,reporting}
mkdir -p tests/{test_parsers,test_comparison,test_reporting}
mkdir examples
```

#### Canonical Schema Model
```python
# Deliverable: spec_alignment_checker/schema.py
# Must include:
# - FieldType enum
# - FieldSchema dataclass
# - EndpointSchema dataclass
# - SchemaModel dataclass
# - merge() method
# - matches() method for comparison
```

#### OpenAPI Parser
```python
# Deliverable: spec_alignment_checker/parsers/openapi.py
# Must handle:
# - OpenAPI 3.0.x and 3.1.x
# - YAML and JSON formats
# - $ref resolution
# - components/schemas
# - paths (endpoints)
# - request bodies
# - responses
# - parameters
# - Nested objects and arrays
```

### Phase 2 Tasks (48 hours)

#### Pydantic Parser
```python
# Deliverable: spec_alignment_checker/parsers/pydantic.py
# Must handle:
# - Pydantic v2 BaseModel classes
# - Field annotations (str, int, Optional[str], List[int], etc.)
# - Default values
# - Field() with constraints
# - Nested models
# - Enums
# - Validators (for detecting custom constraints)
```

#### Code Parser
```python
# Deliverable: spec_alignment_checker/parsers/code.py
# Must handle:
# - Function type hints
# - Route decorators (FastAPI, Flask)
# - Return type annotations
# - Docstring extraction (optional)
# - Generic dict/list annotations
```

### Phase 3 Tasks (40 hours)

#### Comparison Engine
```python
# Deliverable: spec_alignment_checker/comparison/engine.py
# Must detect:
# - Type mismatches
# - Required/optional mismatches
# - Enum value differences
# - Format mismatches (uuid, date-time, etc.)
# - Missing fields in one source
# - Extra fields not in spec
# - Endpoint path mismatches
# - HTTP method mismatches
```

#### Contradiction Classification
```python
# Must classify by:
# - Type (TYPE_MISMATCH, REQUIRED_MISMATCH, etc.)
# - Severity (CRITICAL, HIGH, MEDIUM, LOW)
# - Provide actionable suggestions
```

### Phase 4 Tasks (40 hours)

#### Reporters
```python
# Human reporter: Clear, colored terminal output
# JSON reporter: Machine-readable for CI
# SARIF reporter: GitHub Advanced Security format
```

#### Suggestion Engine
```python
# Must provide:
# - Specific fix location (file:line)
# - Concrete code suggestion
# - Explanation of the issue
```

### Phase 5 Tasks (40 hours)

#### CLI Features
```python
# Commands:
spec-check <openapi> <models> <code>  # Basic check
spec-check --output json              # JSON output
spec-check --format yaml              # YAML output
spec-check --fail-on critical         # Exit code 1 on critical
spec-check --severity high            # Only show high+
spec-check --watch                    # Continuous mode
spec-check --config .spec-check.yaml  # Config file
spec-check --init                     # Generate config

# Global options:
--verbose                             # Detailed output
--quiet                               # Minimal output
--version                             # Show version
--help                                # Show help
```

#### Configuration File
```yaml
# .spec-check.yaml
openapi: openapi.yaml
models:
  - models/
code:
  - src/
  - handlers/
output: json
fail_on: critical
ignore:
  - models/legacy.py  # Skip known issues
severity_overrides:
  - field: "JobRequest.priority"
    severity: low  # Downgrade known minor issues
```

---

## Dependencies

### Runtime Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.10"
openapi-spec-validator = "^0.6.0"
pyyaml = "^6.0"
typer = "^0.9.0"
rich = "^13.0"
pydantic = "^2.0"
```

### Development Dependencies
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"
mypy = "^1.0"
ruff = "^0.1.0"
black = "^23.0"
```

### Optional Dependencies
```toml
[tool.poetry.extras]
watch = ["watchfiles"]
sarif = ["sarif-om"]
```

---

## Milestones

### Milestone 1: MVP (End of Week 3)
- [ ] Parse OpenAPI specs
- [ ] Parse Pydantic models
- [ ] Parse basic code
- [ ] Detect type mismatches
- [ ] Detect required field mismatches
- [ ] Basic text output

### Milestone 2: Alpha (End of Week 4)
- [ ] All comparison rules
- [ ] Severity classification
- [ ] Human-readable reports
- [ ] JSON output
- [ ] SARIF output

### Milestone 3: Beta (End of Week 5)
- [ ] Full CLI
- [ ] --watch mode
- [ ] Config file support
- [ ] Error handling
- [ ] Performance targets met

### Milestone 4: Release (End of Week 6)
- [ ] GitHub Action
- [ ] Pre-commit hook
- [ ] Documentation
- [ ] Examples
- [ ] Published to PyPI

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Complex $ref resolution in OpenAPI | Medium | High | Use mature library (openapi-spec-validator) |
| Pydantic v2 breaking changes | Low | Medium | Pin to v2, test thoroughly |
| Performance issues on large codebases | Medium | Medium | Implement caching, incremental mode |
| False positives erode trust | High | Critical | Conservative defaults, allow overrides |
| Edge cases in type mapping | Medium | Medium | Extensive testing with real projects |

---

## Testing Strategy

### Unit Tests
- Each parser independently testable
- Comparison engine with fixture data
- Report generation with known contradictions

### Integration Tests
- Parse real OpenAPI specs (Pet Store, GitHub API)
- Parse real FastAPI/Pydantic codebases
- End-to-end: spec → parse → compare → report

### Performance Tests
- Benchmark against vtic-sized codebase (100+ files)
- Target: <5s total runtime
- Memory profiling

### Regression Tests
- Golden file testing for reports
- CI runs against known-good projects

---

## Success Criteria for Each Phase

### Phase 1 Success
```bash
python -c "
from spec_alignment_checker.parsers.openapi import OpenAPIParser
from spec_alignment_checker.parsers.pydantic import PydanticParser

# Parse OpenAPI
oas = OpenAPIParser('examples/petstore.yaml').parse()
assert len(oas.models) > 0

# Parse Pydantic
pyd = PydanticParser(['examples/models/']).parse()
assert len(pyd.models) > 0
"
```

### Phase 3 Success
```bash
spec-check examples/openapi.yaml examples/models/ examples/src/
# Should output contradictions found
```

### Phase 5 Success
```bash
# CI mode
spec-check openapi.yaml models/ src/ --fail-on critical
echo $?  # Should be 0 if no critical issues, 1 if found

# Watch mode
spec-check openapi.yaml models/ src/ --watch &
# Change a file, should auto-recheck
```

---

## Post-v1.0 Roadmap

### v1.1: Enhanced Features
- Auto-fix suggestions (with --dry-run)
- TypeScript support
- JSON Schema support

### v1.2: Integrations
- VS Code extension
- PyCharm plugin
- GitLab CI template

### v2.0: Advanced Features
- GraphQL schema support
- Database schema alignment
- Semantic analysis (business logic checks)
