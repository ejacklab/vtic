from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from vtic.models import Severity, Status, Ticket
from vtic.utils import slugify


FIXED_TIMESTAMP = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)



def make_ticket(
    id: str,
    title: str,
    *,
    repo: str = "owner/repo",
    category: str = "code_quality",
    severity: Severity = Severity.MEDIUM,
    status: Status = Status.OPEN,
    description: str | None = None,
    fix: str | None = None,
    owner: str | None = "owner",
    file: str | None = None,
    tags: list[str] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    due_date: date | None = None,
) -> Ticket:
    """Create a test ticket with sensible defaults."""
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
        due_date=due_date,
    )



@pytest.fixture
def sample_timestamp() -> datetime:
    return datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def sample_ticket(sample_timestamp: datetime) -> Ticket:
    return Ticket(
        id="S-1",
        title="CORS Wildcard in Production",
        description="All FastAPI services use allow_origins=['*'].",
        fix="Use ALLOWED_ORIGINS from env.",
        repo="ejacklab/open-dsearch",
        owner="smoke01",
        category="security",
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
            id="C-2",
            title="Duplicated auth helpers across services",
            description="Helpers drift across services.",
            fix=None,
            repo="ejacklab/open-dsearch",
            owner="smoke01",
            category="code_quality",
            severity=Severity.HIGH,
            status=Status.ACTIVE,
            file="backend/auth/utils.py:1-120",
            tags=["auth", "refactor", "duplication"],
            created_at=sample_timestamp,
            updated_at=sample_timestamp,
            slug="duplicated-auth-helpers-across-services",
        ),
    ]
