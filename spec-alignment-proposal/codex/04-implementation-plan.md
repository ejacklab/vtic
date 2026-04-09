# Implementation Plan: spec-alignment-checker

## Overview

Total estimated time: **4-6 weeks** for MVP with core functionality.

## Phase 1: Foundation (Week 1-2)

### Goals
- Set up project structure
- Implement canonical schema representation
- Build OpenAPI parser
- Build basic comparison engine
- Create console reporter

### Tasks

#### 1.1 Project Setup (Day 1-2)

```bash
# Create project structure
mkdir -p spec-alignment-checker/{spec_align,tests}
cd spec-alignment-checker

# Initialize with poetry
poetry init --name spec-align
poetry add click rich pyyaml pydantic

# Development dependencies
poetry add --group dev pytest pytest-cov black ruff mypy
```

**Deliverable**: Working project skeleton with CI (GitHub Actions).

#### 1.2 Canonical Schema (Day 2-3)

Implement the canonical representation:

```python
# spec_align/normalize/canonical.py
# See architecture doc for full implementation
```

**Dependencies**: None
**Deliverable**: `canonical.py` with full type definitions and serialization.

#### 1.3 OpenAPI Parser (Day 3-5)

```python
# spec_align/normalize/openapi_parser.py
class OpenAPIParser:
    def parse(self, file_path: Path) -> List[SchemaSpec]:
        # Parse OpenAPI 3.0/3.1 YAML/JSON
        # Convert to canonical SchemaSpec
        pass
```

**Dependencies**: 1.2
**Testing**: Use vtic's openapi.yaml as test fixture

```python
# tests/test_openapi_parser.py
def test_parse_vtic_openapi():
    parser = OpenAPIParser()
    schemas = parser.parse(Path("tests/fixtures/vtic_openapi.yaml"))
    
    # Verify we got the TranscriptRequest schema
    transcript = next(s for s in schemas if s.name == "TranscriptRequest")
    assert "audio_format" in transcript.fields
    assert transcript.fields["audio_format"].type_ref.enum_values == ["wav", "mp3", "flac"]
```

**Deliverable**: Parser that handles 90% of common OpenAPI patterns.

#### 1.4 Basic Comparison Engine (Day 5-7)

```python
# spec_align/compare/engine.py
class ComparisonEngine:
    def compare(self, schemas: List[Tuple[str, SchemaSpec]]) -> List[Contradiction]:
        # Compare schemas by name
        # Detect type mismatches, required conflicts
        pass
```

**Dependencies**: 1.2
**Deliverable**: Engine that detects type and required contradictions.

#### 1.5 Console Reporter (Day 7-8)

```python
# spec_align/report/console.py
# Rich-based console output
```

**Dependencies**: 1.4
**Deliverable**: Human-readable output like shown in solution doc.

#### 1.6 CLI MVP (Day 8-10)

```python
# spec_align/cli.py
@cli.command()
def check(openapi, output_format):
    # Wire everything together
    pass
```

**Deliverable**: Working CLI that can check OpenAPI files against each other.

### Phase 1 Milestone

```bash
# This should work end-to-end
$ spec-align check openapi.yaml openapi-v2.yaml

CONTRADICTIONS FOUND: 2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ TYPE MISMATCH: TranscriptRequest.audio_format
   ...
```

**Estimate**: 10 days

---

## Phase 2: Pydantic Integration (Week 3)

### Goals
- Parse Pydantic v1 and v2 models
- Compare OpenAPI ↔ Pydantic
- Add enum drift detection

### Tasks

#### 2.1 Pydantic Parser (Day 1-4)

```python
# spec_align/normalize/pydantic_parser.py
class PydanticParser:
    def parse(self, file_path: Path) -> List[SchemaSpec]:
        # Use AST to parse Pydantic models
        # Handle v1 and v2 syntax
        pass
```

**Challenges**:
- Handling `Field()` with complex defaults
- Resolving forward references
- Handling `Optional`, `Union`, `Literal` types
- Enum class lookups

**Testing**: Use vtic's Pydantic models

```python
def test_parse_vtic_pydantic():
    parser = PydanticParser()
    schemas = parser.parse(Path("vtic/src/models/request.py"))
    
    transcript = next(s for s in schemas if s.name == "TranscriptRequest")
    # AudioFormat enum should have 5 values
    assert len(transcript.fields["audio_format"].type_ref.enum_values) == 5
```

**Deliverable**: Parser that handles 80% of common Pydantic patterns.

#### 2.2 OpenAPI ↔ Pydantic Comparison (Day 4-5)

Already handled by comparison engine, but add specific tests:

```python
def test_detect_enum_drift():
    openapi_schemas = openapi_parser.parse("openapi.yaml")
    pydantic_schemas = pydantic_parser.parse("models/")
    
    engine = ComparisonEngine()
    contradictions = engine.compare([
        ("openapi", openapi_schemas[0]),
        ("pydantic", pydantic_schemas[0])
    ])
    
    # Should detect the audio_format enum drift
    enum_drifts = [c for c in contradictions if c.type == ContradictionType.ENUM_DRIFT]
    assert len(enum_drifts) > 0
```

**Deliverable**: Full contradiction detection between OpenAPI and Pydantic.

#### 2.3 Fix Suggestions (Day 5-7)

```python
# spec_align/fix/suggester.py
class FixSuggester:
    def suggest(self, contradiction: Contradiction) -> List[FixSuggestion]:
        # Generate code fixes
        pass
```

Example output:

```bash
$ spec-align explain enum-drift-001

Suggested fix (update OpenAPI):
  
  File: openapi.yaml:45
  
  - enum: [wav, mp3, flac]
  + enum: [wav, mp3, flac, ogg, webm]

Auto-fix: spec-align fix enum-drift-001 --strategy=openapi
```

**Deliverable**: Actionable fix suggestions for common contradictions.

### Phase 2 Milestone

```bash
# This should work end-to-end
$ spec-align check --openapi openapi.yaml --pydantic src/models/

CONTRADICTIONS FOUND: 23

Type mismatches: 5
Required conflicts: 8
Enum drift: 10
```

**Estimate**: 7 days

---

## Phase 3: TypeScript Support (Week 4)

### Goals
- Parse TypeScript interfaces/types
- Compare OpenAPI ↔ TypeScript
- Handle naming convention differences

### Tasks

#### 3.1 TypeScript Parser (Day 1-4)

Use tree-sitter for parsing:

```python
# spec_align/normalize/typescript_parser.py
import tree_sitter_typescript as tstype

class TypeScriptParser:
    def parse(self, file_path: Path) -> List[SchemaSpec]:
        # Parse TypeScript interfaces and types
        # Convert to canonical SchemaSpec
        pass
```

**Challenges**:
- Handling complex TypeScript types (generics, unions, intersections)
- camelCase vs snake_case naming
- Optional properties (`name?: string`)

**Deliverable**: Parser that handles 70% of common TypeScript patterns.

#### 3.2 Naming Convention Handling (Day 4-5)

```python
# spec_align/compare/naming.py
class NamingNormalizer:
    def normalize(self, name: str, convention: str) -> str:
        # snake_case ↔ camelCase conversion
        pass
```

Config option:

```yaml
# spec-align.yaml
naming:
  openapi: snake_case
  typescript: camelCase
  auto_convert: true
```

**Deliverable**: Automatic naming convention handling.

#### 3.3 Three-Way Comparison (Day 5-7)

```bash
$ spec-align check \
    --openapi openapi.yaml \
    --pydantic src/models/ \
    --typescript src/types/
```

**Deliverable**: Full three-way comparison with clear attribution.

### Phase 3 Milestone

```bash
# Three-way comparison works
$ spec-align check --all

CONTRADICTIONS FOUND: 45

OpenAPI ↔ Pydantic: 23
OpenAPI ↔ TypeScript: 15
Pydantic ↔ TypeScript: 7
```

**Estimate**: 7 days

---

## Phase 4: CI/CD Integration (Week 5)

### Goals
- GitHub Actions integration
- SARIF output for GitHub Security
- Pre-commit hook
- Watch mode

### Tasks

#### 4.1 SARIF Output (Day 1-2)

```python
# spec_align/report/sarif.py
class SarifReporter:
    def report(self, result: AlignmentResult) -> dict:
        # Generate SARIF JSON for GitHub
        pass
```

```yaml
# GitHub Actions usage
- name: Check spec alignment
  run: spec-align check --format sarif --output results.sarif
  
- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: results.sarif
```

**Deliverable**: SARIF output that shows in GitHub Security tab.

#### 4.2 GitHub Actions Action (Day 2-3)

```yaml
# action.yml
name: 'Spec Alignment Check'
description: 'Check for contradictions between specs'
inputs:
  openapi:
    description: 'Path to OpenAPI spec'
    required: true
  fail-on:
    description: 'Severities that cause failure'
    default: 'critical,high'
runs:
  using: 'composite'
  steps:
    - run: pip install spec-alignment-checker
    - run: spec-align check --openapi ${{ inputs.openapi }} --fail-on ${{ inputs.fail-on }}
```

**Deliverable**: Reusable GitHub Action.

#### 4.3 Pre-Commit Hook (Day 3-4)

```yaml
# .pre-commit-hooks.yaml
- id: spec-align
  name: Check spec alignment
  entry: spec-align check --quick
  language: python
  files: \.(yaml|json|py|ts)$
```

**Deliverable**: Pre-commit hook that runs on spec changes.

#### 4.4 Watch Mode (Day 4-5)

```python
# spec_align/watch.py
from watchdog.observers import Observer

class Watcher:
    def watch(self, paths: List[Path], callback):
        # Watch for file changes
        # Re-run check on change
        pass
```

**Deliverable**: Live monitoring during development.

### Phase 4 Milestone

```bash
# CI/CD integration complete
$ # Pre-commit hook runs automatically
$ spec-align watch  # Live monitoring
```

**Estimate**: 5 days

---

## Phase 5: Polish & Documentation (Week 6)

### Goals
- Comprehensive documentation
- Error handling
- Performance optimization
- Real-world testing

### Tasks

#### 5.1 Documentation (Day 1-2)

- README with quick start
- Configuration guide
- Contradiction type reference
- CI/CD integration guide
- API reference for programmatic use

**Deliverable**: Docs site or comprehensive README.

#### 5.2 Error Handling (Day 2-3)

```python
# Graceful handling of:
# - Malformed OpenAPI specs
# - Unparseable Python code
# - Circular references
# - Missing files
```

**Deliverable**: No crashes, clear error messages.

#### 5.3 Performance Optimization (Day 3-4)

- Implement caching
- Parallel parsing
- Incremental checking

**Target**: 100 schemas in <5 seconds (first run), <1 second (cached)

**Deliverable**: Meeting performance targets.

#### 5.4 Real-World Testing (Day 4-5)

Test on:
- vtic codebase (the original problem)
- Other OpenClaw projects
- Public OpenAPI specs

**Deliverable**: Validation that tool catches real contradictions.

### Phase 5 Milestone

- v1.0.0 release
- Published to PyPI
- Documentation complete

**Estimate**: 5 days

---

## Dependency Graph

```
Phase 1 (Foundation)
├── 1.1 Project Setup ─────┐
├── 1.2 Canonical Schema ──┤
│                          ▼
├── 1.3 OpenAPI Parser ───►│
│                          │
├── 1.4 Comparison Engine ─┤
│                          │
├── 1.5 Console Reporter ──┤
│                          │
└── 1.6 CLI MVP ───────────┘
                           │
                           ▼
Phase 2 (Pydantic) ────────┤
├── 2.1 Pydantic Parser    │
├── 2.2 Comparison ────────┤
└── 2.3 Fix Suggestions    │
                           │
                           ▼
Phase 3 (TypeScript) ──────┤
├── 3.1 TS Parser          │
├── 3.2 Naming Conventions │
└── 3.3 Three-Way Compare  │
                           │
                           ▼
Phase 4 (CI/CD) ───────────┤
├── 4.1 SARIF Output       │
├── 4.2 GitHub Action      │
├── 4.3 Pre-Commit Hook    │
└── 4.4 Watch Mode         │
                           │
                           ▼
Phase 5 (Polish) ──────────┘
├── 5.1 Documentation
├── 5.2 Error Handling
├── 5.3 Performance
└── 5.4 Real-World Testing
```

## Milestones Summary

| Milestone | Week | Key Deliverable |
|-----------|------|-----------------|
| M1: OpenAPI → OpenAPI | 2 | Compare multiple OpenAPI specs |
| M2: OpenAPI ↔ Pydantic | 3 | Catch vtic-style contradictions |
| M3: Three-way comparison | 4 | OpenAPI + Pydantic + TypeScript |
| M4: CI/CD ready | 5 | GitHub Actions + pre-commit |
| M5: v1.0.0 release | 6 | Production-ready, documented |

## Risk Mitigation

### Risk: Pydantic AST Parsing Complexity

**Mitigation**: Start with simple cases, use `ast` module's built-in helpers. Fall back to runtime introspection if needed.

### Risk: TypeScript Parsing

**Mitigation**: Use tree-sitter, which handles TypeScript well. Accept that some complex types won't be fully resolved.

### Risk: Performance

**Mitigation**: Cache aggressively. Incremental checking is key for watch mode.

### Risk: False Positives

**Mitigation**: Conservative defaults. Clear config options to adjust sensitivity.

## Success Criteria for v1.0

1. ✓ Detects all 58 vtic contradictions
2. ✓ Runs in <5 seconds on vtic codebase (first run)
3. ✓ Runs in <1 second on cached runs
4. ✓ Clear, actionable output
5. ✓ CI/CD integration works
6. ✓ Documentation is comprehensive
7. ✓ Zero crashes on malformed input

## Post-v1.0 Roadmap

- JSON Schema support
- Protocol Buffers support
- IDE integrations (VS Code extension)
- Auto-fix for common contradictions
- Spec generation from code (reverse mode)
