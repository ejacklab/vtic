from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError as PydanticValidationError

from vtic.constants import CATEGORY_PREFIXES as CONSTANT_CATEGORY_PREFIXES
from vtic.constants import TERMINAL_STATUSES
from vtic.models import (
    CATEGORY_PREFIXES,
    Category,
    CategoryLiteral,
    PaginatedResponse,
    SearchFilters,
    SearchRequest,
    Severity,
    SeverityLiteral,
    Status,
    StatusLiteral,
    Ticket,
    TicketCreate,
    TicketResponse,
    TicketUpdate,
)
from vtic.utils import slugify, ticket_path


def test_enum_values_and_string_comparison() -> None:
    assert Severity.CRITICAL == "critical"
    assert Status.IN_PROGRESS == "in_progress"
    assert Category.CODE_QUALITY == "code_quality"
    assert set(get_args(SeverityLiteral)) == {"critical", "high", "medium", "low"}
    assert set(get_args(StatusLiteral)) == {"open", "in_progress", "blocked", "fixed", "wont_fix", "closed"}
    assert set(get_args(CategoryLiteral)) == {category.value for category in Category}


def test_all_enum_values() -> None:
    assert len(Severity) == 4
    assert len(Status) == 6
    assert len(Category) == 15
    assert Severity.LOW.value == "low"
    assert Status.WONT_FIX.value == "wont_fix"
    assert Category.DEPENDENCIES.value == "dependencies"


def test_category_auth_value_is_auth() -> None:
    assert Category.AUTH.value == "auth"


def test_category_prefixes_completeness() -> None:
    assert set(CATEGORY_PREFIXES) == set(Category)
    assert {category.value: prefix for category, prefix in CATEGORY_PREFIXES.items()} == CONSTANT_CATEGORY_PREFIXES
    assert CATEGORY_PREFIXES[Category.CODE_QUALITY] == "C"
    assert CATEGORY_PREFIXES[Category.SECURITY] == "S"
    assert CATEGORY_PREFIXES[Category.API] == "X"


def test_ticket_creation_with_all_fields(sample_ticket: Ticket, sample_timestamp: datetime) -> None:
    assert sample_ticket.id == "S1"
    assert sample_ticket.title == "CORS Wildcard in Production"
    assert sample_ticket.repo == "ejacklab/open-dsearch"
    assert sample_ticket.owner == "smoke01"
    assert sample_ticket.category is Category.SECURITY
    assert sample_ticket.severity is Severity.CRITICAL
    assert sample_ticket.status is Status.OPEN
    assert sample_ticket.tags == ["cors", "security", "fastapi"]
    assert sample_ticket.created_at == sample_timestamp
    assert sample_ticket.updated_at == sample_timestamp


def test_ticket_defaults_and_validators(sample_timestamp: datetime) -> None:
    ticket = Ticket(
        id="c7",
        title="  Needs cleanup  ",
        repo="EJackLab/Open-DSearch",
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug=slugify("Needs cleanup"),
        tags=["  Auth ", "auth", "", "Refactor "],
    )

    assert ticket.id == "C7"
    assert ticket.title == "Needs cleanup"
    assert ticket.repo == "ejacklab/open-dsearch"
    assert ticket.category is Category.CODE_QUALITY
    assert ticket.severity is Severity.MEDIUM
    assert ticket.status is Status.OPEN
    assert ticket.tags == ["auth", "refactor"]


def test_ticket_with_due_date(sample_timestamp: datetime) -> None:
    """Ticket accepts optional due_date."""
    ticket = Ticket(
        id="C1",
        title="With due date",
        repo="owner/repo",
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug="with-due-date",
        due_date=date(2026, 6, 1),
    )

    assert ticket.due_date == date(2026, 6, 1)


def test_ticket_without_due_date_is_none(sample_timestamp: datetime) -> None:
    """Ticket due_date defaults to None for backward compatibility."""
    ticket = Ticket(
        id="C1",
        title="No due date",
        repo="owner/repo",
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug="no-due-date",
    )

    assert ticket.due_date is None


def test_ticket_normalizes_newlines_in_title_and_owner(sample_timestamp: datetime) -> None:
    ticket = Ticket(
        id="C8",
        title="Needs\ncleanup",
        repo="owner/repo",
        owner="smoke\n01",
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug="needs-cleanup",
    )

    assert ticket.title == "Needs cleanup"
    assert ticket.owner == "smoke 01"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "bad-1"),
        ("repo", "missing-slash"),
        ("slug", "Bad Slug"),
        ("file", "app.py:1:2"),
    ],
)
def test_ticket_validation_bad_fields(sample_timestamp: datetime, field: str, value: str) -> None:
    data = {
        "id": "C1",
        "title": "Valid",
        "repo": "owner/repo",
        "created_at": sample_timestamp,
        "updated_at": sample_timestamp,
        "slug": "valid",
    }
    data[field] = value

    with pytest.raises(PydanticValidationError):
        Ticket(**data)


def test_ticket_validation_bad_timestamps(sample_timestamp: datetime) -> None:
    with pytest.raises(PydanticValidationError, match="updated_at cannot be earlier than created_at"):
        Ticket(
            id="C1",
            title="Valid",
            repo="owner/repo",
            created_at=sample_timestamp,
            updated_at=sample_timestamp - timedelta(seconds=1),
            slug="valid",
        )


def test_ticket_validation_too_many_tags(sample_timestamp: datetime) -> None:
    with pytest.raises(PydanticValidationError, match="Cannot have more than 50 tags"):
        Ticket(
            id="C1",
            title="Valid",
            repo="owner/repo",
            created_at=sample_timestamp,
            updated_at=sample_timestamp,
            slug="valid",
            tags=[f"tag-{i}" for i in range(51)],
        )


def test_ticket_create_validation_defaults_and_repo_normalization() -> None:
    payload = TicketCreate(
        title="  New ticket  ",
        repo="Owner/Repo",
        tags=["UPPER", "duplicate", "duplicate"],
    )

    assert payload.title == "New ticket"
    assert payload.repo == "owner/repo"
    assert payload.category is Category.CODE_QUALITY
    assert payload.severity is Severity.MEDIUM
    assert payload.status is Status.OPEN
    assert payload.tags == ["upper", "duplicate"]


def test_ticket_create_with_due_date() -> None:
    """TicketCreate accepts due_date."""
    payload = TicketCreate(
        title="Has due date",
        repo="owner/repo",
        due_date=date(2026, 12, 31),
    )

    assert payload.due_date == date(2026, 12, 31)


def test_ticket_create_without_due_date() -> None:
    """TicketCreate without due_date defaults to None."""
    payload = TicketCreate(title="No due date", repo="owner/repo")

    assert payload.due_date is None


def test_ticket_create_with_all_explicit_fields() -> None:
    payload = TicketCreate(
        title="Explicit auth ticket",
        repo="Owner/Repo",
        description="Detailed description.",
        fix="Apply the patch.",
        owner="Smoke01",
        category=Category.AUTH,
        severity=Severity.HIGH,
        status=Status.BLOCKED,
        file="src/auth.py:10-20",
        tags=["Auth", "backend", "Auth"],
    )

    assert payload.title == "Explicit auth ticket"
    assert payload.repo == "owner/repo"
    assert payload.description == "Detailed description."
    assert payload.fix == "Apply the patch."
    assert payload.owner == "Smoke01"
    assert payload.category is Category.AUTH
    assert payload.severity is Severity.HIGH
    assert payload.status is Status.BLOCKED
    assert payload.file == "src/auth.py:10-20"
    assert payload.tags == ["auth", "backend"]


def test_ticket_create_validation_rejects_empty_title() -> None:
    with pytest.raises(PydanticValidationError, match="Title cannot be empty"):
        TicketCreate(title="   ", repo="owner/repo")


def test_ticket_create_rejects_repo_path_traversal() -> None:
    with pytest.raises(PydanticValidationError, match="Repo path segments cannot be '.' or '..'"):
        TicketCreate(title="Traversal", repo="../escape")


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (
            {"title": "", "repo": "owner/repo"},
            "Title cannot be empty",
        ),
        (
            {"title": "   ", "repo": "owner/repo"},
            "Title cannot be empty",
        ),
        (
            {"title": "Valid title", "repo": "noslash"},
            "Invalid repo format",
        ),
        (
            {"title": "Valid title", "repo": "owner/repo", "severity": "urgent"},
            "Input should be",
        ),
    ],
)
def test_ticket_validation_edge_cases(payload: dict[str, object], match: str) -> None:
    with pytest.raises(PydanticValidationError, match=match):
        TicketCreate(**payload)


def test_ticket_update_forbids_extra_fields() -> None:
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        TicketUpdate(title="Updated", invalid="field")


def test_ticket_update_validates_repo_unchanged() -> None:
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        TicketUpdate(repo="owner/other")


def test_ticket_update_set_due_date() -> None:
    """TicketUpdate can set due_date."""
    update = TicketUpdate(due_date=date(2026, 7, 15))
    data = update.model_dump(exclude_unset=True)

    assert data["due_date"] == date(2026, 7, 15)


def test_ticket_update_clear_due_date() -> None:
    """TicketUpdate can clear due_date by setting None."""
    update = TicketUpdate(due_date=None)
    data = update.model_dump(exclude_unset=True)

    assert data["due_date"] is None


def test_ticket_create_forbids_extra_fields() -> None:
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        TicketCreate(title="Valid", repo="owner/repo", unexpected="value")


def test_search_request_forbids_extra_fields() -> None:
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        SearchRequest(query="auth", unexpected="value")


def test_search_request_rejects_semantic_true() -> None:
    with pytest.raises(PydanticValidationError, match="Semantic search is not yet implemented"):
        SearchRequest(query="auth", semantic=True)


def test_search_filters_reject_invalid_created_range() -> None:
    with pytest.raises(
        PydanticValidationError,
        match="created_after cannot be later than created_before",
    ):
        SearchFilters(
            created_after=datetime(2026, 3, 17, 0, 0, tzinfo=UTC),
            created_before=datetime(2026, 3, 16, 0, 0, tzinfo=UTC),
        )


def test_search_filters_reject_invalid_updated_range() -> None:
    with pytest.raises(
        PydanticValidationError,
        match="updated_after cannot be later than updated_before",
    ):
        SearchFilters(
            updated_after=datetime(2026, 3, 17, 0, 0, tzinfo=UTC),
            updated_before=datetime(2026, 3, 16, 0, 0, tzinfo=UTC),
        )


def test_ticket_response_from_ticket(sample_ticket: Ticket) -> None:
    response = TicketResponse.from_ticket(sample_ticket)

    assert response.id == sample_ticket.id
    assert response.category == sample_ticket.category.value
    assert response.severity == sample_ticket.severity.value
    assert response.status == sample_ticket.status.value
    assert response.created_at == sample_ticket.created_at.isoformat()
    assert response.updated_at == sample_ticket.updated_at.isoformat()
    assert response.is_terminal is False
    assert response.filename == sample_ticket.filename
    assert response.filepath == sample_ticket.filepath


def test_ticket_response_includes_due_date(sample_timestamp: datetime) -> None:
    """TicketResponse.from_ticket includes due_date."""
    ticket = Ticket(
        id="C1",
        title="Response test",
        repo="owner/repo",
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug="response-test",
        due_date=date(2026, 10, 1),
    )

    response = TicketResponse.from_ticket(ticket)

    assert response.due_date == "2026-10-01"


def test_ticket_response_none_due_date(sample_timestamp: datetime) -> None:
    """TicketResponse.from_ticket handles None due_date."""
    ticket = Ticket(
        id="C1",
        title="No due",
        repo="owner/repo",
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug="no-due",
    )

    response = TicketResponse.from_ticket(ticket)

    assert response.due_date is None


def test_ticket_properties(sample_ticket: Ticket, tmp_path: Path) -> None:
    assert sample_ticket.is_terminal is False
    assert sample_ticket.filename == "S1-cors-wildcard-in-production.md"
    assert sample_ticket.filepath == "ejacklab/open-dsearch/security/S1-cors-wildcard-in-production.md"
    assert sample_ticket.search_text == (
        "S1 CORS Wildcard in Production All FastAPI services use allow_origins=['*']. "
        "backend/api-gateway/main.py:27-32 Use ALLOWED_ORIGINS from env. cors security fastapi"
    )
    assert ticket_path(tmp_path, sample_ticket) == (
        tmp_path
        / "ejacklab"
        / "open-dsearch"
        / "security"
        / "S1-cors-wildcard-in-production.md"
    )


def test_search_text_includes_fix(sample_timestamp: datetime) -> None:
    ticket = Ticket(
        id="C1",
        title="Shared helper cleanup",
        description="Move auth helpers into one place.",
        fix="Extract helpers into a common module.",
        repo="owner/repo",
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug="shared-helper-cleanup",
    )

    assert "Extract helpers into a common module." in ticket.search_text


def test_terminal_status_property(sample_timestamp: datetime) -> None:
    ticket = Ticket(
        id="C9",
        title="Terminal",
        repo="owner/repo",
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug="terminal",
        status=Status.FIXED,
    )

    assert ticket.is_terminal is True
    assert ticket.status in TERMINAL_STATUSES


def test_slugify_helper_is_stable() -> None:
    assert slugify("Hello, World!!!") == "hello-world"
    assert slugify("Already---Slugged") == "already-slugged"


def test_ticket_direct_validation_edge_cases(sample_timestamp: datetime) -> None:
    """Test Ticket model validation directly for edge cases not covered by TicketCreate."""
    # Empty title after stripping
    with pytest.raises(PydanticValidationError, match="Title cannot be empty"):
        Ticket(
            id="C1", title="", repo="owner/repo",
            created_at=sample_timestamp, updated_at=sample_timestamp, slug="valid",
        )

    # Whitespace-only title
    with pytest.raises(PydanticValidationError, match="Title cannot be empty"):
        Ticket(
            id="C1", title="   ", repo="owner/repo",
            created_at=sample_timestamp, updated_at=sample_timestamp, slug="valid",
        )

    # Invalid repo format - no slash
    with pytest.raises(PydanticValidationError, match="Invalid repo format"):
        Ticket(
            id="C1", title="Valid", repo="noslash",
            created_at=sample_timestamp, updated_at=sample_timestamp, slug="valid",
        )

    # Invalid repo format - too many slashes
    with pytest.raises(PydanticValidationError, match="Invalid repo format"):
        Ticket(
            id="C1", title="Valid", repo="a/b/c",
            created_at=sample_timestamp, updated_at=sample_timestamp, slug="valid",
        )

    # Invalid severity value
    with pytest.raises(PydanticValidationError):
        Ticket(
            id="C1", title="Valid", repo="owner/repo",
            severity="urgent",
            created_at=sample_timestamp, updated_at=sample_timestamp, slug="valid",
        )

    # Repo with dot segments
    with pytest.raises(PydanticValidationError, match="cannot be '\\.' or '\\.\\.'"):
        Ticket(
            id="C1", title="Valid", repo="./repo",
            created_at=sample_timestamp, updated_at=sample_timestamp, slug="valid",
        )


def test_paginated_response_create() -> None:
    """Test PaginatedResponse.create() factory method."""
    resp = PaginatedResponse.create(
        data=[1, 2, 3],
        total=10,
        limit=3,
        offset=0,
    )
    assert resp.data == [1, 2, 3]
    assert resp.total == 10
    assert resp.limit == 3
    assert resp.offset == 0
    assert resp.has_more is True

    # Last page
    resp_last = PaginatedResponse.create(
        data=[10],
        total=10,
        limit=3,
        offset=9,
    )
    assert resp_last.has_more is False

    # Empty result
    resp_empty = PaginatedResponse.create(
        data=[],
        total=0,
        limit=10,
        offset=0,
    )
    assert resp_empty.has_more is False
    assert resp_empty.total == 0


def test_search_filters_normalize_repo_and_tags() -> None:
    """Test SearchFilters normalization of repo and tags."""
    filters = SearchFilters(
        repo=["  Acme/App  ", "OWNER/REPO"],
        tags=["  Auth  ", "auth", "DUPLICATE", "duplicate", ""],
    )
    assert filters.repo == ["acme/app", "owner/repo"]
    assert filters.tags == ["auth", "duplicate"]

    # Empty strings filtered out
    filters_empty = SearchFilters(repo=["  ", ""], tags=["", "  "])
    assert filters_empty.repo is None
    assert filters_empty.tags == []


def test_search_filters_due_date_range() -> None:
    """SearchFilters accepts due_before/due_after."""
    filters = SearchFilters(
        due_after=date(2026, 1, 1),
        due_before=date(2026, 12, 31),
    )

    assert filters.due_after == date(2026, 1, 1)
    assert filters.due_before == date(2026, 12, 31)


def test_ticket_update_none_fields_preserve_existing() -> None:
    """Test that TicketUpdate with None fields does not alter existing values."""
    ts = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)
    base_data = {
        "id": "C1",
        "title": "Original",
        "repo": "owner/repo",
        "created_at": ts,
        "updated_at": ts,
        "slug": "original",
    }
    original = Ticket(**base_data)

    # All-None update should not change anything
    update = TicketUpdate()
    update_data = update.model_dump(exclude_unset=True)
    assert update_data == {}

    # Partial update with explicit Nones
    partial = TicketUpdate(title=None, description=None, fix=None)
    unset = partial.model_dump(exclude_unset=True)
    # Explicitly set fields ARE included even if None
    assert "title" in unset
