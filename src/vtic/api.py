"""FastAPI application for the vtic HTTP API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from vtic import __version__
from vtic.config import load_config
from vtic.errors import VticError
from vtic.models import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    Ticket,
    TicketCreate,
    TicketResponse,
    TicketUpdate,
)
from vtic.search import TicketSearch
from vtic.storage import TicketStore
from vtic.utils import parse_repo, slugify, utc_now


def _error_json(error: ErrorResponse) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content=error.model_dump())


def _validation_error_response(exc: RequestValidationError | PydanticValidationError) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"] if part != "body") or None,
            message=error["msg"],
            code=error["type"],
        )
        for error in exc.errors()
    ]
    response = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details=details,
        status_code=422,
    )
    return _error_json(response)


def create_app(tickets_dir: str | None = None) -> FastAPI:
    """Create the vtic FastAPI application."""

    config = load_config()
    base_dir = Path(tickets_dir) if tickets_dir is not None else config.tickets.dir
    store = TicketStore(base_dir)
    search = TicketSearch(store)

    app = FastAPI(title="vtic API", version=__version__)
    app.state.store = store
    app.state.search = search

    @app.exception_handler(VticError)
    async def handle_vtic_error(_: Request, exc: VticError) -> JSONResponse:
        return _error_json(exc.to_response())

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _validation_error_response(exc)

    @app.exception_handler(PydanticValidationError)
    async def handle_pydantic_validation_error(
        _: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        return _validation_error_response(exc)

    @app.post(
        "/tickets",
        response_model=TicketResponse,
        status_code=status.HTTP_201_CREATED,
        responses={422: {"model": ErrorResponse}},
    )
    def create_ticket(payload: TicketCreate) -> TicketResponse:
        repo_owner, repo_name = parse_repo(payload.repo)
        normalized_repo = f"{repo_owner.lower()}/{repo_name.lower()}"
        ticket = store.create_ticket(
            title=payload.title,
            repo=normalized_repo,
            owner=payload.owner or repo_owner.lower(),
            category=payload.category,
            severity=payload.severity,
            status=payload.status,
            description=payload.description,
            fix=payload.fix,
            file=payload.file,
            tags=payload.tags,
            slug=slugify(payload.title),
        )
        return TicketResponse.from_ticket(ticket)

    @app.get(
        "/tickets",
        response_model=PaginatedResponse[TicketResponse],
        responses={422: {"model": ErrorResponse}},
    )
    def list_tickets(
        severity: str | None = Query(None),
        status_value: str | None = Query(None, alias="status"),
        category: str | None = Query(None),
        repo: str | None = Query(None),
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> PaginatedResponse[TicketResponse]:
        filters = SearchFilters(
            severity=[severity] if severity else None,
            status=[status_value] if status_value else None,
            category=[category] if category else None,
            repo=[repo.lower()] if repo else None,
        )
        tickets = store.list(filters)
        page = tickets[offset : offset + limit]
        data = [TicketResponse.from_ticket(ticket) for ticket in page]
        return PaginatedResponse[TicketResponse].create(
            data=data,
            total=len(tickets),
            limit=limit,
            offset=offset,
        )

    @app.get(
        "/tickets/{ticket_id}",
        response_model=TicketResponse,
        responses={404: {"model": ErrorResponse}},
    )
    def get_ticket(ticket_id: str) -> TicketResponse:
        return TicketResponse.from_ticket(store.get(ticket_id))

    @app.patch(
        "/tickets/{ticket_id}",
        response_model=TicketResponse,
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    def update_ticket(ticket_id: str, payload: TicketUpdate) -> TicketResponse:
        return TicketResponse.from_ticket(store.update(ticket_id, payload))

    @app.delete(
        "/tickets/{ticket_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={404: {"model": ErrorResponse}},
    )
    def delete_ticket(ticket_id: str) -> Response:
        store.delete(ticket_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post(
        "/search",
        response_model=SearchResponse,
        responses={422: {"model": ErrorResponse}},
    )
    def search_tickets(payload: SearchRequest) -> SearchResponse:
        return search.search(
            payload.query,
            filters=payload.filters,
            topk=payload.topk,
            offset=payload.offset,
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        ticket_count = len(store.list())
        return HealthResponse(
            status="healthy",
            ticket_count=ticket_count,
            index_status="ready",
            version=__version__,
            timestamp=utc_now().isoformat(),
            checks={"storage": True, "search": True},
        )

    return app


__all__ = ["create_app"]
