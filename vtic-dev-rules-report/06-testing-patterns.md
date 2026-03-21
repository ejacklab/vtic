# Testing Patterns and Best Practices

**Project:** vtic — AI-first ticketing system  
**Source:** coding-standards.md, test-hygiene skill, vtic codebase

---

## 1. Testing Philosophy

### Core Principle: Real Tests Over Mocks

**Mocks give false confidence. Real-service tests catch real bugs.**

| Test Type | Confidence | Use For |
|-----------|-----------|---------|
| Unit test with real services | High | Core logic, data transformations |
| Integration test (TestClient) | **Highest** | Full request→response flow |
| Unit test with mocks | Medium | External API calls only |
| Performance test | High | Verify targets (<10ms BM25) |

### vtic Lesson: Mocks Hide Real Bugs

```
❌ Mock-based API route tests: all passed ✅
✅ Integration tests with real TicketService: async/await bug caught ❌

The mock didn't enforce the actual async contract.
```

---

## 2. Test Types

### Unit Tests

Test individual functions/components in isolation:

```python
# ✅ Unit test with real services
@pytest.mark.asyncio
async def test_ticket_creation(tmp_path):
    store = MarkdownStore(tmp_path)
    index = ZvecIndex(tmp_path / ".vtic")
    service = TicketService(store, index)
    
    ticket = await service.create(TicketCreate(
        title="Test ticket",
        repo="test/repo"
    ))
    
    assert ticket.id.startswith("B")
    assert ticket.title == "Test ticket"
```

### Integration Tests

Test full request/response flow:

```python
# ✅ Integration test with FastAPI TestClient
@pytest.fixture
def client(tmp_path):
    store = MarkdownStore(tmp_path)
    index = ZvecIndex(tmp_path / ".vtic")
    service = TicketService(store, index)
    app = create_app(service)
    return TestClient(app)

def test_create_ticket_endpoint(client):
    response = client.post("/tickets", json={
        "title": "Bug report",
        "repo": "test/repo"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Bug report"
    assert "id" in data
```

### Performance Tests

Verify performance targets:

```python
# ✅ Performance test
@pytest.mark.asyncio
async def test_bm25_search_performance(benchmark_client):
    # Insert 1000 tickets
    for i in range(1000):
        await benchmark_client.create_ticket(...)
    
    # Measure search time
    start = time.time()
    results = await benchmark_client.search("CORS")
    elapsed = time.time() - start
    
    assert elapsed < 0.010  # < 10ms target
```

---

## 3. Mock vs Real Decision Matrix

| Dependency | Mock? | Why |
|------------|-------|-----|
| External API (OpenAI, GitHub) | ✅ Mock | Unreliable, rate-limited, costs money |
| Internal service (TicketService) | ❌ Real | Must verify actual behavior |
| Database (Zvec, Postgres) | ❌ Real | Different DBs behave differently |
| File system | ❌ Real | Use tmp_path, not mocks |
| HTTP client (internal) | ❌ Real | Use TestClient, not mocks |
| Time/timeouts | ✅ Mock | Can't wait for real time in tests |

---

## 4. Test Infrastructure

### Fixtures

```python
# conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def tmp_tickets_dir(tmp_path):
    """Provide isolated tickets directory."""
    tickets_dir = tmp_path / "tickets"
    tickets_dir.mkdir()
    return tickets_dir

@pytest.fixture
async def ticket_service(tmp_tickets_dir):
    """Provide configured TicketService."""
    store = MarkdownStore(tmp_tickets_dir)
    index = ZvecIndex(tmp_tickets_dir / ".vtic")
    service = TicketService(store, index)
    yield service
    await index.close()

@pytest.fixture
def client(ticket_service):
    """Provide FastAPI TestClient."""
    from fastapi.testclient import TestClient
    app = create_app(ticket_service)
    return TestClient(app)
```

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_models.py
│   ├── test_store.py
│   └── test_search.py
├── integration/
│   ├── test_api_tickets.py
│   └── test_api_search.py
└── performance/
    └── test_benchmarks.py
```

---

## 5. Writing Good Tests

### Test Structure (AAA Pattern)

```python
def test_update_ticket_status():
    # Arrange
    ticket = create_ticket(title="Test", status="open")
    
    # Act
    updated = update_ticket(ticket.id, status="in_progress")
    
    # Assert
    assert updated.status == "in_progress"
    assert updated.updated > ticket.updated
```

### Test One Thing

```python
# ✅ One assertion per logical concept
def test_ticket_creation():
    ticket = create_ticket(title="Test")
    
    assert ticket.id is not None
    assert ticket.created is not None
    assert ticket.status == "open"  # Default

# ❌ Testing too much
def test_everything():
    # Creates ticket, updates, deletes, searches...
    # 50 lines of setup, 20 assertions
    pass
```

### Test Edge Cases

```python
# ✅ Edge cases
@pytest.mark.parametrize("title", [
    "a",                      # Minimum length
    "a" * 200,                # Maximum length
    "Special: chars! @#",     # Special characters
    "Unicode: 你好世界",       # Unicode
])
def test_ticket_title_validation(title):
    if len(title) > 200:
        with pytest.raises(ValidationError):
            TicketCreate(title=title, repo="test/repo")
    else:
        ticket = TicketCreate(title=title, repo="test/repo")
        assert ticket.title == title
```

---

## 6. Test Hygiene

### Run Tests Early

```
❌ Don't write 100 lines then test
✅ Run tests after each logical change
```

### Verify Test Validity

Before debugging code, check if the test itself is correct:

```python
# ❌ Common test bugs
def test_date_range():
    start = datetime.now()
    end = datetime.now()      # Same instant! Zero duration
    assert in_range(start, end)  # Always fails

# ✅ Correct
def test_date_range():
    start = datetime(2026, 1, 1)
    end = datetime(2026, 1, 2)   # Different dates
    assert in_range(start, end)
```

### Don't Over-Debug

```
Rule: If a test keeps failing after 2 attempts, 
      step back and question the TEST, not just the code.
```

Common test bugs:
- Zero-duration date ranges
- Missing mocks or stubs
- Incorrect expected values
- Testing the wrong thing

---

## 7. Async Testing

### pytest-asyncio

```python
import pytest

@pytest.mark.asyncio
async def test_async_ticket_creation(ticket_service):
    ticket = await ticket_service.create(TicketCreate(
        title="Test",
        repo="test/repo"
    ))
    
    assert ticket.id is not None
```

### Handling Async Fixtures

```python
@pytest.fixture
async def ticket_service(tmp_path):
    store = MarkdownStore(tmp_path)
    index = await ZvecIndex.create(tmp_path / ".vtic")
    service = TicketService(store, index)
    yield service
    await index.close()  # Cleanup
```

### Testing Async Iterators

```python
@pytest.mark.asyncio
async def test_async_ticket_streaming(ticket_service):
    tickets = []
    async for ticket in ticket_service.stream_all():
        tickets.append(ticket)
    
    assert len(tickets) == 100
```

---

## 8. Test Data

### Factory Pattern

```python
# factories.py
import factory
from vtic.models import TicketCreate

class TicketCreateFactory(factory.Factory):
    class Meta:
        model = TicketCreate
    
    title = factory.Sequence(lambda n: f"Ticket {n}")
    repo = "ejacklab/vtic"
    category = "bug"
    severity = "medium"

# Usage
def test_something():
    ticket = TicketCreateFactory()
    # Uses default values
    
    ticket = TicketCreateFactory(title="Custom title")
    # Overrides specific field
```

### Fixtures for Common Data

```python
@pytest.fixture
def sample_ticket(ticket_service):
    return ticket_service.create(TicketCreate(
        title="Sample ticket",
        repo="test/repo",
        category="bug",
        severity="high"
    ))

@pytest.fixture
def many_tickets(ticket_service):
    tickets = []
    for i in range(100):
        ticket = ticket_service.create(TicketCreate(
            title=f"Ticket {i}",
            repo="test/repo"
        ))
        tickets.append(ticket)
    return tickets
```

---

## 9. Error Testing

### Testing Exceptions

```python
import pytest
from vtic.errors import TicketNotFoundError, ValidationError

# ✅ Test exceptions
@pytest.mark.asyncio
async def test_get_nonexistent_ticket(ticket_service):
    with pytest.raises(TicketNotFoundError) as exc_info:
        await ticket_service.get("B999999")
    
    assert "B999999" in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_ticket_validation(ticket_service):
    with pytest.raises(ValidationError) as exc_info:
        await ticket_service.create(TicketCreate(
            title="",  # Empty title
            repo="test/repo"
        ))
    
    assert "title" in str(exc_info.value)
```

### Testing Error Responses

```python
def test_api_error_response(client):
    response = client.post("/tickets", json={
        "title": "",  # Invalid
        "repo": "invalid-repo-format"
    })
    
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert len(error["details"]) == 2  # Two validation errors
```

---

## 10. Performance Testing

### Benchmarks

```python
# tests/performance/test_search.py
import time
import pytest

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_bm25_search_latency(benchmark_client):
    """BM25 search must complete in < 10ms."""
    # Setup: 10K tickets indexed
    
    times = []
    for _ in range(100):
        start = time.perf_counter()
        results = await benchmark_client.search("CORS")
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    
    assert avg_time < 0.010  # 10ms average
    assert max_time < 0.050  # 50ms max (allow outliers)
```

### Load Testing (Future)

```python
@pytest.mark.load
@pytest.mark.asyncio
async def test_concurrent_requests():
    """Handle 100 concurrent requests."""
    async with aiohttp.ClientSession() as session:
        tasks = [
            session.post("http://localhost:8000/tickets", json={...})
            for _ in range(100)
        ]
        responses = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in responses if r.status == 201)
        assert success_count == 100
```

---

## 11. Coverage

### Minimum Coverage

```
Target: ≥ 80% code coverage
```

### Running Coverage

```bash
# Run with coverage
pytest --cov=src/vtic --cov-report=html --cov-report=term

# Fail if coverage below threshold
pytest --cov=src/vtic --cov-fail-under=80
```

### What to Cover

| Category | Must Cover |
|----------|-----------|
| Happy paths | ✅ Yes |
| Error paths | ✅ Yes |
| Edge cases | ✅ Yes |
| Validation | ✅ Yes |
| External APIs | Mock, test interface |

---

## 12. Test Maintenance

### Keep Tests Fast

```
Target: Unit tests < 100ms each
Target: Full suite < 30 seconds
```

### Avoid Brittle Tests

```python
# ❌ Brittle - depends on exact error message
def test_error_message():
    with pytest.raises(ValueError, match="exact error text"):
        do_something()

# ✅ Resilient - checks error type and key content
def test_error_message():
    with pytest.raises(ValueError) as exc:
        do_something()
    assert "field_name" in str(exc.value)
```

### Update Tests with Code

```
Rule: When you change code behavior, update the tests.
Don't leave outdated tests that "pass" but test the wrong thing.
```

---

## Quick Reference Card

| Aspect | Rule |
|--------|------|
| Mock vs Real | Prefer real services, mock only external APIs |
| Test structure | Arrange → Act → Assert |
| Test scope | One logical concept per test |
| Async testing | Use pytest-asyncio |
| Edge cases | Always test boundaries (min, max, empty) |
| Performance | Verify targets (<10ms BM25) |
| Coverage | ≥ 80% target |
| Test data | Use factories, not hardcoded data |
| Error testing | Test both happy path and error cases |

---

## References

- `rules/coding-standards.md` — Section 2 (Unit Tests)
- `skills/test-hygiene/SKILL.md` — Testing philosophy
- `tmp/vtic/tests/` — Reference test suite
