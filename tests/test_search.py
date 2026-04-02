from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from vtic.models import Category, SearchFilters, Severity, Status, Ticket
from vtic.search import TicketSearch
from vtic.storage import TicketStore


def _make_ticket(
    id: str,
    title: str,
    description: str = "",
    repo: str = "owner/repo",
    category: Category = Category.CODE_QUALITY,
    severity: Severity = Severity.MEDIUM,
    status: Status = Status.OPEN,
    tags: list[str] | None = None,
) -> Ticket:
    now = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)
    return Ticket(
        id=id,
        title=title,
        description=description or None,
        repo=repo,
        category=category,
        severity=severity,
        status=status,
        tags=tags or [],
        created_at=now,
        updated_at=now,
        slug=title.lower().replace(" ", "-")[:100],
    )


@pytest.fixture
def store(tmp_path: Path) -> TicketStore:
    ticket_store = TicketStore(tmp_path / "tickets")
    tickets = [
        _make_ticket(
            "S1",
            "CORS Wildcard in Production",
            description="All FastAPI services use allow_origins=[*]. CORS remains open.",
            repo="ejacklab/open-dsearch",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
            tags=["cors", "security", "fastapi"],
        ),
        _make_ticket(
            "C2",
            "Duplicated auth helpers across services",
            description="Helpers drift across services and increase auth maintenance.",
            repo="ejacklab/open-dsearch",
            category=Category.CODE_QUALITY,
            severity=Severity.HIGH,
            status=Status.IN_PROGRESS,
            tags=["auth", "refactor"],
        ),
        _make_ticket(
            "P3",
            "Slow query path in analytics worker",
            description="Analytics worker hits repeated database scans under load.",
            repo="acme/analytics",
            category=Category.PERFORMANCE,
            severity=Severity.MEDIUM,
            tags=["query", "db"],
        ),
        _make_ticket(
            "D4",
            "Missing onboarding documentation",
            description="Developer setup steps are incomplete for staging.",
            repo="acme/docs",
            category=Category.DOCUMENTATION,
            severity=Severity.LOW,
            status=Status.CLOSED,
            tags=["docs", "onboarding"],
        ),
        _make_ticket(
            "S5",
            "TLS certificate rotation missing",
            description="Production TLS certificates are manually rotated and risk expiry.",
            repo="acme/platform",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
            tags=["tls", "security"],
        ),
        _make_ticket(
            "C6",
            "Analytics alert thresholds drift",
            description="Alert threshold tuning is inconsistent across analytics jobs.",
            repo="acme/analytics",
            category=Category.CODE_QUALITY,
            severity=Severity.MEDIUM,
            tags=["analytics", "alerts"],
        ),
    ]
    for ticket in tickets:
        ticket_store.create(ticket)
    return ticket_store


def test_keyword_search(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("CORS")

    assert response.total >= 1
    assert response.results[0].id == "S1"
    assert response.results[0].score > 0


def test_search_with_filters(store: TicketStore) -> None:
    engine = TicketSearch(store)
    filters = SearchFilters(severity=[Severity.CRITICAL])

    response = engine.search("", filters=filters)

    assert response.results
    assert response.total == 2
    assert all(result.severity == Severity.CRITICAL.value for result in response.results)
    assert [result.id for result in response.results] == ["S1", "S5"]


def test_empty_results(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("xyznonexistent123")

    assert response.total == 0
    assert response.results == []
    assert response.has_more is False


def test_search_ranking(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    tickets = [
        _make_ticket(
            "C1",
            "Auth failure",
            description="auth",
            repo="owner/ranking",
        ),
        _make_ticket(
            "C2",
            "Auth auth auth regression",
            description="auth auth",
            repo="owner/ranking",
        ),
        _make_ticket(
            "C3",
            "Minor cleanup",
            description="unrelated auth mention",
            repo="owner/ranking",
        ),
    ]
    for ticket in tickets:
        store.create(ticket)

    engine = TicketSearch(store)
    response = engine.search("auth", topk=10)

    assert [result.id for result in response.results][:3] == ["C2", "C1", "C3"]
    assert response.results[0].score > response.results[1].score > response.results[2].score


def test_search_empty_query(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("")

    assert response.total == 6
    assert [result.id for result in response.results] == ["C2", "C6", "D4", "P3", "S1", "S5"]
    assert all(result.score == 1.0 for result in response.results)


def test_search_by_repo_filter(store: TicketStore) -> None:
    engine = TicketSearch(store)
    filters = SearchFilters(repo=["acme/analytics"])

    response = engine.search("", filters=filters)

    assert response.total == 2
    assert all(result.repo == "acme/analytics" for result in response.results)
    assert [result.id for result in response.results] == ["C6", "P3"]


def test_search_pagination(store: TicketStore) -> None:
    engine = TicketSearch(store)

    first_page = engine.search("", topk=2, offset=0)
    second_page = engine.search("", topk=2, offset=2)
    third_page = engine.search("", topk=2, offset=4)

    assert [result.id for result in first_page.results] == ["C2", "C6"]
    assert first_page.has_more is True
    assert [result.id for result in second_page.results] == ["D4", "P3"]
    assert second_page.has_more is True
    assert [result.id for result in third_page.results] == ["S1", "S5"]
    assert third_page.has_more is False


def test_search_highlights(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("cors fastapi")

    assert response.results
    assert response.results[0].id == "S1"
    assert "cors" in response.results[0].highlights
    assert "fastapi" in response.results[0].highlights
