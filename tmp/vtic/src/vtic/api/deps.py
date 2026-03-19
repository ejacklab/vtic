"""FastAPI dependencies for vtic API."""

from __future__ import annotations

from typing import Optional

from fastapi import Request

from vtic.models.config import Config, load_config

# Singleton config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or load the vtic configuration.
    
    Returns:
        Config instance (singleton per process)
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: Config) -> None:
    """Set the global config (used for testing).
    
    Args:
        config: Config instance to set
    """
    global _config
    _config = config


def clear_config() -> None:
    """Clear the global config (used for testing)."""
    global _config
    _config = None


def get_ticket_service(request: Request) -> "TicketService":  # type: ignore
    """Get TicketService instance from app state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        TicketService instance
    """
    return request.app.state.ticket_service
