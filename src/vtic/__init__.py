"""vtic package exports."""

from __future__ import annotations

__version__ = "0.1.0"


class TicketService:  # pragma: no cover - Phase 1 forward reference only
    """Forward reference placeholder until ticket service is implemented."""


def __getattr__(name: str):
    if name == "VticConfig":
        from .config import VticConfig

        return VticConfig
    if name in {"Ticket", "TicketCreate", "TicketUpdate"}:
        from .models import Ticket, TicketCreate, TicketUpdate

        return {
            "Ticket": Ticket,
            "TicketCreate": TicketCreate,
            "TicketUpdate": TicketUpdate,
        }[name]
    if name == "TicketStore":
        from .storage import TicketStore

        return TicketStore
    if name == "TicketService":
        return TicketService
    raise AttributeError(name)


__all__ = [
    "__version__",
    "Ticket",
    "TicketCreate",
    "TicketUpdate",
    "TicketService",
    "VticConfig",
    "TicketStore",
]
