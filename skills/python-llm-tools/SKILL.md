---
name: python-llm-tools
description: Write Python functions optimized for LLM tool calling. Use when creating functions that LLMs invoke directly - API wrappers, data processors, CLI tools, or any callable interface. Covers type hints, docstrings, error handling, and input validation patterns that make functions machine-interpretable.
---

# Python LLM Tools

Design Python functions for reliable LLM invocation.

## Core Principles

### 1. Signatures Are Contracts

Type hints are mandatory. LLMs read signatures to understand what to pass.

```python
# ❌ Bad - LLM must guess types
def search(query, limit=10):
    ...

# ✅ Good - LLM knows exactly what to pass
def search(query: str, limit: int = 10) -> list[dict]:
    ...
```

### 2. Docstrings Are API Docs

Use Google Style. Factual tone, not imperative. Include Args/Returns/Raises.

```python
def fetch_user(user_id: str) -> dict:
    """Fetch user data from the database.
    
    Args:
        user_id: The unique identifier for the user.
        
    Returns:
        User record with id, name, and email fields.
        
    Raises:
        NotFoundError: If user_id does not exist.
        ConnectionError: If database is unreachable.
    """
```

### 3. Input Validation at Boundaries

Validate immediately. Fail fast with specific errors.

```python
def process_data(items: list[str]) -> dict:
    if not items:
        raise ValueError("items cannot be empty")
    if len(items) > 1000:
        raise ValueError(f"items exceeds max length of 1000: got {len(items)}")
    ...
```

### 4. Specific Exception Types

Custom exceptions enable LLMs to handle errors programmatically.

```python
class ToolError(Exception):
    """Base exception for tool errors."""
    pass

class InvalidInputError(ToolError):
    """Input validation failed."""
    pass

class ResourceNotFoundError(ToolError):
    """Requested resource does not exist."""
    pass

class RateLimitError(ToolError):
    """API rate limit exceeded."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")
```

### 5. Consistent Return Types

Always return a dict with predictable structure.

```python
# ✅ Good - Consistent structure
def search(query: str) -> dict:
    return {
        "success": True,
        "results": [...],
        "count": 5,
        "query": query
    }

# On error:
def search(query: str) -> dict:
    return {
        "success": False,
        "error": "Query cannot be empty",
        "error_code": "INVALID_INPUT"
    }
```

## Error Handling Pattern

```python
def tool_function(arg: str) -> dict:
    """Function description."""
    try:
        # Input validation
        if not arg:
            raise InvalidInputError("arg cannot be empty")
        
        # Main logic
        result = do_work(arg)
        
        return {"success": True, "data": result}
        
    except InvalidInputError as e:
        return {"success": False, "error": str(e), "error_code": "INVALID_INPUT"}
    except ResourceNotFoundError as e:
        return {"success": False, "error": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        # Log unexpected errors
        return {"success": False, "error": "Internal error", "error_code": "INTERNAL"}
```

## Naming Conventions

```python
# ✅ Descriptive - LLM understands purpose
validate_user_email(email: str) -> bool
fetch_order_history(user_id: str, limit: int) -> list[dict]

# ❌ Cryptic - LLM must guess
chk_eml(e) -> bool
get_ord(u, n) -> list
```

## MCP/FastAPI Integration

For tools exposed via HTTP or MCP:

```python
from pydantic import BaseModel
from typing import Optional

class SearchRequest(BaseModel):
    """Search request parameters."""
    query: str
    limit: int = 10
    filters: Optional[dict] = None

class SearchResponse(BaseModel):
    """Search response structure."""
    success: bool
    results: list[dict]
    error: Optional[str] = None

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """Execute search query.
    
    See SearchRequest and SearchResponse for schema details.
    """
    ...
```

## Checklist

Before shipping any LLM-callable function:

- [ ] All parameters have type hints
- [ ] Return type is declared
- [ ] Docstring with Args/Returns/Raises
- [ ] Input validation at function start
- [ ] Custom exception types for expected failures
- [ ] Consistent return structure (success/error)
- [ ] Descriptive names (no abbreviations)
