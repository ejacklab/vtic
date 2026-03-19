"""System service for health, stats, reindex, and diagnostics."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from vtic.models.api import (
    HealthResponse,
    StatsResponse,
    StatsTotals,
    DateRange,
    ReindexResult,
    ReindexError,
    DoctorResult,
    DoctorCheck,
)
from vtic.models.config import Config

if TYPE_CHECKING:
    from vtic.ticket import TicketService


class SystemService:
    """System-level operations: health, stats, reindex, diagnostics.
    
    Aggregates data from:
    - TicketService (for counts and reindex)
    - Zvec collection (for index status)
    - Config (for embedding provider info)
    - File system (for doctor checks)
    """
    
    def __init__(
        self,
        config: Config,
        ticket_service: "TicketService",
    ) -> None:
        """Initialize system service.
        
        Args:
            config: Application configuration.
            ticket_service: TicketService instance for counts/reindex.
        """
        self._config = config
        self._ticket_service = ticket_service
    
    async def health(
        self,
        version: str = "0.1.0",
        uptime_seconds: Optional[int] = None,
    ) -> HealthResponse:
        """Get system health status.
        
        Checks:
        - Zvec index availability
        - Ticket count in index
        - Embedding provider status
        
        Args:
            version: API version string.
            uptime_seconds: Server uptime in seconds.
            
        Returns:
            HealthResponse with nested index_status and embedding_provider.
        """
        # Check Zvec collection status
        try:
            from vtic.index.client import get_collection
            collection = get_collection(self._config.storage.dir)
            
            # Try to get ticket count from index
            try:
                # Use collection.count() if available, otherwise count tickets
                if hasattr(collection, 'count'):
                    ticket_count = collection.count()
                else:
                    # Fall back to TicketService
                    ticket_count = await self._ticket_service.count_tickets()
                zvec_status = "available"
            except Exception:
                ticket_count = 0
                zvec_status = "corrupted"
        except Exception:
            zvec_status = "unavailable"
            ticket_count = 0
        
        # Get embedding provider info
        provider = self._config.embeddings.provider
        if provider == "none":
            embedding_provider = None
        else:
            from vtic.models.api import EmbeddingProviderInfo
            embedding_provider = EmbeddingProviderInfo(
                name=provider,
                model=self._config.embeddings.model,
                dimension=self._config.embeddings.dimension,
            )
        
        # Determine overall status
        if zvec_status == "corrupted":
            status = "unhealthy"
        elif zvec_status == "unavailable":
            status = "degraded"
        elif provider == "none":
            status = "degraded"
        else:
            status = "healthy"
        
        return HealthResponse(
            status=status,
            version=version,
            uptime_seconds=uptime_seconds,
            index_status={
                "zvec": zvec_status,
                "ticket_count": ticket_count,
                "last_reindex": None,  # Could be stored in collection metadata
            },
            embedding_provider=embedding_provider,
        )
    
    async def stats(self, by_repo: bool = False) -> StatsResponse:
        """Get ticket statistics.
        
        Aggregates:
        - Total counts (all, open, closed)
        - By status, severity, category
        - Optionally by repo
        - Date range (earliest/latest created)
        
        Args:
            by_repo: Include by_repo breakdown (default False).
            
        Returns:
            StatsResponse with nested totals and breakdowns.
        """
        # Get all tickets
        tickets = await self._ticket_service.list_tickets(
            limit=10000,  # High limit to get all tickets
            offset=0,
        )
        
        # Initialize counters
        all_count = len(tickets)
        open_count = 0
        closed_count = 0
        by_status: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        by_repo_dict: dict[str, int] = {}
        
        earliest: Optional[datetime] = None
        latest: Optional[datetime] = None
        
        # Aggregate counts
        for ticket in tickets:
            # Status counts
            status_val = ticket.status.value
            by_status[status_val] = by_status.get(status_val, 0) + 1
            
            # Open/closed classification
            if status_val in ("open", "in_progress", "blocked"):
                open_count += 1
            elif status_val in ("fixed", "wont_fix", "closed"):
                closed_count += 1
            
            # Severity counts
            severity_val = ticket.severity.value
            by_severity[severity_val] = by_severity.get(severity_val, 0) + 1
            
            # Category counts
            category_val = ticket.category.value
            by_category[category_val] = by_category.get(category_val, 0) + 1
            
            # Repo counts (if requested)
            if by_repo and ticket.repo:
                by_repo_dict[ticket.repo] = by_repo_dict.get(ticket.repo, 0) + 1
            
            # Date range
            if ticket.created:
                if earliest is None or ticket.created < earliest:
                    earliest = ticket.created
                if latest is None or ticket.created > latest:
                    latest = ticket.created
        
        # Build date range
        date_range = None
        if earliest and latest:
            date_range = DateRange(earliest=earliest, latest=latest)
        
        return StatsResponse(
            totals=StatsTotals(
                all=all_count,
                open=open_count,
                closed=closed_count,
            ),
            by_status=by_status,
            by_severity=by_severity,
            by_category=by_category,
            by_repo=by_repo_dict if by_repo else None,
            date_range=date_range,
        )
    
    async def reindex(self) -> ReindexResult:
        """Rebuild the search index from markdown files.
        
        Delegates to TicketService.reindex_all().
        
        Returns:
            ReindexResult with processed/skipped/failed counts.
        """
        start_time = time.time()
        
        # Call TicketService.reindex_all()
        result = await self._ticket_service.reindex_all()
        
        # Convert errors to ReindexError models
        errors = []
        for err in result.get("errors", []):
            if isinstance(err, dict):
                errors.append(ReindexError(
                    ticket_id=err.get("ticket_id", "unknown"),
                    message=err.get("message", "Unknown error"),
                ))
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return ReindexResult(
            processed=result.get("processed", 0),
            skipped=result.get("skipped", 0),
            failed=result.get("failed", 0),
            duration_ms=duration_ms,
            errors=errors,
        )
    
    async def doctor(self) -> DoctorResult:
        """Run diagnostic checks.
        
        Checks:
        - zvec_index: Index health and accessibility
        - config_file: Configuration validity
        - embedding_provider: Provider configuration status
        - file_permissions: Write permissions on tickets directory
        - ticket_files: Scan for malformed markdown files
        
        Returns:
            DoctorResult with overall status and individual checks.
        """
        checks = []
        
        # Check 1: Zvec index
        checks.append(await self._check_zvec_index())
        
        # Check 2: Config file
        checks.append(await self._check_config_file())
        
        # Check 3: Embedding provider
        checks.append(await self._check_embedding_provider())
        
        # Check 4: File permissions
        checks.append(await self._check_file_permissions())
        
        # Check 5: Ticket files
        checks.append(await self._check_ticket_files())
        
        return DoctorResult.create(checks=checks)
    
    async def _check_zvec_index(self) -> DoctorCheck:
        """Check Zvec index health."""
        try:
            from vtic.index.client import get_collection
            collection = get_collection(self._config.storage.dir)
            
            # Try to access the collection
            if hasattr(collection, 'count'):
                count = collection.count()
                return DoctorCheck(
                    name="zvec_index",
                    status="ok",
                    message=f"Index is healthy with {count} tickets",
                    fix=None,
                )
            else:
                return DoctorCheck(
                    name="zvec_index",
                    status="ok",
                    message="Index is accessible",
                    fix=None,
                )
        except FileNotFoundError:
            return DoctorCheck(
                name="zvec_index",
                status="error",
                message="Index file not found",
                fix="Run 'vtic reindex' to rebuild the index",
            )
        except Exception as e:
            return DoctorCheck(
                name="zvec_index",
                status="error",
                message=f"Index error: {str(e)}",
                fix="Run 'vtic reindex' to rebuild the index",
            )
    
    async def _check_config_file(self) -> DoctorCheck:
        """Check configuration validity."""
        try:
            # Config was already loaded successfully if we got here
            # Check for common issues
            issues = []
            
            # Check storage directory
            storage_dir = self._config.storage.dir
            if not storage_dir.exists():
                issues.append("Storage directory does not exist")
            
            # Check API config
            if self._config.api.port < 1 or self._config.api.port > 65535:
                issues.append(f"Invalid API port: {self._config.api.port}")
            
            if issues:
                return DoctorCheck(
                    name="config_file",
                    status="warning",
                    message="; ".join(issues),
                    fix="Update vtic.toml configuration",
                )
            
            return DoctorCheck(
                name="config_file",
                status="ok",
                message="Configuration valid",
                fix=None,
            )
        except Exception as e:
            return DoctorCheck(
                name="config_file",
                status="error",
                message=f"Configuration error: {str(e)}",
                fix="Check vtic.toml for syntax errors",
            )
    
    async def _check_embedding_provider(self) -> DoctorCheck:
        """Check embedding provider configuration."""
        provider = self._config.embeddings.provider
        
        if provider == "none":
            return DoctorCheck(
                name="embedding_provider",
                status="warning",
                message="No embedding provider configured (BM25 only)",
                fix="Set embeddings.provider = 'local' in vtic.toml for semantic search",
            )
        
        # Check if model is set
        if not self._config.embeddings.model:
            return DoctorCheck(
                name="embedding_provider",
                status="warning",
                message=f"Provider '{provider}' has no model configured",
                fix=f"Set embeddings.model in vtic.toml for provider '{provider}'",
            )
        
        return DoctorCheck(
            name="embedding_provider",
            status="ok",
            message=f"{provider} provider using {self._config.embeddings.model}",
            fix=None,
        )
    
    async def _check_file_permissions(self) -> DoctorCheck:
        """Check file system permissions."""
        storage_dir = self._config.storage.dir
        
        try:
            # Check if directory exists
            if not storage_dir.exists():
                return DoctorCheck(
                    name="file_permissions",
                    status="error",
                    message=f"Storage directory does not exist: {storage_dir}",
                    fix=f"Create the directory: mkdir -p {storage_dir}",
                )
            
            # Check read permission
            if not os.access(storage_dir, os.R_OK):
                return DoctorCheck(
                    name="file_permissions",
                    status="error",
                    message=f"Cannot read from storage directory: {storage_dir}",
                    fix=f"Check permissions on {storage_dir}",
                )
            
            # Check write permission
            if not os.access(storage_dir, os.W_OK):
                return DoctorCheck(
                    name="file_permissions",
                    status="error",
                    message=f"Cannot write to storage directory: {storage_dir}",
                    fix=f"Check permissions on {storage_dir}",
                )
            
            return DoctorCheck(
                name="file_permissions",
                status="ok",
                message="All directories writable",
                fix=None,
            )
        except Exception as e:
            return DoctorCheck(
                name="file_permissions",
                status="error",
                message=f"Permission check failed: {str(e)}",
                fix=f"Check permissions on {storage_dir}",
            )
    
    async def _check_ticket_files(self) -> DoctorCheck:
        """Scan for malformed markdown files."""
        storage_dir = self._config.storage.dir
        
        if not storage_dir.exists():
            return DoctorCheck(
                name="ticket_files",
                status="warning",
                message="Storage directory does not exist",
                fix="Create tickets directory or run 'vtic reindex'",
            )
        
        try:
            # Count markdown files
            md_files = list(storage_dir.rglob("*.md"))
            
            if not md_files:
                return DoctorCheck(
                    name="ticket_files",
                    status="ok",
                    message="No ticket files found (empty storage)",
                    fix=None,
                )
            
            # Check for malformed files
            malformed = 0
            for md_file in md_files:
                try:
                    content = md_file.read_text(encoding="utf-8")
                    # Basic check: should have frontmatter between ---
                    if "---" not in content:
                        malformed += 1
                except Exception:
                    malformed += 1
            
            if malformed > 0:
                return DoctorCheck(
                    name="ticket_files",
                    status="warning",
                    message=f"Found {malformed} potentially malformed ticket files out of {len(md_files)}",
                    fix="Run 'vtic doctor --fix' to attempt repairs (not yet implemented)",
                )
            
            return DoctorCheck(
                name="ticket_files",
                status="ok",
                message=f"All {len(md_files)} ticket files look valid",
                fix=None,
            )
        except Exception as e:
            return DoctorCheck(
                name="ticket_files",
                status="error",
                message=f"Failed to scan ticket files: {str(e)}",
                fix="Check storage directory permissions",
            )
