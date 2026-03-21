# Solution Overview: spec-alignment-checker

## The Vision

`spec-alignment-checker` is a CLI tool that automatically detects contradictions between OpenAPI specs, Pydantic models, TypeScript types, and code implementations. It runs locally, in CI, and as a pre-commit hook.

## High-Level Approach

### Normalize, Compare, Report

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ OpenAPI Spec│────▶│              │     │             │
├─────────────┤     │   Normalize  │────▶│   Compare   │
│ Pydantic    │────▶│   to Common  │     │   & Detect  │
│ Models      │     │   Schema     │     │   Drift     │
├─────────────┤     │   Format     │     │             │
│ TypeScript  │────▶│              │     │             │
│ Types       │     └──────────────┘     └──────┬──────┘
├─────────────┤                                 │
│ Code        │─────────────────────────────────┘
│ (runtime)   │
└─────────────┘                                 │
                                                ▼
                                         ┌─────────────┐
                                         │   Report    │
                                         │   Generator │
                                         └─────────────┘
```

### Three-Phase Operation

1. **Discovery**: Find all spec files in the project
2. **Normalization**: Convert each format to a common representation
3. **Comparison**: Detect contradictions and generate reports

## Core Features

### 1. Multi-Format Parser

```bash
# Supports multiple input formats
spec-align check \
  --openapi openapi.yaml \
  --pydantic src/models/ \
  --typescript src/types/ \
  --code src/
```

Supported formats:
- OpenAPI 3.0/3.1 (YAML/JSON)
- Pydantic v1/v2 models (Python AST parsing)
- TypeScript interfaces/types (TypeScript compiler API)
- JSON Schema (full support)
- Protocol Buffers (basic support)

### 2. Contradiction Detection Engine

Detects these contradiction types:

| Category | Example | Severity |
|----------|---------|----------|
| Type mismatch | `string` vs `integer` | Critical |
| Required conflict | optional vs required | High |
| Enum drift | `[a,b,c]` vs `[a,b,d]` | High |
| Format mismatch | `date-time` vs `date` | Medium |
| Default conflict | `30` vs `60` | Medium |
| Naming inconsistency | `user_id` vs `userId` | Low |
| Description drift | Different descriptions | Info |

### 3. Smart Normalization

Converts all formats to a canonical schema representation:

```python
# Internal representation (pseudo-code)
@dataclass
class FieldSpec:
    name: str
    type: TypeRef
    required: bool
    default: Any
    constraints: Constraints
    source_location: Location
    
@dataclass  
class TypeRef:
    base_type: str  # string, number, boolean, object, array
    format: Optional[str]  # date-time, uuid, etc.
    enum_values: Optional[List[str]]
    array_item: Optional[TypeRef]
    object_fields: Optional[Dict[str, FieldSpec]]
```

### 4. Contextual Reporting

```bash
$ spec-align check

CONTRADICTIONS FOUND: 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ TYPE MISMATCH: TranscriptRequest.audio_format
   Severity: CRITICAL
   
   OpenAPI (openapi.yaml:45):
     audio_format:
       type: string
       enum: [wav, mp3, flac]
   
   Pydantic (src/models/request.py:12):
     audio_format: AudioFormat = Field(
         default=AudioFormat.WAV,
         description="Audio format"
     )
     # AudioFormat enum has 5 values: wav, mp3, flac, ogg, webm
   
   Impact: API accepts 3 formats, code handles 5
   Fix: Sync enum values between spec and code

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  REQUIRED CONFLICT: IntentPrediction.confidence
   Severity: HIGH
   
   OpenAPI (openapi.yaml:78):
     confidence:
       type: number
       # Not in required list
   
   TypeScript (src/types/prediction.ts:23):
     interface IntentPrediction {
       confidence: number;  // Required (no ?)
     }
   
   Impact: API allows null, frontend expects value
   Fix: Mark as required in OpenAPI or optional in TypeScript

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️  NAMING INCONSISTENCY: user_id vs userId
   Severity: LOW
   
   OpenAPI uses: user_id (snake_case)
   TypeScript uses: userId (camelCase)
   
   Impact: Potential serialization issues
   Fix: Add naming transformation config or standardize

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY:
  Critical: 1  (blocks merge)
  High:     1  (should fix)
  Medium:   0
  Low:      1  (info only)
  
Run `spec-align explain <id>` for detailed fix suggestions.
```

### 5. CI/CD Integration

```yaml
# GitHub Actions example
name: Spec Alignment Check

on: [pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check spec alignment
        run: |
          pip install spec-alignment-checker
          spec-align check \
            --openapi openapi.yaml \
            --pydantic src/models/ \
            --fail-on critical,high
            
      # Fails the build if critical or high contradictions found
```

### 6. Pre-Commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: spec-align
        name: Check spec alignment
        entry: spec-align check --quick
        language: system
        files: \.(yaml|json|py|ts)$
```

### 7. Watch Mode

```bash
# Continuous monitoring during development
spec-align watch \
  --openapi openapi.yaml \
  --pydantic src/models/

Watching for changes...
✓ No contradictions detected (12:34:56)
✓ No contradictions detected (12:35:02)
⚠ Change detected in src/models/request.py
✓ Rechecked: No contradictions (12:35:15)
```

## Integration Points

### With OpenClaw

```bash
# As an OpenClaw tool
openclaw spec-check \
  --project ./my-project \
  --agents codex,claude-code

# Checks alignment after multi-agent work sessions
```

### With Existing Tools

- **Spectral**: Uses Spectral for OpenAPI linting, adds cross-format checking
- **mypy**: Integrates with mypy for Python type checking
- **tsc**: Uses TypeScript compiler for type analysis
- **pytest**: Plugin for checking alignment in tests

### With AI Agents

```python
# Agent can invoke before committing
from spec_alignment_checker import check_alignment

result = check_alignment(
    openapi="openapi.yaml",
    pydantic_models="src/models/"
)

if result.contradictions:
    # Agent can auto-fix or flag for human review
    for contradiction in result.contradictions:
        print(f"Fix needed: {contradiction}")
```

## Design Principles

### 1. Zero False Positives by Default

Default configuration is conservative. Only report clear contradictions:

```yaml
# spec-align.yaml
strictness:
  type_mismatch: strict      # Always report
  required_conflict: strict  # Always report
  naming: lenient            # Only report if configured
  description: ignore        # Never report by default
```

### 2. Incremental Adoption

Works on a single file pair at first:

```bash
# Start simple: just check OpenAPI vs one Pydantic file
spec-align check openapi.yaml src/models/request.py

# Gradually add more sources
spec-align check openapi.yaml src/models/ src/types/
```

### 3. Fix Suggestions, Not Just Errors

Every contradiction comes with actionable fix suggestions:

```bash
$ spec-align explain contradiction-001

CONTRADICTION: audio_format enum drift

Current state:
  OpenAPI: [wav, mp3, flac]
  Pydantic: [wav, mp3, flac, ogg, webm]

Suggested fix (update OpenAPI):
  Add ogg, webm to the enum in openapi.yaml:45
  
  audio_format:
    type: string
    enum: [wav, mp3, flac, ogg, webm]

Alternative fix (restrict Pydantic):
  Remove ogg, webm from AudioFormat enum in src/models/request.py:12
  
  class AudioFormat(str, Enum):
      WAV = "wav"
      MP3 = "mp3"
      FLAC = "flac"

Auto-fix available: spec-align fix contradiction-001 --strategy=openapi
```

### 4. Performance First

- Incremental checking (only changed files)
- Parallel parsing
- Caching of normalized schemas

```bash
$ time spec-align check
First run:   2.3s
Cached run:  0.4s
Watch mode:  <0.1s per change
```

## The Payoff

With `spec-alignment-checker`:

1. **Catch contradictions immediately** - Not after 10 hours of debugging
2. **Block bad merges** - CI fails on contradictions
3. **Fix with confidence** - Clear suggestions, not guesswork
4. **Scale with your team** - Works with 2 specs or 200

The vtic incident would have been caught in the first PR, not after weeks of drift.
