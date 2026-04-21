from __future__ import annotations

from datetime import UTC, datetime

import pytest

from vtic.models import Category, Severity, Status, Ticket
from vtic.utils import slugify


FIXED_TIMESTAMP = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)


def make_ticket(
    ticket_id: str,
    title: str,
    *,
    description: str | None = None,
    repo: str = "owner/repo",
    category: Category = Category.CODE_QUALITY,
    severity: Severity = Severity.MEDIUM,
    status: Status = Status.OPEN,
    fix: str | None = None,
    owner: str | None = "owner",
    file: str | None = None,
    tags: list[str] | None = None,
) -> Ticket:
    """Create a test Ticket with sensible defaults."""
    return Ticket(
        id=ticket_id,
        title=title,
        description=description,
        fix=fix,
        repo=repo,
        owner=owner,
        category=category,
        severity=severity,
        status=status,
        file=file,
        tags=tags or [],
        created_at=FIXED_TIMESTAMP,
        updated_at=FIXED_TIMESTAMP,
        slug=slugify(title),
    )


FIXED_TIMESTAMP = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)


def make_ticket(
    id: str,
    title: str,
    *,
    repo: str = "owner/repo",
    category: Category = Category.CODE_QUALITY,
    severity: Severity = Severity.MEDIUM,
    status: Status = Status.OPEN,
    description: str | None = None,
    fix: str | None = None,
    owner: str | None = "owner",
    file: str | None = None,
    tags: list[str] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Ticket:
    """Create a test ticket with sensible defaults.

    Provides all Ticket fields so callers can override any subset.
    Used across test_storage, test_api, and test_search to avoid
    duplicating helper functions (I8 from Round 1 review).
    """
    ts = created_at or FIXED_TIMESTAMP
    return Ticket(
        id=id,
        title=title,
        description=description,
        fix=fix,
        repo=repo,
        owner=owner,
        category=category,
        severity=severity,
        status=status,
        file=file,
        tags=tags or [],
        created_at=ts,
        updated_at=updated_at or ts,
        slug=slugify(title),
    )


# Re-export slugify so test files that import it from here don't break
from vtic.utils import slugify  # noqa: E402


@pytest.fixture
def sample_timestamp() -> datetime:
    return datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def sample_ticket(sample_timestamp: datetime) -> Ticket:
    return Ticket(
        id="S1",
        title="CORS Wildcard in Production",
        description="All FastAPI services use allow_origins=['*'].",
        fix="Use ALLOWED_ORIGINS from env.",
        repo="ejacklab/open-dsearch",
        owner="smoke01",
        category=Category.SECURITY,
        severity=Severity.CRITICAL,
        status=Status.OPEN,
        file="backend/api-gateway/main.py:27-32",
        tags=["cors", "security", "fastapi"],
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug="cors-wildcard-in-production",
    )


@pytest.fixture
def sample_tickets(sample_ticket: Ticket, sample_timestamp: datetime) -> list[Ticket]:
    return [
        sample_ticket,
        Ticket(
            id="C2",
            title="Duplicated auth helpers across services",
            description="Helpers drift across services.",
            fix=None,
            repo="ejacklab/open-dsearch",
            owner="smoke01",
            category=Category.CODE_QUALITY,
            severity=Severity.HIGH,
            status=Status.IN_PROGRESS,
            file="backend/auth/utils.py:1-120",
            tags=["auth", "refactor", "duplication"],
            created_at=sample_timestamp,
            updated_at=sample_timestamp,
            slug="duplicated-auth-helpers-across-services",
        ),
    ]
