# Solution Overview: Spec Alignment Checker

## Vision

A tool that automatically detects contradictions between OpenAPI specifications, Pydantic models, and implementation code—catching in seconds what takes humans hours to find manually.

**One command:**

```bash
spec-check ./openapi.yaml ./models/ ./src/
```

**Output:**

```
❌ Found 3 contradictions:

1. [TYPE_MISMATCH] models/job.py:15
   Field 'job_id': OpenAPI expects 'string (uuid)', Pydantic defines 'int'
   
2. [REQUIRED_MISMATCH] openapi.yaml:142
   Field 'output_format': OpenAPI marks required, Pydantic marks optional
   
3. [ENUM_MISMATCH] src/status.py:8
   Enum Status: Code has value 'running' not in OpenAPI enum

Run with --fix for suggested corrections
```

---

## High-Level Approach

### Three-Phase Analysis

```
┌─────────────────────────────────────────────────────────────┐
│                     Spec Alignment Checker                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: Parse          Phase 2: Extract      Phase 3:     │
│  ──────────────         ───────────────       ─────────────│
│  OpenAPI Spec    ───►   Schema Model    ◄───  Compare &     │
│  (YAML/JSON)            (Canonical)           Report        │
│                                                              │
│  Pydantic Models ───►   Schema Model                         │
│  (.py files)            (Canonical)                          │
│                                                              │
│  Code (Type Hints) ─►   Schema Model                         │
│  (.py files)            (Canonical)                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Canonical Schema Model

The core innovation is a **canonical schema representation** that all sources map to:

```python
class FieldSchema:
    name: str
    type: FieldType  # string, integer, boolean, array, object, etc.
    required: bool
    default: Optional[Any]
    enum_values: Optional[List[str]]
    format: Optional[str]  # uuid, date-time, email, etc.
    description: Optional[str]
    constraints: Dict[str, Any]  # min, max, pattern, etc.

class EndpointSchema:
    path: str
    method: str  # GET, POST, PUT, DELETE
    request_body: Optional[FieldSchema]
    response_schema: Dict[int, FieldSchema]  # status code -> schema
    parameters: List[ParameterSchema]

class SchemaModel:
    endpoints: Dict[str, EndpointSchema]  # key: "METHOD /path"
    models: Dict[str, FieldSchema]  # key: model name
```

Each source (OpenAPI, Pydantic, code) is parsed into this canonical form, then compared field-by-field.

---

## Core Features

### 1. Multi-Source Parsing

**OpenAPI 3.x Support**
```yaml
# Input: openapi.yaml
openapi: 3.0.0
paths:
  /api/v1/jobs:
    post:
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/JobRequest'
components:
  schemas:
    JobRequest:
      type: object
      required: [source_url]
      properties:
        source_url:
          type: string
          format: uri
```

**Pydantic Model Extraction**
```python
# Input: models/job.py
from pydantic import BaseModel
from typing import Optional

class JobRequest(BaseModel):
    source_url: str
    output_format: Optional[str] = None  # Detected as optional
    priority: int = 1  # Has default
```

**Code Type Hint Analysis**
```python
# Input: handlers/jobs.py
from typing import Dict, Any

def create_job(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected request: {source_url: str, output_format?: str}
    Returns: {job_id: str, status: str}
    """
    # Analyzer extracts from type hints and docstrings
```

### 2. Contradiction Detection

**Type Mismatches**
```
OpenAPI: job_id is string (uuid)
Pydantic: job_id is int
→ CONTRADICTION
```

**Required Field Mismatches**
```
OpenAPI: output_format is required
Pydantic: output_format is Optional[str]
→ CONTRADICTION
```

**Enum Value Mismatches**
```
OpenAPI: status in [pending, completed, failed]
Code: Status.RUNNING = "running"
→ CONTRADICTION: 'running' not in OpenAPI enum
```

**Endpoint Mismatches**
```
OpenAPI: POST /api/v1/jobs
Code implements: POST /api/v1/tasks
→ CONTRADICTION: endpoint not found in OpenAPI
```

**Response Schema Mismatches**
```
OpenAPI: 200 response has {job_id: string, status: string}
Code returns: {"id": ..., "state": ...}
→ CONTRADICTION: field names don't match
```

### 3. Severity Classification

| Severity | Description | Example |
|----------|-------------|---------|
| **CRITICAL** | Will cause runtime errors | Type mismatch, missing required field |
| **HIGH** | Will cause test failures | Endpoint path mismatch, enum value conflict |
| **MEDIUM** | May cause client issues | Undocumented field, format mismatch |
| **LOW** | Documentation drift | Description mismatch, example mismatch |

### 4. Smart Reporting

**Human-Readable Output**
```
═══════════════════════════════════════════════════════════════
SPEC ALIGNMENT REPORT
Generated: 2024-03-15 14:32:01
Sources: openapi.yaml, models/, src/
═══════════════════════════════════════════════════════════════

SUMMARY
───────
Total Contradictions: 3
  ❌ Critical: 1
  ⚠️  High: 1
  ℹ️  Medium: 1

CRITICAL ISSUES (must fix)
──────────────────────────
1. [TYPE_MISMATCH] models/job.py:15
   Field: JobRequest.source_url
   OpenAPI: string (format: uri)
   Pydantic: str (no format constraint)
   
   Impact: Invalid URIs may pass validation
   Fix: Add @field_validator for URI format

HIGH ISSUES (should fix)
────────────────────────
2. [ENUM_MISMATCH] src/status.py:8
   Enum: JobStatus
   OpenAPI: [pending, processing, completed, failed]
   Code: [pending, running, completed, failed]
   
   Impact: 'running' status will fail OpenAPI validation
   Fix: Rename 'running' to 'processing' or update OpenAPI

═══════════════════════════════════════════════════════════════
```

**Machine-Readable Output (JSON)**
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
      "id": "contradiction-001",
      "severity": "critical",
      "type": "TYPE_MISMATCH",
      "location": {
        "file": "models/job.py",
        "line": 15,
        "field": "JobRequest.source_url"
      },
      "openapi": {"type": "string", "format": "uri"},
      "actual": {"type": "str", "format": null},
      "suggestion": "Add @field_validator for URI format"
    }
  ]
}
```

### 5. CI/CD Integration

**GitHub Actions**
```yaml
name: Spec Alignment Check
on: [push, pull_request]

jobs:
  check-specs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install spec-alignment-checker
        run: pip install spec-alignment-checker
      - name: Check alignment
        run: spec-check openapi.yaml models/ src/ --output json > results.json
      - name: Fail on critical issues
        run: |
          if [ $(jq '.summary.critical' results.json) -gt 0 ]; then
            echo "Critical spec contradictions found!"
            exit 1
          fi
```

**Pre-commit Hook**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: spec-alignment-check
        name: Spec Alignment Checker
        entry: spec-check openapi.yaml models/ src/ --fail-on critical
        language: system
        pass_filenames: false
```

---

## Integration Points

### 1. OpenClaw Integration

**As an OpenClaw Tool**
```bash
# Use within OpenClaw workflow
openclaw spec-check --watch

# Auto-fix during development
openclaw spec-check --fix --interactive
```

**Agent-Aware Checking**
```python
# Agents can query alignment status
from spec_alignment_checker import check_alignment

result = check_alignment(
    openapi="openapi.yaml",
    models=["models/"],
    code=["src/"]
)

if result.has_critical:
    # Agent can suggest fixes or block further changes
    return result.to_agent_message()
```

### 2. IDE Integration

**VS Code Extension**
- Real-time squiggles on misaligned fields
- Quick-fix suggestions
- Side-by-side comparison view

**PyCharm Plugin**
- Inspection integration
- Intention actions for fixes

### 3. Language Support

**Phase 1 (MVP)**
- OpenAPI 3.x (YAML/JSON)
- Python Pydantic v2 models
- Python type hints

**Phase 2**
- TypeScript interfaces
- JSON Schema
- GraphQL schemas

**Phase 3**
- Java classes (Jackson annotations)
- Go structs
- Rust serde types

---

## Design Principles

1. **Zero False Positives on Critical Issues**
   - If we report CRITICAL, it's a real problem
   - Better to miss some issues than erode trust with false alarms

2. **Actionable Reports**
   - Every contradiction includes file, line, field
   - Every report includes a suggested fix
   - JSON output enables automation

3. **Fast Enough for CI**
   - Target: <5 seconds for typical codebase
   - Incremental mode: only check changed files
   - Parallel parsing of large projects

4. **Incremental Adoption**
   - Works with partial coverage (only check what exists)
   - Severity thresholds allow gradual cleanup
   - Can start with --fail-on critical only

5. **Extensible Architecture**
   - Pluggable parsers for new sources
   - Custom contradiction detectors
   - Configurable severity rules

---

## Anti-Goals (What We Won't Do)

1. **Auto-fix everything** - Too risky. We suggest, humans confirm.
2. **Semantic analysis** - We check structural alignment, not business logic.
3. **Migration tool** - This is a checker, not a spec migration utility.
4. **IDE replacement** - Complements IDEs, doesn't replace them.
5. **All programming languages** - Start with Python, expand carefully.

---

## Success Criteria

The tool succeeds when:

1. **vtic-style incidents become impossible** - CI catches contradictions before merge
2. **Manual spec reviews become unnecessary** - Automation replaces drudgery
3. **Developers trust the specs again** - "If spec-check passes, docs are accurate"
4. **Time saved > Time invested** - 10+ hours saved per project, <1 hour to adopt

---

## Next Steps

1. Read [03-architecture.md](./03-architecture.md) for technical design
2. Read [04-implementation-plan.md](./04-implementation-plan.md) for timeline
3. Read [05-usage-examples.md](./05-usage-examples.md) for detailed examples
4. Read [06-success-metrics.md](./06-success-metrics.md) for measurement criteria
