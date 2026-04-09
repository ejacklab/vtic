# Coding Conventions

**Project:** vtic — AI-first ticketing system  
**Source:** rules/coding-standards.md

---

## 1. Type Safety

### Python Type Hints

All Python code must use type hints:

```python
# ✅ Good
def create_ticket(data: TicketCreate, config: Config) -> Ticket:
    ...

# ❌ Bad
def create_ticket(data, config):
    ...
```

### Pydantic Models

Use Pydantic v2 for all data validation:

```python
from pydantic import BaseModel, Field

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    repo: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$")
    severity: Severity = Severity.medium
```

### No Any/Unknown

```python
# ❌ Never do this
def process(data: Any) -> Any:
    ...

# ✅ Always use proper types
def process(data: TicketCreate) -> Ticket:
    ...
```

### Optional/Union Types

```python
# ✅ Python 3.10+ syntax
from __future__ import annotations

def find_ticket(ticket_id: str | None) -> Ticket | None:
    ...

# ✅ Or explicit Optional
from typing import Optional

def find_ticket(ticket_id: Optional[str]) -> Optional[Ticket]:
    ...
```

---

## 2. Code Quality Standards

### Meaningful Names

```python
# ❌ Bad
fn()
get_data()
val

# ✅ Good
get_user_by_id()
fetch_ticket_by_id()
total_ticket_count
```

### Function Naming

| Operation | Prefix | Example |
|-----------|--------|---------|
| Retrieve | `get_`, `fetch_` | `get_ticket()`, `fetch_user()` |
| Create | `create_` | `create_ticket()` |
| Update | `update_`, `patch_` | `update_ticket()` |
| Delete | `delete_`, `remove_` | `delete_ticket()` |
| Check | `is_`, `has_` | `is_valid()`, `has_permission()` |
| Transform | `to_`, `from_` | `to_markdown()`, `from_dict()` |

### Variable Naming

```python
# ✅ Use descriptive names
ticket_file_path = Path(tickets_dir) / f"{ticket_id}.md"
search_query = SearchQuery(query="CORS", limit=10)

# ❌ Avoid abbreviations
fp = Path(td) / f"{tid}.md"  # What is fp? tid?
```

### Constants

```python
# ✅ Uppercase with underscores
MAX_TITLE_LENGTH = 200
DEFAULT_SEARCH_LIMIT = 10
VALID_CATEGORIES = ["bug", "feature", "security", "performance"]

# ❌ Not camelCase or lowercase
maxTitleLength = 200  # Wrong
default_limit = 10    # Wrong
```

---

## 3. Error Handling

### Custom Exceptions

```python
# ✅ Define domain-specific exceptions
class VticError(Exception):
    """Base exception for vtic."""
    pass

class TicketNotFoundError(VticError):
    """Ticket ID does not exist."""
    pass

class ValidationError(VticError):
    """Input validation failed."""
    pass
```

### Explicit Error Handling

```python
# ✅ Handle errors explicitly
try:
    ticket = await store.read_ticket(ticket_id)
except FileNotFoundError:
    raise TicketNotFoundError(f"Ticket {ticket_id} not found")
except PermissionError:
    raise VticError(f"Permission denied reading {ticket_id}")

# ❌ Don't swallow exceptions
try:
    ticket = await store.read_ticket(ticket_id)
except Exception:  # Too broad!
    return None
```

### Error Response Format

```python
class ErrorDetail(BaseModel):
    field: str | None = None
    message: str

class ErrorObject(BaseModel):
    code: str  # VALIDATION_ERROR, NOT_FOUND, etc.
    message: str
    details: list[ErrorDetail] = []

class ErrorResponse(BaseModel):
    error: ErrorObject
```

---

## 4. Async Patterns

### Consistent Async/Await

```python
# ✅ All I/O is async
async def create_ticket(data: TicketCreate) -> Ticket:
    # Write to markdown (async file I/O)
    await store.write_ticket(ticket)
    
    # Index in Zvec
    await index.upsert_ticket(ticket)
    
    return ticket

# ❌ Mixing sync and async
def create_ticket(data: TicketCreate) -> Ticket:
    store.write_ticket(ticket)  # Blocking!
    index.upsert_ticket(ticket)  # Blocking!
    return ticket
```

### Async Context Managers

```python
# ✅ Proper async resource management
async with zvec.open_collection("tickets") as collection:
    results = await collection.query(...)

# ❌ Missing context manager
collection = zvec.open_collection("tickets")  # Resource leak risk
results = collection.query(...)  # May not be properly closed
```

---

## 5. Docstrings

### Google Style Docstrings

```python
def search_tickets(
    query: str,
    filters: FilterSet | None = None,
    limit: int = 10,
) -> SearchResult:
    """Search tickets using BM25 + optional semantic search.
    
    Args:
        query: Search query string. Empty queries return empty results.
        filters: Optional filters to apply (severity, status, category, repo).
        limit: Maximum number of results (1-100).
        
    Returns:
        SearchResult containing hits, total count, and metadata.
        
    Raises:
        ValidationError: If query is invalid or limit out of range.
        SearchError: If search index is unavailable.
        
    Example:
        >>> results = await search_tickets("CORS", filters={"severity": "critical"})
        >>> len(results.hits)
        5
    """
```

### Module Docstrings

```python
"""Ticket storage module.

Provides async read/write operations for ticket markdown files.
All operations use atomic writes (temp file + rename) to prevent corruption.

Example:
    >>> from vtic.store import write_ticket, read_ticket
    >>> await write_ticket(ticket, path)
    >>> loaded = await read_ticket(path)
"""
```

---

## 6. Imports

### Import Order

```python
# 1. Standard library
import asyncio
from pathlib import Path
from typing import Optional

# 2. Third-party
import aiofiles
from fastapi import FastAPI
from pydantic import BaseModel

# 3. Local imports
from vtic.models import Ticket
from vtic.errors import VticError
```

### Import Styles

```python
# ✅ Preferred: explicit imports
from vtic.models import Ticket, TicketCreate, TicketUpdate

# ✅ Acceptable for large modules
from vtic import models

# ❌ Avoid wildcard imports
from vtic.models import *  # Pollutes namespace
```

---

## 7. Code Organization

### Function Length

```python
# ✅ Keep functions focused (< 50 lines)
async def create_ticket(data: TicketCreate) -> Ticket:
    """Create a new ticket."""
    ticket = _build_ticket(data)
    await _persist_ticket(ticket)
    return ticket

# Helper functions for sub-tasks
def _build_ticket(data: TicketCreate) -> Ticket:
    ...

async def _persist_ticket(ticket: Ticket) -> None:
    ...
```

### Class Organization

```python
class TicketService:
    """Orchestrates ticket CRUD operations."""
    
    # 1. Class variables
    DEFAULT_PAGE_SIZE = 20
    
    # 2. __init__
    def __init__(self, store: Store, index: Index):
        self._store = store
        self._index = index
    
    # 3. Public methods (alphabetical)
    async def create(self, data: TicketCreate) -> Ticket:
        ...
    
    async def delete(self, ticket_id: str) -> None:
        ...
    
    async def get(self, ticket_id: str) -> Ticket | None:
        ...
    
    async def update(self, ticket_id: str, data: TicketUpdate) -> Ticket:
        ...
    
    # 4. Private methods
    def _validate_id(self, ticket_id: str) -> None:
        ...
```

---

## 8. Comments

### When to Comment

```python
# ✅ Explain WHY, not WHAT
# Zvec returns empty array for non-existent IDs instead of raising
# This is by design — we filter out None values downstream
results = [r for r in raw_results if r is not None]

# ❌ Don't state the obvious
x = x + 1  # Increment x by 1  (No!)
```

### Comment Format

```python
# ✅ Single line comments use hash-space
count = 0  # Counter for processed tickets

# ✅ Section headers for logical blocks
# ───────────────────────────────────────
# Search query building
# ───────────────────────────────────────
query = build_query(filters)

# ✅ TODO comments with context
# TODO(ejack): Add pagination support for >1000 results
# See: https://github.com/ejacklab/vtic/issues/42
```

---

## 9. String Formatting

### f-strings for Simple Cases

```python
# ✅ f-strings
path = f"{owner}/{repo}/{category}/{ticket_id}.md"
message = f"Ticket {ticket_id} created successfully"

# ❌ Old-style formatting
path = "%s/%s/%s/%s.md" % (owner, repo, category, ticket_id)
```

### Template Strings for Complex Cases

```python
from string import Template

# ✅ Template for reusable patterns
ticket_template = Template("""---
id: $id
title: $title
repo: $repo
created: $created
---

$description
""")

content = ticket_template.substitute(
    id=ticket.id,
    title=ticket.title,
    repo=ticket.repo,
    created=ticket.created.isoformat(),
    description=ticket.description,
)
```

---

## 10. Anti-Patterns

### ❌ Dead Code

```python
# Remove unused imports, variables, and commented-out blocks
import json  # Never used — delete it!

def process(data):
    result = data  # result never used
    # old_code = "deprecated"
    # if old_code:
    #     return None
    return data
```

### ❌ Magic Numbers

```python
# ❌ Bad
def paginate(items):
    return items[:20]  # Why 20?

# ✅ Good
DEFAULT_PAGE_SIZE = 20

def paginate(items):
    return items[:DEFAULT_PAGE_SIZE]
```

### ❌ Nested Conditionals

```python
# ❌ Hard to follow
def can_edit(user, ticket):
    if user:
        if user.is_active:
            if ticket:
                if ticket.status != "closed":
                    return True
    return False

# ✅ Flatten with early returns
def can_edit(user, ticket):
    if not user or not user.is_active:
        return False
    if not ticket:
        return False
    if ticket.status == "closed":
        return False
    return True
```

---

## Completion Checklist

Before marking code complete:

- [ ] Type hints on all functions
- [ ] No `Any` or `Unknown` types
- [ ] Meaningful variable/function names
- [ ] Docstrings on public APIs
- [ ] Proper error handling
- [ ] Async/await consistency
- [ ] No dead code or unused imports
- [ ] Passes `mypy --strict` (if configured)
- [ ] Passes `ruff` or `black` formatting

---

## References

- `rules/coding-standards.md` — Section 4 (Code Quality)
- `tmp/vtic/src/vtic/` — Reference implementation
- <https://docs.python.org/3/library/typing.html> — Python typing docs
