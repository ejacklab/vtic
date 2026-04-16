from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from vtic.models import Category, SearchFilters, Severity, Status, Ticket, TicketUpdate
from vtic.search import TicketSearch, _BuiltinBM25
from vtic.storage import TicketStore

from tests.conftest import make_ticket as _make_ticket


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
        ticket_store._create(ticket)
    return ticket_store


def test_keyword_search(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("CORS")

    assert response.total >= 1
    assert response.results[0].id == "S1"
    assert response.results[0].score > 0


def test_single_term_search(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("tls")

    assert response.total == 1
    assert response.results[0].id == "S5"


def test_multi_term_search(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("analytics worker")

    assert response.results
    assert response.results[0].id == "P3"


def test_partial_match(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("analytics-worker")

    assert response.results
    assert response.results[0].id == "P3"


def test_search_with_filters(store: TicketStore) -> None:
    engine = TicketSearch(store)
    filters = SearchFilters(severity=[Severity.CRITICAL])

    response = engine.search("", filters=filters)

    assert response.results
    assert response.total == 2
    assert all(result.severity == Severity.CRITICAL.value for result in response.results)
    assert [result.id for result in response.results] == ["S1", "S5"]


def test_filter_combination(store: TicketStore) -> None:
    engine = TicketSearch(store)
    filters = SearchFilters(
        severity=[Severity.HIGH],
        status=[Status.IN_PROGRESS],
    )

    response = engine.search("", filters=filters)

    assert response.total == 1
    assert [result.id for result in response.results] == ["C2"]


def test_empty_results(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("xyznonexistent123")

    assert response.total == 0
    assert response.results == []
    assert response.has_more is False


def test_search_empty_store_returns_empty_response(tmp_path: Path) -> None:
    engine = TicketSearch(TicketStore(tmp_path / "tickets"))

    response = engine.search("")

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
        store._create(ticket)

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


def test_special_characters_in_query(store: TicketStore) -> None:
    engine = TicketSearch(store)

    response = engine.search("CORS (*)")

    assert response.total >= 1
    assert response.results[0].id == "S1"


def test_search_with_tokenless_corpus_returns_empty(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    store._create(
        _make_ticket(
            "C1",
            "x",
            description="y",
            repo="owner/tokenless",
        )
    )
    engine = TicketSearch(store)

    response = engine.search("auth")

    assert response.total == 0
    assert response.results == []
    assert response.has_more is False


def test_search_handles_bm25_empty_scores(store: TicketStore, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = TicketSearch(store)
    engine.build_index()

    monkeypatch.setattr(engine._bm25, "get_scores", lambda query: [])

    response = engine.search("cors")

    assert response.total == 0
    assert response.results == []
    assert response.has_more is False


def test_search_falls_back_when_bm25_scores_are_non_positive(
    store: TicketStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = TicketSearch(store)
    engine.build_index()

    monkeypatch.setattr(engine._bm25, "get_scores", lambda query: [0.0] * len(store.list()))

    response = engine.search("analytics worker")

    assert response.total == 2
    assert [result.id for result in response.results] == ["P3", "C6"]
    assert response.results[0].score == 1.0
    assert response.results[0].bm25_score == 0.0


def test_search_rebuilds_index_when_ticket_content_changes(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    store._create(
        _make_ticket(
            "C1",
            "Old title",
            description="legacy content",
            repo="owner/cache",
        )
    )
    engine = TicketSearch(store)

    first = engine.search("legacy")
    assert [result.id for result in first.results] == ["C1"]

    store.update(
        "C1",
        TicketUpdate(
            title="Updated auth title",
            description="fresh auth content",
            tags=["auth"],
        ),
    )

    second = engine.search("auth")
    assert [result.id for result in second.results] == ["C1"]
    assert second.results[0].title == "Updated auth title"


def test_search_reuses_cached_metadata_for_unchanged_tickets(
    store: TicketStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = TicketSearch(store)
    first = engine.search("cors")
    assert first.total >= 1

    calls: list[str] = []
    original_read_ticket = store._read_ticket

    def tracking_read_ticket(*args, **kwargs):
        calls.append(str(args[0]))
        return original_read_ticket(*args, **kwargs)

    monkeypatch.setattr(store, "_read_ticket", tracking_read_ticket)

    second = engine.search("cors")

    assert second.total == first.total
    assert calls == []


def test_builtin_bm25_empty_corpus_scores_empty() -> None:
    scorer = _BuiltinBM25([])

    assert scorer.get_scores(["auth"]) == []


def test_search_category_filter(store: TicketStore) -> None:
    engine = TicketSearch(store)
    filters = SearchFilters(category=[Category.SECURITY])

    response = engine.search("", filters=filters)

    assert response.total == 2
    assert all(result.category == Category.SECURITY.value for result in response.results)
    assert [result.id for result in response.results] == ["S1", "S5"]


def test_search_owner_filter(store: TicketStore) -> None:
    # The store fixture tickets don't have owner set via the helper
    # Create a ticket with owner directly
    from datetime import UTC, datetime
    owner_ticket = Ticket(
        id="C7", title="Owned by alice", repo="owner/repo",
        category=Category.CODE_QUALITY, severity=Severity.MEDIUM, status=Status.OPEN,
        tags=[], owner="alice",
        created_at=datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC),
        slug="owned-by-alice",
    )
    store._create(owner_ticket)

    engine = TicketSearch(store)
    filters = SearchFilters(owner="alice")

    response = engine.search("", filters=filters)

    assert response.total == 1
    assert response.results[0].id == "C7"


def test_search_tags_filter(store: TicketStore) -> None:
    engine = TicketSearch(store)
    filters = SearchFilters(tags=["fastapi"])

    response = engine.search("", filters=filters)

    assert response.total == 1
    assert response.results[0].id == "S1"


def test_search_has_fix_filter(tmp_path: Path) -> None:
    from vtic.utils import slugify
    s = TicketStore(tmp_path / "tickets")
    now = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)
    s._create(Ticket(
        id="C1", title="Has fix", description="desc", fix="Apply patch.",
        repo="owner/repo", tags=[], slug=slugify("Has fix"),
        created_at=now, updated_at=now,
    ))
    s._create(Ticket(
        id="C2", title="No fix", description="desc",
        repo="owner/repo", tags=[], slug=slugify("No fix"),
        created_at=now, updated_at=now,
    ))

    engine = TicketSearch(s)

    # Tickets with fix
    response = engine.search("", filters=SearchFilters(has_fix=True))
    assert response.total == 1
    assert response.results[0].id == "C1"

    # Tickets without fix
    response = engine.search("", filters=SearchFilters(has_fix=False))
    assert response.total == 1
    assert response.results[0].id == "C2"
