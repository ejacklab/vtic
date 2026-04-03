# Code Review — Round 1

**Project:** vtic  
**Branch:** `feat/ticket-lifecycle-core`  
**Date:** 2026-04-04  
**Reviewer:** Codex (gpt-5.4) + Apex (manual verification)  
**Test Status:** 114/114 passing (0.61s)  
**Files Reviewed:** 11 source files (`src/vtic/`), 7 test files (`tests/`)

---

## Summary

The codebase is well-structured with clean separation of concerns (models, storage, search, API, CLI). Path traversal protections are solid, BM25 search is correctly implemented, and concurrent ID generation is properly guarded with `fcntl.flock`. No critical bugs found. The main concerns are CLI error handling gaps, config validation bypass, test coverage gaps (API tests don't use TestClient), and spec drift between the data model spec and the implemented search API.

**Severity counts:** 0 critical, 8 warning, 6 info

---

## Findings

### WARNING-1: CLI commands don't catch `ValueError` from `parse_repo()`

**Files:** `src/vtic/cli/main.py:123-141`, `src/vtic/cli/main.py:267-292`, `src/vtic/utils.py:39-47`

**Description:** The `create()` command calls `parse_repo(repo)` which raises plain `ValueError` on malformed input (e.g., missing `/`). But the command only catches `VticError`, so users get a raw traceback instead of a clean CLI error message. Similarly, `update()` calls `Category(category)` at line 278 which also raises `ValueError` for invalid category strings.

**Impact:** Poor UX — raw Python tracebacks shown to CLI users on invalid input.

**Suggestion:** Add `except (ValueError, PydanticValidationError)` to the CLI command try/except blocks, and route them through `_exit_with_error()` with a friendly message.

---

### WARNING-2: Config env overrides can bypass cross-field validation

**Files:** `src/vtic/config.py:62-74`, `src/vtic/config.py:99-125`, `src/vtic/config.py:144-156`

**Description:** `SearchConfig` has model validators for semantic config (`semantic_enabled + provider="none"` is invalid) and weight sum validation. But `from_env()` mutates fields after model construction (e.g., `config.search.semantic_enabled = ...`), and config models don't enable `validate_assignment`. Similarly, `load_config()` uses `setattr` to apply env overrides after the fact. This means invalid combinations like `VTIC_SEARCH_SEMANTIC_ENABLED=true` + `VTIC_SEARCH_EMBEDDING_PROVIDER=none` will silently pass.

**Impact:** Invalid config accepted without error, leading to confusing runtime failures.

**Suggestion:** Either (a) merge TOML + env data into a dict first and instantiate `VticConfig` once, or (b) add `validate_assignment=True` to config model configs, or (c) re-validate after applying overrides.

---

### WARNING-3: Search implementation doesn't match DATA_MODELS.md spec

**Files:** `src/vtic/models.py:366-393`, `src/vtic/api.py:161-172`, `DATA_MODELS.md:442-454`

**Description:** The spec defines `SearchRequest` with `semantic`, `sort_by`, and `sort_order` fields. The implementation:
- Actively **rejects** `semantic=True` via a validator (line 389-392)
- **Omits** `sort_by` and `sort_order` fields entirely
- Uses `topk` and `offset` for pagination (spec also has these)

The spec describes a hybrid search system that doesn't exist yet.

**Impact:** Spec/code mismatch creates confusion for contributors and API consumers.

**Suggestion:** Update `DATA_MODELS.md` and `README.md` to reflect the current keyword-only search API. Add a `<!-- TODO -->` comment in the spec for planned features (semantic, sort_by, sort_order).

---

### WARNING-4: API list endpoint uses untyped query params

**Files:** `src/vtic/api.py:112-134`

**Description:** `list_tickets()` takes `severity`, `status_value`, and `category` as raw `str | None` query params. Validation only happens when constructing `SearchFilters`. While Pydantic will catch invalid values at runtime (producing a 422), the OpenAPI schema won't advertise the valid enum values. This conflicts with the README's "OpenAPI 3.1 conventions" guidance.

**Impact:** Weakened API documentation; consumers can't discover valid values from the schema.

**Suggestion:** Use typed params like `severity: Severity | None = Query(None)` or accept `list[Severity]` directly.

---

### WARNING-5: `next_id()` is public but not thread-safe

**Files:** `src/vtic/storage.py:194-207`

**Description:** The `create_ticket()` method safely generates IDs under `fcntl.flock`. However, `next_id()` is a public method that scans the filesystem without locking. Any caller doing `id = store.next_id(category)` then `store.create(ticket)` separately can race and produce duplicate IDs.

**Impact:** External callers using `next_id()` + `create()` risk ID collisions under concurrency.

**Suggestion:** Either (a) make `next_id()` private (`_next_id`), or (b) add a docstring warning that `create_ticket()` is the only safe creation API, or (c) add locking to `next_id()`.

---

### WARNING-6: `create()` method is not atomic

**Files:** `src/vtic/storage.py:47-50`, `src/vtic/storage.py:339-347`

**Description:** The public `create()` method writes directly with `open("x")` without file locking or temp-file atomic write. `create_ticket()` and `update()` both use `fcntl.flock` + temp files for atomicity, but `create()` doesn't. This creates inconsistent durability semantics across the public API.

**Impact:** Concurrent callers using `create()` can corrupt state or lose writes.

**Suggestion:** Route `create()` through the same atomic write path, or document it as a low-level method for pre-validated tickets where the caller handles concurrency.

---

### WARNING-7: API tests bypass HTTP layer

**Files:** `tests/test_api.py:61-65`

**Description:** API tests call route functions directly (via `_route_endpoint()` helper) instead of using FastAPI's `TestClient`. This means:
- Malformed JSON bodies are never tested
- Exception handlers (VticError, ValidationError) are never exercised
- Query param coercion is not tested
- HTTP status codes are not verified for error cases
- OpenAPI schema generation is not validated

**Impact:** Significant test coverage gap for the API layer.

**Suggestion:** Migrate to `from starlette.testclient import TestClient` and test through `client.post("/tickets", json=...)` to exercise the full HTTP stack.

---

### WARNING-8: CLI tests don't cover invalid inputs

**Files:** `tests/test_cli.py`

**Description:** No CLI tests verify behavior when users provide invalid `--repo`, `--category`, `--file`, or `--tags` values. Since the CLI doesn't catch `ValueError` (see WARNING-1), these tests would reveal raw tracebacks.

**Impact:** Broken CLI UX goes undetected.

**Suggestion:** Add tests using `typer.testing.CliRunner` that invoke CLI commands with invalid inputs and verify clean error messages.

---

## Info-Level Findings

### INFO-1: `TicketUpdate.extra="forbid"` works correctly

**File:** `src/vtic/models.py:261-279`

In Pydantic v2, a subclass `model_config` overrides the parent's config. `TicketUpdate` sets `extra="forbid"` which correctly overrides `VticBaseModel`'s `extra="ignore"`. Confirmed by existing test at `tests/test_models.py:203`.

### INFO-2: Path traversal protection is solid

**Files:** `src/vtic/utils.py:65-73`, `src/vtic/models.py:177-187`

`parse_repo()` rejects `.` and `..` segments. `ticket_path()` resolves the full path and checks `is_relative_to(base_dir)`. The `Ticket._normalize_repo()` validator also rejects traversal patterns. No traversal path found.

### INFO-3: Empty search queries handled gracefully

**Files:** `src/vtic/search.py:183-200`, `tests/test_search.py:210`

When the query tokenizes to empty, search returns all filtered tickets sorted by ticket ID with `score=1.0`. Properly tested.

### INFO-4: Search index is ephemeral

**Files:** `src/vtic/search.py:110-115`, `src/vtic/cli/main.py:331-343`

The `reindex` command rebuilds the in-memory BM25 index but doesn't persist it. Every search/list call re-parses all markdown files from disk. This is acceptable for small local usage but doesn't match the "build index" framing in docs.

**Suggestion:** Either document as on-demand scanning, or add a persistent index file.

### INFO-5: `_parse_body()` handles edge cases correctly

**File:** `src/vtic/storage.py:276-306`

Empty descriptions, fix-only bodies, description-only bodies, and bodies with literal `## Fix` headings are all handled correctly. The `<!-- DESCRIPTION -->` / `<!-- FIX -->` HTML comment delimiters prevent ambiguity with markdown headings.

### INFO-6: BM25 regex is complete (display artifact)

**File:** `src/vtic/search.py:13`

The regex appears truncated in read tool output (`re.com...]+")`) but is complete and correct in the actual file. The `***` in `Category.AUTH` (line 39 of models.py) is also a display artifact — the actual value is `"auth"` as confirmed by runtime behavior and passing tests.

---

## Spec Compliance

| Spec Feature | Implementation | Status |
|---|---|---|
| Ticket CRUD (create/get/update/delete) | Fully implemented | ✅ |
| Soft delete + trash | Fully implemented | ✅ |
| Restore from trash | Fully implemented | ✅ |
| Markdown file format | Matches spec exactly | ✅ |
| Category prefix mapping | Correct and complete | ✅ |
| BM25 keyword search | Implemented | ✅ |
| Semantic search | Rejected with validator | ⚠️ Not implemented |
| Hybrid search (sort_by, sort_order) | Not in SearchRequest | ⚠️ Not implemented |
| Search pagination (topk/offset) | Implemented | ✅ |
| Path traversal protection | Solid | ✅ |
| Config (TOML + env) | Implemented with caveats | ⚠️ Validation gap |
| OpenAPI-first API design | Partial (untyped query params) | ⚠️ |

---

## Test Coverage Assessment

| Area | Covered | Gap |
|---|---|---|
| Model validation | ✅ Thorough | — |
| Storage CRUD | ✅ Thorough | — |
| Concurrent creation | ✅ Tested | — |
| Soft delete / trash | ✅ Tested | — |
| BM25 search | ✅ Tested | — |
| Empty queries | ✅ Tested | — |
| API (HTTP layer) | ❌ Direct function calls | Use TestClient |
| CLI error handling | ❌ Not tested | Use CliRunner |
| Config validation edge cases | ⚠️ Partial | Test env override combos |
| Malformed markdown bodies | ⚠️ Partial | Test content before delimiters |
| Invalid query param types | ❌ Not tested | Test via TestClient |

---

## Recommended Fix Priority

1. **WARNING-1 + WARNING-8:** CLI error handling (quick win, improves UX immediately)
2. **WARNING-7:** Migrate API tests to TestClient (improves confidence)
3. **WARNING-2:** Config validation bypass (prevents silent misconfiguration)
4. **WARNING-3:** Update spec to match implementation (documentation debt)
5. **WARNING-4:** Type API query params (OpenAPI quality)
6. **WARNING-5 + WARNING-6:** Storage API consistency (low risk, document for now)
