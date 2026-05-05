"""vtic package exports."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str):
    if name == "VticConfig":
        from .config import VticConfig

        return VticConfig
    if name in {"Ticket", "TicketCreate", "TicketUpdate", "CheckItem"}:
        from .models import Ticket, TicketCreate, TicketUpdate, CheckItem

        return {
            "Ticket": Ticket,
            "TicketCreate": TicketCreate,
            "TicketUpdate": TicketUpdate,
            "CheckItem": CheckItem,
        }[name]
    if name == "TicketStore":
        from .storage import TicketStore

        return TicketStore
    raise AttributeError(name)


__all__ = [
    "__version__",
    "Ticket",
    "TicketCreate",
    "TicketUpdate",
    "VticConfig",
    "TicketStore",
    "CheckItem",
]
