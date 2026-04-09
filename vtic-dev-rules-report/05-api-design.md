# API Design Rules and Patterns

**Project:** vtic — AI-first ticketing system  
**Source:** openapi.yaml, data-models-stage4-api.md, EXECUTION_PLAN.md

---

## 1. RESTful Design Principles

### Resource-Oriented URLs

```
✅ Resources are nouns, not verbs
✅ Use plural for collections
✅ Hierarchical relationships in path
❌ No verbs in URLs
❌ No actions as endpoints (use HTTP methods)
```

```
# ✅ Good
GET    /tickets              # List all tickets
POST   /tickets              # Create new ticket
GET    /tickets/{id}         # Get specific ticket
PATCH  /tickets/{id}         # Update ticket
DELETE /tickets/{id}         # Delete ticket

# ❌ Bad
GET    /getTicket/{id}       # Verb in URL
POST   /createTicket         # Verb in URL
POST   /updateTicket         # Verb in URL
GET    /ticket/{id}          # Singular (prefer plural)
```

### HTTP Methods

| Method | Action | Idempotent | Safe |
|--------|--------|------------|------|
| GET | Read | Yes | Yes |
| POST | Create | No | No |
| PUT | Replace | Yes | No |
| PATCH | Partial update | No | No |
| DELETE | Remove | Yes | No |

```python
# ✅ Proper method usage
GET    /tickets/{id}         # Read (safe, idempotent)
POST   /tickets              # Create (not idempotent)
PATCH  /tickets/{id}         # Partial update
DELETE /tickets/{id}         # Delete (idempotent)

# ❌ Improper usage
GET    /tickets/{id}/delete  # Using GET for delete
POST   /tickets/{id}         # Using POST for update
```

---

## 2. URL Patterns

### Standard CRUD

```
Collection Operations:
  GET    /tickets              → List tickets (paginated)
  POST   /tickets              → Create ticket

Single Resource Operations:
  GET    /tickets/{id}         → Get ticket
  PATCH  /tickets/{id}         → Update ticket
  DELETE /tickets/{id}         → Delete ticket
```

### Actions as Sub-Resources

```
# ✅ Actions modeled as sub-resources or dedicated endpoints
POST   /tickets/{id}/similar  → Find similar tickets
POST   /tickets/bulk          → Bulk operations
POST   /reindex               → Rebuild search index
GET    /health                → Health check
GET    /stats                 → System statistics
```

### Filtering and Search

```
# ✅ Query parameters for filtering
GET /tickets?repo=ejacklab/vtic&status=open&severity=critical

# ✅ Dedicated search endpoint for complex queries
POST /search
{
  "query": "CORS wildcard",
  "filters": {
    "severity": "critical",
    "status": "open"
  },
  "limit": 10
}

# ✅ Simple search with query string
GET /search?q=CORS&severity=critical
```

---

## 3. Request/Response Patterns

### Create (POST)

**Request:**
```json
POST /tickets
{
  "title": "CORS error on API endpoint",
  "description": "Options request returns 403...",
  "repo": "ejacklab/vtic",
  "category": "bug",
  "severity": "critical"
}
```

**Response (201 Created):**
```json
{
  "id": "B12",
  "title": "CORS error on API endpoint",
  "description": "Options request returns 403...",
  "repo": "ejacklab/vtic",
  "category": "bug",
  "severity": "critical",
  "status": "open",
  "created": "2026-03-19T10:30:00Z",
  "updated": "2026-03-19T10:30:00Z"
}
```

### Update (PATCH)

**Request:**
```json
PATCH /tickets/B12
{
  "status": "in_progress",
  "severity": "high"
}
```

**Response (200 OK):**
```json
{
  "id": "B12",
  "title": "CORS error on API endpoint",
  "status": "in_progress",
  "severity": "high",
  "updated": "2026-03-19T11:00:00Z"
  // ... other fields
}
```

### List with Pagination

**Request:**
```
GET /tickets?limit=20&offset=40&status=open
```

**Response (200 OK):**
```json
{
  "data": [
    {"id": "B12", "title": "...", ...},
    {"id": "B13", "title": "...", ...}
  ],
  "meta": {
    "total": 156,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

---

## 4. Response Envelope

### Standard Envelope Structure

```json
{
  "data": { ... },           // The actual response data
  "meta": { ... }            // Metadata (pagination, etc.)
}
```

### Single Resource Response

```json
{
  "data": {
    "id": "B12",
    "title": "CORS error",
    "status": "open"
  }
}
```

### List Response

```json
{
  "data": [
    {"id": "B12", "title": "..."},
    {"id": "B13", "title": "..."}
  ],
  "meta": {
    "total": 156,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

### Search Response

```json
{
  "data": [
    {
      "ticket_id": "B12",
      "score": 0.95,
      "title": "CORS error...",
      "highlight": "...CORS <mark>wildcard</mark>..."
    }
  ],
  "meta": {
    "total": 5,
    "query": "CORS wildcard",
    "limit": 10,
    "offset": 0
  }
}
```

---

## 5. Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "title",
        "message": "Title must be between 1 and 200 characters"
      },
      {
        "field": "repo",
        "message": "Invalid repository format (expected owner/repo)"
      }
    ]
  }
}
```

### HTTP Status Codes

| Code | When to Use | Example |
|------|-------------|---------|
| 200 | Success | GET /tickets/B12 |
| 201 | Created | POST /tickets |
| 204 | No content | DELETE /tickets/B12 |
| 400 | Bad request | Validation failed |
| 404 | Not found | Ticket doesn't exist |
| 409 | Conflict | Duplicate ID |
| 422 | Unprocessable | Semantic validation failed |
| 500 | Server error | Unexpected exception |

### Error Code Constants

```python
class ErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    SEARCH_ERROR = "SEARCH_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
```

---

## 6. Pagination

### Offset Pagination (Default)

```
GET /tickets?limit=20&offset=40
```

**Parameters:**
- `limit` — items per page (default: 20, max: 100)
- `offset` — items to skip (default: 0)

**Response:**
```json
{
  "data": [...],
  "meta": {
    "total": 156,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

### Cursor Pagination (Future)

```
GET /tickets?limit=20&cursor=abc123
```

**When to use:**
- Large datasets (>10K items)
- Real-time data that changes during pagination
- Need stable ordering across pages

---

## 7. Filtering

### Query Parameter Format

```
# Equality filters
GET /tickets?status=open
GET /tickets?severity=critical&status=open

# Multiple values (OR)
GET /tickets?severity=high,critical

# Range filters
GET /tickets?created_after=2026-01-01&created_before=2026-03-01

# Combined
GET /tickets?repo=ejacklab/vtic&status=open&severity=critical&limit=10
```

### Complex Filters (POST Search)

```json
POST /search
{
  "query": "CORS",
  "filters": {
    "severity": ["high", "critical"],
    "status": ["open", "in_progress"],
    "repo": "ejacklab/vtic"
  },
  "sort": "-created",
  "limit": 20
}
```

---

## 8. Sorting

### Sort Syntax

```
GET /tickets?sort=created              # Ascending
GET /tickets?sort=-created             # Descending (minus prefix)
GET /tickets?sort=severity,-created    # Multiple fields
```

### Valid Sort Fields

```python
VALID_SORT_FIELDS = [
    "created",
    "updated", 
    "severity",
    "status",
    "title",
    "relevance"  # For search results
]
```

---

## 9. Content Negotiation

### JSON (Default)

```
Accept: application/json
```

### Markdown (Raw Ticket)

```
GET /tickets/B12
Accept: text/markdown

Response:
---
id: B12
title: CORS error on API endpoint
repo: ejacklab/vtic
---

Options request returns 403...
```

### Field Selection

```
GET /tickets?fields=id,title,status
```

**Response:**
```json
{
  "data": [
    {"id": "B12", "title": "...", "status": "open"}
  ]
}
```

---

## 10. API Versioning

### URL Path Versioning (Future)

```
/v1/tickets       # Current version
/v2/tickets       # Future version
```

### Deprecation Headers

```http
Deprecation: true
Sunset: Sat, 01 Jan 2027 00:00:00 GMT
Link: </v2/tickets>; rel="successor-version"
```

---

## 11. Rate Limiting (Future)

### Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### Response (429 Too Many Requests)

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "details": [
      {
        "field": null,
        "message": "Retry after: 60 seconds"
      }
    ]
  }
}
```

---

## 12. OpenAPI Specification

### Keep Spec as Canonical Source

The `openapi.yaml` is the **canonical source** for:
- Route definitions
- Request/response schemas
- Error formats
- Query parameters

**Rule:** All code must match the spec exactly. If code and spec disagree, spec wins.

### Spec Structure

```yaml
openapi: 3.1.0
info:
  title: vtic API
  version: 0.1.0

paths:
  /tickets:
    get:
      summary: List tickets
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        200:
          description: List of tickets
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaginatedResponse'

components:
  schemas:
    Ticket:
      type: object
      properties:
        id:
          type: string
          pattern: '^[CFGHST]\\d+$'
        title:
          type: string
          minLength: 1
          maxLength: 200
```

---

## 13. Security (Future)

### Authentication (Not in v0.1)

vtic v0.1 is local-first, single-user. No auth required.

### Future Auth Patterns

```
Authorization: Bearer <token>
```

### API Keys

```
X-API-Key: <api_key>
```

---

## 14. Webhooks (Future)

### Webhook Payload Format

```json
{
  "event": "ticket.created",
  "timestamp": "2026-03-19T10:30:00Z",
  "data": {
    "ticket_id": "B12",
    "title": "CORS error...",
    "url": "https://api.vtic.local/tickets/B12"
  }
}
```

---

## Quick Reference Card

| Aspect | Pattern | Example |
|--------|---------|---------|
| Resources | Plural nouns | `/tickets`, `/users` |
| Actions | HTTP methods | GET, POST, PATCH, DELETE |
| IDs | In path | `/tickets/B12` |
| Filters | Query params | `?status=open&limit=10` |
| Pagination | Limit + offset | `?limit=20&offset=40` |
| Sorting | Field name +/- | `?sort=-created` |
| Search | POST + body | `POST /search {query}` |
| Response | Envelope | `{"data": {}, "meta": {}}` |
| Errors | Structured | `{"error": {code, message, details}}` |

---

## References

- `tmp/vtic/openapi.yaml` — Complete OpenAPI 3.1.1 specification
- `tmp/vtic/data-models-stage4-api.md` — API model definitions
- `tmp/vtic/openapi-stages/` — Staged API evolution
