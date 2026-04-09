"""Error definitions for vtic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Error codes (exactly 6 from OpenAPI)
VALIDATION_ERROR = "VALIDATION_ERROR"
NOT_FOUND = "NOT_FOUND"
CONFLICT = "CONFLICT"
PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
INTERNAL_ERROR = "INTERNAL_ERROR"
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorDetail(BaseModel):
    """Individual validation error detail.
    
    Attributes:
        field: The field that failed validation (optional).
        message: Human-readable error message.
        value: The invalid value that was provided (optional).
    """
    field: Optional[str] = None
    message: str
    value: Optional[str] = None


class ErrorObject(BaseModel):
    """Error object nested within ErrorResponse.
    
    Attributes:
        code: Machine-readable error code (e.g., VALIDATION_ERROR, NOT_FOUND).
        message: Human-readable error description.
        details: Optional list of specific validation errors.
        docs: Optional link to error documentation.
    """
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="List of specific validation errors"
    )
    docs: Optional[str] = Field(
        default=None,
        description="Link to error documentation"
    )


class ErrorResponse(BaseModel):
    """Error envelope for all error responses.
    
    This is the canonical error response structure from the OpenAPI spec.
    All API errors return this format.
    
    Example:
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Query string cannot be empty",
                "details": [
                    {"field": "query", "message": "Required field is missing or empty"}
                ]
            }
        }
    """
    error: ErrorObject
    meta: Optional[dict] = Field(
        default=None,
        description="Optional metadata like request_id"
    )


@dataclass
class VticError(Exception):
    """Base error class for all vtic exceptions.
    
    All vtic errors have:
    - code: Machine-readable error code (one of 6 codes from OpenAPI)
    - status: HTTP status code
    - message: Human-readable error message
    - details: List of ErrorDetail objects (optional)
    - docs: Link to documentation (optional)
    """
    
    code: str = INTERNAL_ERROR
    status: int = 500
    message: str = "An unexpected error occurred"
    details: Optional[List[Dict[str, Any]]] = field(default=None)
    docs: Optional[str] = field(default=None)
    
    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        docs: Optional[str] = None,
        **kwargs
    ):
        """Initialize error with optional details and docs."""
        if message:
            self.message = message
        if details:
            self.details = details
        if docs:
            self.docs = docs
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        super().__init__(self.message)
    
    def to_response(self) -> Dict[str, Any]:
        """Convert error to ErrorResponse dictionary for JSON serialization.
        
        Returns:
            Dict matching ErrorResponse schema.
        """
        error_obj: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        
        if self.details:
            error_obj["details"] = self.details
        
        if self.docs:
            error_obj["docs"] = self.docs
        
        return {"error": error_obj}
    
    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.details:
            parts.append(f"details: {self.details}")
        return " ".join(parts)


# Specific error classes by code

class ValidationError(VticError):
    """Validation failure - missing or invalid fields."""
    code: str = VALIDATION_ERROR
    status: int = 400


class NotFoundError(VticError):
    """Resource not found."""
    code: str = NOT_FOUND
    status: int = 404


class ConflictError(VticError):
    """Conflict - duplicate or invalid state."""
    code: str = CONFLICT
    status: int = 409


class PayloadTooLargeError(VticError):
    """Request payload exceeds size limit."""
    code: str = PAYLOAD_TOO_LARGE
    status: int = 413


class InternalError(VticError):
    """Unexpected internal error."""
    code: str = INTERNAL_ERROR
    status: int = 500


class ServiceUnavailableError(VticError):
    """Service temporarily unavailable."""
    code: str = SERVICE_UNAVAILABLE
    status: int = 503


# Error factory functions

def ticket_not_found(ticket_id: str) -> NotFoundError:
    """Create a NOT_FOUND error for missing ticket."""
    return NotFoundError(
        message=f"Ticket '{ticket_id}' not found",
        details=[{"field": "ticket_id", "message": "No ticket exists with this ID"}]
    )


def validation_failed(field: str, message: str, value: Any = None) -> ValidationError:
    """Create a VALIDATION_ERROR for field validation failures."""
    detail: Dict[str, Any] = {"field": field, "message": message}
    if value is not None:
        detail["value"] = str(value)
    return ValidationError(
        message=f"Validation failed: {message}",
        details=[detail]
    )


def duplicate_ticket(ticket_id: str) -> ConflictError:
    """Create a CONFLICT error for duplicate ticket ID."""
    return ConflictError(
        message=f"Ticket '{ticket_id}' already exists",
        details=[{"field": "id", "message": "A ticket with this ID already exists"}]
    )


def semantic_search_unavailable() -> ServiceUnavailableError:
    """Create a SERVICE_UNAVAILABLE error for missing embedding provider."""
    return ServiceUnavailableError(
        message="Semantic search requested but no embedding provider is configured",
        details=[
            {"field": "semantic", "message": "Set 'semantic: false' or configure an embedding provider"}
        ],
        docs="https://vtic.ejai.ai/docs/semantic-search"
    )


def payload_too_large(max_size: int, actual_size: int) -> PayloadTooLargeError:
    """Create a PAYLOAD_TOO_LARGE error."""
    return PayloadTooLargeError(
        message=f"Request body too large: {actual_size} bytes (max: {max_size})",
        details=[{"field": "body", "message": f"Maximum allowed size is {max_size} bytes"}]
    )


def index_error(detail: str) -> InternalError:
    """Create an INTERNAL_ERROR for index failures."""
    return InternalError(
        message=f"Search index error: {detail}",
        details=[{"message": detail}]
    )
