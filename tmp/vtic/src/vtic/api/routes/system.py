"""System routes for health, stats, reindex, and diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from vtic.models.api import (
    HealthResponse,
    StatsResponse,
    ReindexResult,
    DoctorResult,
    ErrorResponse,
)
from vtic.errors import (
    VticError,
    InternalError,
    ServiceUnavailableError,
)
from ..deps import get_system_service

router = APIRouter()

# App start time for uptime calculation
_app_start_time: datetime = datetime.now(timezone.utc)


def _get_uptime_seconds() -> int:
    """Calculate uptime in seconds."""
    return int((datetime.now(timezone.utc) - _app_start_time).total_seconds())


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        503: {"model": HealthResponse, "description": "System unhealthy"},
    },
    summary="Health check endpoint",
)
async def get_health(
    request: Request,
    service=Depends(get_system_service),
) -> HealthResponse | JSONResponse:
    """Get system health status.
    
    Returns comprehensive health information including:
    - Overall status (healthy, degraded, unhealthy)
    - API version and uptime
    - Index status (zvec availability, ticket count)
    - Embedding provider configuration
    
    Args:
        request: FastAPI request object
        service: SystemService instance
        
    Returns:
        HealthResponse (200) or 503 if unhealthy
    """
    try:
        # Get version from app state or use default
        version = getattr(request.app.state, 'version', "0.1.0")
        uptime_seconds = _get_uptime_seconds()
        
        health_response = await service.health(
            version=version,
            uptime_seconds=uptime_seconds,
        )
        
        # Return 503 if unhealthy
        if health_response.status == "unhealthy":
            return JSONResponse(
                status_code=503,
                content=health_response.model_dump(),
            )
        
        return health_response
    except VticError:
        raise
    except Exception as e:
        raise InternalError(message=f"Health check failed: {e}")


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get ticket statistics",
)
async def get_stats(
    by_repo: bool = Query(default=False, description="Include repo breakdown"),
    service=Depends(get_system_service),
) -> StatsResponse:
    """Get aggregated ticket statistics.
    
    Returns ticket counts broken down by:
    - Totals (all, open, closed)
    - Status (open, in_progress, blocked, fixed, wont_fix, closed)
    - Severity (critical, high, medium, low, info)
    - Category (crash, hotfix, feature, security, general)
    - Repo (optional, only when by_repo=true)
    
    Args:
        by_repo: Include breakdown by repository (default: false)
        service: SystemService instance
        
    Returns:
        StatsResponse with aggregated counts
    """
    try:
        return await service.stats(by_repo=by_repo)
    except VticError:
        raise
    except Exception as e:
        raise InternalError(message=f"Failed to get stats: {e}")


@router.post(
    "/reindex",
    response_model=ReindexResult,
    responses={
        500: {"model": ErrorResponse, "description": "Reindex failed"},
    },
    summary="Rebuild search index",
)
async def reindex(
    service=Depends(get_system_service),
) -> ReindexResult:
    """Rebuild the search index from markdown files.
    
    Re-indexes all tickets found in the storage directory.
    This operation may take some time for large ticket collections.
    
    Args:
        service: SystemService instance
        
    Returns:
        ReindexResult with counts of processed, skipped, and failed tickets
        
    Raises:
        InternalError: If reindex operation fails
    """
    try:
        return await service.reindex()
    except VticError:
        raise
    except Exception as e:
        raise InternalError(message=f"Reindex failed: {e}")


@router.get(
    "/doctor",
    response_model=DoctorResult,
    summary="Run diagnostic checks",
)
async def run_doctor(
    service=Depends(get_system_service),
) -> DoctorResult:
    """Run system diagnostic checks.
    
    Performs 5 diagnostic checks:
    1. zvec_index - Index health and accessibility
    2. config_file - Configuration validity
    3. embedding_provider - Provider configuration status
    4. file_permissions - Write permissions on tickets directory
    5. ticket_files - Scan for malformed markdown files
    
    Args:
        service: SystemService instance
        
    Returns:
        DoctorResult with overall status and individual check results
    """
    try:
        return await service.doctor()
    except VticError:
        raise
    except Exception as e:
        raise InternalError(message=f"Doctor check failed: {e}")
