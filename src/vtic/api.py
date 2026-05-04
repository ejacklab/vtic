"""FastAPI application for the vtic HTTP API."""

from __future__ import annotations

import re
from datetime import date, datetime
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
    Severity,
    Status,
    TicketCreate,
    TicketResponse,
    TicketUpdate,
)
from vtic.search import TicketSearch
from vtic.storage import TicketStore
from vtic.utils import parse_repo, slugify, utc_now


_TICKET_ID_PATTERN = re.compile(r"^[A-Z]+-\d+$")


def _validate_ticket_id(ticket_id: str) -> str:
    """Validate and normalize a ticket ID path parameter."""
    normalized = ticket_id.strip().upper()
    if not _TICKET_ID_PATTERN.match(normalized):
        from vtic.errors import ValidationError as VticValidationError
        raise VticValidationError(f"Invalid ticket ID format: {ticket_id}")
    return normalized


def _error_json(error: ErrorResponse) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content=error.model_dump())


def _validation_error_response(exc: RequestValidationError | PydanticValidationError) -> JSONResponse:
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed"
    if any(error["type"] == "json_invalid" for error in exc.errors()):
        error_code = "INVALID_REQUEST"
        message = "Invalid request body"
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"] if part != "body") or None,
            message=error["msg"],
            code=error["type"],
        )
        for error in exc.errors()
    ]
    response = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        status_code=400,
    )
    return _error_json(response)


def create_app(tickets_dir: str | None = None) -> FastAPI:
    """Create the vtic FastAPI application."""

    config = load_config()
    base_dir = Path(tickets_dir) if tickets_dir is not None else config.effective_tickets_dir
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
        responses={400: {"model": ErrorResponse}},
    )
    async def create_ticket(payload: TicketCreate) -> TicketResponse:
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
            due_date=payload.due_date,
            start_date=payload.start_date,
        )
        return TicketResponse.from_ticket(ticket)

    @app.get(
        "/tickets",
        response_model=PaginatedResponse[TicketResponse],
        responses={400: {"model": ErrorResponse}},
    )
    async def list_tickets(
        severity: Severity | None = Query(None),
        status_value: Status | None = Query(None, alias="status"),
        category: str | None = Query(None),
        repo: str | None = Query(None),
        owner: str | None = Query(None),
        tags: list[str] | None = Query(None),
        created_after: datetime | None = Query(None),
        created_before: datetime | None = Query(None),
        updated_after: datetime | None = Query(None),
        updated_before: datetime | None = Query(None),
        due_before: date | None = Query(None),
        due_after: date | None = Query(None),
        start_before: date | None = Query(None),
        start_after: date | None = Query(None),
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> PaginatedResponse[TicketResponse]:
        filters = SearchFilters(
            severity=[severity] if severity else None,
            status=[status_value] if status_value else None,
            category=[category] if category else None,
            repo=[repo] if repo else None,
            owner=owner,
            tags=tags,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            due_before=due_before,
            due_after=due_after,
            start_before=start_before,
            start_after=start_after,
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
    async def get_ticket(ticket_id: str) -> TicketResponse:
        ticket_id = _validate_ticket_id(ticket_id)
        return TicketResponse.from_ticket(store.get(ticket_id))

    @app.patch(
        "/tickets/{ticket_id}",
        response_model=TicketResponse,
        responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    async def update_ticket(ticket_id: str, payload: TicketUpdate) -> TicketResponse:
        ticket_id = _validate_ticket_id(ticket_id)
        return TicketResponse.from_ticket(store.update(ticket_id, payload))

    @app.delete(
        "/tickets/{ticket_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={404: {"model": ErrorResponse}},
    )
    async def delete_ticket(ticket_id: str, force: bool = False) -> Response:
        ticket_id = _validate_ticket_id(ticket_id)
        store.delete(ticket_id, force=force)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post(
        "/search",
        response_model=SearchResponse,
        responses={400: {"model": ErrorResponse}},
    )
    async def search_tickets(payload: SearchRequest) -> SearchResponse:
        return search.search(
            payload.query,
            filters=payload.filters,
            topk=payload.topk,
            offset=payload.offset,
        )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        tickets, errors = store.list_with_errors()
        corrupted_tickets = [detail.field for detail in errors if detail.field]
        is_healthy = not errors
        return HealthResponse(
            status="healthy" if is_healthy else "degraded",
            ticket_count=len(tickets),
            index_status="ready" if is_healthy else "corrupted",
            version=__version__,
            timestamp=utc_now().isoformat(),
            checks={"storage": is_healthy, "search": is_healthy},
            corrupted_tickets=corrupted_tickets,
        )

    return app


__all__ = ["create_app"]
