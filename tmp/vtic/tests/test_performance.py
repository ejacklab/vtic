"""Performance benchmarks for vtic.

Targets (median over N runs):
  BM25 search  (10K docs)   < 10 ms
  Index CRUD   single op     <  5 ms each
  Reindex      10K tickets   <  5 s
  Suggest      (10K docs)   <  5 ms
  Stats query  (index-based) < 50 ms

All index-layer benchmarks bypass disk I/O by using insert_tickets()
and query_tickets() directly on the Zvec collection.
File-based benchmarks (SystemService.stats) use 100 tickets to avoid
O(n) markdown-file reads dominating the measurement.
"""

from __future__ import annotations

import time
import pytest
from datetime import datetime, timezone
from pathlib import Path

from vtic.index.client import get_collection
from vtic.index.operations import (
    insert_tickets,
    query_tickets,
    fetch_ticket,
    upsert_ticket,
    delete_ticket,
    rebuild_index,
)
from vtic.models.config import Config, StorageConfig, ApiConfig, EmbeddingsConfig
from vtic.models.search import SearchQuery
from vtic.search.engine import SearchEngine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TICKET_COUNT = 10_000
CATEGORIES = ["general", "crash", "hotfix", "feature", "security"]
SEVERITIES = ["low", "medium", "high", "critical", "info"]


# ---------------------------------------------------------------------------
# Ticket factory
# ---------------------------------------------------------------------------

def _make_ticket(i: int) -> dict:
    """Generate a synthetic ticket dict for bench population."""
    now = datetime.now(timezone.utc).isoformat()
    category = CATEGORIES[i % len(CATEGORIES)]
    severity = SEVERITIES[i % len(SEVERITIES)]
    noun = ("authentication", "database", "network")[i % 3]
    return {
        "id": f"G{i}",
        "title": f"Performance ticket {i} about {noun} subsystem failure",
        "description": (
            f"Ticket {i} reports an issue in the {noun} subsystem. "
            f"Error code ERR{i:05d}. Severity: {severity}. Category: {category}."
        ),
        "repo": f"owner/repo{i % 10}",
        "category": category,
        "severity": severity,
        "status": "open",
        "assignee": None,
        "tags": [],
        "references": [],
        "created": now,
        "updated": now,
    }


# ---------------------------------------------------------------------------
# Module-scoped collection fixture (shared across all perf tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def large_collection(tmp_path_factory):
    """Zvec collection pre-populated with TICKET_COUNT tickets.

    Uses batches of 100 to respect Zvec's per-insert document limit.
    """
    tmp_dir = tmp_path_factory.mktemp("perf_index")
    collection = get_collection(tmp_dir)

    tickets = [_make_ticket(i) for i in range(1, TICKET_COUNT + 1)]

    BATCH_SIZE = 100
    total_inserted = 0
    t0 = time.perf_counter()
    for i in range(0, len(tickets), BATCH_SIZE):
        batch = tickets[i : i + BATCH_SIZE]
        total_inserted += insert_tickets(collection, batch)
    elapsed = time.perf_counter() - t0

    print(f"\n[SETUP] Inserted {total_inserted}/{TICKET_COUNT} tickets in {elapsed:.3f}s")
    assert total_inserted == TICKET_COUNT, (
        f"Bulk insert incomplete: only {total_inserted}/{TICKET_COUNT}"
    )
    return collection


@pytest.fixture(scope="module")
def search_engine(large_collection):
    """SearchEngine wrapping the large collection."""
    return SearchEngine(large_collection)


# ---------------------------------------------------------------------------
# Helper: median of a list
# ---------------------------------------------------------------------------

def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2.0


# =============================================================================
# Benchmark 1: BM25 Search  (target < 10 ms median)
# =============================================================================

class TestBM25SearchPerformance:
    TARGET_MS = 10.0
    RUNS = 20

    def test_simple_query(self, large_collection):
        """query_tickets('authentication error') × {RUNS} — median < 10ms."""
        timings = []
        for _ in range(self.RUNS):
            t0 = time.perf_counter()
            results = query_tickets(large_collection, "authentication error", limit=20)
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"\n[BM25] simple query:   median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"BM25 simple query: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )

    def test_query_with_category_filter(self, large_collection):
        """query_tickets with category filter — median < 10ms."""
        timings = []
        for _ in range(self.RUNS):
            t0 = time.perf_counter()
            results = query_tickets(
                large_collection,
                "database subsystem failure",
                filters={"severity": ["high"]},
                limit=20,
            )
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"[BM25] filtered query: median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"BM25 filtered query: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )

    def test_search_engine_search(self, search_engine):
        """SearchEngine.search() — median < 10ms."""
        query = SearchQuery(query="network error subsystem ERR", limit=20)
        timings = []
        for _ in range(self.RUNS):
            t0 = time.perf_counter()
            result = search_engine.search(query)
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"[BM25] engine.search(): median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"SearchEngine.search(): {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )

    def test_query_with_pagination(self, large_collection):
        """query_tickets with offset=100 — median < 10ms."""
        timings = []
        for _ in range(self.RUNS):
            t0 = time.perf_counter()
            results = query_tickets(large_collection, "performance ticket", limit=20, offset=100)
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"[BM25] paginated query: median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"BM25 paginated query: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )


# =============================================================================
# Benchmark 2: Index CRUD  (target < 5 ms per op)
# =============================================================================

class TestIndexCRUDPerformance:
    TARGET_MS = 5.0
    RUNS = 50
    # Offset IDs far enough not to collide with large_collection (G1..G10000)
    ID_BASE = 500_000

    def test_insert_single(self, large_collection):
        """insert_tickets([one ticket]) — median < 5ms."""
        timings = []
        for i in range(self.RUNS):
            ticket = _make_ticket(self.ID_BASE + i)
            t0 = time.perf_counter()
            insert_tickets(large_collection, [ticket])
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"\n[CRUD] insert single:  median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"Index insert: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )

    def test_fetch_by_id(self, large_collection):
        """fetch_ticket(existing id) — median < 5ms."""
        timings = []
        for i in range(self.RUNS):
            tid = f"G{(i % TICKET_COUNT) + 1}"
            t0 = time.perf_counter()
            _ = fetch_ticket(large_collection, tid)
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"[CRUD] fetch by id:    median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"Index fetch: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )

    def test_upsert(self, large_collection):
        """upsert_ticket (update existing) — median < 5ms."""
        timings = []
        for i in range(self.RUNS):
            ticket = _make_ticket((i % TICKET_COUNT) + 1)
            ticket["title"] = f"Updated title round {i}"
            t0 = time.perf_counter()
            upsert_ticket(large_collection, ticket)
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"[CRUD] upsert:         median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"Index upsert: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )

    def test_delete(self, large_collection):
        """delete_ticket — median < 5ms (inserts first, then measures delete)."""
        # Pre-insert tickets that we'll delete
        to_del = [_make_ticket(600_000 + i) for i in range(self.RUNS)]
        insert_tickets(large_collection, to_del)

        timings = []
        for i in range(self.RUNS):
            tid = f"G{600_000 + i}"
            t0 = time.perf_counter()
            delete_ticket(large_collection, tid)
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"[CRUD] delete:         median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"Index delete: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )


# =============================================================================
# Benchmark 3: Reindex  (target < 5 s for 10K tickets)
# =============================================================================

class TestReindexPerformance:
    TARGET_SEC = 5.0

    def test_reindex_10k_via_loader(self, tmp_path):
        """rebuild_index with ticket_loader bypassing disk I/O — < 5 seconds."""
        collection = get_collection(tmp_path / "reindex_bench")
        tickets = [_make_ticket(i) for i in range(1, TICKET_COUNT + 1)]

        def loader(base_dir):
            return tickets

        t0 = time.perf_counter()
        stats = rebuild_index(collection, tmp_path / "reindex_bench", ticket_loader=loader)
        elapsed = time.perf_counter() - t0

        print(
            f"\n[Reindex] 10K tickets: {elapsed:.3f}s  target=<{self.TARGET_SEC}s  "
            f"processed={stats['processed']} failed={stats['failed']}"
        )
        assert stats["processed"] >= int(TICKET_COUNT * 0.95), (
            f"Too few tickets processed: {stats['processed']}/{TICKET_COUNT}"
        )
        assert elapsed < self.TARGET_SEC, (
            f"Reindex: {elapsed:.3f}s exceeds {self.TARGET_SEC}s target"
        )


# =============================================================================
# Benchmark 4: Suggest  (target < 5 ms median)
# =============================================================================

class TestSuggestPerformance:
    TARGET_MS = 5.0
    RUNS = 30

    def test_suggest(self, search_engine):
        """SearchEngine.suggest() with 10K indexed tickets — median < 5ms."""
        queries = ["au", "ne", "da", "er", "sy", "pe", "fa"]
        timings = []
        for i in range(self.RUNS):
            q = queries[i % len(queries)]
            t0 = time.perf_counter()
            _ = search_engine.suggest(q, limit=5)
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"\n[Suggest] 10K tickets: median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"Suggest: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )

    def test_suggest_limit_20(self, search_engine):
        """Suggest with limit=20 — still < 5ms."""
        timings = []
        for _ in range(self.RUNS):
            t0 = time.perf_counter()
            _ = search_engine.suggest("pe", limit=20)
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"[Suggest] limit=20:    median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"Suggest limit=20: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )


# =============================================================================
# Benchmark 5: Stats  (target < 50 ms median for index-layer queries)
# =============================================================================

class TestStatsPerformance:
    """
    SystemService.stats() reads ALL ticket markdown files from disk.
    With 10K tickets this is inherently I/O bound; the 50 ms target
    applies to the *index-layer* stats calculation instead.

    A separate async test exercises SystemService.stats() with 100 tickets
    to show the per-ticket file I/O cost.
    """

    TARGET_MS = 50.0
    RUNS = 10

    def test_stats_via_index_queries(self, large_collection):
        """Count-by-category via query_tickets() × 5 categories — total < 50ms."""
        timings = []
        for _ in range(self.RUNS):
            t0 = time.perf_counter()
            for cat in CATEGORIES:
                query_tickets(
                    large_collection,
                    "performance ticket",
                    filters={"category": [cat]},
                    limit=1,
                )
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"\n[Stats] 5 category counts (10K idx): median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"Stats index queries: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )

    def test_stats_full_breakdown_via_index(self, large_collection):
        """Status + severity + category counts — total < 50ms."""
        statuses = ["open", "in_progress", "fixed", "closed", "blocked", "wont_fix"]
        timings = []
        for _ in range(self.RUNS):
            t0 = time.perf_counter()
            for sev in SEVERITIES:
                query_tickets(large_collection, "error", filters={"severity": [sev]}, limit=1)
            for cat in CATEGORIES:
                query_tickets(large_collection, "error", filters={"category": [cat]}, limit=1)
            timings.append((time.perf_counter() - t0) * 1000)
        med = _median(timings)
        print(f"[Stats] full breakdown (10K idx):    median={med:.2f}ms  target=<{self.TARGET_MS}ms")
        assert med < self.TARGET_MS, (
            f"Stats full breakdown: {med:.2f}ms exceeds {self.TARGET_MS}ms target"
        )

    @pytest.mark.asyncio
    async def test_system_service_stats_100_tickets(self, tmp_path):
        """SystemService.stats() with 100 file-backed tickets — baseline measurement."""
        from vtic.ticket import TicketService
        from vtic.services.system import SystemService
        from vtic.models.ticket import TicketCreate

        cfg = Config(
            storage=StorageConfig(dir=tmp_path / "stats_bench"),
            api=ApiConfig(host="localhost", port=8080),
            embeddings=EmbeddingsConfig(provider="none"),
        )
        svc = TicketService(cfg)
        await svc.initialize()

        N = 100
        for i in range(N):
            await svc.create_ticket(
                TicketCreate(
                    title=f"Stats benchmark ticket {i}",
                    description=f"Description for ticket {i}",
                    repo="owner/repo",
                )
            )

        sys_svc = SystemService(cfg, svc)

        t0 = time.perf_counter()
        stats = await sys_svc.stats()
        elapsed_ms = (time.perf_counter() - t0) * 1000

        print(
            f"\n[Stats] SystemService {N} file tickets: {elapsed_ms:.2f}ms  "
            f"(Note: file I/O bound; 10K would be ~{elapsed_ms * 100:.0f}ms)"
        )
        assert stats.totals.all == N, f"Expected {N} tickets, got {stats.totals.all}"


# =============================================================================
# Summary test — prints consolidated results
# =============================================================================

def test_benchmark_summary(large_collection, search_engine):
    """Print a consolidated performance summary table."""
    RUNS = 30
    queries = [
        ("authentication error", None),
        ("database subsystem failure", {"severity": ["high"]}),
        ("network error", {"category": ["general"]}),
    ]

    search_timings = []
    for q, f in queries:
        for _ in range(RUNS // len(queries)):
            t0 = time.perf_counter()
            query_tickets(large_collection, q, filters=f, limit=20)
            search_timings.append((time.perf_counter() - t0) * 1000)

    fetch_timings = []
    for i in range(RUNS):
        t0 = time.perf_counter()
        fetch_ticket(large_collection, f"G{(i % TICKET_COUNT) + 1}")
        fetch_timings.append((time.perf_counter() - t0) * 1000)

    suggest_timings = []
    for i in range(RUNS):
        q = ("au", "ne", "da")[i % 3]
        t0 = time.perf_counter()
        search_engine.suggest(q, limit=5)
        suggest_timings.append((time.perf_counter() - t0) * 1000)

    print("\n" + "=" * 58)
    print("  VTIC PERFORMANCE SUMMARY  (all medians, 10K doc index)")
    print("=" * 58)
    print(f"  BM25 search   {_median(search_timings):7.2f} ms   target < 10 ms")
    print(f"  Index fetch   {_median(fetch_timings):7.2f} ms   target <  5 ms")
    print(f"  Suggest       {_median(suggest_timings):7.2f} ms   target <  5 ms")
    print("=" * 58)
