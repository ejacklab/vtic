"""End-to-end data consistency test for vtic."""

from __future__ import annotations

import gc
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from vtic.api import deps
from vtic.api.app import create_app
from vtic.index.operations import fetch_ticket
from vtic.models.config import ApiConfig, Config, EmbeddingsConfig, SearchConfig, StorageConfig
from vtic.search.engine import SearchEngine
from vtic.ticket import TicketService


@pytest.fixture
def config(tmp_path: Path) -> Config:
    storage_dir = tmp_path / "tickets"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return Config(
        storage=StorageConfig(dir=storage_dir),
        api=ApiConfig(host="127.0.0.1", port=8080),
        search=SearchConfig(bm25_enabled=True, semantic_enabled=False),
        embeddings=EmbeddingsConfig(provider="none"),
    )


async def _build_client(config: Config) -> AsyncGenerator[tuple[AsyncClient, TicketService], None]:
    service = TicketService(config)
    await service.initialize()

    app = create_app(config)
    app.state.ticket_service = service

    def _search_engine_override() -> SearchEngine:
        return SearchEngine(service.collection)

    app.dependency_overrides[deps.get_search_engine] = _search_engine_override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, service

    app.dependency_overrides.clear()
    await service.close()


@pytest.fixture
async def api_client(config: Config) -> AsyncGenerator[tuple[AsyncClient, TicketService], None]:
    async for client, service in _build_client(config):
        yield client, service


async def _create_ticket(client: AsyncClient, payload: dict) -> dict:
    response = await client.post("/tickets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _search(client: AsyncClient, query: str, limit: int = 10) -> dict:
    response = await client.post("/search", json={"query": query, "limit": limit})
    assert response.status_code == 200, response.text
    return response.json()


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_data_consistency_between_store_and_index(
    api_client: tuple[AsyncClient, TicketService],
    config: Config,
) -> None:
    client, service = api_client
    ticket_specs = [
        {
            "title": "Atlas alpha startup crash",
            "description": "Alpha process crashes during startup validation",
            "repo": "acme/vtic",
            "category": "crash",
            "severity": "high",
        },
        {
            "title": "Atlas beta memory leak",
            "description": "Beta worker leaks memory after sustained load",
            "repo": "acme/vtic",
            "category": "crash",
            "severity": "medium",
        },
        {
            "title": "Atlas gamma audit trail request",
            "description": "Gamma users want audit trail exports",
            "repo": "acme/vtic",
            "category": "feature",
            "severity": "low",
        },
        {
            "title": "Atlas delta database timeout",
            "description": "Delta API times out while reaching PostgreSQL",
            "repo": "acme/vtic",
            "category": "hotfix",
            "severity": "high",
        },
        {
            "title": "Atlas epsilon sanitization gap",
            "description": "Epsilon input sanitization fails security review",
            "repo": "acme/vtic",
            "category": "security",
            "severity": "critical",
        },
    ]
    search_terms = ["alpha", "beta", "gamma", "delta", "epsilon"]

    tickets = [await _create_ticket(client, spec) for spec in ticket_specs]
    assert len(tickets) == 5

    for ticket, term in zip(tickets, search_terms):
        search_body = await _search(client, term)
        hit_ids = [hit["ticket_id"] for hit in search_body["hits"]]
        assert ticket["id"] in hit_ids
        assert search_body["meta"]["total"] == search_body["total"]
        assert search_body["meta"]["latency_ms"] is not None

    target = tickets[0]
    before_get = await client.get(f"/tickets/{target['id']}")
    assert before_get.status_code == 200, before_get.text
    before_data = before_get.json()["data"]
    before_updated = _parse_timestamp(before_data["updated"])

    updated_title = "Atlas zeta startup crash rename"
    update_response = await client.patch(
        f"/tickets/{target['id']}",
        json={"title": updated_title},
    )
    assert update_response.status_code == 200, update_response.text
    updated_ticket = update_response.json()["data"]
    assert updated_ticket["title"] == updated_title
    assert _parse_timestamp(updated_ticket["updated"]) >= before_updated

    live_index_ticket = fetch_ticket(service.collection, target["id"])
    assert live_index_ticket is not None
    assert live_index_ticket["title"] == updated_ticket["title"]
    assert _parse_timestamp(live_index_ticket["created"]) == _parse_timestamp(updated_ticket["created"])
    assert _parse_timestamp(live_index_ticket["updated"]) == _parse_timestamp(updated_ticket["updated"])

    new_title_search = await _search(client, "zeta")
    new_hit_ids = [hit["ticket_id"] for hit in new_title_search["hits"]]
    assert target["id"] in new_hit_ids

    old_title_search = await _search(client, "alpha")
    old_hit_ids = [hit["ticket_id"] for hit in old_title_search["hits"]]
    if target["id"] in old_hit_ids:
        old_rank = next(i for i, hit in enumerate(old_title_search["hits"]) if hit["ticket_id"] == target["id"])
        new_rank = next(i for i, hit in enumerate(new_title_search["hits"]) if hit["ticket_id"] == target["id"])
        assert new_rank <= old_rank

    deleted = tickets[1]
    delete_response = await client.delete(f"/tickets/{deleted['id']}")
    assert delete_response.status_code == 204, delete_response.text

    deleted_search = await _search(client, "beta")
    assert deleted["id"] not in [hit["ticket_id"] for hit in deleted_search["hits"]]
    deleted_get = await client.get(f"/tickets/{deleted['id']}")
    assert deleted_get.status_code == 404, deleted_get.text
    assert fetch_ticket(service.collection, deleted["id"]) is None

    reindex_response = await client.post("/reindex")
    assert reindex_response.status_code == 200, reindex_response.text
    reindex_body = reindex_response.json()
    assert reindex_body["failed"] == 0
    assert reindex_body["processed"] == 4

    remaining = [tickets[0], tickets[2], tickets[3], tickets[4]]
    await client.aclose()
    await service.close()
    del service.collection
    gc.collect()

    async for reopened_client, reopened_service in _build_client(config):
        list_response = await reopened_client.get("/tickets?limit=100")
        assert list_response.status_code == 200, list_response.text
        list_body = list_response.json()
        listed_ids = {item["id"] for item in list_body["data"]}
        for ticket in remaining:
            assert ticket["id"] in listed_ids

        stats_response = await reopened_client.get("/stats")
        assert stats_response.status_code == 200, stats_response.text
        stats_body = stats_response.json()
        assert stats_body["totals"]["all"] == list_body["meta"]["total"]

        list_items = {item["id"]: item for item in list_body["data"]}
        for ticket in remaining:
            get_response = await reopened_client.get(f"/tickets/{ticket['id']}")
            assert get_response.status_code == 200, get_response.text
            ticket_data = get_response.json()["data"]

            created = _parse_timestamp(ticket_data["created"])
            updated = _parse_timestamp(ticket_data["updated"])
            assert created <= updated

            summary = list_items[ticket["id"]]
            assert summary["created"] == ticket_data["created"]
            assert summary["updated"] == ticket_data["updated"]
        break
