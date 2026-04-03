from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, cast

import pytest
from pydantic import ValidationError as PydanticValidationError

from vtic.api import create_app
from vtic.models import Category, SearchRequest, Severity, Status, Ticket, TicketCreate, TicketUpdate
from vtic.storage import TicketStore
from vtic.utils import slugify


FIXED_TIMESTAMP = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)


def _make_ticket(
    ticket_id: str,
    *,
    title: str,
    repo: str = "owner/repo",
    category: Category = Category.CODE_QUALITY,
    severity: Severity = Severity.MEDIUM,
    status: Status = Status.OPEN,
    description: str | None = None,
    fix: str | None = None,
    owner: str | None = "owner",
    file: str | None = None,
    tags: list[str] | None = None,
) -> Ticket:
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


@pytest.fixture
def app(tmp_path: Path):
    return create_app(str(tmp_path))


@pytest.fixture
def store(tmp_path: Path) -> TicketStore:
    return TicketStore(tmp_path)


def _route_endpoint(app, path: str, method: str) -> Callable[..., Any]:
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return cast(Callable[..., Any], route.endpoint)
    raise AssertionError(f"Route {method} {path} not found")


def test_create_ticket(app) -> None:
    endpoint = _route_endpoint(app, "/tickets", "POST")
    body = endpoint(
        TicketCreate(
            title="CORS wildcard in production",
            repo="EjAcKLab/Open-DSearch",
            description="All FastAPI services use allow_origins=['*'].",
            category="security",
            severity="critical",
            tags=["cors", "security", "fastapi"],
        )
    ).model_dump()

    assert body["id"] == "S1"
    assert body["title"] == "CORS wildcard in production"
    assert body["repo"] == "ejacklab/open-dsearch"
    assert body["owner"] == "ejacklab"
    assert body["category"] == "security"
    assert body["severity"] == "critical"
    assert body["status"] == "open"
    assert body["slug"] == "cors-wildcard-in-production"


def test_get_ticket(app, store: TicketStore) -> None:
    endpoint = _route_endpoint(app, "/tickets/{ticket_id}", "GET")
    ticket = _make_ticket("S1", title="CORS wildcard", category=Category.SECURITY)
    store.create(ticket)

    response = endpoint("S1")

    assert response.id == "S1"


def test_get_not_found(app) -> None:
    endpoint = _route_endpoint(app, "/tickets/{ticket_id}", "GET")

    with pytest.raises(Exception, match="Ticket S404 not found"):
        endpoint("S404")


def test_list_tickets(app, store: TicketStore) -> None:
    endpoint = _route_endpoint(app, "/tickets", "GET")
    store.create(_make_ticket("C1", title="Cleanup helpers"))
    store.create(_make_ticket("S1", title="Fix TLS", category=Category.SECURITY))

    body = endpoint(None, None, None, None, 100, 0).model_dump()

    assert body["total"] == 2
    assert [ticket["id"] for ticket in body["data"]] == ["C1", "S1"]


def test_list_with_filters(app, store: TicketStore) -> None:
    endpoint = _route_endpoint(app, "/tickets", "GET")
    store.create(_make_ticket("C1", title="Cleanup helpers", severity=Severity.LOW))
    store.create(
        _make_ticket(
            "S1",
            title="Fix TLS",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
        )
    )

    body = endpoint("critical", None, None, None, 100, 0).model_dump()

    assert body["total"] == 1
    assert [ticket["id"] for ticket in body["data"]] == ["S1"]


def test_update_ticket(app, store: TicketStore) -> None:
    endpoint = _route_endpoint(app, "/tickets/{ticket_id}", "PATCH")
    store.create(_make_ticket("C1", title="Needs update", severity=Severity.MEDIUM))

    body = endpoint(
        "C1",
        TicketUpdate(severity="high", status="in_progress", description="Updated details"),
    ).model_dump()

    assert body["severity"] == "high"
    assert body["status"] == "in_progress"
    assert body["description"] == "Updated details"


def test_delete_ticket(app, store: TicketStore) -> None:
    endpoint = _route_endpoint(app, "/tickets/{ticket_id}", "DELETE")
    store.create(_make_ticket("C1", title="Delete me"))

    response = endpoint("C1")

    assert response.status_code == 204
    with pytest.raises(Exception, match="Ticket C1 not found"):
        store.get("C1")


def test_search_endpoint(app, store: TicketStore) -> None:
    endpoint = _route_endpoint(app, "/search", "POST")
    store.create(
        _make_ticket(
            "S1",
            title="CORS wildcard in production",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
            description="FastAPI service uses wildcard CORS.",
            tags=["cors", "fastapi"],
        )
    )
    store.create(
        _make_ticket(
            "C2",
            title="Another CORS misconfiguration",
            category=Category.SECURITY,
            severity=Severity.HIGH,
            description="Missing CORS headers on API endpoints.",
            tags=["cors", "api"],
        )
    )
    store.create(
        _make_ticket(
            "C1",
            title="Cleanup auth helpers",
            description="Refactor duplicated auth helper code.",
        )
    )

    body = endpoint(SearchRequest(query="cors", topk=10, offset=0)).model_dump()

    assert body["total"] >= 1
    result_ids = [r["id"] for r in body["results"]]
    assert "S1" in result_ids
    assert "C1" not in result_ids


def test_create_ticket_rejects_unknown_fields() -> None:
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        TicketCreate(title="CORS wildcard in production", repo="ejacklab/open-dsearch", unexpected="value")


def test_search_rejects_unknown_fields() -> None:
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        SearchRequest(query="cors", unexpected="value")


def test_search_rejects_semantic_true() -> None:
    with pytest.raises(PydanticValidationError, match="Semantic search is not yet implemented"):
        SearchRequest(query="cors", semantic=True)
