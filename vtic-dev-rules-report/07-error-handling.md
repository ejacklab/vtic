# Error Handling and Validation Patterns

**Project:** vtic — AI-first ticketing system  
**Source:** coding-standards.md, data-models-stage6-errors-map.md, vtic codebase

---

## 1. Error Handling Philosophy

### Explicit Over Implicit

Every function that can fail should handle errors explicitly:

```python
# ✅ Explicit error handling
async def get_ticket(ticket_id: str) -> Ticket:
    try:
        data = await store.read(ticket_id)
    except FileNotFoundError:
        raise TicketNotFoundError(f"Ticket {ticket_id} not found")
    except PermissionError:
        raise VticError(f"Permission denied reading {ticket_id}")
    
    return Ticket.parse_raw(data)

# ❌ Swallowing exceptions
def get_ticket(ticket_id):
    try:
        return store.read(ticket_id)
    except Exception:  # Too broad!
        return None
```

### Fail Fast

Validate inputs at the boundary:

```python
# ✅ Fail fast with validation
@router.post("/tickets")
async def create_ticket(data: TicketCreate) -> Ticket:
    # Pydantic validates TicketCreate before this runs
    ticket = await service.create(data)
    return ticket

# ❌ Late validation
async def create_ticket(data: dict) -> Ticket:
    # Who knows what's in data?
    if "title" not in data:  # Validation too late
        raise Error(...)
```

---

## 2. Exception Hierarchy

### Base Exception

```python
class VticError(Exception):
    """Base exception for all vtic errors."""
    pass
```

### Specific Exceptions

```python
class TicketNotFoundError(VticError):
    """Ticket ID does not exist."""
    pass

class TicketAlreadyExistsError(VticError):
    """Ticket ID already exists."""
    pass

class ValidationError(VticError):
    """Input validation failed."""
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field

class SearchError(VticError):
    """Search operation failed."""
    pass

class ConfigError(VticError):
    """Configuration error."""
    pass

class StoreError(VticError):
    """Storage operation failed."""
    pass

class IndexError(VticError):
    """Index operation failed."""
    pass
```

---

## 3. Error Response Format

### Standard Error Structure

```python
from pydantic import BaseModel
from typing import Optional

class ErrorDetail(BaseModel):
    """Detailed error information for a specific field."""
    field: Optional[str] = None
    message: str

class ErrorObject(BaseModel):
    """Standard error object."""
    code: str
    message: str
    details: list[ErrorDetail] = []

class ErrorResponse(BaseModel):
    """Standard error response wrapper."""
    error: ErrorObject
```

### Error Code Constants

```python
class ErrorCode:
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    REQUIRED_FIELD = "REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_VALUE = "INVALID_VALUE"
    
    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    
    # Search errors
    SEARCH_ERROR = "SEARCH_ERROR"
    EMPTY_QUERY = "EMPTY_QUERY"
    
    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    STORE_ERROR = "STORE_ERROR"
    INDEX_ERROR = "INDEX_ERROR"
```

### Example Error Responses

```json
// Validation error
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
        "message": "Invalid format (expected owner/repo)"
      }
    ]
  }
}

// Not found error
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Ticket B999 not found",
    "details": []
  }
}

// Search error
{
  "error": {
    "code": "EMPTY_QUERY",
    "message": "Search query cannot be empty",
    "details": [
      {
        "field": "query",
        "message": "Query must contain at least one character"
      }
    ]
  }
}
```

---

## 4. HTTP Status Code Mapping

| Error Code | HTTP Status | When to Use |
|------------|-------------|-------------|
| VALIDATION_ERROR | 400 | Request format or content is invalid |
| REQUIRED_FIELD | 400 | Required field is missing |
| INVALID_FORMAT | 400 | Field format doesn't match pattern |
| NOT_FOUND | 404 | Resource doesn't exist |
| ALREADY_EXISTS | 409 | Resource already exists (conflict) |
| EMPTY_QUERY | 400 | Search query is empty |
| SEARCH_ERROR | 500 | Search index error |
| CONFIG_ERROR | 500 | Configuration is invalid |
| STORE_ERROR | 500 | File system error |
| INDEX_ERROR | 500 | Vector index error |
| INTERNAL_ERROR | 500 | Unexpected error |

### FastAPI Exception Handlers

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(VticError)
async def vtic_error_handler(request: Request, exc: VticError):
    """Handle all vtic errors."""
    
    if isinstance(exc, TicketNotFoundError):
        status_code = 404
        code = "NOT_FOUND"
    elif isinstance(exc, ValidationError):
        status_code = 400
        code = "VALIDATION_ERROR"
    elif isinstance(exc, SearchError):
        status_code = 500
        code = "SEARCH_ERROR"
    else:
        status_code = 500
        code = "INTERNAL_ERROR"
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc),
                "details": getattr(exc, "details", [])
            }
        }
    )

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": []
            }
        }
    )
```

---

## 5. Validation Patterns

### Pydantic Model Validation

```python
from pydantic import BaseModel, Field, validator

class TicketCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Ticket title"
    )
    repo: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$",
        description="Repository (owner/repo)"
    )
    severity: Severity = Field(
        default=Severity.medium
    )
    
    @validator("title")
    def title_not_whitespace(cls, v):
        if v.strip() != v:
            raise ValueError("Title cannot start or end with whitespace")
        return v
```

### Custom Validators

```python
from pydantic import validator
import re

VALID_ID_PATTERN = re.compile(r"^[CFGHST]\\d+$")

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[Status] = None
    
    @root_validator
    def at_least_one_field(cls, values):
        """Ensure at least one field is being updated."""
        if not any(v is not None for v in values.values()):
            raise ValueError("At least one field must be provided for update")
        return values

def validate_ticket_id(ticket_id: str) -> None:
    """Validate ticket ID format."""
    if not VALID_ID_PATTERN.match(ticket_id):
        raise ValidationError(
            f"Invalid ticket ID format: {ticket_id}",
            field="ticket_id"
        )
```

### Service-Level Validation

```python
class TicketService:
    async def create(self, data: TicketCreate) -> Ticket:
        # Validate repo exists (if we had repo registry)
        if not await self._repo_exists(data.repo):
            raise ValidationError(
                f"Repository {data.repo} not found",
                field="repo"
            )
        
        # Generate ID
        ticket_id = await self._generate_id(data.category)
        
        # Check for duplicates (shouldn't happen with generated IDs)
        if await self._exists(ticket_id):
            raise TicketAlreadyExistsError(f"Ticket {ticket_id} already exists")
        
        # Create ticket
        ticket = Ticket(id=ticket_id, **data.dict())
        await self._store.write(ticket)
        await self._index.upsert(ticket)
        
        return ticket
```

---

## 6. Error Context

### Adding Context to Errors

```python
class VticError(Exception):
    """Base exception with context."""
    
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}

# Usage
try:
    await index.insert(ticket)
except ZvecError as e:
    raise IndexError(
        f"Failed to index ticket {ticket.id}",
        context={
            "ticket_id": ticket.id,
            "operation": "insert",
            "original_error": str(e)
        }
    )
```

### Logging Errors

```python
import logging

logger = logging.getLogger("vtic")

async def create_ticket(data: TicketCreate) -> Ticket:
    try:
        ticket = await service.create(data)
        return ticket
    except VticError as e:
        logger.error(
            "Failed to create ticket",
            extra={
                "error_code": type(e).__name__,
                "error_message": str(e),
                "input_data": data.dict()
            }
        )
        raise
```

---

## 7. Retry Patterns

### Exponential Backoff

```python
import asyncio
from functools import wraps

def retry(max_attempts: int = 3, delay: float = 1.0):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except TransientError as e:
                    if attempt == max_attempts - 1:
                        raise
                    wait = delay * (2 ** attempt)
                    logger.warning(f"Retry {attempt + 1}/{max_attempts} after {wait}s: {e}")
                    await asyncio.sleep(wait)
        return wrapper
    return decorator

@retry(max_attempts=3)
async def search_with_retry(query: str) -> SearchResult:
    return await search_engine.search(query)
```

---

## 8. Graceful Degradation

### Optional Features

```python
class SearchEngine:
    def __init__(self, embedding_provider: EmbeddingProvider | None = None):
        self._embedding_provider = embedding_provider
    
    async def search(
        self,
        query: str,
        semantic: bool = False
    ) -> SearchResult:
        # Always do BM25
        bm25_results = await self._bm25_search(query)
        
        # Only do semantic if provider available and requested
        if semantic and self._embedding_provider:
            semantic_results = await self._semantic_search(query)
            return self._merge_results(bm25_results, semantic_results)
        
        # Graceful degradation: BM25 only
        return bm25_results
```

---

## 9. User-Facing Error Messages

### Guidelines

1. **Be specific**: "Title is required" not "Validation failed"
2. **Be actionable**: "Use format owner/repo" not "Invalid format"
3. **Be polite**: No blame on user
4. **Include context**: Field names, expected formats

### Examples

```python
# ✅ Good messages
"Title is required and must be between 1 and 200 characters"
"Repository must be in format 'owner/repo' (e.g., 'ejacklab/vtic')"
"Ticket B12 not found. Use 'vtic list' to see available tickets."
"Search query cannot be empty. Provide a keyword to search for."

# ❌ Bad messages
"Error"  # Too vague
"Invalid input"  # Not actionable
"You entered wrong data"  # Blame on user
"ValueError: None"  # Technical jargon
```

---

## 10. Error Testing

### Testing Exception Handling

```python
import pytest

@pytest.mark.asyncio
async def test_create_ticket_validation(ticket_service):
    with pytest.raises(ValidationError) as exc_info:
        await ticket_service.create(TicketCreate(
            title="",  # Invalid: empty
            repo="invalid"  # Invalid: wrong format
        ))
    
    error = exc_info.value
    assert "title" in str(error).lower()

@pytest.mark.asyncio
async def test_get_nonexistent_ticket(ticket_service):
    with pytest.raises(TicketNotFoundError):
        await ticket_service.get("B999999")
```

### Testing Error Responses

```python
def test_validation_error_response(client):
    response = client.post("/tickets", json={
        "title": "",  # Invalid
        "repo": "no-slash"  # Invalid
    })
    
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert len(error["details"]) == 2
```

---

## Quick Reference Card

| Aspect | Rule |
|--------|------|
| Exception base | `VticError` for all domain errors |
| Validation | Use Pydantic at boundaries |
| Error format | Consistent `{error: {code, message, details}}` |
| HTTP codes | Map error codes to appropriate status |
| Messages | Specific, actionable, polite |
| Retry | Use exponential backoff for transient errors |
| Degradation | Gracefully fall back when optional features unavailable |

---

## References

- `rules/coding-standards.md` — Error handling rules
- `data-models-stage6-errors-map.md` — Error schema definitions
- `tmp/vtic/src/vtic/errors.py` — Reference implementation
