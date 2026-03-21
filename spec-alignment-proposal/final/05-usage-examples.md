# Usage Examples: spec-alignment-checker

## Installation

```bash
# From PyPI
pip install spec-alignment-checker

# With poetry
poetry add spec-alignment-checker

# Development
git clone https://github.com/openclaw/spec-alignment-checker
cd spec-alignment-checker
poetry install
```

---

## Basic Usage

### Check OpenAPI vs Pydantic

```bash
# Simple check
spec-align check \
  --openapi openapi.yaml \
  --pydantic src/models/

# With multiple Pydantic directories
spec-align check \
  --openapi openapi.yaml \
  --pydantic src/models/ \
  --pydantic src/schemas/
```

### Full Comparison

```bash
# OpenAPI + Pydantic + TypeScript
spec-align check \
  --openapi openapi.yaml \
  --pydantic src/models/ \
  --typescript src/types/
```

### Quick Mode

```bash
# Faster, skip deep analysis
spec-align check --quick \
  --openapi openapi.yaml \
  --pydantic src/models/
```

---

## Output Formats

### Console (Default)

```
$ spec-align check --openapi openapi.yaml --pydantic src/models/

CONTRADICTIONS FOUND: 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ TYPE MISMATCH: TranscriptRequest.audio_format
   Severity: CRITICAL
   Location: openapi.yaml:45 vs src/models/request.py:12
   
   OpenAPI:
     audio_format:
       type: string
       enum: [wav, mp3, flac]
   
   Pydantic:
     class AudioFormat(Enum):
         WAV = "wav"
         MP3 = "mp3"
         FLAC = "flac"
         OGG = "ogg"
         WEBM = "webm"
   
   Impact: API accepts 3 formats, code handles 5
   Fix: Add ogg, webm to OpenAPI or remove from Pydantic

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  REQUIRED CONFLICT: IntentPrediction.confidence
   Severity: HIGH
   Location: openapi.yaml:78 vs src/models/prediction.py:23
   
   OpenAPI: optional
   Pydantic: required (no default)
   
   Impact: API allows null, code expects value
   Fix: Add required=true in OpenAPI or default in Pydantic

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️  DEFAULT CONFLICT: TranscriptRequest.timeout_seconds
   Severity: MEDIUM
   Location: openapi.yaml:52 vs src/models/request.py:18
   
   OpenAPI: default=30
   Pydantic: default=60
   
   Impact: Inconsistent default behavior
   Fix: Align defaults to 30 or 60

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY:
  Critical: 1  (blocks merge)
  High:     1  (should fix)
  Medium:   1  (info)
  
Run `spec-align explain <id>` for details.
```

### JSON Output

```bash
$ spec-align check --openapi openapi.yaml --pydantic src/models/ --output json
```

```json
{
  "summary": {
    "total": 3,
    "critical": 1,
    "high": 1,
    "medium": 1
  },
  "contradictions": [
    {
      "id": "TYPE-001",
      "category": "TYPE_MISMATCH",
      "severity": "critical",
      "field": "TranscriptRequest.audio_format",
      "sources": [
        {
          "file": "openapi.yaml",
          "line": 45,
          "value": "enum: [wav, mp3, flac]"
        },
        {
          "file": "src/models/request.py",
          "line": 12,
          "value": "enum: [wav, mp3, flac, ogg, webm]"
        }
      ],
      "impact": "API accepts 3 formats, code handles 5",
      "suggestion": "Sync enum values"
    }
  ]
}
```

### SARIF Output (for GitHub)

```bash
$ spec-align check --openapi openapi.yaml --pydantic src/models/ --output sarif > results.sarif
```

Upload to GitHub Advanced Security for PR annotations.

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/spec-check.yml
name: Spec Alignment Check

on:
  pull_request:
    paths:
      - 'openapi.yaml'
      - 'src/models/**'
      - 'src/api/**'

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install spec-align
        run: pip install spec-alignment-checker
      
      - name: Check spec alignment
        run: |
          spec-align check \
            --openapi openapi.yaml \
            --pydantic src/models/ \
            --fail-on critical,high \
            --output sarif > results.sarif
      
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: results.sarif
```

### GitLab CI

```yaml
# .gitlab-ci.yml
spec-check:
  stage: test
  image: python:3.11
  script:
    - pip install spec-alignment-checker
    - spec-align check
      --openapi openapi.yaml
      --pydantic src/models/
      --fail-on critical
      --output json > spec-report.json
  artifacts:
    reports:
      dotenv: spec-report.json
  rules:
    - changes:
      - openapi.yaml
      - src/models/**/*
```

### Pre-Commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/openclaw/spec-alignment-checker
    rev: v1.0.0
    hooks:
      - id: spec-align
        args: ['--quick', '--fail-on', 'critical']
        files: \.(yaml|json|py|ts)$
```

---

## Advanced Usage

### Watch Mode

```bash
$ spec-align watch --openapi openapi.yaml --pydantic src/models/

Watching for changes...
✓ No contradictions (12:34:56)
✓ No contradictions (12:35:02)
⚠ Change detected in src/models/request.py
✓ Rechecked: No contradictions (12:35:15)
❌ Contradiction found (12:36:02)
  → TYPE MISMATCH: audio_format (critical)
```

### Config File

```yaml
# .spec-align.yaml
openapi: openapi.yaml
models:
  - src/models/
  - src/schemas/
code:
  - src/api/
output: console
fail_on: critical

ignore:
  - src/models/legacy.py  # Skip known issues
  - src/models/generated/ # Skip generated code

severity_overrides:
  - field: "JobRequest.priority"
    severity: low  # Downgrade known minor issue
```

```bash
# Uses config file
$ spec-align check

# Override config
$ spec-align check --fail-on critical,high
```

### Explain Contradiction

```bash
$ spec-align explain TYPE-001

CONTRADICTION: audio_format enum drift

Current state:
  OpenAPI (openapi.yaml:45):
    enum: [wav, mp3, flac]
  
  Pydantic (src/models/request.py:12):
    enum: [wav, mp3, flac, ogg, webm]

Suggested fix (option 1 - update OpenAPI):
  
  audio_format:
    type: string
    enum: [wav, mp3, flac, ogg, webm]

Suggested fix (option 2 - restrict Pydantic):
  
  class AudioFormat(str, Enum):
      WAV = "wav"
      MP3 = "mp3"
      FLAC = "flac"
      # Remove: OGG, WEBM

Apply fix:
  spec-align fix TYPE-001 --strategy openapi
  spec-align fix TYPE-001 --strategy pydantic
```

### Auto-Fix

```bash
# Dry-run first
$ spec-align fix TYPE-001 --dry-run

Would apply:
  - Add 'ogg' to openapi.yaml:47
  - Add 'webm' to openapi.yaml:47

# Apply fix
$ spec-align fix TYPE-001 --strategy openapi

Fixed:
  ✓ Updated openapi.yaml:47
  ✓ Re-checked: No contradictions
```

---

## Before/After Scenarios

### Scenario: New Feature Development

#### Before (Manual)

| Phase | Time | Pain |
|-------|------|------|
| Write OpenAPI spec | 2h | No validation |
| Write Pydantic models | 2h | May not match |
| Write code | 4h | May not match either |
| PR review | 1h | May miss contradictions |
| Manual spec review | 6h | Tedious |
| Bug discovery | 3-10h | Late |
| **Total** | **18-25h** | High variance |

#### After (With spec-align)

| Phase | Time | Improvement |
|-------|------|-------------|
| Write OpenAPI | 2h | Same |
| Write Pydantic | 1.5h | Instant feedback |
| Write code | 3h | Confidence |
| PR review | 0.5h | CI validated |
| Auto spec check | 30s | Complete |
| Bug discovery | 0-1h | Caught early |
| **Total** | **8-9h** | **Predictable** |

**Savings: 10-16 hours per feature**

---

### Scenario: Debugging Type Error

#### Before

```
14:00 - User reports error
14:15 - Reproduce
14:30 - Check logs, see type error
14:45 - Examine code
15:00 - Compare with Pydantic
15:15 - Compare with OpenAPI
15:30 - Find contradiction
15:45 - Fix
16:00 - Test
16:15 - Deploy
Total: 2h 15min
```

#### After

```
14:00 - User reports error
14:05 - Run spec-align
14:07 - See contradiction with location
14:15 - Fix
14:20 - Test
14:25 - Deploy
Total: 25 min
```

**Savings: 1h 50min per bug**

---

## Programmatic API

### Python Integration

```python
from spec_alignment_checker import check_alignment, Format

# Basic check
result = check_alignment(
    openapi="openapi.yaml",
    pydantic_dirs=["src/models/"],
)

# Check contradictions
if result.contradictions:
    for c in result.contradictions:
        print(f"{c.severity}: {c.field_name}")
        print(f"  {c.suggestion}")

# Custom output
json_output = result.to_json()
sarif_output = result.to_sarif()

# Filter by severity
critical = [c for c in result.contradictions if c.severity == "critical"]
```

### AI Agent Integration

```python
# For AI agents to invoke before committing
from spec_alignment_checker import quick_check

def before_commit():
    result = quick_check(
        openapi="openapi.yaml",
        models="src/models/"
    )
    
    if result.has_critical():
        # Agent should not commit
        return False, result.explain()
    
    if result.has_high():
        # Agent should flag for review
        return True, f"Warning: {result.summary}"
    
    return True, "No contradictions"
```

---

## Performance

### Benchmarks

| Codebase Size | Files | First Run | Cached |
|---------------|-------|-----------|--------|
| Small (<10) | 8 | 0.5s | 0.1s |
| Medium (10-50) | 35 | 1.8s | 0.3s |
| Large (50-200) | 120 | 4.2s | 0.8s |
| Enterprise (200+) | 350 | 12s | 2.1s |

### CI Performance

```yaml
# Typical CI run
- checkout: 10s
- install: 5s
- spec-align check: 2s (cached)
- Total: ~20s
```

---

## Troubleshooting

### Common Issues

**Issue**: "Cannot parse OpenAPI spec"
```
Solution: Ensure OpenAPI 3.0+ format
Run: spec-align validate openapi.yaml
```

**Issue**: "Too many false positives"
```
Solution: Use .spec-align.yaml to configure strictness
Set: strictness.naming: lenient
```

**Issue**: "Slow on large codebase"
```
Solution: Use --quick mode for fast feedback
Run: spec-align check --quick
```
