# Usage Examples: Spec Alignment Checker

## Basic Usage

### Quick Check

```bash
# Check OpenAPI spec against Pydantic models and code
spec-check openapi.yaml models/ src/
```

**Output:**
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

No issues found - your specs are aligned! ✨
```

### With Contradictions

```bash
spec-check openapi.yaml models/ src/
```

**Output:**
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

❌ CRITICAL ISSUES (must fix)
─────────────────────────────
1. [TYPE_MISMATCH] models/job.py:15
   Field: JobRequest.job_id
   Sources:
     openapi: string (format: uuid)
     pydantic: int
   
   Impact: Runtime type error when API returns UUID string
   Fix: Change models/job.py:15
        - job_id: int
        + job_id: str

─────────────────────────────
⚠️  HIGH ISSUES (should fix)
─────────────────────────────
2. [REQUIRED_MISMATCH] openapi.yaml:142
   Field: TranscodeRequest.output_format
   Sources:
     openapi: required
     pydantic: optional (has default None)
   
   Impact: API accepts invalid requests without output_format
   Fix: Change openapi.yaml:142
        - required: [source_url, output_format]
        + required: [source_url]
   
   OR: Change models/transcode.py:23
        - output_format: Optional[str] = None
        + output_format: str

─────────────────────────────
ℹ️  MEDIUM ISSUES (review)
─────────────────────────────
3. [ENUM_MISMATCH] src/status.py:8
   Enum: JobStatus
   Sources:
     openapi: [pending, processing, completed, failed]
     code: [pending, running, completed, failed]
   
   Impact: Status "running" not in OpenAPI enum
   Fix: Choose one:
   
   Option A - Update OpenAPI:
     openapi.yaml:89
     - enum: [pending, processing, completed, failed]
     + enum: [pending, running, completed, failed]
   
   Option B - Update code:
     src/status.py:8
     - RUNNING = "running"
     + PROCESSING = "processing"

═══════════════════════════════════════════════════════════════
Run with --fix for interactive correction mode
═══════════════════════════════════════════════════════════════
```

---

## Output Formats

### JSON Output (for CI/CD)

```bash
spec-check openapi.yaml models/ src/ --output json
```

**Output:**
```json
{
  "summary": {
    "total": 3,
    "critical": 1,
    "high": 1,
    "medium": 1,
    "low": 0
  },
  "contradictions": [
    {
      "id": "contradiction-001",
      "type": "TYPE_MISMATCH",
      "severity": "critical",
      "field": "JobRequest.job_id",
      "message": "Type mismatch: OpenAPI expects string (uuid), Pydantic defines int",
      "impact": "Runtime type error when API returns UUID string",
      "sources": {
        "openapi": {
          "file": "openapi.yaml",
          "line": 45,
          "type": "string",
          "format": "uuid"
        },
        "pydantic": {
          "file": "models/job.py",
          "line": 15,
          "type": "int"
        }
      },
      "suggestion": {
        "file": "models/job.py",
        "line": 15,
        "current": "job_id: int",
        "proposed": "job_id: str"
      }
    },
    {
      "id": "contradiction-002",
      "type": "REQUIRED_MISMATCH",
      "severity": "high",
      "field": "TranscodeRequest.output_format",
      "message": "Required mismatch: OpenAPI marks required, Pydantic marks optional",
      "sources": {
        "openapi": {
          "file": "openapi.yaml",
          "line": 142,
          "required": true
        },
        "pydantic": {
          "file": "models/transcode.py",
          "line": 23,
          "required": false,
          "default": null
        }
      },
      "suggestion": {
        "type": "choice",
        "options": [
          {
            "file": "openapi.yaml",
            "line": 142,
            "description": "Make field optional in OpenAPI",
            "current": "required: [source_url, output_format]",
            "proposed": "required: [source_url]"
          },
          {
            "file": "models/transcode.py",
            "line": 23,
            "description": "Make field required in Pydantic",
            "current": "output_format: Optional[str] = None",
            "proposed": "output_format: str"
          }
        ]
      }
    }
  ],
  "metadata": {
    "timestamp": "2024-03-15T14:32:01Z",
    "version": "1.0.0",
    "sources_scanned": {
      "openapi": "openapi.yaml",
      "pydantic": ["models/"],
      "code": ["src/"]
    }
  }
}
```

### SARIF Output (for GitHub Advanced Security)

```bash
spec-check openapi.yaml models/ src/ --output sarif > results.sarif
```

**Output:**
```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "spec-alignment-checker",
          "version": "1.0.0",
          "informationUri": "https://github.com/openclaw/spec-alignment-checker",
          "rules": [
            {
              "id": "TYPE_MISMATCH",
              "shortDescription": {
                "text": "Type mismatch between OpenAPI and code"
              },
              "defaultConfiguration": {
                "level": "error"
              }
            },
            {
              "id": "REQUIRED_MISMATCH",
              "shortDescription": {
                "text": "Required field mismatch"
              },
              "defaultConfiguration": {
                "level": "warning"
              }
            }
          ]
        }
      },
      "results": [
        {
          "ruleId": "TYPE_MISMATCH",
          "level": "error",
          "message": {
            "text": "Field 'job_id': OpenAPI expects string (uuid), Pydantic defines int"
          },
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": {
                  "uri": "models/job.py"
                },
                "region": {
                  "startLine": 15
                }
              }
            }
          ]
        }
      ]
    }
  ]
}
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/spec-check.yml
name: Spec Alignment Check

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  check-specs:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install spec-alignment-checker
        run: |
          pip install spec-alignment-checker
      
      - name: Check spec alignment
        run: |
          spec-check openapi.yaml models/ src/ \
            --output json \
            --output-file spec-check-results.json
      
      - name: Upload results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: spec-check-results
          path: spec-check-results.json
      
      - name: Fail on critical issues
        run: |
          CRITICAL=$(jq '.summary.critical' spec-check-results.json)
          if [ "$CRITICAL" -gt 0 ]; then
            echo "::error::Found $CRITICAL critical spec contradictions"
            spec-check openapi.yaml models/ src/ --severity critical
            exit 1
          fi
      
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('spec-check-results.json'));
            
            if (results.summary.total > 0) {
              const body = `## Spec Alignment Check Results
            
            **${results.summary.total}** contradictions found:
            - ❌ Critical: ${results.summary.critical}
            - ⚠️ High: ${results.summary.high}
            - ℹ️ Medium: ${results.summary.medium}
            
            <details>
            <summary>View details</summary>
            
            \`\`\`
            ${results.contradictions.map(c => 
              `[${c.severity}] ${c.field}: ${c.message}`
            ).join('\n')}
            \`\`\`
            </details>`;
            
              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: body
              });
            }
```

### GitLab CI

```yaml
# .gitlab-ci.yml
spec-check:
  stage: test
  image: python:3.11
  script:
    - pip install spec-alignment-checker
    - spec-check openapi.yaml models/ src/ --output json > spec-check-results.json
    - |
      if [ $(jq '.summary.critical' spec-check-results.json) -gt 0 ]; then
        echo "Critical spec contradictions found!"
        spec-check openapi.yaml models/ src/ --severity critical
        exit 1
      fi
  artifacts:
    reports:
      junit: spec-check-results.json
    paths:
      - spec-check-results.json
    expire_in: 1 week
  allow_failure: false
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/openclaw/spec-alignment-checker
    rev: v1.0.0
    hooks:
      - id: spec-check
        name: Spec Alignment Checker
        entry: spec-check openapi.yaml models/ src/ --fail-on critical
        language: python
        types: [python, yaml]
        pass_filenames: false
```

Or local:

```yaml
repos:
  - repo: local
    hooks:
      - id: spec-check
        name: Spec Alignment Checker
        entry: spec-check openapi.yaml models/ src/ --fail-on critical
        language: system
        pass_filenames: false
```

---

## Advanced Usage

### Watch Mode

```bash
# Continuously check on file changes
spec-check openapi.yaml models/ src/ --watch
```

**Output:**
```
👀 Watching for changes...
  openapi.yaml
  models/
  src/

✓ Initial check passed - no contradictions

[14:32:05] File changed: models/job.py
[14:32:05] Rechecking...

❌ Found 1 contradiction:
  [TYPE_MISMATCH] models/job.py:15
  Field 'job_id': OpenAPI expects string, Pydantic defines int

[14:33:12] File changed: models/job.py
[14:33:12] Rechecking...

✓ Check passed - no contradictions
```

### Configuration File

```bash
# Create config file
spec-check --init
```

**Generated `.spec-check.yaml`:**
```yaml
# Spec Alignment Checker Configuration
# Generated: 2024-03-15

# Source files
openapi: openapi.yaml
models:
  - models/
code:
  - src/
  - handlers/

# Output settings
output: text  # text, json, sarif
output_file: null

# Failure thresholds
fail_on: critical  # critical, high, medium, low, none

# Severity display
severity: all  # all, critical, high, medium, low

# Ignore patterns
ignore:
  - models/legacy_*.py
  - src/deprecated/

# Severity overrides (downgrade known issues)
severity_overrides:
  - field: "LegacyRequest.old_field"
    severity: low
    reason: "Deprecated field, will be removed"

  - pattern: "*_internal"
    severity: low
    reason: "Internal fields not in public API"

# Custom rules
rules:
  # Treat format mismatches as high severity instead of medium
  FORMAT_MISMATCH:
    severity: high
```

```bash
# Use config file
spec-check --config .spec-check.yaml
```

### Filtering by Severity

```bash
# Only show critical issues
spec-check openapi.yaml models/ src/ --severity critical

# Show high and critical
spec-check openapi.yaml models/ src/ --severity high

# Show all (default)
spec-check openapi.yaml models/ src/ --severity all
```

### Exit Codes

```bash
spec-check openapi.yaml models/ src/ --fail-on critical
```

| Condition | Exit Code |
|-----------|-----------|
| No contradictions | 0 |
| Only low/medium issues | 0 (unless --fail-on=medium) |
| High issues (with --fail-on=high) | 1 |
| Critical issues (with --fail-on=critical) | 1 |
| Error during parsing | 2 |
| Invalid arguments | 3 |

---

## Example Catches

### Example 1: Type Mismatch

**OpenAPI:**
```yaml
components:
  schemas:
    JobRequest:
      type: object
      properties:
        job_id:
          type: string
          format: uuid
```

**Pydantic:**
```python
class JobRequest(BaseModel):
    job_id: int  # ❌ Should be str
```

**Detection:**
```bash
$ spec-check openapi.yaml models/ --severity critical

❌ [TYPE_MISMATCH] models/job.py:15
   Field: JobRequest.job_id
   OpenAPI: string (format: uuid)
   Pydantic: int
   
   This will cause: TypeError when UUID string is assigned to int field
```

### Example 2: Required Field Mismatch

**OpenAPI:**
```yaml
components:
  schemas:
    TranscodeRequest:
      type: object
      required:
        - source_url
        - output_format
```

**Pydantic:**
```python
class TranscodeRequest(BaseModel):
    source_url: str
    output_format: Optional[str] = None  # ❌ Marked optional but OpenAPI says required
```

**Detection:**
```bash
$ spec-check openapi.yaml models/

⚠️ [REQUIRED_MISMATCH] models/transcode.py:8
   Field: TranscodeRequest.output_format
   OpenAPI: required
   Pydantic: optional (default: None)
   
   This will cause: API accepts invalid requests
```

### Example 3: Enum Mismatch

**OpenAPI:**
```yaml
components:
  schemas:
    Status:
      type: string
      enum: [pending, processing, completed, failed]
```

**Code:**
```python
class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"  # ❌ Not in OpenAPI enum
    COMPLETED = "completed"
    FAILED = "failed"
```

**Detection:**
```bash
$ spec-check openapi.yaml src/

⚠️ [ENUM_MISMATCH] src/status.py:4
   Enum: Status
   OpenAPI: [pending, processing, completed, failed]
   Code: [pending, running, completed, failed]
   
   Extra in code: 'running'
   Missing in code: 'processing'
   
   This will cause: Validation error when status="running" is serialized
```

### Example 4: Endpoint Mismatch

**OpenAPI:**
```yaml
paths:
  /api/v1/jobs:
    post:
      summary: Create a job
```

**Code:**
```python
@router.post("/api/v1/tasks")  # ❌ Wrong path
def create_job(request: JobRequest):
    ...
```

**Detection:**
```bash
$ spec-check openapi.yaml src/

⚠️ [ENDPOINT_MISMATCH] src/handlers.py:23
   Endpoint: POST /api/v1/tasks
   Not found in OpenAPI spec
   
   Similar endpoints in spec:
     POST /api/v1/jobs
   
   This will cause: 404 errors, endpoint not documented
```

### Example 5: Response Schema Mismatch

**OpenAPI:**
```yaml
paths:
  /api/v1/jobs/{id}:
    get:
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status:
                    type: string
```

**Code:**
```python
@router.get("/api/v1/jobs/{id}")
def get_job(id: str) -> dict:
    return {
        "id": job.id,      # ❌ Should be "job_id"
        "state": job.status  # ❌ Should be "status"
    }
```

**Detection:**
```bash
$ spec-check openapi.yaml src/

⚠️ [RESPONSE_MISMATCH] src/handlers.py:45
   Endpoint: GET /api/v1/jobs/{id}
   Response (200):
   
   Field mismatches:
     - OpenAPI expects 'job_id', code returns 'id'
     - OpenAPI expects 'status', code returns 'state'
   
   This will cause: Client SDK fails to parse response
```

---

## Workflow Examples

### Development Workflow

```bash
# 1. Start development with watch mode in terminal
spec-check openapi.yaml models/ src/ --watch &

# 2. Make changes to models or OpenAPI
vim models/job.py

# 3. Watch mode auto-rechecks and shows issues
# [Output in terminal]

# 4. Fix issues immediately while context is fresh
vim models/job.py  # Fix the contradiction

# 5. Watch mode confirms fix
# ✓ Check passed - no contradictions
```

### PR Review Workflow

```bash
# 1. Developer creates PR
# 2. CI runs spec-check automatically
# 3. If issues found, PR is blocked

# Developer view in terminal:
gh pr checks
# > spec-check: FAIL (critical issues found)

# 4. Developer runs locally to see details
spec-check openapi.yaml models/ src/ --severity critical

# 5. Fix and push
git add .
git commit -m "Fix spec contradiction in JobRequest"
git push

# 6. CI passes, PR approved
```

### Release Workflow

```bash
# 1. Before release, run full check
spec-check openapi.yaml models/ src/ --fail-on medium

# 2. Review any medium/low issues
spec-check openapi.yaml models/ src/ --output json | jq '.contradictions[] | select(.severity=="medium")'

# 3. Document known issues in CHANGELOG
# - Document any accepted spec drift

# 4. Create release tag only if no critical/high issues
```

---

## Tips & Best Practices

### 1. Start with --fail-on critical

Don't overwhelm the team. Start with:
```bash
spec-check openapi.yaml models/ src/ --fail-on critical
```

Gradually increase strictness as you fix existing issues.

### 2. Use severity_overrides for Known Issues

```yaml
# .spec-check.yaml
severity_overrides:
  - field: "LegacyModel.old_field"
    severity: low
    reason: "Deprecated, removing in v2.0"
```

### 3. Run in Pre-commit for Fast Feedback

```yaml
# .pre-commit-config.yaml
hooks:
  - id: spec-check
    entry: spec-check openapi.yaml models/ src/ --fail-on critical
```

Catches issues before they reach CI.

### 4. Use JSON Output for Tooling

```bash
# Generate report for external tool
spec-check openapi.yaml models/ src/ --output json | \
  jq '.contradictions | length'
```

### 5. Document Your Spec Drift Policy

```markdown
# SPEC_POLICY.md

## Acceptable Spec Drift

- **Critical**: Never acceptable - must fix immediately
- **High**: Fix within current sprint
- **Medium**: Document and fix within 30 days
- **Low**: Review quarterly
```
