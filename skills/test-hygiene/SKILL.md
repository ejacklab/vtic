---
name: test-hygiene
description: "Guidelines for writing effective tests that actually catch bugs. Use when: (1) writing tests for new code, (2) deciding whether to mock or use real services, (3) reviewing test quality, (4) setting up test infrastructure. NOT for: running tests (that's just exec)."
---

# Test Hygiene

## Core Principle

**Real tests over mocks.** Mocks give false confidence. Real-service tests catch real bugs.

## Mock vs Real Decision

| Dependency | Mock? | Why |
|------------|-------|-----|
| External API (OpenAI, GitHub) | ✅ Mock | Unreliable, rate-limited, costs money |
| Internal service (TicketService) | ❌ Real | Must verify actual behavior |
| Database (Zvec, Postgres) | ❌ Real | Different DBs behave differently |
| File system | ❌ Real | Use tmp_path, not mocks |
| HTTP client (internal) | ❌ Real | Use TestClient, not mocks |
| Time/timeouts | ✅ Mock | Can't wait for real time in tests |

## vtic Lessons

### Mocks Hide Real Bugs
- Mock-based API route tests: all passed ✅
- Integration tests with real TicketService: **async/await bug caught** ❌
- The mock didn't enforce the actual async contract

### Test Types by Confidence

| Type | Confidence | Use For |
|------|-----------|---------|
| Unit test with real services | High | Core logic, data transformations |
| Integration test (FastAPI TestClient) | Highest | Full request→response flow |
| Unit test with mocks | Medium | External API calls only |
| Performance test | High | Verify targets (<10ms BM25, <5ms CRUD) |

## Test Infrastructure

```python
# Good pattern: tmp_path + real services
def test_create_ticket(client, tmp_path):
    """client = FastAPI TestClient with real TicketService + Zvec"""
    response = client.post("/tickets", json={"title": "Bug in login"})
    assert response.status_code == 201
    assert response.json()["title"] == "Bug in login"
```

```python
# Bad pattern: mocked everything
def test_create_ticket(mocker):
    mock_service = mocker.MagicMock()
    mock_service.create.return_value = Ticket(id="C1", ...)
    # This test proves nothing — it tests the mock, not the code
```

## Test Naming

Use descriptive names that explain what's being tested:
```
✅ test_search_with_filters_returns_only_matching_tickets
✅ test_create_ticket_with_missing_title_returns_400
❌ test_search
❌ test_create
```

## Edge Cases to Always Test

- Empty input / empty results
- Invalid input (wrong types, missing fields)
- Not found (404)
- Duplicate operations
- Boundary values (limit=0, limit=10000)
- Concurrent-like patterns (sequential rapid ops)
