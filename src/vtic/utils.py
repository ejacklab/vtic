"""Utility helpers for vtic."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from .models import Ticket


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""

    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    slug = slug.strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:100]


def utc_now() -> datetime:
    """Return current UTC datetime."""

    return datetime.now(UTC)


def isoformat_z(dt: datetime) -> str:
    """Serialize a datetime as ISO 8601 in UTC with a Z suffix."""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.isoformat().replace("+00:00", "Z")


def parse_repo(repo: str) -> tuple[str, str]:
    """Parse an owner/repo string into its components."""

    parts = repo.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid repo format: {repo}. Expected: 'owner/repo'")
    return parts[0], parts[1]


def normalize_tags(tags: list[str]) -> list[str]:
    """Normalize tags using the same rules as the Ticket model."""

    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        clean = tag.lower().strip()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized


def ticket_path(root: Path, ticket: Ticket) -> Path:
    """Build the on-disk path for a ticket."""

    owner, repo_name = parse_repo(ticket.repo)
    return root / owner / repo_name / ticket.category.value / ticket.filename

