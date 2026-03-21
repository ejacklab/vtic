# Usage Examples: spec-alignment-checker

## Installation

```bash
# From PyPI (when released)
pip install spec-alignment-checker

# Or with poetry
poetry add spec-alignment-checker

# Development install
git clone https://github.com/openclaw/spec-alignment-checker
cd spec-alignment-checker
poetry install
```

## Basic Usage

### Check OpenAPI vs Pydantic

```bash
# Simple check
spec-align check \
  --openapi openapi.yaml \
  --pydantic src/models/

# With explicit files
spec-align check \
  --openapi openapi.yaml \
  --pydantic src/models/request.py \
  --pydantic src/models/response.py
```

### Check Multiple Spec Types

```bash
# Full comparison
spec-align check \
  --openapi openapi.yaml \
  --pydantic src/models/ \
  --typescript src/types/ \
  --jsonschema schemas/
```

### Quick Mode (Faster, Less Deep)

```bash
# Skip deep analysis for faster feedback
spec-align check --quick --openapi openapi.yaml --pydantic src/models/
```

## Output Formats

### Console (Default)

```bash
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
     audio_format: AudioFormat  # has 5 values
   
   Impact: API accepts 3 formats, code handles 5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  REQUIRED CONFLICT: IntentPrediction.confidence
   Severity: HIGH
   Location: openapi.yaml:78 vs src/models/prediction.py:23
   
   OpenAPI: optional (not in required list)
   Pydantic: required (no default)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️  DEFAULT CONFLICT: TranscriptRequest.timeout_seconds
   Severity: MEDIUM
   Location: openapi.yaml:52 vs src/models/request.py:18
   
   OpenAPI: default=30
   Pydantic: default=60

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY:
  Critical: 1  (blocks merge)
  High:     1  (should fix)
  Medium:   1  (info only)
  Low:      0

Run `spec-align explain <id>` for fix suggestions.
```

### JSON Output

```bash
$ spec-align check --format json --output results.json

# results.json
{
  "summary": {
    "total": 3,
    "by_severity": {
      "critical": 1,
      "high": 1,
      "medium": 1
    }
  },
  "contradictions": [
    {
      "id": "type-mismatch-001",
      "type": "TYPE_MISMATCH",
      "severity": "critical",
      "schema": "TranscriptRequest",
      "field": "audio_format",
      "sources": {
        "openapi": {
          "file": "openapi.yaml",
          "line": 45,
          "value": {
            "type": "string",
            "enum": ["wav", "mp3", "flac"]
          }
        },
        "pydantic": {
          "file": "src/models/request.py",
          "line": 12,
          "value": {
            "type": "AudioFormat",
            "enum_values": ["wav", "mp3", "flac", "ogg", "webm"]
          }
        }
      },
      "message": "Enum values differ",
      "fix_suggestions": [...]
    }
  ]
}
```

### SARIF Output (for GitHub)

```bash
$ spec-align check --format sarif --output results.sarif

# Upload to GitHub
$ gh api repos/{owner}/{repo}/code-scanning/sarifs \
  -f sarif=@results.sarif \
  -f ref=refs/heads/main
```

## Explain Command

Get detailed fix suggestions:

```bash
$ spec-align explain type-mismatch-001

CONTRADICTION: audio_format enum drift
ID: type-mismatch-001

CURRENT STATE:
  OpenAPI (openapi.yaml:45):
    enum: [wav, mp3, flac]
  
  Pydantic (src/models/request.py:12):
    class AudioFormat(str, Enum):
        WAV = "wav"
        MP3 = "mp3"
        FLAC = "flac"
        OGG = "ogg"
        WEBM = "webm"

DIFF:
  OpenAPI is missing: ogg, webm

SUGGESTED FIX (update OpenAPI):
  
  File: openapi.yaml:45
  
  - audio_format:
  -   type: string
  -   enum: [wav, mp3, flac]
  + audio_format:
  +   type: string
  +   enum: [wav, mp3, flac, ogg, webm]

ALTERNATIVE FIX (restrict Pydantic):
  
  File: src/models/request.py:12
  
  - class AudioFormat(str, Enum):
  -     WAV = "wav"
  -     MP3 = "mp3"
  -     FLAC = "flac"
  -     OGG = "ogg"
  -     WEBM = "webm"
  + class AudioFormat(str, Enum):
  +     WAV = "wav"
  +     MP3 = "mp3"
  +     FLAC = "flac"

AUTO-FIX:
  spec-align fix type-mismatch-001 --strategy=openapi
  spec-align fix type-mismatch-001 --strategy=pydantic
```

## Auto-Fix

```bash
# Fix by updating OpenAPI to match Pydantic
$ spec-align fix type-mismatch-001 --strategy=openapi

✓ Updated openapi.yaml:45
  Added: ogg, webm to audio_format enum

# Fix by updating Pydantic to match OpenAPI
$ spec-align fix type-mismatch-001 --strategy=pydantic

✓ Updated src/models/request.py:12
  Removed: ogg, webm from AudioFormat enum

# Preview changes without applying
$ spec-align fix type-mismatch-001 --strategy=openapi --dry-run

Would update openapi.yaml:45
  - enum: [wav, mp3, flac]
  + enum: [wav, mp3, flac, ogg, webm]
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/spec-alignment.yml
name: Spec Alignment Check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
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
            --format sarif \
            --output results.sarif
      
      - name: Upload SARIF results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: results.sarif
```

### GitLab CI

```yaml
# .gitlab-ci.yml
spec-alignment:
  stage: test
  image: python:3.11
  script:
    - pip install spec-alignment-checker
    - spec-align check
        --openapi openapi.yaml
        --pydantic src/models/
        --fail-on critical,high
  artifacts:
    reports:
      junit: results.xml
```

### Pre-Commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/openclaw/spec-alignment-checker
    rev: v1.0.0
    hooks:
      - id: spec-align
        args: ['--quick']  # Fast mode for commits
```

Or local:

```yaml
repos:
  - repo: local
    hooks:
      - id: spec-align
        name: Check spec alignment
        entry: spec-align check --quick --openapi openapi.yaml --pydantic src/models/
        language: system
        files: \.(yaml|yml|json|py)$
        pass_filenames: false
```

## Watch Mode

Live monitoring during development:

```bash
$ spec-align watch \
  --openapi openapi.yaml \
  --pydantic src/models/

Watching for changes...
Press Ctrl+C to stop

[12:34:56] ✓ No contradictions detected
[12:35:02] ✓ No contradictions detected
[12:35:15] ⚠ Change detected in src/models/request.py
[12:35:15] ✓ Rechecked: No contradictions
[12:36:42] ⚠ Change detected in openapi.yaml
[12:36:42]
CONTRADICTIONS FOUND: 1

❌ TYPE MISMATCH: TranscriptRequest.sample_rate
   OpenAPI: type=integer, minimum=8000
   Pydantic: type=float
   
[12:36:45] ✓ Fixed in openapi.yaml
[12:36:45] ✓ No contradictions detected
```

## Configuration File

```yaml
# spec-align.yaml
version: 1

# Source specifications
sources:
  openapi:
    - openapi.yaml
    - api-specs/*.yaml
  pydantic:
    - src/models/
  typescript:
    - src/types/
  jsonschema:
    - schemas/*.json

# Ignore patterns
ignore:
  - "**/test_*.py"
  - "**/*.test.ts"
  - "deprecated/**"

# Severity configuration
severities:
  type_mismatch: critical
  required_conflict: high
  enum_drift: high
  format_mismatch: medium
  default_conflict: medium
  naming_inconsistency: low
  description_drift: info

# Naming conventions
naming:
  openapi: snake_case
  pydantic: snake_case
  typescript: camelCase
  auto_convert: true

# Output settings
output:
  format: console
  color: true
  show_source: true

# Fail settings (for CI)
fail_on:
  - critical
  - high

# Caching
cache:
  enabled: true
  directory: .spec-align-cache
  ttl: 3600  # 1 hour
```

With config file:

```bash
# Uses spec-align.yaml by default
$ spec-align check

# Explicit config file
$ spec-align check --config my-config.yaml
```

## Programmatic Usage

```python
from spec_alignment_checker import AlignmentChecker

# Create checker
checker = AlignmentChecker(
    openapi_specs=["openapi.yaml"],
    pydantic_dirs=["src/models/"]
)

# Run check
result = checker.check()

# Process results
if result.contradictions:
    for c in result.contradictions:
        print(f"{c.severity}: {c.schema_name}.{c.field_name}")
        print(f"  {c.message}")
        
        # Get fix suggestions
        fixes = checker.suggest_fixes(c)
        for fix in fixes:
            print(f"  Fix: {fix.description}")

# Check specific severity
if result.has_critical():
    raise ValueError("Critical spec contradictions found")

# Export results
result.to_json("results.json")
result.to_sarif("results.sarif")
```

## Example Catches

### Catch 1: Enum Drift (vtic incident)

```bash
$ spec-align check

❌ ENUM DRIFT: TranscriptRequest.audio_format
   Severity: HIGH
   
   OpenAPI (openapi.yaml:45):
     enum: [wav, mp3, flac]
   
   Pydantic (src/models/request.py:12):
     enum: [wav, mp3, flac, ogg, webm]
   
   Impact: 
   - API validates for 3 formats
   - Code handles 5 formats
   - Clients sending ogg/webm get 400 errors
```

### Catch 2: Required Conflict

```bash
$ spec-align check

⚠️  REQUIRED CONFLICT: IntentPrediction.confidence
   Severity: HIGH
   
   OpenAPI (openapi.yaml:78):
     confidence: number (optional)
   
   Pydantic (src/models/prediction.py:23):
     confidence: float (required)
   
   TypeScript (src/types/prediction.ts:45):
     confidence: number (required)
   
   Impact:
   - API allows confidence to be omitted
   - Backend and frontend expect it
   - Type mismatch in serialization
```

### Catch 3: Type Mismatch

```bash
$ spec-align check

❌ TYPE MISMATCH: TranscriptRequest.sample_rate
   Severity: CRITICAL
   
   OpenAPI (openapi.yaml:52):
     type: integer
     minimum: 8000
     maximum: 48000
   
   Pydantic (src/models/request.py:15):
     sample_rate: float
   
   Impact:
   - API expects integer (e.g., 16000)
   - Code accepts float (e.g., 16000.5)
   - Precision loss, validation failures
```

### Catch 4: Default Conflict

```bash
$ spec-align check

ℹ️  DEFAULT CONFLICT: TranscriptRequest.timeout_seconds
   Severity: MEDIUM
   
   OpenAPI (openapi.yaml:58):
     default: 30
   
   Pydantic (src/models/request.py:20):
     default = 60
   
   Impact:
   - API docs say 30 seconds
   - Code uses 60 seconds
   - Client expectations mismatched
```

### Catch 5: Naming Inconsistency

```bash
$ spec-align check

ℹ️  NAMING INCONSISTENCY: User fields
   Severity: LOW
   
   OpenAPI uses snake_case:
     - user_id
     - created_at
     - is_active
   
   TypeScript uses camelCase:
     - userId
     - createdAt
     - isActive
   
   Impact:
   - Requires transformation layer
   - Potential serialization bugs
   - Consider configuring auto_convert: true
```

## Advanced Usage

### Custom Contradiction Types

```yaml
# spec-align.yaml
custom_rules:
  - name: "no_any_types"
    description: "Flag use of 'any' type"
    severity: medium
    check: "type_ref.base_type == 'any'"
  
  - name: "require_description"
    description: "All fields must have descriptions"
    severity: low
    check: "field.description is None"
```

### Filtering Results

```bash
# Only show critical and high
$ spec-align check --severity critical,high

# Only show specific contradiction types
$ spec-align check --type type_mismatch,enum_drift

# Ignore specific schemas
$ spec-align check --ignore-schema InternalModel,LegacyRequest
```

### Incremental Checks

```bash
# Only check changed files (uses git diff)
$ spec-align check --incremental

# Check only files changed since main
$ spec-align check --incremental --base main
```

### Export for Analysis

```bash
# Export to CSV for spreadsheet analysis
$ spec-align check --format csv --output contradictions.csv

# Export to Markdown for documentation
$ spec-align check --format markdown --output SPEC_ISSUES.md
```

## Integration with OpenClaw

```bash
# As an OpenClaw command
$ openclaw spec-check

# Check after agent work
$ openclaw spec-check --since-last-commit

# Auto-fix detected contradictions
$ openclaw spec-check --auto-fix
```

### Agent Hook

Agents can automatically check before committing:

```python
# In agent code
from spec_alignment_checker import quick_check

def before_commit():
    issues = quick_check(
        openapi="openapi.yaml",
        pydantic="src/models/"
    )
    
    if issues.critical:
        raise Exception(f"Cannot commit: {len(issues.critical)} critical spec contradictions")
    
    if issues.high:
        print(f"Warning: {len(issues.high)} high-severity spec issues")
```

## Summary

The `spec-alignment-checker` provides:

1. **Flexible CLI** - Check from command line with various options
2. **Multiple formats** - Console, JSON, SARIF outputs
3. **CI/CD ready** - GitHub Actions, GitLab CI, pre-commit hooks
4. **Live feedback** - Watch mode for development
5. **Actionable output** - Fix suggestions and auto-fix
6. **Programmatic API** - Use in Python code

Every contradiction caught early saves debugging time. The vtic incident's 58 contradictions would have been caught immediately, not after 10+ hours of waste.
