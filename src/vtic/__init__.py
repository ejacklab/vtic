"""vtic package exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import VticConfig
from .models import Ticket, TicketCreate, TicketUpdate
from .storage import TicketStore

__version__ = "0.1.0"

if TYPE_CHECKING:
    from .ticket import TicketService
else:
    class TicketService:  # pragma: no cover - Phase 1 forward reference only
        """Forward reference placeholder until ticket service is implemented."""


__all__ = [
    "__version__",
    "Ticket",
    "TicketCreate",
    "TicketUpdate",
    "TicketService",
    "VticConfig",
    "TicketStore",
]
