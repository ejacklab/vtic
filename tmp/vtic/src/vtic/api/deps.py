"""FastAPI dependencies for vtic API."""

from __future__ import annotations

from typing import Optional

from fastapi import Request, Depends

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


def get_search_engine(config: Config = Depends(get_config)) -> "SearchEngine":  # type: ignore
    """Get SearchEngine instance.
    
    Args:
        config: Config instance
        
    Returns:
        SearchEngine instance
    """
    from vtic.search.engine import SearchEngine
    from vtic.index.client import get_collection
    collection = get_collection(config.storage.dir)
    return SearchEngine(collection)


def get_system_service(
    config: Config = Depends(get_config),
    ticket_service: "TicketService" = Depends(get_ticket_service),  # type: ignore
) -> "SystemService":  # type: ignore
    """Get SystemService instance.
    
    Args:
        config: Config instance
        ticket_service: TicketService instance
        
    Returns:
        SystemService instance
    """
    from vtic.services.system import SystemService
    return SystemService(config, ticket_service)
