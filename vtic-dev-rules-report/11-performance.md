# Performance Guidelines and Patterns

**Project:** vtic — AI-first ticketing system  
**Source:** BUILD_PLAN.md, EXECUTION_PLAN.md, performance benchmarks

---

## 1. Performance Targets

### vtic v0.1 Targets

| Operation | Target | Method |
|-----------|--------|--------|
| **Create ticket** | < 20ms | BM25 index write |
| **Get ticket** | < 5ms | Direct file read |
| **BM25 search** | < 10ms | 8500+ QPS index |
| **Hybrid search** | < 50ms | BM25 + dense + rerank |
| **Batch create (100)** | < 500ms | Bulk insert + async I/O |
| **Similar tickets** | < 15ms | Vector query on single doc |
| **Reindex (10K)** | < 5s | Full scan + bulk insert |

### Why Performance Matters

- **User experience** — Fast responses feel responsive
- **Agent productivity** — AI agents make many API calls
- **Cost efficiency** — Lower compute = lower bills
- **Scalability** — Fast systems handle more load

---

## 2. Async Everything

### Rule: Async All the Way

```python
# ✅ Async file I/O
import aiofiles

async def write_ticket(ticket: Ticket, path: Path):
    async with aiofiles.open(path, 'w') as f:
        await f.write(ticket.to_markdown())

# ❌ Sync blocking I/O
def write_ticket(ticket: Ticket, path: Path):
    with open(path, 'w') as f:
        f.write(ticket.to_markdown())  # Blocks!
```

### Async Context Managers

```python
# ✅ Proper async resource management
async with zvec.open_collection("tickets") as collection:
    results = await collection.query(query)

# ❌ Resource leak risk
collection = zvec.open_collection("tickets")
results = collection.query(query)
```

### FastAPI Async Handlers

```python
# ✅ Async handler
@router.post("/tickets")
async def create_ticket(data: TicketCreate):
    ticket = await ticket_service.create(data)
    return ticket

# ❌ Blocking handler (rare exceptions only)
@router.get("/health")
def health_check():
    return {"status": "ok"}  # Simple, sync OK
```

---

## 3. Connection Pooling

### HTTP Clients

```python
import httpx

# ✅ Pooled client (reuse connections)
client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100, max_keepalive=20),
    timeout=httpx.Timeout(10.0)
)

async def get_embedding(text: str) -> list[float]:
    response = await client.post(
        "https://api.openai.com/v1/embeddings",
        json={"input": text}
    )
    return response.json()["data"][0]["embedding"]

# ❌ New connection each time
async def get_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:  # New TCP handshake each time!
        response = await client.post(...)
```

### Database Connections

```python
# ✅ Reuse Zvec collection
class SearchEngine:
    def __init__(self):
        self._collection = None
    
    async def _get_collection(self):
        if self._collection is None:
            self._collection = await zvec.open_collection("tickets")
        return self._collection
    
    async def search(self, query: str):
        collection = await self._get_collection()
        return await collection.query(query)
```

---

## 4. Batch Operations

### Bulk Inserts

```python
# ✅ Batch insert for performance
async def create_many_tickets(tickets: list[TicketCreate]):
    # Prepare all tickets
    ticket_objects = [build_ticket(t) for t in tickets]
    
    # Batch write files
    await asyncio.gather(*[
        write_ticket(t, get_path(t))
        for t in ticket_objects
    ])
    
    # Batch index
    await index.upsert_batch(ticket_objects)

# ❌ Individual inserts (slow)
async def create_many_tickets(tickets: list[TicketCreate]):
    for t in tickets:
        await create_ticket(t)  # One at a time!
```

### Parallel Processing

```python
import asyncio

async def parallel_search(queries: list[str]):
    # Run searches in parallel
    results = await asyncio.gather(*[
        search_engine.search(q)
        for q in queries
    ])
    return dict(zip(queries, results))
```

---

## 5. Caching

### Embedding Cache

```python
import hashlib
from functools import lru_cache

class EmbeddingCache:
    def __init__(self, max_size: int = 10000):
        self._cache: dict[str, list[float]] = {}
        self._max_size = max_size
    
    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
    
    async def get(self, text: str) -> list[float] | None:
        key = self._hash(text)
        return self._cache.get(key)
    
    async def set(self, text: str, embedding: list[float]):
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        
        key = self._hash(text)
        self._cache[key] = embedding
```

### LRU Cache for Expensive Operations

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_category_prefix(category: str) -> str:
    """Get ID prefix for category (expensive lookup)."""
    # Simulate expensive operation
    return CATEGORY_MAP[category]
```

---

## 6. Index Optimization

### Zvec Optimization

```python
# ✅ Optimize after bulk writes
async def bulk_import(tickets: list[Ticket]):
    # Batch insert
    await index.upsert_batch(tickets)
    
    # Optimize index for better performance
    await index.optimize()

# ✅ Schedule optimization periodically
async def scheduled_optimize():
    while True:
        await asyncio.sleep(3600)  # Every hour
        await index.optimize()
```

### Index Schema Optimization

```python
# ✅ Use appropriate index types
schema = {
    "fields": {
        "id": {"type": "keyword"},        # Exact match, fast
        "title": {"type": "text", "bm25": {}},  # Full-text search
        "repo": {"type": "keyword", "index": True},  # Filter
        "severity": {"type": "keyword", "index": True},  # Filter
    }
}
```

---

## 7. Memory Efficiency

### Streaming for Large Results

```python
# ✅ Stream large result sets
async def stream_tickets(limit: int = 1000):
    """Stream tickets to avoid memory spike."""
    count = 0
    async for ticket in ticket_service.stream_all():
        yield ticket
        count += 1
        if count >= limit:
            break

# ❌ Load all into memory
async def get_all_tickets():
    tickets = await ticket_service.list_all()  # All in memory!
    return tickets
```

### Pagination

```python
# ✅ Paginated retrieval
async def get_paginated_tickets(page: int, page_size: int = 20):
    offset = (page - 1) * page_size
    return await store.list(limit=page_size, offset=offset)

# ❌ Load everything
def get_all_tickets():
    return store.list()  # May be thousands of tickets!
```

---

## 8. Profiling

### Timing Decorator

```python
import time
import functools

def timed(func):
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__} took {elapsed*1000:.2f}ms")
        return result
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__} took {elapsed*1000:.2f}ms")
        return result
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

@timed
async def search_tickets(query: str):
    return await index.query(query)
```

### Benchmark Tests

```python
import time
import pytest

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_bm25_search_performance(benchmark_service):
    """BM25 search must complete in < 10ms."""
    # Setup
    await benchmark_service.index_many(TEST_TICKETS)
    
    # Benchmark
    times = []
    for _ in range(100):
        start = time.perf_counter()
        await benchmark_service.search("CORS")
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    avg = sum(times) / len(times)
    p95 = sorted(times)[int(len(times) * 0.95)]
    
    assert avg < 0.010, f"Average {avg*1000:.2f}ms exceeds 10ms target"
    assert p95 < 0.050, f"P95 {p95*1000:.2f}ms exceeds 50ms"
```

---

## 9. Resource Limits

### Memory Limits

```python
# ✅ Limit memory usage
import resource

# Set memory limit (soft = warning, hard = kill)
soft, hard = resource.getrlimit(resource.RLIMIT_AS)
resource.setrlimit(resource.RLIMIT_AS, (soft, hard))

# Or for specific operations
async def process_large_batch(items: list):
    CHUNK_SIZE = 1000
    
    for i in range(0, len(items), CHUNK_SIZE):
        chunk = items[i:i + CHUNK_SIZE]
        await process_chunk(chunk)
        # Allow GC to run between chunks
        gc.collect()
```

### Connection Limits

```python
# ✅ Limit concurrent operations
from asyncio import Semaphore

MAX_CONCURRENT = 50
semaphore = Semaphore(MAX_CONCURRENT)

async def rate_limited_operation(item):
    async with semaphore:
        return await do_operation(item)

# Use with gather
results = await asyncio.gather(*[
    rate_limited_operation(item)
    for item in items
])
```

---

## 10. Performance Checklist

### Before Release

- [ ] All performance targets met (<10ms BM25, <5ms CRUD)
- [ ] Async operations throughout
- [ ] Connection pooling enabled
- [ ] Batch operations for bulk data
- [ ] Caching for expensive operations
- [ ] Streaming for large results
- [ ] Index optimized after bulk writes
- [ ] Benchmark tests pass
- [ ] Memory usage within limits

---

## Quick Reference Card

| Target | Limit | Method |
|--------|-------|--------|
| BM25 search | < 10ms | Zvec sparse index |
| CRUD | < 5ms | Direct I/O |
| Hybrid search | < 50ms | BM25 + dense |
| Batch create | < 500ms | Bulk + async |
| Reindex 10K | < 5s | Full scan |

| Technique | Use Case |
|-----------|----------|
| Async I/O | All file and network operations |
| Connection pooling | HTTP clients, database |
| Batch operations | Multiple inserts/updates |
| Caching | Expensive computations |
| Streaming | Large result sets |
| Optimization | After bulk writes |

---

## References

- `BUILD_PLAN.md` — Performance targets
- `tmp/vtic/tests/performance/` — Benchmark tests
- `rules/coding-standards.md` — Section 11 (Phase Separation)
