"""FastAPI application for vtic API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vtic.models.config import Config
from vtic.errors import VticError, ValidationError, ErrorResponse as VticErrorResponse
from .deps import get_config, set_config
from .routes import tickets, search, system, priority, dashboard

# App start time for uptime calculation
_app_start_time: datetime = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup: load config, init TicketService
    config = get_config()
    set_config(config)
    
    # Import TicketService here to avoid circular imports
    try:
        from vtic.ticket import TicketService
        ticket_service = TicketService(config)
        app.state.ticket_service = ticket_service
        app.state.config = config
        
        # Initialize index if needed
        await ticket_service.initialize()
    except ImportError:
        # TicketService not available yet - create a placeholder
        app.state.ticket_service = None
        app.state.config = config
    
    yield
    
    # Shutdown: cleanup
    if hasattr(app.state, 'ticket_service') and app.state.ticket_service:
        await app.state.ticket_service.close()


def create_app(config: Config | None = None) -> FastAPI:
    """Create and configure the FastAPI application.
    
    Args:
        config: Optional config to use (for testing)
        
    Returns:
        Configured FastAPI application
    """
    # Use provided config or load default
    if config is not None:
        set_config(config)
    
    app = FastAPI(
        title="vtic",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
    app.include_router(search.router, prefix="/search", tags=["Search"])
    app.include_router(system.router, tags=["System", "Management"])
    app.include_router(priority.router, prefix="/api", tags=["Priority"])
    app.include_router(dashboard.router)
    
    # Register error handlers
    @app.exception_handler(VticError)
    async def vtic_error_handler(request: Request, exc: VticError):
        """Handle VticError exceptions."""
        return JSONResponse(
            status_code=exc.status,
            content=VticErrorResponse(
                error={
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "docs": exc.docs,
                }
            ).model_dump(),
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Handle FastAPI validation errors (422) and convert to 400 VALIDATION_ERROR."""
        details = [
            {
                "field": ".".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "value": str(err.get("input")) if err.get("input") is not None else None,
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=400,
            content=VticErrorResponse(
                error={
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": details,
                }
            ).model_dump(),
        )
    
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        """Handle generic exceptions."""
        return JSONResponse(
            status_code=500,
            content=VticErrorResponse(
                error={
                    "code": "INTERNAL_ERROR",
                    "message": str(exc) or "An unexpected error occurred",
                }
            ).model_dump(),
        )
    
    return app


# Default app instance for uvicorn
app = create_app()
