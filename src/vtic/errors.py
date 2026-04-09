"""Error hierarchy for vtic."""

from __future__ import annotations


from .models import ErrorDetail, ErrorResponse


class VticError(Exception):
    """Base exception for all vtic errors."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 500,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            details=self.details,
            status_code=self.status_code,
        )


class TicketNotFoundError(VticError):
    """Raised when a requested ticket does not exist."""

    def __init__(self, ticket_id: str) -> None:
        super().__init__(
            error_code="TICKET_NOT_FOUND",
            message=f"Ticket {ticket_id} not found",
            status_code=404,
        )


class ValidationError(VticError):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: list[ErrorDetail] | None = None) -> None:
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )


class ConfigError(VticError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(
            error_code="CONFIG_ERROR",
            message=message,
            status_code=500,
        )


class TicketAlreadyExistsError(VticError):
    """Raised when attempting to create a ticket with existing ID."""

    def __init__(self, ticket_id: str) -> None:
        super().__init__(
            error_code="TICKET_ALREADY_EXISTS",
            message=f"Ticket {ticket_id} already exists",
            status_code=409,
        )


class TicketWriteError(VticError):
    """Raised when file system write fails."""

    def __init__(self, ticket_id: str, details: str) -> None:
        super().__init__(
            error_code="TICKET_WRITE_ERROR",
            message=f"Failed to write ticket {ticket_id}: {details}",
            status_code=500,
        )


class TicketReadError(VticError):
    """Raised when file system read fails."""

    def __init__(self, ticket_id: str, details: str) -> None:
        super().__init__(
            error_code="TICKET_READ_ERROR",
            message=f"Failed to read ticket {ticket_id}: {details}",
            status_code=500,
        )


class TicketDeleteError(VticError):
    """Raised when file system delete fails."""

    def __init__(self, ticket_id: str, details: str) -> None:
        super().__init__(
            error_code="TICKET_DELETE_ERROR",
            message=f"Failed to delete ticket {ticket_id}: {details}",
            status_code=500,
        )


class ConflictError(VticError):
    """Raised when optimistic concurrency check fails."""

    def __init__(
        self,
        ticket_id: str,
        expected: int,
        actual: int,
        current_ticket: "Ticket | None" = None,
    ) -> None:
        self.ticket_id = ticket_id
        self.expected = expected
        self.actual = actual
        self.current_ticket = current_ticket
        super().__init__(
            error_code="CONFLICT",
            message=(
                f"Ticket {ticket_id} version conflict: "
                f"expected {expected}, actual {actual}. "
                f"Re-read the ticket and retry."
            ),
            status_code=409,
        )
