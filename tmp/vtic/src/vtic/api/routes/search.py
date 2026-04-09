"""Search routes for vtic API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import ValidationError as PydanticValidationError

from vtic.models.search import SearchQuery, SearchResult, SuggestResult
from vtic.models.api import ErrorResponse
from vtic.errors import (
    VticError,
    ValidationError,
    InternalError,
    semantic_search_unavailable,
)
from ..deps import get_search_engine

router = APIRouter()


@router.post(
    "",
    response_model=SearchResult,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Semantic search unavailable"},
    },
    summary="Hybrid search for tickets",
)
async def search_tickets(
    request: Request,
    query: SearchQuery,
    explain: bool = Query(default=False, description="Show scoring breakdown"),
    engine = Depends(get_search_engine),
) -> SearchResult:
    """Execute hybrid BM25 search for tickets.

    Args:
        request: FastAPI request object
        query: SearchQuery with search parameters
        explain: Include BM25/semantic scores in response
        engine: SearchEngine instance from dependency injection

    Returns:
        SearchResult with hits, total count, and metadata

    Raises:
        ValidationError: If query validation fails
        ServiceUnavailableError: If semantic=True but no embedding provider configured
    """
    try:
        # Check if semantic search is requested but unavailable
        if query.semantic:
            # Check if engine has embedding provider configured
            # Engine exposes config or has a method to check semantic availability
            has_semantic = getattr(engine, "has_semantic_provider", lambda: False)()
            if not has_semantic:
                raise semantic_search_unavailable()

        request_id = getattr(request.state, "request_id", None)
        result = engine.search(query, request_id)
        return result
    except VticError:
        raise
    except PydanticValidationError as e:
        raise ValidationError(
            message="Request validation failed",
            details=[
                {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                for err in e.errors()
            ],
        )
    except Exception as e:
        raise InternalError(message=f"Search failed: {e}")


@router.get(
    "/suggest",
    response_model=list[SuggestResult],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameter"},
    },
    summary="Get autocomplete suggestions",
)
async def suggest_search(
    q: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Partial query string (min 2 characters)",
    ),
    limit: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of suggestions (1-20, default: 5)",
    ),
    engine = Depends(get_search_engine),
) -> list[SuggestResult]:
    """Get autocomplete suggestions based on partial query.

    Args:
        q: Partial query string (minimum 2 characters)
        limit: Maximum number of suggestions to return
        engine: SearchEngine instance from dependency injection

    Returns:
        List of SuggestResult with matching ticket titles/phrases

    Raises:
        ValidationError: If query parameter validation fails
    """
    try:
        return engine.suggest(q, limit)
    except VticError:
        raise
    except Exception as e:
        raise InternalError(message=f"Suggestion failed: {e}")
