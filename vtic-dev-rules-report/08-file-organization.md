# File Organization and Project Structure

**Project:** vtic — AI-first ticketing system  
**Source:** coding-standards.md, EXECUTION_PLAN.md, BUILD_PLAN.md

---

## 1. Project Structure Rules

### Max 5 Levels Deep

Files must not be placed randomly at the project root. Use a clean, logical folder structure.

```
✅ Maximum 5 levels from project root
✅ project/src/tools/my-tool/handlers/create.ts (5 levels)
❌ project/src/tools/my-tool/handlers/sub-handlers/create.ts (6 levels)
```

### Structure by Domain, Not File Type

```
✅ Good: Group by feature/domain
vtic/
├── src/
│   ├── models/          # Data models
│   ├── store/           # Storage layer
│   ├── search/          # Search functionality
│   └── api/             # HTTP layer
└── tests/
    ├── unit/
    └── integration/

❌ Bad: Group by file type
vtic/
├── src/
│   ├── classes/
│   ├── functions/
│   ├── constants/
│   └── utils/
```

---

## 2. vtic Project Structure

```
vtic/                              # Project root
├── src/                           # Level 1: Source code
│   └── vtic/                     # Level 2: Package
│       ├── __init__.py           # Package exports
│       ├── models/               # Level 3: Domain modules
│       │   ├── __init__.py
│       │   ├── enums.py         # Enumerations
│       │   ├── ticket.py        # Ticket models
│       │   ├── search.py        # Search models
│       │   └── api.py           # API response models
│       ├── store/                # Level 3: Storage layer
│       │   ├── __init__.py
│       │   ├── markdown.py      # Markdown operations
│       │   └── paths.py         # Path utilities
│       ├── index/                # Level 3: Search index
│       │   ├── __init__.py
│       │   ├── client.py        # Zvec client
│       │   ├── schema.py        # Index schema
│       │   └── operations.py    # Index operations
│       ├── search/               # Level 3: Search engine
│       │   ├── __init__.py
│       │   ├── bm25.py         # BM25 implementation
│       │   └── engine.py        # Search orchestrator
│       ├── api/                  # Level 3: HTTP layer
│       │   ├── __init__.py
│       │   ├── app.py          # FastAPI app
│       │   ├── deps.py         # Dependencies
│       │   └── routes/          # Level 4: Route modules
│       │       ├── __init__.py
│       │       ├── tickets.py
│       │       ├── search.py
│       │       └── system.py
│       ├── cli/                  # Level 3: CLI
│       │   ├── __init__.py
│       │   └── main.py          # Typer app
│       └── errors.py            # Error definitions
├── tests/                        # Level 1: Tests
│   ├── conftest.py              # Pytest fixtures
│   ├── unit/                    # Level 2: Unit tests
│   │   ├── test_models.py
│   │   ├── test_store.py
│   │   └── test_search.py
│   ├── integration/              # Level 2: Integration tests
│   │   ├── test_api_tickets.py
│   │   └── test_api_search.py
│   └── performance/              # Level 2: Benchmarks
│       └── test_benchmarks.py
├── docs/                         # Level 1: Documentation
│   ├── api/
│   └── guides/
├── pyproject.toml               # Project config
├── pyproject.toml               # uv configuration
├── vtic.toml                    # Default config
├── .gitignore
├── LICENSE
└── README.md
```

---

## 3. Source Code Organization

### Package Layout

```
src/vtic/                    # Root package
├── __init__.py             # Public API exports
│                           
│   # Sub-packages (domain grouping)
├── models/                  # Data models
├── store/                   # Persistence layer
├── index/                   # Vector index
├── search/                  # Search logic
├── api/                     # HTTP interface
├── cli/                     # CLI interface
│
│   # Single-file modules (utility)
├── errors.py               # Exceptions
├── config.py               # Configuration
└── version.py              # Version info
```

### Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `models/` | Pydantic models, enums, data types |
| `store/` | Read/write markdown files |
| `index/` | Zvec index operations |
| `search/` | Search logic (BM25, hybrid) |
| `api/` | FastAPI routes, request handling |
| `cli/` | Typer command definitions |
| `errors.py` | Exception classes, error codes |
| `config.py` | Configuration loading |

---

## 4. Test Organization

### Co-located vs Dedicated

**Rule:** Put tests next to the code they test OR in a dedicated `tests/` mirror.

```
# Option 1: Co-located (some projects prefer)
src/vtic/
├── models/
│   ├── ticket.py
│   └── ticket_test.py    # Next to source

# Option 2: Dedicated (vtic uses this)
tests/
├── unit/
│   ├── test_models.py   # Mirrors src structure
│   ├── test_store.py
│   └── test_search.py
```

### Test Directory Structure

```
tests/
├── conftest.py              # Shared fixtures for all tests
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_models.py      # Test models
│   ├── test_store.py       # Test storage
│   ├── test_index.py       # Test index
│   └── test_search.py      # Test search
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── test_api.py        # Test HTTP layer
│   ├── test_service.py     # Test service layer
│   └── test_lifecycle.py  # Test full workflows
└── performance/             # Performance tests
    ├── __init__.py
    └── test_benchmarks.py
```

---

## 5. Configuration Files

### Root Level Config

```
vtic/                       # Project root
├── pyproject.toml          # Dependencies + project metadata
├── vtic.toml               # Default runtime config
├── .gitignore              # Git exclusions
├── .env.example            # Env var template (never commit .env!)
├── LICENSE                 # MIT license
├── README.md               # Project overview
└── CHANGELOG.md            # Version history
```

### Config Precedence

```
1. Environment variables (highest priority)
2. Project config (./vtic.toml)
3. Global config (~/.config/vtic/config.toml)
4. Defaults (lowest priority)
```

### Environment-Specific Files

```
.env                       # Never commit! Contains secrets
.env.local                # Local overrides, never commit
.env.example              # Template for .env
```

---

## 6. Documentation Organization

### docs/ Directory

```
docs/
├── api/                    # API documentation
│   ├── openapi.yaml       # OpenAPI spec (source of truth)
│   └── endpoints/         # Per-endpoint docs
│       ├── tickets.md
│       └── search.md
├── guides/                 # User guides
│   ├── getting-started.md
│   ├── configuration.md
│   └── troubleshooting.md
├── architecture/           # Developer docs
│   ├── overview.md
│   ├── data-flow.md
│   └── decisions/          # ADRs
│       └── 001-use-markdown-storage.md
└── CONTRIBUTING.md        # Contribution guidelines
```

---

## 7. Temporary Files

### Workspace-Local Temp Files

**Critical Rule:** Never use `/tmp` for anything you need to keep.

```python
# ❌ Never do this
/path/to/tmp/design-doc.md  # Will be wiped by system cleanup!

# ✅ Always use workspace-relative temp
workspace/tmp/vtic/design-doc.md  # Survives session restarts
```

### Temp Directory Structure

```
workspace/
├── src/
├── tests/
├── tmp/                        # Temporary files
│   └── vtic/                   # vtic-specific temp
│       ├── design-doc-1.md     # Versioned temp files
│       ├── design-doc-2.md
│       └── tickets/            # Ticket test data
│           └── test-repo/
└── vtic-dev-rules-report/      # Generated reports
```

---

## 8. Ticket Storage Structure

### Directory Layout

```
tickets/                              # Ticket root
├── {owner}/                         # Level 1: Owner
│   └── {repo}/                     # Level 2: Repository
│       ├── bug/                    # Level 3: Category
│       │   ├── B1.md              # Level 4: Ticket files
│       │   ├── B2.md
│       │   └── B3.md
│       ├── feature/                # Level 3: Category
│       │   ├── F1.md
│       │   └── F2.md
│       ├── security/              # Level 3: Category
│       │   └── S1.md
│       └── .trash/                # Soft-deleted tickets
│           ├── B10.md
│           └── F5.md
└── .vtic/                          # Index directory
    └── index.zvec                  # Zvec database
```

### Ticket File Format

```markdown
# tickets/{owner}/{repo}/{category}/{id}.md

---
id: B1
title: CORS error on API endpoint
repo: ejacklab/vtic
category: bug
severity: critical
status: open
created: 2026-03-19T10:30:00Z
updated: 2026-03-19T10:30:00Z
tags: [api, cors, security]
related: [F1, S2]
---

## Description

The CORS headers are not being set correctly...

## Steps to Reproduce

1. Make an OPTIONS request to `/api/tickets`
2. Observe missing `Access-Control-Allow-Origin` header
```

---

## 9. Shared Utilities

### When to Create a Utility Module

```
✅ Create when:
- Code is used in 3+ places
- Function is well-defined and stable
- It has no external dependencies

❌ Don't create when:
- It's a one-off helper
- It has complex dependencies
- It needs to be customized per call site
```

### Utility Module Structure

```
src/vtic/utils/
├── __init__.py
├── markdown.py          # Markdown parsing/serialization
├── paths.py             # Path manipulation
├── time.py              # Date/time utilities
└── validators.py        # Validation helpers
```

---

## 10. Anti-Patterns

### ❌ Flat Directory

```
❌ project/
    a.py
    b.py
    c.py
    helpers.py
    utils.py
    constants.py
```

### ❌ Deep Nesting

```
❌ project/
    src/
        modules/
            features/
                ticket/
                    handlers/
                        create/
                            create_handler.py
```

### ❌ Mixed File Types

```
❌ project/
    src/
        ticket_model.py    # Model
        ticket_routes.py   # Route
        ticket_store.py    # Store
        ticket_utils.py    # Utilities
```

### ❌ Utility Hell

```
❌ project/
    utils/
        string_utils.py
        list_utils.py
        dict_utils.py
        math_utils.py
        date_utils.py
        file_utils.py
        path_utils.py
        url_utils.py
        ...
```

---

## 11. Import Organization

### Import Order

```python
# 1. Standard library (alphabetical)
import asyncio
from pathlib import Path
from typing import Optional

# 2. Third-party
import aiofiles
from fastapi import FastAPI
from pydantic import BaseModel

# 3. Local imports (absolute, then relative)
from vtic.models import Ticket
from vtic.errors import VticError

# 4. Relative imports within package
from .models import TicketCreate
from ..store import MarkdownStore
```

### Relative vs Absolute Imports

```python
# ✅ Within same package: relative
from .models import TicketCreate
from .errors import VticError

# ✅ Cross packages: absolute
from vtic.models import TicketCreate
from vtic.store import MarkdownStore

# ❌ Confusing mixed style
from . import errors
from vtic import models
```

---

## Quick Reference Card

| Aspect | Rule |
|--------|------|
| Max depth | 5 levels from project root |
| Grouping | By domain/feature, not file type |
| Tests | Dedicated `tests/` directory or co-located |
| Config | Root level, with precedence: env > project > global |
| Temp files | Workspace-relative, never `/tmp` |
| Utilities | Only when used 3+ times |
| Imports | stdlib > third-party > local, alphabetical |

---

## References

- `rules/coding-standards.md` — Section 3 (Project Structure)
- `tmp/vtic/src/vtic/` — Reference implementation
- `tmp/vtic/pyproject.toml` — Dependency config
