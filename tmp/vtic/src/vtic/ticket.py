"""Ticket Service - Orchestrator for markdown store + Zvec index.

This module provides the TicketService class that coordinates between
the markdown file storage and Zvec vector index to keep them in sync.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vtic.models.config import Config, load_config
from vtic.models.ticket import Ticket, TicketCreate, TicketUpdate, TicketSummary
from vtic.models.enums import Category, Severity, Status, VALID_STATUS_TRANSITIONS
from vtic.errors import NotFoundError, ValidationError
from vtic.store import paths as store_paths
from vtic.store import markdown as store_markdown
from vtic.index import client as index_client
from vtic.index import operations as index_ops


def _generate_slug(title: str) -> str:
    """Generate URL-safe slug from title."""
    slug = title.lower()
    slug = "".join(c if c.isalnum() or c.isspace() else " " for c in slug)
    words = slug.split()
    slug = "-".join(words)
    if len(slug) > 80:
        slug = slug[:80].rsplit("-", 1)[0]
    slug = slug.strip("-")
    return slug


class TicketService:
    """Service class that orchestrates markdown store + Zvec index.
    
    Each method performs BOTH file + index operations to keep them in sync.
    
    All public methods are async to work with FastAPI routes, but internally
    they call sync store/index operations.
    """
    
    def __init__(self, config: Config | None = None):
        """Initialize the ticket service.
        
        Args:
            config: Optional configuration. If None, loads default config.
        """
        self.config = config or load_config()
        self.base_dir = self.config.storage.dir
        self._initialized = False
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Zvec collection
        self.collection = index_client.get_collection(self.base_dir)
    
    async def initialize(self) -> None:
        """Initialize the service (async for API compatibility).
        
        This is a no-op since initialization happens in __init__.
        Provided for FastAPI lifespan compatibility.
        """
        self._initialized = True
    
    async def close(self) -> None:
        """Close the service and release resources (async for API compatibility).
        
        This is a no-op for now. Provided for FastAPI lifespan compatibility.
        """
        self._initialized = False
    
    def _get_next_id(self, category: Category) -> str:
        """Generate next sequential ID for a category.
        
        Scans existing tickets on disk for the same category prefix,
        extracts numbers, finds max, and increments.
        
        Args:
            category: The ticket category.
            
        Returns:
            Next ID string like "C1", "H5", "F12", etc.
        """
        prefix = Category.get_prefix(category)
        
        # Scan all existing tickets
        max_num = 0
        if self.base_dir.exists():
            for path in self.base_dir.rglob("*.md"):
                # Skip trash directory and hidden files
                if ".trash" in path.parts or path.name.startswith("."):
                    continue
                
                # Check if filename starts with our prefix followed by digits
                match = re.match(rf"{prefix}(\d+)-", path.name)
                if match:
                    num = int(match.group(1))
                    max_num = max(max_num, num)
        
        return f"{prefix}{max_num + 1}"
    
    def _validate_status_transition(self, current: Status, new: Status) -> None:
        """Validate that a status transition is allowed.
        
        Args:
            current: Current status.
            new: Target status.
            
        Raises:
            ValidationError: If the transition is not allowed.
        """
        if current == new:
            return
        
        allowed = VALID_STATUS_TRANSITIONS.get(current, set())
        if new not in allowed:
            raise ValidationError(
                message=f"Invalid status transition from '{current.value}' to '{new.value}'",
                details=[{
                    "field": "status",
                    "message": f"Cannot transition from {current.value} to {new.value}",
                    "value": new.value
                }]
            )
    
    def _ticket_to_dict(self, ticket: Ticket) -> dict[str, Any]:
        """Convert Ticket model to dictionary for storage.
        
        Args:
            ticket: Ticket model.
            
        Returns:
            Dictionary representation.
        """
        return {
            "id": ticket.id,
            "slug": ticket.slug,
            "title": ticket.title,
            "description": ticket.description,
            "repo": ticket.repo,
            "category": ticket.category.value,
            "severity": ticket.severity.value,
            "status": ticket.status.value,
            "assignee": ticket.assignee,
            "fix": ticket.fix,
            "tags": ticket.tags,
            "references": ticket.references,
            "created": ticket.created.isoformat() if ticket.created else None,
            "updated": ticket.updated.isoformat() if ticket.updated else None,
        }
    
    def _dict_to_ticket(self, data: dict[str, Any]) -> Ticket:
        """Convert dictionary to Ticket model.
        
        Args:
            data: Ticket dictionary.
            
        Returns:
            Ticket model.
        """
        # Parse datetime fields
        created = data.get("created")
        updated = data.get("updated")
        
        if isinstance(created, str):
            created = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        
        return Ticket(
            id=data["id"],
            slug=data.get("slug"),
            title=data["title"],
            description=data["description"],
            repo=data["repo"],
            category=Category(data["category"]),
            severity=Severity(data["severity"]),
            status=Status(data["status"]),
            assignee=data.get("assignee"),
            fix=data.get("fix"),
            tags=data.get("tags", []),
            references=data.get("references", []),
            created=created,
            updated=updated,
        )
    
    def _ticket_to_summary(self, ticket: Ticket) -> TicketSummary:
        """Convert Ticket to TicketSummary.
        
        Args:
            ticket: Full ticket model.
            
        Returns:
            TicketSummary with essential fields only.
        """
        return TicketSummary(
            id=ticket.id,
            title=ticket.title,
            severity=ticket.severity,
            status=ticket.status,
            repo=ticket.repo,
            category=ticket.category,
            created=ticket.created,
            assignee=ticket.assignee,
            updated=ticket.updated,
        )
    
    async def create_ticket(self, data: TicketCreate) -> Ticket:
        """Create a new ticket.
        
        Steps:
        1. Generate ID: category_prefix + next_sequence_number
        2. Generate slug from title
        3. Auto-fill timestamps (created, updated = now)
        4. Build Ticket dict
        5. Write markdown file
        6. Insert into Zvec index
        7. Return Ticket model
        
        Args:
            data: Ticket creation data.
            
        Returns:
            Created ticket model.
        """
        # Determine category (default to GENERAL)
        category = data.category or Category.GENERAL
        
        # Generate ID
        ticket_id = self._get_next_id(category)
        
        # Generate slug from title
        slug = _generate_slug(data.title)
        
        # Auto-fill timestamps
        now = datetime.now(timezone.utc)
        
        # Build Ticket
        ticket = Ticket(
            id=ticket_id,
            slug=slug,
            title=data.title,
            description=data.description,
            repo=data.repo,
            category=category,
            severity=data.severity or Severity.MEDIUM,
            status=data.status or Status.OPEN,
            assignee=data.assignee,
            fix=None,  # fix is not set on creation, only via update
            tags=data.tags,
            references=data.references,
            created=now,
            updated=now,
        )
        
        # Convert to dict for storage
        ticket_dict = self._ticket_to_dict(ticket)
        
        # Build file path
        file_path = store_paths.ticket_file_path(
            self.base_dir,
            ticket.repo,
            ticket.category.value,
            ticket.id,
            ticket.slug or ""
        )
        
        # Write markdown file
        store_markdown.write_ticket(file_path, ticket_dict)
        
        # Insert into Zvec index
        index_ops.insert_tickets(self.collection, [ticket_dict])
        
        return ticket
    
    async def get_ticket(self, ticket_id: str) -> Ticket:
        """Get a ticket by ID.
        
        Steps:
        1. Fetch from Zvec index
        2. If not found → read from disk
        3. If still not found → raise NotFoundError
        4. Return Ticket model
        
        Args:
            ticket_id: Ticket ID (e.g., "C1", "H5").
            
        Returns:
            Ticket model.
            
        Raises:
            NotFoundError: If ticket not found.
        """
        # Try Zvec index first
        ticket_dict = index_ops.fetch_ticket(self.collection, ticket_id)
        
        if ticket_dict is None:
            # Fallback to disk
            paths = store_paths.resolve_path(self.base_dir, ticket_id)
            
            # Filter out trash directory
            paths = [p for p in paths if ".trash" not in p.parts]
            
            if not paths:
                raise NotFoundError(
                    message=f"Ticket '{ticket_id}' not found",
                    details=[{"field": "ticket_id", "message": "No ticket exists with this ID"}]
                )
            
            # Read first matching file
            ticket_dict = store_markdown.read_ticket(paths[0])
            if ticket_dict is None:
                raise NotFoundError(
                    message=f"Ticket '{ticket_id}' not found",
                    details=[{"field": "ticket_id", "message": "No ticket exists with this ID"}]
                )
        
        return self._dict_to_ticket(ticket_dict)
    
    async def update_ticket(self, ticket_id: str, data: TicketUpdate) -> Ticket:
        """Update an existing ticket.
        
        Steps:
        1. Get existing ticket
        2. Merge update fields (handle description_append)
        3. Update timestamp (updated = now)
        4. Write updated markdown file
        5. Upsert into Zvec index
        6. Validate status transition if status changed
        7. Return updated Ticket model
        
        Args:
            ticket_id: Ticket ID to update.
            data: Update data (partial).
            
        Returns:
            Updated ticket model.
            
        Raises:
            NotFoundError: If ticket not found.
            ValidationError: If status transition is invalid.
        """
        # Get existing ticket
        existing = await self.get_ticket(ticket_id)
        
        # Track if status is being changed
        new_status = data.status
        if new_status is not None and new_status != existing.status:
            # Validate status transition
            self._validate_status_transition(existing.status, new_status)
        
        # Merge update fields
        updates = data.model_dump(exclude_unset=True)
        
        # Handle description_append specially
        description_append = updates.pop("description_append", None)
        
        # Build updated fields
        updated_data = self._ticket_to_dict(existing)
        
        for key, value in updates.items():
            if key == "category" and value is not None:
                updated_data[key] = value.value if isinstance(value, Category) else value
            elif key == "severity" and value is not None:
                updated_data[key] = value.value if isinstance(value, Severity) else value
            elif key == "status" and value is not None:
                updated_data[key] = value.value if isinstance(value, Status) else value
            elif value is not None:
                updated_data[key] = value
        
        # Append to description if requested
        if description_append:
            updated_data["description"] = updated_data.get("description", "") + description_append
        
        # Update timestamp
        updated_data["updated"] = datetime.now(timezone.utc).isoformat()
        
        # Convert back to Ticket model for validation
        updated_ticket = self._dict_to_ticket(updated_data)
        
        # Build file path
        file_path = store_paths.ticket_file_path(
            self.base_dir,
            updated_ticket.repo,
            updated_ticket.category.value,
            updated_ticket.id,
            updated_ticket.slug or ""
        )
        
        # Write updated markdown file
        store_markdown.write_ticket(file_path, updated_data)
        
        # Upsert into Zvec index
        index_ops.upsert_ticket(self.collection, updated_data)
        
        return updated_ticket
    
    async def delete_ticket(self, ticket_id: str, mode: str = "soft") -> None:
        """Delete a ticket.
        
        Steps:
        1. Resolve path on disk
        2. Delete from disk (soft/hard)
        3. Delete from Zvec index
        4. If ticket not found → raise NotFoundError
        
        Args:
            ticket_id: Ticket ID to delete.
            mode: "soft" (move to trash) or "hard" (permanent delete).
            
        Raises:
            NotFoundError: If ticket not found.
            ValueError: If mode is invalid.
        """
        # Resolve path on disk
        paths = store_paths.resolve_path(self.base_dir, ticket_id)
        if not paths:
            raise NotFoundError(
                message=f"Ticket '{ticket_id}' not found",
                details=[{"field": "ticket_id", "message": "No ticket exists with this ID"}]
            )
        
        file_path = paths[0]
        
        # Delete from disk
        store_markdown.delete_ticket(file_path, mode=mode, trash_dir=self.base_dir / ".trash")
        
        # Delete from Zvec index
        index_ops.delete_ticket(self.collection, ticket_id)
    
    async def list_tickets(
        self,
        repo: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0
    ) -> list[TicketSummary]:
        """List tickets with optional filtering and pagination.
        
        Steps:
        1. List files from disk with filters
        2. Parse each file
        3. Apply additional filters (severity, status)
        4. Sort by created desc
        5. Apply pagination (limit/offset)
        6. Return list of TicketSummary
        
        Args:
            repo: Filter by repository (owner/repo format).
            category: Filter by category.
            severity: Filter by severity.
            status: Filter by status.
            limit: Maximum number of results.
            offset: Pagination offset.
            
        Returns:
            List of ticket summaries.
        """
        # Handle category-only filter by scanning all repos
        if category and not repo:
            # Scan all category directories across all repos
            # Structure: base_dir/owner/repo/category/*.md
            files = []
            if self.base_dir.exists():
                for owner_path in self.base_dir.iterdir():
                    if owner_path.is_dir() and not owner_path.name.startswith("."):
                        for repo_path in owner_path.iterdir():
                            if repo_path.is_dir():
                                category_path = repo_path / category
                                if category_path.exists():
                                    files.extend(category_path.glob("*.md"))
        else:
            # Use standard list_tickets for repo and/or category
            files = store_markdown.list_tickets(self.base_dir, repo=repo, category=category)
        
        # Parse and filter
        tickets: list[Ticket] = []
        for file_path in files:
            try:
                ticket_dict = store_markdown.read_ticket(file_path)
                if ticket_dict:
                    ticket = self._dict_to_ticket(ticket_dict)
                    
                    # Apply severity filter
                    if severity and ticket.severity.value != severity:
                        continue
                    
                    # Apply status filter
                    if status and ticket.status.value != status:
                        continue
                    
                    tickets.append(ticket)
            except (ValueError, OSError):
                # Skip files that can't be parsed
                continue
        
        # Sort by created desc
        tickets.sort(key=lambda t: t.created or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        # Apply pagination
        tickets = tickets[offset:offset + limit]
        
        # Convert to summaries
        return [self._ticket_to_summary(t) for t in tickets]
    
    async def count_tickets(
        self,
        repo: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> int:
        """Count tickets with optional filtering.
        
        Args:
            repo: Filter by repository (owner/repo format).
            category: Filter by category.
            severity: Filter by severity.
            status: Filter by status.
            
        Returns:
            Count of matching tickets.
        """
        # Reuse list_tickets with high limit to get count
        results = await self.list_tickets(
            repo=repo,
            category=category,
            severity=severity,
            status=status,
            limit=10000,  # High limit to get all matching tickets
            offset=0
        )
        return len(results)
    
    async def reindex_all(self) -> dict:
        """Rebuild Zvec index from markdown files.
        
        Returns:
            Dict with {processed, skipped, failed, duration_ms, errors}.
        """
        return index_ops.rebuild_index(self.collection, self.base_dir)
