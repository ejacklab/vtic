"""FastAPI routes for vtic API."""

from vtic.api.routes.tickets import router as tickets_router
from vtic.api.routes.search import router as search_router
from vtic.api.routes.system import router as system_router

__all__ = [
    "tickets_router",
    "search_router",
    "system_router",
]
