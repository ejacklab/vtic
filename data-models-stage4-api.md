# VTIC API Response Models (Stage 4)

Pydantic v2 models for API responses.

> **Important:** This module imports enums from Stage 1 (canonical definitions). All response models follow REST conventions.

---

## Imports

```python
from datetime import datetime, timezone
from typing import Generic, TypeVar, List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict

# Import canonical enums from Stage 1
# In actual implementation:
# from .enums import Severity, Status, Category

T = TypeVar('T')
```

---

## 1. PaginatedResponse[T]

Generic paginated wrapper for list endpoints.

### Pydantic v2 Generic Syntax

```python
from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.
    
    Used for any endpoint that returns a list of items with pagination.
    Follows REST pagination conventions.
    
    Attributes:
        data: List of items for the current page
        total: Total number of items across all pages
        limit: Number of items requested per page
        offset: Number of items skipped (0-based)
        has_more: True if there are more items after this page
    
    Type Parameters:
        T: The type of items in the data list (e.g., TicketResponse)
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [],
                "total": 100,
                "limit": 20,
                "offset": 0,
                "has_more": True
            }
        }
    )
    
    data: List[T] = Field(
        default_factory=list,
        description="List of items for the current page"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items across all pages"
    )
    limit: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Number of items requested per page"
    )
    offset: int = Field(
        ...,
        ge=0,
        description="Number of items skipped (0-based offset)"
    )
    has_more: bool = Field(
        ...,
        description="True if there are more items after this page"
    )
    
    @classmethod
    def create(
        cls, 
        items: List[T], 
        total: int, 
        limit: int, 
        offset: int
    ) -> "PaginatedResponse[T]":
        """
        Factory method to create a paginated response.
        
        Args:
            items: List of items for current page
            total: Total count across all pages
            limit: Page size
            offset: Current offset
            
        Returns:
            PaginatedResponse with has_more calculated automatically
        """
        return cls(
            data=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(items)) < total
        )
```

---

## 2. TicketListResponse

Response for `GET /tickets` endpoint.

Uses `PaginatedResponse[TicketResponse]` where `TicketResponse` is the full ticket model from Stage 2.

```python
# Type alias for clarity - TicketResponse is from Stage 2
# from .ticket import TicketResponse
# TicketListResponse = PaginatedResponse[TicketResponse]

# Example usage in FastAPI:
# @app.get("/tickets", response_model=TicketListResponse)
# def list_tickets(...) -> TicketListResponse:
#     ...
```

**Example JSON Response:**
```json
{
  "data": [
    {
      "id": "S1",
      "slug": "cors-wildcard",
      "title": "CORS Wildcard",
      "description": "API allows CORS wildcard origin",
      "repo": "ejacklab/open-dsearch",
      "owner": "ejacklab",
      "category": "security",
      "severity": "critical",
      "status": "open",
      "tags": ["cors", "security"],
      "created_at": "2024-01-15T09:30:00Z",
      "updated_at": "2024-01-15T09:30:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

---

## 3. ErrorResponse

Standard error response for all API errors. Follows REST conventions.

```python
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class ErrorDetail(BaseModel):
    """Field-level or contextual error detail."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "severity",
                "message": "Invalid value 'urgent'. Expected one of: critical, high, medium, low",
                "code": "INVALID_ENUM_VALUE"
            }
        }
    )
    
    field: Optional[str] = Field(
        default=None,
        description="Field name that failed validation (if applicable)"
    )
    message: str = Field(
        ...,
        description="Human-readable error message for this detail"
    )
    code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code for this detail"
    )


class ErrorResponse(BaseModel):
    """
    Standard error response for all API errors.
    
    REST Conventions:
    - Uses HTTP status codes appropriately (4xx client errors, 5xx server errors)
    - Provides machine-readable error_code for programmatic handling
    - Includes human-readable message for display
    - Optional details for field-level validation errors
    - Request ID for debugging and log correlation
    - Timestamp in UTC ISO 8601 format
    
    Attributes:
        error: Error object containing code, message, and optional details
        request_id: Unique request ID for debugging (from X-Request-ID header)
        timestamp: UTC timestamp when the error occurred
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": {
                        "code": "TICKET_NOT_FOUND",
                        "message": "Ticket S1 not found",
                        "details": None
                    },
                    "request_id": "req_abc123",
                    "timestamp": "2024-01-15T09:30:00Z"
                },
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "details": [
                            {
                                "field": "title",
                                "message": "Field required",
                                "code": "REQUIRED"
                            },
                            {
                                "field": "severity",
                                "message": "Invalid value 'urgent'. Expected one of: critical, high, medium, low",
                                "code": "INVALID_ENUM_VALUE"
                            }
                        ]
                    },
                    "request_id": "req_def456",
                    "timestamp": "2024-01-15T09:31:00Z"
                }
            ]
        }
    )
    
    class ErrorObject(BaseModel):
        """Nested error object."""
        code: str = Field(
            ...,
            description="Machine-readable error code (e.g., TICKET_NOT_FOUND, VALIDATION_ERROR)",
            examples=["TICKET_NOT_FOUND", "VALIDATION_ERROR", "INVALID_STATUS_TRANSITION"]
        )
        message: str = Field(
            ...,
            description="Human-readable error message",
            examples=["Ticket S1 not found", "Request validation failed"]
        )
        details: Optional[List[ErrorDetail]] = Field(
            default=None,
            description="List of field-level validation errors or additional context"
        )
    
    error: ErrorObject = Field(
        ...,
        description="Error object containing code, message, and optional details"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request ID for debugging (from X-Request-ID header)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the error occurred"
    )
    
    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        request_id: Optional[str] = None
    ) -> "ErrorResponse":
        """Factory method to create an error response."""
        return cls(
            error=cls.ErrorObject(code=code, message=message, details=details),
            request_id=request_id,
            timestamp=datetime.now(timezone.utc)
        )


# Common error codes (documented for API consumers)
ERROR_CODES = {
    # Client errors (4xx)
    "VALIDATION_ERROR": "Request validation failed",
    "TICKET_NOT_FOUND": "Ticket with specified ID does not exist",
    "INVALID_STATUS_TRANSITION": "Status transition is not allowed",
    "DUPLICATE_ID": "Ticket with this ID already exists",
    "INVALID_REPO_FORMAT": "Repository must be in 'owner/repo' format",
    "FILTER_ERROR": "Invalid filter expression",
    "SEARCH_ERROR": "Search query error",
    
    # Server errors (5xx)
    "INTERNAL_ERROR": "Unexpected server error",
    "INDEX_ERROR": "Search index error",
    "EMBEDDING_ERROR": "Embedding provider error",
    "STORAGE_ERROR": "Ticket storage error",
}
```

---

## 4. HealthResponse

Response for `GET /health` endpoint. Provides comprehensive health check information.

```python
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class ComponentHealth(BaseModel):
    """Health status of a single component."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "message": "Index ready",
                "details": {"document_count": 42}
            }
        }
    )
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Component health status"
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional human-readable status message"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional additional details about component state"
    )


class HealthResponse(BaseModel):
    """
    Health check response for monitoring.
    
    Provides comprehensive system health status including:
    - Overall health status (aggregated from components)
    - API version
    - Ticket statistics
    - Component-level health checks (index, embedding provider, storage)
    - Server uptime
    
    HTTP Status Codes:
    - 200 OK: status is "healthy" or "degraded"
    - 503 Service Unavailable: status is "unhealthy"
    
    Attributes:
        status: Overall health status (healthy, degraded, unhealthy)
        version: API version string
        ticket_count: Total number of tickets in the system
        index_status: Status of the search index
        uptime_seconds: Server uptime in seconds
        checks: Component-level health checks
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "ticket_count": 42,
                "index_status": "ready",
                "uptime_seconds": 3600.5,
                "checks": {
                    "index": {
                        "status": "healthy",
                        "message": "Index ready with 42 documents",
                        "details": {"document_count": 42}
                    },
                    "embedding": {
                        "status": "healthy",
                        "message": "Using local sentence-transformers",
                        "details": {"provider": "local", "model": "all-MiniLM-L6-v2"}
                    },
                    "storage": {
                        "status": "healthy",
                        "message": "Storage directory accessible",
                        "details": {"path": "/data/tickets", "writable": True}
                    }
                }
            }
        }
    )
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Overall health status. 'healthy' = all systems operational, "
                    "'degraded' = partial functionality, 'unhealthy' = system unavailable"
    )
    version: str = Field(
        ...,
        description="API version string (semver format)",
        examples=["1.0.0", "1.2.3-beta.1"],
        pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
    )
    ticket_count: int = Field(
        ...,
        ge=0,
        description="Total number of tickets in the system"
    )
    index_status: Literal["ready", "building", "error", "uninitialized"] = Field(
        ...,
        description="Status of the search index: 'ready' = operational, "
                    "'building' = reindexing in progress, 'error' = index failed, "
                    "'uninitialized' = index not yet created"
    )
    uptime_seconds: float = Field(
        ...,
        ge=0.0,
        description="Server uptime in seconds"
    )
    checks: Optional[Dict[str, ComponentHealth]] = Field(
        default=None,
        description="Component-level health checks (index, embedding, storage)"
    )
    
    @classmethod
    def create(
        cls,
        version: str,
        ticket_count: int,
        index_status: str,
        uptime_seconds: float,
        embedding_provider: Optional[str] = None,
        storage_path: Optional[str] = None
    ) -> "HealthResponse":
        """
        Factory method to create a health response with component checks.
        
        Args:
            version: API version
            ticket_count: Total tickets
            index_status: Index status
            uptime_seconds: Server uptime
            embedding_provider: Active embedding provider (or None)
            storage_path: Path to ticket storage
            
        Returns:
            HealthResponse with computed status and component checks
        """
        # Build component checks
        checks: Dict[str, ComponentHealth] = {}
        
        # Index check
        index_healthy = index_status == "ready"
        checks["index"] = ComponentHealth(
            status="healthy" if index_healthy else "degraded" if index_status == "building" else "unhealthy",
            message=f"Index {index_status}" + (f" with {ticket_count} documents" if index_healthy else ""),
            details={"document_count": ticket_count} if index_healthy else None
        )
        
        # Embedding check
        if embedding_provider:
            checks["embedding"] = ComponentHealth(
                status="healthy",
                message=f"Using {embedding_provider} provider",
                details={"provider": embedding_provider}
            )
        else:
            checks["embedding"] = ComponentHealth(
                status="degraded",
                message="No embedding provider configured (semantic search disabled)"
            )
        
        # Storage check
        if storage_path:
            checks["storage"] = ComponentHealth(
                status="healthy",
                message="Storage directory accessible",
                details={"path": storage_path}
            )
        
        # Determine overall status
        component_statuses = [c.status for c in checks.values()]
        if "unhealthy" in component_statuses:
            overall_status = "unhealthy"
        elif "degraded" in component_statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return cls(
            status=overall_status,
            version=version,
            ticket_count=ticket_count,
            index_status=index_status,
            uptime_seconds=uptime_seconds,
            checks=checks
        )


# HTTP Status mapping
# 200 OK: healthy or degraded
# 503 Service Unavailable: unhealthy
```

---

## 5. StatsResponse

Response for `GET /stats` endpoint. Provides comprehensive ticket statistics.

```python
from typing import Dict
from pydantic import BaseModel, Field, ConfigDict


class StatsResponse(BaseModel):
    """
    Ticket statistics response.
    
    Provides aggregated counts of tickets grouped by various dimensions
    for dashboards and reporting. Covers all stat breakdowns per FEATURES.md:
    - by_severity: critical, high, medium, low
    - by_status: open, in_progress, blocked, fixed, wont_fix, closed
    - by_category: all 16 categories from Stage 1 enums
    - by_repo: repository-level breakdown
    
    Attributes:
        by_severity: Ticket counts grouped by severity level
        by_status: Ticket counts grouped by status
        by_category: Ticket counts grouped by category
        by_repo: Ticket counts grouped by repository (owner/repo format)
        total: Total ticket count
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "by_severity": {
                    "critical": 5,
                    "high": 12,
                    "medium": 20,
                    "low": 5
                },
                "by_status": {
                    "open": 15,
                    "in_progress": 8,
                    "blocked": 2,
                    "fixed": 10,
                    "wont_fix": 3,
                    "closed": 4
                },
                "by_category": {
                    "security": 5,
                    "auth": 3,
                    "code_quality": 8,
                    "performance": 4,
                    "frontend": 6,
                    "backend": 10,
                    "testing": 2,
                    "documentation": 1,
                    "infrastructure": 2,
                    "configuration": 1,
                    "other": 0
                },
                "by_repo": {
                    "ejacklab/open-dsearch": 30,
                    "ejacklab/vtic": 12
                },
                "total": 42
            }
        }
    )
    
    by_severity: Dict[str, int] = Field(
        ...,
        description="Ticket counts grouped by severity level (critical, high, medium, low)",
        examples=[{"critical": 5, "high": 12, "medium": 20, "low": 5}]
    )
    by_status: Dict[str, int] = Field(
        ...,
        description="Ticket counts grouped by status (open, in_progress, blocked, fixed, wont_fix, closed)",
        examples=[{"open": 15, "in_progress": 8, "blocked": 2, "fixed": 10, "wont_fix": 3, "closed": 4}]
    )
    by_category: Dict[str, int] = Field(
        ...,
        description="Ticket counts grouped by category (all 16 categories from Stage 1)",
        examples=[{"security": 5, "auth": 3, "backend": 10, "other": 0}]
    )
    by_repo: Dict[str, int] = Field(
        ...,
        description="Ticket counts grouped by repository in 'owner/repo' format",
        examples=[{"ejacklab/open-dsearch": 30, "ejacklab/vtic": 12}]
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of tickets across all groups"
    )
    
    @classmethod
    def empty(cls) -> "StatsResponse":
        """Create an empty stats response (for initialization)."""
        return cls(
            by_severity={"critical": 0, "high": 0, "medium": 0, "low": 0},
            by_status={
                "open": 0, "in_progress": 0, "blocked": 0,
                "fixed": 0, "wont_fix": 0, "closed": 0
            },
            by_category={},
            by_repo={},
            total=0
        )
    
    def validate_totals(self) -> bool:
        """Check if breakdown totals match the total count."""
        severity_sum = sum(self.by_severity.values())
        status_sum = sum(self.by_status.values())
        return severity_sum == self.total and status_sum == self.total
```

---

## 6. ReindexResponse

Response for `POST /reindex` endpoint.

```python
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ReindexError(BaseModel):
    """Details about a single indexing error."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": "S42",
                "error": "Failed to generate embedding: API timeout"
            }
        }
    )
    
    ticket_id: str = Field(
        ...,
        description="ID of the ticket that failed to index"
    )
    error: str = Field(
        ...,
        description="Error message describing the failure"
    )


class ReindexResponse(BaseModel):
    """
    Reindex operation response.
    
    Provides results of a reindex operation, including counts of
    successfully indexed, skipped, and errored tickets.
    
    Attributes:
        indexed: Number of tickets successfully indexed
        skipped: Number of tickets skipped (e.g., unchanged)
        errors: Number of tickets that failed to index
        error_details: Optional list of individual error details
        took_ms: Total time taken for the operation in milliseconds
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "indexed": 42,
                "skipped": 5,
                "errors": 0,
                "error_details": [],
                "took_ms": 1250.5
            }
        }
    )
    
    indexed: int = Field(
        ...,
        ge=0,
        description="Number of tickets successfully indexed"
    )
    skipped: int = Field(
        ...,
        ge=0,
        description="Number of tickets skipped (unchanged or excluded)"
    )
    errors: int = Field(
        ...,
        ge=0,
        description="Number of tickets that failed to index"
    )
    error_details: Optional[List[ReindexError]] = Field(
        default=None,
        description="Details of individual indexing errors (if any)"
    )
    took_ms: float = Field(
        ...,
        ge=0.0,
        description="Total time taken for the operation in milliseconds"
    )
    
    @property
    def total_processed(self) -> int:
        """Total number of tickets processed."""
        return self.indexed + self.skipped + self.errors
    
    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0-100)."""
        total = self.total_processed
        if total == 0:
            return 100.0
        return (self.indexed / total) * 100
```

---

## Complete Models Module

Here's the complete models file ready for use:

```python
"""VTIC API Response Models (Stage 4)

Pydantic v2 models for API responses.
"""

from datetime import datetime, timezone
from typing import Generic, TypeVar, List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


# -----------------------------------------------------------------------------
# PaginatedResponse
# -----------------------------------------------------------------------------

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    data: List[T]
    total: int
    limit: int
    offset: int
    has_more: bool


# -----------------------------------------------------------------------------
# ErrorResponse
# -----------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """Field-level or contextual error detail."""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response for all API errors."""
    
    class ErrorObject(BaseModel):
        code: str
        message: str
        details: Optional[List[ErrorDetail]] = None
    
    error: ErrorObject
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# -----------------------------------------------------------------------------
# HealthResponse
# -----------------------------------------------------------------------------

class ComponentHealth(BaseModel):
    """Health status of a single component."""
    status: Literal["healthy", "degraded", "unhealthy"]
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response for monitoring."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    ticket_count: int
    index_status: Literal["ready", "building", "error", "uninitialized"]
    uptime_seconds: float
    checks: Optional[Dict[str, ComponentHealth]] = None


# -----------------------------------------------------------------------------
# StatsResponse
# -----------------------------------------------------------------------------

class StatsResponse(BaseModel):
    """Ticket statistics response."""
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    by_category: Dict[str, int]
    by_repo: Dict[str, int]
    total: int


# -----------------------------------------------------------------------------
# ReindexResponse
# -----------------------------------------------------------------------------

class ReindexError(BaseModel):
    """Details about a single indexing error."""
    ticket_id: str
    error: str


class ReindexResponse(BaseModel):
    """Reindex operation response."""
    indexed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    errors: int = Field(ge=0)
    error_details: Optional[List[ReindexError]] = None
    took_ms: float


# Type alias for ticket list responses
# TicketResponse would be defined in the core ticket models module (Stage 2)
# from .ticket import TicketResponse
# TicketListResponse = PaginatedResponse[TicketResponse]
```

---

## Cross-Reference with Other Stages

| Stage | Type | Used In Stage 4 |
|-------|------|-----------------|
| Stage 1 | `Severity` | `StatsResponse.by_severity` keys |
| Stage 1 | `Status` | `StatsResponse.by_status` keys |
| Stage 1 | `Category` | `StatsResponse.by_category` keys |
| Stage 2 | `TicketResponse` | `PaginatedResponse[TicketResponse]` |
| Stage 3 | `SearchResponse` | Separate endpoint (POST /search) |

---

## Usage Examples

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPStatus
from typing import Annotated

app = FastAPI()


@app.get("/tickets", response_model=PaginatedResponse[TicketResponse])
def list_tickets(
    limit: int = 20,
    offset: int = 0
) -> PaginatedResponse[TicketResponse]:
    tickets = get_tickets(limit=limit, offset=offset)
    total = count_tickets()
    
    return PaginatedResponse.create(
        items=tickets,
        total=total,
        limit=limit,
        offset=offset
    )


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse.create(
        version="1.0.0",
        ticket_count=42,
        index_status="ready",
        uptime_seconds=get_uptime(),
        embedding_provider="local",
        storage_path="/data/tickets"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check_with_status(response: Response):
    health = HealthResponse.create(
        version="1.0.0",
        ticket_count=42,
        index_status="ready",
        uptime_seconds=get_uptime()
    )
    
    # Set HTTP status based on health
    if health.status == "unhealthy":
        response.status_code = HTTPStatus.SERVICE_UNAVAILABLE
    elif health.status == "degraded":
        response.status_code = HTTPStatus.OK  # Still return 200 for degraded
    
    return health


@app.get("/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    return StatsResponse(
        by_severity={"critical": 5, "high": 12, "medium": 20, "low": 5},
        by_status={"open": 15, "in_progress": 8, "blocked": 2, "fixed": 10, "wont_fix": 3, "closed": 4},
        by_category={"security": 5, "backend": 10, "other": 5},
        by_repo={"ejacklab/open-dsearch": 30, "ejacklab/vtic": 12},
        total=42
    )


@app.post("/reindex", response_model=ReindexResponse)
def reindex_tickets() -> ReindexResponse:
    result = perform_reindex()
    return ReindexResponse(**result)
```

### Error Handler

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class TicketNotFoundError(Exception):
    def __init__(self, ticket_id: str):
        self.ticket_id = ticket_id


@app.exception_handler(TicketNotFoundError)
async def ticket_not_found_handler(request: Request, exc: TicketNotFoundError):
    error = ErrorResponse.create(
        code="TICKET_NOT_FOUND",
        message=f"Ticket {exc.ticket_id} not found",
        request_id=request.headers.get("X-Request-ID")
    )
    return JSONResponse(
        status_code=404,
        content=error.model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [
        ErrorDetail(
            field=".".join(str(loc) for loc in err["loc"]),
            message=err["msg"],
            code=err.get("type")
        )
        for err in exc.errors()
    ]
    
    error = ErrorResponse.create(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=details,
        request_id=request.headers.get("X-Request-ID")
    )
    return JSONResponse(
        status_code=422,
        content=error.model_dump()
    )
```

---

## HTTP Status Code Conventions

| Status | When Used | Example |
|--------|-----------|---------|
| 200 OK | Successful GET, PATCH | Ticket retrieved/updated |
| 201 Created | Successful POST | Ticket created |
| 204 No Content | Successful DELETE | Ticket deleted |
| 400 Bad Request | Validation error | Invalid field value |
| 404 Not Found | Resource not found | Ticket ID doesn't exist |
| 409 Conflict | State conflict | Invalid status transition |
| 422 Unprocessable Entity | Request validation failed | Missing required field |
| 500 Internal Server Error | Unexpected error | Database connection failed |
| 503 Service Unavailable | Health check unhealthy | Index not ready |

---

## Response Envelope Convention

All successful responses use this structure:

```json
// Single resource
{
  "id": "S1",
  "title": "...",
  ...
}

// List with pagination
{
  "data": [...],
  "total": 100,
  "limit": 20,
  "offset": 0,
  "has_more": true
}

// Error
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": [...]
  },
  "request_id": "req_123",
  "timestamp": "2024-01-15T09:30:00Z"
}
```

---

## Implementation Notes

1. **Generic Syntax**: Use `class PaginatedResponse(BaseModel, Generic[T])` for Pydantic v2. Type parameter `T` is bound at runtime.

2. **ConfigDict**: Use `model_config = ConfigDict(...)` instead of `class Config:` for Pydantic v2.

3. **Timestamps**: Always use UTC timezone. Use `datetime.now(timezone.utc)` not `datetime.utcnow()`.

4. **Literal Types**: Use `Literal["a", "b", "c"]` for constrained string values instead of string patterns where possible.

5. **Error Structure**: The nested `error` object in `ErrorResponse` allows for future extension without breaking changes.

6. **Health Checks**: The `checks` field provides component-level visibility while `status` gives overall health.

7. **Stats Keys**: Dictionary keys in `StatsResponse` use enum values (lowercase strings) for consistency.
