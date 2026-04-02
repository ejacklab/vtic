from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vtic.api import create_app
from vtic.models import Category, Severity, Status, Ticket
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
def client(tmp_path: Path) -> TestClient:
    app = create_app(str(tmp_path))
    return TestClient(app)


@pytest.fixture
def store(tmp_path: Path) -> TicketStore:
    return TicketStore(tmp_path)


def test_create_ticket(client: TestClient) -> None:
    response = client.post(
        "/tickets",
        json={
            "title": "CORS wildcard in production",
            "repo": "EjAcKLab/Open-DSearch",
            "description": "All FastAPI services use allow_origins=['*'].",
            "category": "security",
            "severity": "critical",
            "tags": ["cors", "security", "fastapi"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "S1"
    assert body["title"] == "CORS wildcard in production"
    assert body["repo"] == "ejacklab/open-dsearch"
    assert body["owner"] == "ejacklab"
    assert body["category"] == "security"
    assert body["severity"] == "critical"
    assert body["status"] == "open"
    assert body["slug"] == "cors-wildcard-in-production"


def test_get_ticket(client: TestClient, store: TicketStore) -> None:
    ticket = _make_ticket("S1", title="CORS wildcard", category=Category.SECURITY)
    store.create(ticket)

    response = client.get("/tickets/S1")

    assert response.status_code == 200
    assert response.json()["id"] == "S1"


def test_get_not_found(client: TestClient) -> None:
    response = client.get("/tickets/S404")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "TICKET_NOT_FOUND"


def test_list_tickets(client: TestClient, store: TicketStore) -> None:
    store.create(_make_ticket("C1", title="Cleanup helpers"))
    store.create(_make_ticket("S1", title="Fix TLS", category=Category.SECURITY))

    response = client.get("/tickets")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [ticket["id"] for ticket in body["data"]] == ["C1", "S1"]


def test_list_with_filters(client: TestClient, store: TicketStore) -> None:
    store.create(_make_ticket("C1", title="Cleanup helpers", severity=Severity.LOW))
    store.create(
        _make_ticket(
            "S1",
            title="Fix TLS",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
        )
    )

    response = client.get("/tickets", params={"severity": "critical"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [ticket["id"] for ticket in body["data"]] == ["S1"]


def test_update_ticket(client: TestClient, store: TicketStore) -> None:
    store.create(_make_ticket("C1", title="Needs update", severity=Severity.MEDIUM))

    response = client.patch(
        "/tickets/C1",
        json={"severity": "high", "status": "in_progress", "description": "Updated details"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["severity"] == "high"
    assert body["status"] == "in_progress"
    assert body["description"] == "Updated details"


def test_delete_ticket(client: TestClient, store: TicketStore) -> None:
    store.create(_make_ticket("C1", title="Delete me"))

    response = client.delete("/tickets/C1")

    assert response.status_code == 204
    assert response.content == b""
    missing = client.get("/tickets/C1")
    assert missing.status_code == 404


def test_search_endpoint(client: TestClient, store: TicketStore) -> None:
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

    response = client.post(
        "/search",
        json={
            "query": "cors",
            "topk": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    result_ids = [r["id"] for r in body["results"]]
    assert "S1" in result_ids
    assert "C1" not in result_ids

