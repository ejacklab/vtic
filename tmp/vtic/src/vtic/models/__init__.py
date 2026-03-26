"""vtic models package."""

from vtic.models.enums import (
    Category,
    Severity,
    Status,
    Urgency,
    Impact,
    PriorityLevel,
    EmbeddingProvider,
    DeleteMode,
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
    PriorityBreakdown,
    ErrorDetail,
    ErrorBody,
    ErrorResponse,
)
from vtic.models.config import (
    PriorityConfig,
)

__all__ = [
    # Enums
    "Category",
    "Severity",
    "Status",
    "Urgency",
    "Impact",
    "PriorityLevel",
    "EmbeddingProvider",
    "DeleteMode",
    "VALID_STATUS_TRANSITIONS",
    "TERMINAL_STATUSES",
    # Ticket Models
    "Ticket",
    "TicketCreate",
    "TicketUpdate",
    "TicketSummary",
    "TicketResponse",
    "TicketListResponse",
    "PriorityBreakdown",
    # Error Models
    "ErrorDetail",
    "ErrorBody",
    "ErrorResponse",
    # Config Models
    "PriorityConfig",
]
