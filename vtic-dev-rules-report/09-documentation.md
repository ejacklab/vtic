# Documentation Standards

**Project:** vtic — AI-first ticketing system  
**Source:** coding-standards.md, project docs, AGENTS.md

---

## 1. Documentation Philosophy

### Why Document

Documentation serves three purposes:

1. **Communication** — Tell others what this does
2. **Reference** — Help future-you remember how it works
3. **Onboarding** — Reduce time for new contributors

### What to Document

| Type | When | Length |
|------|------|--------|
| **Code comments** | Why, not what | 1-3 lines |
| **Docstrings** | Public APIs, complex functions | 10-50 lines |
| **README** | Project overview | 50-100 lines |
| **Guides** | User tasks | 500-2000 lines |
| **API docs** | Endpoint reference | Per endpoint |
| **Architecture** | Design decisions | 1000+ lines |

### What NOT to Document

- Obvious code (don't explain syntax)
- Dead code (delete it instead)
- Commented-out code (delete it)
- Implementation details that change frequently

---

## 2. Code Comments

### Guidelines

```python
# ✅ Good: Explain WHY, not WHAT
# Zvec returns empty for non-existent IDs instead of raising
# This is by design — we filter None values downstream
results = [r for r in raw_results if r is not None]

# ❌ Bad: State the obvious
x = x + 1  # Increment x by 1

# ❌ Bad: Commented-out code
# old_code = "deprecated"
# if old_code:
#     return None
```

### Section Headers

```python
# ───────────────────────────────────────
# Search query building
# ───────────────────────────────────────
query = build_query(filters)

# ───────────────────────────────────────
# Index operations
# ───────────────────────────────────────
await index.upsert(ticket)
```

### TODO Comments

```python
# TODO(ejack): Add pagination for >1000 results
# See: https://github.com/ejacklab/vtic/issues/42

# FIXME(kimi): Zvec returns None on timeout
# Workaround: retry with exponential backoff
```

---

## 3. Docstrings

### Google Style Format

```python
def search_tickets(
    query: str,
    filters: FilterSet | None = None,
    limit: int = 10,
) -> SearchResult:
    """Search tickets using BM25 + optional semantic search.
    
    Performs full-text search across ticket titles and descriptions
    using BM25 ranking, with optional semantic search for related
    results when an embedding provider is configured.
    
    Args:
        query: Search query string. Supports:
            - Single words: "CORS"
            - Phrases: '"CORS wildcard"'
            - Exclusions: "CORS -production"
        filters: Optional filters to narrow results.
            - severity: Filter by severity level
            - status: Filter by ticket status
            - repo: Filter by repository
        limit: Maximum number of results (1-100, default: 10)
        
    Returns:
        SearchResult containing:
            - hits: List of matching tickets with scores
            - total: Total number of matches
            - meta: Query metadata (took, search_type)
        
    Raises:
        ValidationError: If query is empty or limit out of range
        SearchError: If search index is unavailable
        
    Example:
        >>> results = await search_tickets("CORS")
        >>> len(results.hits)
        5
        >>> results.hits[0].score
        0.95
    """
```

### Module Docstrings

```python
"""Ticket storage module.

Provides async read/write operations for ticket markdown files
stored in a hierarchical directory structure:
    tickets/{owner}/{repo}/{category}/{id}.md

All operations use atomic writes (temp file + rename) to prevent
corruption on system crashes.

Example:
    >>> from vtic.store import write_ticket, read_ticket
    >>> await write_ticket(ticket, path)
    >>> loaded = await read_ticket(path)
"""
```

### Class Docstrings

```python
class TicketService:
    """Orchestrates ticket CRUD operations across storage layers.
    
    Coordinates between the markdown store (source of truth) and
    the Zvec index (for search) to ensure consistency.
    
    Attributes:
        store: MarkdownStore instance for file operations
        index: ZvecIndex instance for search operations
        
    Example:
        >>> service = TicketService(store, index)
        >>> ticket = await service.create(TicketCreate(...))
        >>> results = await service.search("CORS")
    """
```

---

## 4. README Structure

### Required Sections

```markdown
# vtic

AI-first ticketing system with hybrid search.

## Quick Start

```bash
pip install vtic
vtic init
vtic serve
```

## Features

- CRUD operations for tickets
- Hybrid BM25 + semantic search
- Markdown storage with Git compatibility
- REST API + CLI

## Installation

[Installation instructions]

## Usage

[Basic usage examples]

## Configuration

[Configuration options]

## API Reference

[Link to API docs]

## License

MIT
```

### README Guidelines

- Keep it short (1-2 pages max)
- Focus on getting started
- Link to detailed docs
- Include badges for CI, coverage, version

---

## 5. API Documentation

### OpenAPI as Source of Truth

```yaml
# openapi.yaml — Canonical API documentation
paths:
  /tickets:
    post:
      summary: Create a new ticket
      description: |
        Creates a new ticket in the specified repository.
        The ticket ID is auto-generated based on category.
      operationId: createTicket
      tags:
        - Tickets
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TicketCreate'
            example:
              title: "CORS error"
              repo: "ejacklab/vtic"
              severity: critical
      responses:
        201:
          description: Ticket created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Ticket'
        400:
          $ref: '#/components/responses/ValidationError'
        500:
          $ref: '#/components/responses/InternalError'
```

### Per-Endpoint Docs

```
docs/
└── api/
    └── endpoints/
        ├── tickets.md
        ├── search.md
        └── system.md
```

```markdown
# POST /tickets

Create a new ticket.

## Request

```json
{
  "title": "Bug in login",
  "repo": "ejacklab/vtic",
  "category": "bug",
  "severity": "high"
}
```

## Response

**201 Created**
```json
{
  "id": "B1",
  "title": "Bug in login",
  "repo": "ejacklab/vtic",
  "status": "open",
  "created": "2026-03-19T10:30:00Z"
}
```

## Errors

| Status | Code | Description |
|--------|------|-------------|
| 400 | VALIDATION_ERROR | Invalid input |
| 500 | INTERNAL_ERROR | Server error |
```

---

## 6. Architecture Documentation

### Design Doc Structure

```markdown
# Architecture Decision Record: ADR-001

## Title
Use Markdown as Source of Truth

## Status
Accepted

## Context
We need persistent storage for tickets that is:
- Human-readable
- Git-compatible
- Fast to search

## Decision
Store tickets as Markdown files with YAML frontmatter.
Use Zvec for search indexing.

## Consequences
### Positive
- Git diff works naturally
- Human can read/edit files
- Can rebuild index from files

### Negative
- Dual write required
- Need to keep in sync

## Related
- ADR-002: Use Zvec for indexing
- ADR-003: Async all the way
```

### Data Flow Diagrams

```markdown
# Data Flow: Create Ticket

```
User → API → TicketService → MarkdownStore
                      ↓
                   ZvecIndex
```

1. User sends POST /tickets
2. API validates request
3. TicketService generates ID
4. MarkdownStore writes file
5. ZvecIndex indexes ticket
6. Response returned to user
```

---

## 7. User Guides

### Guide Structure

```
docs/guides/
├── getting-started.md
├── configuration.md
├── troubleshooting.md
└── recipes/
    ├── bulk-import.md
    └── scripting.md
```

### Getting Started Guide

```markdown
# Getting Started with vtic

## Prerequisites

- Python 3.10+
- pip or uv

## Installation

```bash
pip install vtic
```

## Initialize

```bash
vtic init
```

This creates:
- `tickets/` directory
- `.vtic/` index directory
- `vtic.toml` config file

## Create Your First Ticket

```bash
vtic create --title "My first ticket" --repo "me/project"
```

## Start the API

```bash
vtic serve
```

Visit http://localhost:8000/docs for API docs.
```

---

## 8. Changelog

### Keep a Changelog Format

```markdown
# Changelog

All notable changes are documented here.

## [0.1.0] - 2026-03-19

### Added
- CRUD operations for tickets
- BM25 search
- REST API with FastAPI
- CLI with Typer

### Changed
- Improved error messages

### Fixed
- Race condition in index updates
```

---

## 9. Inline Documentation Rules

### What to Document in Code

| Element | Document |
|---------|----------|
| Module | Purpose, key classes, usage example |
| Class | Purpose, attributes, usage |
| Public method | Parameters, return, exceptions, example |
| Complex function | Non-obvious logic, algorithms |
| Constants | Why this value, where it comes from |

### What NOT to Document

- Private methods (unless non-obvious)
- Simple getters/setters
- Obvious control flow
- Type hints that are self-explanatory

---

## 10. Documentation Maintenance

### Update Docs with Code

**Rule:** When you change behavior, update the docs.

```
1. Change code
2. Update tests
3. Update docs ← Don't forget this!
4. Commit together
```

### Deprecation Notices

```python
def old_function():
    """Deprecated: Use new_function instead.
    
    .. deprecated::
        Version 0.2. Will be removed in 0.4.
    """
    ...
```

```markdown
# Changelog

## [Unreleased]

### Deprecated
- `old_function()` - Use `new_function()` instead (removed in 0.4)
```

---

## Quick Reference Card

| Type | Location | Style |
|------|----------|-------|
| Code comments | Inline | Why not what |
| Docstrings | Modules, classes, functions | Google format |
| README | Project root | 50-100 lines |
| API docs | openapi.yaml + docs/ | OpenAPI spec |
| Guides | docs/guides/ | Task-oriented |
| Changelog | CHANGELOG.md | Keep a Changelog |

---

## References

- `rules/coding-standards.md` — Documentation rules
- `tmp/vtic/README.md` — Reference README
- `tmp/vtic/openapi.yaml` — API documentation
