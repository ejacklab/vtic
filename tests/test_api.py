from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import asyncio
import httpx
import pytest
from pydantic import ValidationError as PydanticValidationError
from starlette.testclient import TestClient as StarletteTestClient

from vtic.api import create_app
from vtic.models import Category, SearchRequest, Severity, Status, Ticket, TicketCreate
from vtic.storage import TicketStore
from vtic.utils import slugify

from conftest import make_ticket




class TestClient(StarletteTestClient):
    """Compatibility wrapper around Starlette's TestClient for this environment."""

    def __init__(self, app) -> None:
        self.app = app
        self.base_url = "http://testserver"

    def request(self, method: str, url: str, **kwargs):
        async def _send():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url=self.base_url) as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(_send())

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def close(self) -> None:
        return None




@pytest.fixture
def app(tmp_path: Path):
    return create_app(str(tmp_path))


@pytest.fixture
def client(app) -> TestClient:
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
    store._create(make_ticket("S1", title="CORS wildcard", category=Category.SECURITY))

    response = client.get("/tickets/S1")

    assert response.status_code == 200
    assert response.json()["id"] == "S1"


def test_get_not_found(client: TestClient) -> None:
    response = client.get("/tickets/S404")

    assert response.status_code == 404
    assert response.json()["message"] == "Ticket S404 not found"


def test_list_tickets(client: TestClient, store: TicketStore) -> None:
    store._create(make_ticket("C1", title="Cleanup helpers"))
    store._create(make_ticket("S1", title="Fix TLS", category=Category.SECURITY))

    response = client.get("/tickets")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [ticket["id"] for ticket in body["data"]] == ["C1", "S1"]


def test_list_with_filters(client: TestClient, store: TicketStore) -> None:
    store._create(make_ticket("C1", title="Cleanup helpers", severity=Severity.LOW))
    store._create(
        make_ticket(
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


def test_list_with_owner_tags_and_date_filters(
    client: TestClient, store: TicketStore
) -> None:
    store._create(
        make_ticket(
            "C1",
            title="Owned API ticket",
            owner="smoke01",
            tags=["auth", "api"],
        )
    )
    store._create(
        make_ticket(
            "C2",
            title="Wrong owner",
            owner="alex",
            tags=["auth", "api"],
        )
    )

    response = client.get(
        "/tickets",
        params={
            "owner": "smoke01",
            "tags": ["auth", "api"],
            "created_after": "2026-03-16T09:00:00Z",
            "updated_before": "2026-03-16T11:00:00Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [ticket["id"] for ticket in body["data"]] == ["C1"]


def test_list_rejects_invalid_enum_query_param(client: TestClient) -> None:
    response = client.get("/tickets", params={"severity": "urgent"})

    assert response.status_code == 400
    assert response.json()["message"] == "Request validation failed"
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_health_reports_healthy_store(client: TestClient, store: TicketStore) -> None:
    store._create(make_ticket("C1", title="Cleanup helpers"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ticket_count"] == 1
    assert response.json()["status"] == "healthy"
    assert response.json()["corrupted_tickets"] == []


def test_health_reports_corrupted_ticket(client: TestClient, store: TicketStore) -> None:
    store._create(make_ticket("C1", title="Healthy ticket", repo="acme/app"))
    broken_path = store.base_dir / "acme" / "app" / "code_quality" / "C2-broken.md"
    broken_path.parent.mkdir(parents=True, exist_ok=True)
    broken_path.write_text("---\nid: C2\ntitle: Broken\n---\n", encoding="utf-8")

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["index_status"] == "corrupted"
    assert body["checks"] == {"storage": False, "search": False}
    assert body["corrupted_tickets"] == ["acme/app/code_quality/C2-broken.md"]


def test_update_ticket(client: TestClient, store: TicketStore) -> None:
    store._create(make_ticket("C1", title="Needs update", severity=Severity.MEDIUM))

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
    store._create(make_ticket("C1", title="Delete me"))

    response = client.delete("/tickets/C1")

    assert response.status_code == 204
    with pytest.raises(Exception, match="Ticket C1 not found"):
        store.get("C1")


def test_search_endpoint(client: TestClient, store: TicketStore) -> None:
    store._create(
        make_ticket(
            "S1",
            title="CORS wildcard in production",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
            description="FastAPI service uses wildcard CORS.",
            tags=["cors", "fastapi"],
        )
    )
    store._create(
        make_ticket(
            "C2",
            title="Another CORS misconfiguration",
            category=Category.SECURITY,
            severity=Severity.HIGH,
            description="Missing CORS headers on API endpoints.",
            tags=["cors", "api"],
        )
    )
    store._create(
        make_ticket(
            "C1",
            title="Cleanup auth helpers",
            description="Refactor duplicated auth helper code.",
        )
    )

    response = client.post("/search", json={"query": "cors", "topk": 10, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    result_ids = [result["id"] for result in body["results"]]
    assert "S1" in result_ids
    assert "C1" not in result_ids


def test_create_ticket_rejects_unknown_fields() -> None:
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        TicketCreate(title="CORS wildcard in production", repo="ejacklab/open-dsearch", unexpected="value")


def test_create_ticket_malformed_json_returns_400(client: TestClient) -> None:
    response = client.post("/tickets", content="{", headers={"Content-Type": "application/json"})

    assert response.status_code == 400
    assert response.json()["message"] == "Invalid request body"
    assert response.json()["error_code"] == "INVALID_REQUEST"


def test_search_rejects_unknown_fields() -> None:
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        SearchRequest(query="cors", unexpected="value")


def test_search_rejects_semantic_true() -> None:
    with pytest.raises(PydanticValidationError, match="Semantic search is not yet implemented"):
        SearchRequest(query="cors", semantic=True)


def test_search_malformed_json_returns_400(client: TestClient) -> None:
    response = client.post("/search", content="{", headers={"Content-Type": "application/json"})

    assert response.status_code == 400
    assert response.json()["message"] == "Invalid request body"
    assert response.json()["error_code"] == "INVALID_REQUEST"
