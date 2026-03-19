"""VTIC API Response Models (Stage 4)

Pydantic v2 models for API responses per OpenAPI spec.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generic, TypeVar, List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


# -----------------------------------------------------------------------------
# ErrorDetail
# -----------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """
    Field-level or contextual error detail.
    
    Each detail includes field, message, and optional value that caused the error.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "severity",
                "message": "Invalid value. Expected one of: critical, high, medium, low, info",
                "value": "urgent"
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
    value: Optional[Any] = Field(
        default=None,
        description="The actual value that caused the error (for debugging)"
    )


# -----------------------------------------------------------------------------
# ErrorObject
# -----------------------------------------------------------------------------

class ErrorObject(BaseModel):
    """Nested error object per OpenAPI spec."""
    
    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., VALIDATION_ERROR, NOT_FOUND)",
        examples=["VALIDATION_ERROR", "TICKET_NOT_FOUND", "SERVICE_UNAVAILABLE"]
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Query string cannot be empty", "Ticket S1 not found"]
    )
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="List of field-level validation errors or additional context"
    )
    docs: Optional[str] = Field(
        default=None,
        description="Link to error documentation",
        examples=["https://vtic.ejai.ai/docs/semantic-search"]
    )


# -----------------------------------------------------------------------------
# ErrorResponse
# -----------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """
    Standard error response for all API errors.
    
    REST Conventions per OpenAPI spec:
    - Nested `error` object with code, message, details[], and docs
    - HTTP status codes appropriately (4xx client errors, 5xx server errors)
    - Machine-readable error code for programmatic handling
    - Human-readable message for display
    - Optional details for field-level validation errors
    - Optional docs link for error documentation
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Query string cannot be empty",
                        "details": [
                            {
                                "field": "query",
                                "message": "Required field is missing or empty",
                                "value": None
                            }
                        ],
                        "docs": None
                    }
                },
                {
                    "error": {
                        "code": "SERVICE_UNAVAILABLE",
                        "message": "Semantic search requested but no embedding provider is configured",
                        "details": [
                            {
                                "field": "semantic",
                                "message": "Set 'semantic: false' or configure an embedding provider",
                                "value": True
                            }
                        ],
                        "docs": "https://vtic.ejai.ai/docs/semantic-search"
                    }
                }
            ]
        }
    )
    
    error: ErrorObject = Field(
        ...,
        description="Nested error object containing code, message, details, and docs"
    )
    
    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        docs: Optional[str] = None
    ) -> "ErrorResponse":
        """Factory method to create an error response."""
        return cls(
            error=ErrorObject(
                code=code,
                message=message,
                details=details,
                docs=docs
            )
        )
    
    @classmethod
    def validation_error(
        cls,
        message: str,
        details: Optional[List[ErrorDetail]] = None
    ) -> "ErrorResponse":
        """Create a validation error response."""
        return cls.create(
            code="VALIDATION_ERROR",
            message=message,
            details=details
        )
    
    @classmethod
    def not_found(
        cls,
        resource: str,
        identifier: str,
        docs: Optional[str] = None
    ) -> "ErrorResponse":
        """Create a not found error response."""
        return cls.create(
            code="NOT_FOUND",
            message=f"{resource} '{identifier}' not found",
            docs=docs
        )


# Common error codes (documented for API consumers)
ERROR_CODES = {
    # Client errors (4xx)
    "VALIDATION_ERROR": "Request validation failed",
    "NOT_FOUND": "Resource not found",
    "TICKET_NOT_FOUND": "Ticket with specified ID does not exist",
    "INVALID_STATUS_TRANSITION": "Status transition is not allowed",
    "DUPLICATE_ID": "Ticket with this ID already exists",
    "INVALID_REPO_FORMAT": "Repository must be in 'owner/repo' format",
    
    # Server errors (5xx)
    "INTERNAL_ERROR": "Unexpected server error",
    "SERVICE_UNAVAILABLE": "Service temporarily unavailable",
    "INDEX_ERROR": "Search index error",
    "EMBEDDING_ERROR": "Embedding provider error",
    "STORAGE_ERROR": "Ticket storage error",
}


# -----------------------------------------------------------------------------
# PaginationMeta
# -----------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    """
    Pagination metadata for list endpoints.
    
    Follows OpenAPI spec with total, limit, offset, has_more, and request_id.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 100,
                "limit": 20,
                "offset": 0,
                "has_more": True,
                "request_id": "req_abc123"
            }
        }
    )
    
    total: int = Field(
        ...,
        ge=0,
        description="Total matching items across all pages"
    )
    limit: int = Field(
        ...,
        ge=1,
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
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracing"
    )
    
    @classmethod
    def create(
        cls, 
        total: int, 
        limit: int, 
        offset: int,
        request_id: Optional[str] = None
    ) -> "PaginationMeta":
        """Factory method to create pagination metadata."""
        return cls(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
            request_id=request_id
        )


# -----------------------------------------------------------------------------
# PaginatedResponse[T]
# -----------------------------------------------------------------------------

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.
    
    Used for any endpoint that returns a list of items with pagination.
    Follows REST pagination conventions per OpenAPI spec.
    
    Type Parameters:
        T: The type of items in the data list (e.g., TicketSummary)
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [],
                "meta": {
                    "total": 100,
                    "limit": 20,
                    "offset": 0,
                    "has_more": True,
                    "request_id": "req_abc123"
                }
            }
        }
    )
    
    data: List[T] = Field(
        default_factory=list,
        description="List of items for the current page"
    )
    meta: PaginationMeta = Field(
        ...,
        description="Pagination metadata"
    )
    
    @classmethod
    def create(
        cls, 
        items: List[T], 
        total: int, 
        limit: int, 
        offset: int,
        request_id: Optional[str] = None
    ) -> "PaginatedResponse[T]":
        """
        Factory method to create a paginated response.
        
        Args:
            items: List of items for current page
            total: Total count across all pages
            limit: Page size
            offset: Current offset
            request_id: Optional request ID for tracing
            
        Returns:
            PaginatedResponse with has_more calculated automatically
        """
        return cls(
            data=items,
            meta=PaginationMeta.create(
                total=total,
                limit=limit,
                offset=offset,
                request_id=request_id
            )
        )


# -----------------------------------------------------------------------------
# IndexStatus
# -----------------------------------------------------------------------------

class IndexStatus(BaseModel):
    """
    Search index status information.
    
    Nested within HealthResponse per OpenAPI spec.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "zvec": "available",
                "ticket_count": 82,
                "last_reindex": "2026-03-17T08:00:00Z"
            }
        }
    )
    
    zvec: Literal["available", "unavailable", "corrupted"] = Field(
        ...,
        description="Zvec index availability status"
    )
    ticket_count: int = Field(
        ...,
        ge=0,
        description="Number of tickets in the index"
    )
    last_reindex: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last successful reindex"
    )


# -----------------------------------------------------------------------------
# EmbeddingProviderInfo
# -----------------------------------------------------------------------------

class EmbeddingProviderInfo(BaseModel):
    """
    Embedding provider configuration information.
    
    Nested within HealthResponse per OpenAPI spec.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "local",
                "model": "all-MiniLM-L6-v2",
                "dimension": 384
            }
        }
    )
    
    name: Literal["local", "openai", "custom", "none"] = Field(
        ...,
        description="Embedding provider name"
    )
    model: Optional[str] = Field(
        default=None,
        description="Model name used for embeddings",
        examples=["all-MiniLM-L6-v2"]
    )
    dimension: Optional[int] = Field(
        default=None,
        description="Embedding vector dimension",
        examples=[384]
    )


# -----------------------------------------------------------------------------
# HealthResponse
# -----------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """
    Health check response for monitoring.
    
    Provides comprehensive system health status per OpenAPI spec including:
    - Overall health status (healthy, degraded, unhealthy)
    - API version
    - Server uptime
    - Nested index_status object with zvec, ticket_count, last_reindex
    - Nested embedding_provider object with name, model, dimension
    
    HTTP Status Codes:
    - 200 OK: status is "healthy" or "degraded"
    - 503 Service Unavailable: status is "unhealthy"
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "healthy",
                    "version": "0.1.0",
                    "uptime_seconds": 86400,
                    "index_status": {
                        "zvec": "available",
                        "ticket_count": 82,
                        "last_reindex": "2026-03-17T08:00:00Z"
                    },
                    "embedding_provider": {
                        "name": "local",
                        "model": "all-MiniLM-L6-v2",
                        "dimension": 384
                    }
                },
                {
                    "status": "degraded",
                    "version": "0.1.0",
                    "uptime_seconds": 3600,
                    "index_status": {
                        "zvec": "available",
                        "ticket_count": 82,
                        "last_reindex": "2026-03-17T08:00:00Z"
                    },
                    "embedding_provider": {
                        "name": "none",
                        "model": None,
                        "dimension": None
                    }
                },
                {
                    "status": "unhealthy",
                    "version": "0.1.0",
                    "uptime_seconds": 120,
                    "index_status": {
                        "zvec": "corrupted",
                        "ticket_count": 0,
                        "last_reindex": None
                    },
                    "embedding_provider": {
                        "name": "none",
                        "model": None,
                        "dimension": None
                    }
                }
            ]
        }
    )
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Overall system health. 'healthy' = all systems operational, "
                    "'degraded' = partial functionality, 'unhealthy' = system unavailable"
    )
    version: str = Field(
        ...,
        description="API version string (semver format)",
        examples=["0.1.0", "1.2.3"]
    )
    uptime_seconds: Optional[int] = Field(
        default=None,
        description="Server uptime in seconds"
    )
    index_status: IndexStatus = Field(
        ...,
        description="Nested index status object"
    )
    embedding_provider: Optional[EmbeddingProviderInfo] = Field(
        default=None,
        description="Nested embedding provider information"
    )
    
    @classmethod
    def create(
        cls,
        version: str,
        uptime_seconds: Optional[int],
        zvec_status: str,
        ticket_count: int,
        last_reindex: Optional[datetime],
        provider_name: str = "none",
        provider_model: Optional[str] = None,
        provider_dimension: Optional[int] = None
    ) -> "HealthResponse":
        """
        Factory method to create a health response.
        
        Automatically determines overall status based on component states.
        """
        # Build nested objects
        index_status = IndexStatus(
            zvec=zvec_status,
            ticket_count=ticket_count,
            last_reindex=last_reindex
        )
        
        embedding_provider = EmbeddingProviderInfo(
            name=provider_name,
            model=provider_model,
            dimension=provider_dimension
        )
        
        # Determine overall status
        if zvec_status == "corrupted":
            overall_status = "unhealthy"
        elif zvec_status == "unavailable" or provider_name == "none":
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return cls(
            status=overall_status,
            version=version,
            uptime_seconds=uptime_seconds,
            index_status=index_status,
            embedding_provider=embedding_provider
        )


# -----------------------------------------------------------------------------
# StatsTotals
# -----------------------------------------------------------------------------

class StatsTotals(BaseModel):
    """
    Aggregate ticket totals.
    
    Nested within StatsResponse per OpenAPI spec.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "all": 82,
                "open": 23,
                "closed": 59
            }
        }
    )
    
    all: int = Field(
        ...,
        ge=0,
        description="Total tickets across all statuses"
    )
    open: int = Field(
        ...,
        ge=0,
        description="Tickets with status open or in_progress"
    )
    closed: int = Field(
        ...,
        ge=0,
        description="Tickets with status fixed, wont_fix, or closed"
    )


# -----------------------------------------------------------------------------
# DateRange
# -----------------------------------------------------------------------------

class DateRange(BaseModel):
    """
    Date range for statistics.
    
    Optional nested object within StatsResponse per OpenAPI spec.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "earliest": "2024-01-15T09:30:00Z",
                "latest": "2024-12-20T14:45:00Z"
            }
        }
    )
    
    earliest: datetime = Field(
        ...,
        description="Earliest ticket creation date"
    )
    latest: datetime = Field(
        ...,
        description="Latest ticket creation date"
    )


# -----------------------------------------------------------------------------
# StatsResponse
# -----------------------------------------------------------------------------

class StatsResponse(BaseModel):
    """
    Ticket statistics response.
    
    Per OpenAPI spec, uses nested StatsTotals object and optional date_range.
    Provides aggregated counts by status, severity, category, and optionally by repo.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "totals": {
                    "all": 82,
                    "open": 23,
                    "closed": 59
                },
                "by_status": {
                    "open": 15,
                    "in_progress": 8,
                    "blocked": 2,
                    "fixed": 42,
                    "wont_fix": 3,
                    "closed": 12
                },
                "by_severity": {
                    "critical": 2,
                    "high": 10,
                    "medium": 35,
                    "low": 25,
                    "info": 10
                },
                "by_category": {
                    "crash": 8,
                    "hotfix": 5,
                    "feature": 22,
                    "security": 12,
                    "general": 35
                },
                "by_repo": None,
                "date_range": None
            }
        }
    )
    
    totals: StatsTotals = Field(
        ...,
        description="Nested aggregate totals object"
    )
    by_status: Dict[str, int] = Field(
        ...,
        description="Ticket counts by status",
        examples=[{"open": 15, "in_progress": 8, "fixed": 42}]
    )
    by_severity: Dict[str, int] = Field(
        ...,
        description="Ticket counts by severity level",
        examples=[{"critical": 2, "high": 10, "medium": 35, "low": 25, "info": 10}]
    )
    by_category: Dict[str, int] = Field(
        ...,
        description="Ticket counts by category",
        examples=[{"crash": 8, "hotfix": 5, "feature": 22, "security": 12, "general": 35}]
    )
    by_repo: Optional[Dict[str, int]] = Field(
        default=None,
        description="Ticket counts by repository (only when by_repo=true)",
        examples=[{"ejacklab/open-dsearch": 45, "ejacklab/vtic": 25, "ejacklab/zvec": 12}]
    )
    date_range: Optional[DateRange] = Field(
        default=None,
        description="Optional date range for the statistics"
    )
    
    @classmethod
    def create(
        cls,
        all_count: int,
        open_count: int,
        closed_count: int,
        by_status: Dict[str, int],
        by_severity: Dict[str, int],
        by_category: Dict[str, int],
        by_repo: Optional[Dict[str, int]] = None,
        date_range: Optional[DateRange] = None
    ) -> "StatsResponse":
        """Factory method to create a stats response."""
        return cls(
            totals=StatsTotals(
                all=all_count,
                open=open_count,
                closed=closed_count
            ),
            by_status=by_status,
            by_severity=by_severity,
            by_category=by_category,
            by_repo=by_repo,
            date_range=date_range
        )


# -----------------------------------------------------------------------------
# ReindexError
# -----------------------------------------------------------------------------

class ReindexError(BaseModel):
    """Details about a single indexing error."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": "C15",
                "message": "Failed to generate embedding: API timeout"
            }
        }
    )
    
    ticket_id: str = Field(
        ...,
        description="ID of the ticket that failed to index"
    )
    message: str = Field(
        ...,
        description="Error message describing the failure"
    )


# -----------------------------------------------------------------------------
# ReindexResult
# -----------------------------------------------------------------------------

class ReindexResult(BaseModel):
    """
    Result of a reindex operation.
    
    Per OpenAPI spec, includes processed, skipped, failed counts,
    duration_ms, and errors list.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "processed": 80,
                    "skipped": 2,
                    "failed": 0,
                    "duration_ms": 12340,
                    "errors": []
                },
                {
                    "processed": 78,
                    "skipped": 2,
                    "failed": 2,
                    "duration_ms": 14500,
                    "errors": [
                        {
                            "ticket_id": "C15",
                            "message": "Failed to generate embedding: API timeout"
                        },
                        {
                            "ticket_id": "H3",
                            "message": "Invalid markdown format in frontmatter"
                        }
                    ]
                }
            ]
        }
    )
    
    processed: int = Field(
        ...,
        ge=0,
        description="Tickets that were (re-)embedded and indexed"
    )
    skipped: int = Field(
        default=0,
        ge=0,
        description="Tickets unchanged since last index"
    )
    failed: int = Field(
        ...,
        ge=0,
        description="Tickets that failed to index"
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Total reindex duration in milliseconds"
    )
    errors: List[ReindexError] = Field(
        default_factory=list,
        description="List of individual indexing errors"
    )
    
    @property
    def total_processed(self) -> int:
        """Total number of tickets processed."""
        return self.processed + self.skipped + self.failed
    
    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0-100)."""
        total = self.total_processed
        if total == 0:
            return 100.0
        return (self.processed / total) * 100


# -----------------------------------------------------------------------------
# DoctorCheck
# -----------------------------------------------------------------------------

class DoctorCheck(BaseModel):
    """
    Single diagnostic check result.
    
    Per OpenAPI spec: name, status, message, fix.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "zvec_index",
                    "status": "ok",
                    "message": "Index is healthy with 82 tickets",
                    "fix": None
                },
                {
                    "name": "config_file",
                    "status": "warning",
                    "message": "Using deprecated config key 'embeddings.provider'",
                    "fix": "Update to 'embeddings.provider' in vtic.toml"
                },
                {
                    "name": "file_permissions",
                    "status": "error",
                    "message": "Cannot write to tickets directory",
                    "fix": "Check permissions on ./tickets/ directory"
                }
            ]
        }
    )
    
    name: str = Field(
        ...,
        description="Check identifier",
        examples=["zvec_index", "config_file", "embedding_provider", "file_permissions"]
    )
    status: Literal["ok", "warning", "error"] = Field(
        ...,
        description="Check result status"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable status message"
    )
    fix: Optional[str] = Field(
        default=None,
        description="Suggested fix command or action"
    )


# -----------------------------------------------------------------------------
# DoctorResult
# -----------------------------------------------------------------------------

class DoctorResult(BaseModel):
    """
    Diagnostic check results.
    
    Per OpenAPI spec: overall status and list of checks.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "overall": "ok",
                    "checks": [
                        {"name": "zvec_index", "status": "ok", "message": "Index is healthy with 82 tickets", "fix": None},
                        {"name": "config_file", "status": "ok", "message": "Configuration valid", "fix": None},
                        {"name": "embedding_provider", "status": "ok", "message": "Local provider using all-MiniLM-L6-v2", "fix": None},
                        {"name": "file_permissions", "status": "ok", "message": "All directories writable", "fix": None}
                    ]
                },
                {
                    "overall": "warnings",
                    "checks": [
                        {"name": "zvec_index", "status": "ok", "message": "Index is healthy", "fix": None},
                        {"name": "config_file", "status": "warning", "message": "Using deprecated config key", "fix": "Update to 'embeddings.provider' in vtic.toml"},
                        {"name": "embedding_provider", "status": "warning", "message": "No embedding provider configured", "fix": "Set embeddings.provider = 'local' in vtic.toml"}
                    ]
                },
                {
                    "overall": "errors",
                    "checks": [
                        {"name": "zvec_index", "status": "error", "message": "Index file corrupted or missing", "fix": "Run 'vtic reindex' to rebuild the index"},
                        {"name": "config_file", "status": "ok", "message": "Configuration valid", "fix": None},
                        {"name": "file_permissions", "status": "error", "message": "Cannot write to tickets directory", "fix": "Check permissions on ./tickets/ directory"}
                    ]
                }
            ]
        }
    )
    
    overall: Literal["ok", "warnings", "errors"] = Field(
        ...,
        description="Aggregated status from all checks"
    )
    checks: List[DoctorCheck] = Field(
        ...,
        description="List of individual diagnostic checks"
    )
    
    @classmethod
    def create(cls, checks: List[DoctorCheck]) -> "DoctorResult":
        """
        Factory method that automatically determines overall status.
        
        - If any check is "error", overall is "errors"
        - Else if any check is "warning", overall is "warnings"
        - Else overall is "ok"
        """
        statuses = [c.status for c in checks]
        
        if "error" in statuses:
            overall = "errors"
        elif "warning" in statuses:
            overall = "warnings"
        else:
            overall = "ok"
        
        return cls(overall=overall, checks=checks)
    
    def get_errors(self) -> List[DoctorCheck]:
        """Get all checks with error status."""
        return [c for c in self.checks if c.status == "error"]
    
    def get_warnings(self) -> List[DoctorCheck]:
        """Get all checks with warning status."""
        return [c for c in self.checks if c.status == "warning"]
