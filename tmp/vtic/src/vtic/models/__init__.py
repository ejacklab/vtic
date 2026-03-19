"""vtic models package."""

from vtic.models.enums import (
    Category,
    Severity,
    Status,
    VALID_STATUS_TRANSITIONS,
    TERMINAL_STATUSES,
)
from vtic.models.ticket import (
    Ticket,
    TicketCreate,
    TicketUpdate,
    TicketSummary,
    TicketResponse,
    TicketListResponse,
    ErrorDetail,
    ErrorBody,
    ErrorResponse,
)

__all__ = [
    # Enums
    "Category",
    "Severity",
    "Status",
    "VALID_STATUS_TRANSITIONS",
    "TERMINAL_STATUSES",
    # Ticket Models
    "Ticket",
    "TicketCreate",
    "TicketUpdate",
    "TicketSummary",
    "TicketResponse",
    "TicketListResponse",
    # Error Models
    "ErrorDetail",
    "ErrorBody",
    "ErrorResponse",
]
