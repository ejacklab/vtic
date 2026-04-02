# Code Review — Round 1

**Project:** vtic  
**Branch:** `feat/ticket-lifecycle-core`  
**Date:** 2026-04-03  
**Reviewer:** Codex (GPT-5.4) via Hermes  
**Files reviewed:** All `.py` under `src/vtic/` and `tests/`, plus `README.md` and `DATA_MODELS.md`  
**Test status:** 80/80 passing (0.62s)

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 2 |
| Warning  | 6 |
| Info     | 2 |

---

## Critical Findings

### C1 — Path traversal via repo field (security)

The repo validator in both `Ticket` and `TicketCreate` accepts `.` and `..` path segments. The regex `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$` matches `../escape/repo`. `parse_repo()` in `utils.py` splits on `/` without checking for traversal, and `ticket_path()` joins those segments directly into the filesystem path. `create()` writes to that path without verifying it stays under `base_dir`.

**Impact:** A repo value like `../escape/repo` resolves outside the ticket root, enabling arbitrary file write/read/delete on the host filesystem.

**References:**
- `src/vtic/models.py:120` — Ticket repo regex allows `.` and `..`
- `src/vtic/models.py:223` — TicketCreate repo regex allows `.` and `..`
- `src/vtic/utils.py:37` — `parse_repo()` only splits on `/`
- `src/vtic/utils.py:59` — `ticket_path()` joins segments directly
- `src/vtic/storage.py:27` — `create()` writes without path containment check

**Suggested fix:**
1. Reject repo segments containing `.` or `..` in the validator regex: `^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]/[a-zA-Z0-9][a-zA-Z0-9_.-]*[a-zA-Z0-9]$` (or strip `.`/`..` explicitly).
2. Add a runtime check in `ticket_path()` and all storage read/write/delete paths: verify `resolved_path.is_relative_to(base_dir.resolve())`.

---

### C2 — Race condition in ID generation and non-atomic file creation

`next_id()` derives the next ID by scanning existing files on disk. The API and CLI call `next_id()` separately from `create()`, and `create()` uses `path.exists()` followed by `write_text()` (non-atomic). Two concurrent writers can allocate the same ID, and the later write silently overwrites the earlier one.

**Impact:** Data loss or corruption under concurrent usage. Ticket files can be silently overwritten.

**References:**
- `src/vtic/storage.py:85` — `next_id()` scans files to derive next ID
- `src/vtic/api.py:94` — API calls `next_id()` then `create()` as separate steps
- `src/vtic/cli/main.py:88` — CLI calls `next_id()` then `create()` as separate steps
- `src/vtic/storage.py:28,33` — `create()` uses `exists()` + `write_text()` (non-atomic)

**Suggested fix:**
1. Use a file lock (e.g., `fcntl.flock` or `filelock`) around the ID allocation + file write sequence.
2. Use exclusive file creation: `open(path, "x")` or `os.open(path, os.O_CREAT | os.O_EXCL)` instead of `exists()` + `write_text()`.
3. Ideally, merge `next_id()` and `create()` into a single atomic storage method.

---

## Warning Findings

### W1 — API silently ignores unknown fields in create/search requests

`VticBaseModel` sets `extra="ignore"`, and both `TicketCreate` and `SearchRequest` inherit it. Typoed fields in `POST /tickets` or `POST /search` are silently dropped instead of returning 422. This conflicts with the "strict validation" contract in `DATA_MODELS.md`.

**References:**
- `src/vtic/models.py:95` — `extra="ignore"` on base model
- `src/vtic/models.py:215` — `TicketCreate` inherits `extra="ignore"`
- `src/vtic/models.py:341` — `SearchRequest` inherits `extra="ignore"`
- `DATA_MODELS.md:92` — spec says "strict validation"

**Suggested fix:** Set `extra="forbid"` on `TicketCreate` and `SearchRequest` (similar to `TicketUpdate` which already uses `extra="forbid"`).

---

### W2 — Search request fields accepted but ignored (`semantic`, `sort_by`, `sort_order`)

`SearchRequest` exposes `semantic`, `sort_by`, and `sort_order`, but the API only forwards `query`, `filters`, `topk`, and `offset`. The search engine is BM25-only and always returns `semantic=False`, despite README promises of hybrid and semantic search.

**References:**
- `src/vtic/models.py:346,349` — `SearchRequest` defines `semantic`, `sort_by`, `sort_order`
- `src/vtic/api.py:170` — API only forwards `query`, `filters`, `topk`, `offset`
- `src/vtic/search.py:105,199` — always returns `semantic=False`
- `README.md:20,66,110` — promises hybrid/semantic search

**Suggested fix:** Either implement semantic search and sorting, or remove these fields from the contract (and return a clear error if `semantic=True` is requested).

---

### W3 — Repo wildcard filtering documented but not implemented

`SearchFilters.repo` docstring says "supports wildcards" and the README shows `--repo "ejacklab/*"`, but filtering uses exact string equality only.

**References:**
- `src/vtic/models.py:330` — `SearchFilters.repo` says "supports wildcards"
- `src/vtic/storage.py:223` — filtering is exact equality only
- `README.md:70` — example uses `--repo "ejacklab/*"`

**Suggested fix:** Use `fnmatch.fnmatch()` for repo filtering, or document that only exact matching is supported.

---

### W4 — Markdown serialization/parsing is brittle; can corrupt tickets

Frontmatter is emitted by string concatenation, but fields like `title` and `owner` do not forbid embedded newlines. The ad-hoc line-by-line `_parse_frontmatter()` parser and `## Fix` body splitter can break on tickets with newlines in metadata or `## Fix` headings in the description.

**References:**
- `src/vtic/storage.py:192` — frontmatter emitted by string concatenation
- `src/vtic/storage.py:139` — line-by-line parser
- `src/vtic/storage.py:178` — body splits on `## Fix` marker
- `src/vtic/models.py:113,123` — `title` and `owner` allow newlines

**Suggested fix:**
1. Use `yaml.dump()` / `yaml.safe_load()` for frontmatter serialization/parsing.
2. Add explicit section delimiters (e.g., `<!-- DESCRIPTION -->` / `<!-- FIX -->`) instead of matching markdown headings.
3. Alternatively, strip/replace newlines from title and owner at the model level.

---

### W5 — Implementation does not match documented file format or CLI contract

Storage uses YAML frontmatter, but the README specifies heading-based markdown metadata. The README documents `vtic create --fix`, `vtic search --semantic`, and positional `update/delete` IDs, but the CLI lacks `--fix` and `--semantic`, and requires `--id` for update/delete.

**References:**
- `src/vtic/storage.py:120,192` — YAML frontmatter in implementation
- `README.md:155` — heading-based metadata in docs
- `README.md:47,67,84` — documents `--fix`, `--semantic`, positional IDs
- `src/vtic/cli/main.py:71,159,202,241` — CLI requires `--id`, no `--fix`/`--semantic`

**Suggested fix:** Either update the README to match the implementation, or update the implementation to match the README. Pick one as the source of truth.

---

### W6 — Config schema mismatch with README; config parse errors not normalized

README documents `[api]` section, `enable_semantic`, and `"custom"` embedding provider. Code expects `[server]`, `semantic_enabled`, and `Literal["openai", "local", "none"]`. Also `from_env()` does raw `int()` casts and `from_toml()` doesn't wrap TOML errors, so bad config crashes with unstructured exceptions.

**References:**
- `README.md:187,190,195` — documents `[api]`, `enable_semantic`, `"custom"`
- `src/vtic/config.py:28` — code uses `[server]`
- `src/vtic/config.py:43,44` — code uses `semantic_enabled`, `Literal["openai", "local", "none"]`
- `src/vtic/config.py:94,105` — raw `int()` casts in `from_env()`
- `src/vtic/config.py:76` — `from_toml()` doesn't wrap errors

**Suggested fix:** Align config schema with README. Wrap `int()` casts and TOML parsing in try/except with `ConfigError`.

---

## Info Findings

### I1 — Test coverage misses highest-risk paths

No tests for:
- Repo path traversal (`../escape/repo`)
- Newline/frontmatter injection in title or owner
- Description text containing `## Fix` heading
- Wildcard repo filters (`ejacklab/*`)
- Semantic/sort flags being silently ignored
- Bad env/TOML config values
- Malformed request bodies with unknown fields
- Actual concurrent ID generation (the "concurrent" test is sequential)

**References:**
- `tests/test_storage.py:140` — `test_concurrent_id_generation` is sequential
- `tests/test_api.py:61` — no malformed body tests

**Suggested fix:** Add targeted tests for each of these scenarios, especially path traversal and concurrent ID allocation.

---

### I2 — Maintainability: duplicated constants and broken type-checking import

`CATEGORY_PREFIXES` is defined in both `models.py:73` and `constants.py:9`, inviting drift. `__init__.py` exposes a placeholder `TicketService` and has a type-checking import of a non-existent `.ticket` module.

**References:**
- `src/vtic/models.py:73` — first `CATEGORY_PREFIXES` definition
- `src/vtic/constants.py:9` — second `CATEGORY_PREFIXES` definition
- `src/vtic/__init__.py:13` — imports non-existent `.ticket` module

**Suggested fix:** Keep `CATEGORY_PREFIXES` only in `constants.py` and import it in `models.py`. Fix or remove the `TYPE_CHECKING` import in `__init__.py`.

---

## Specific Checks

| Check | Status | Notes |
|-------|--------|-------|
| Markdown file I/O safe (no path traversal)? | ❌ No | C1: repo field allows `.`/`..` traversal |
| CLI inputs properly validated? | ⚠️ Partial | Enums OK, repo path safety not enforced |
| API handles malformed requests? | ⚠️ Partial | Pydantic catches type errors, but unknown fields silently ignored |
| Race conditions in ID generation? | ❌ Yes | C2: non-atomic next_id() + create() |
| Empty search queries handled gracefully? | ✅ Yes | Returns empty results, covered by tests |

---

## Positive Observations

- **80/80 tests pass** with good coverage of happy paths
- Clean Pydantic model design with proper validation
- Good separation of concerns (models, storage, API, CLI, search)
- `TicketUpdate` correctly uses `extra="forbid"`
- Empty search query handling is correct and tested
- Category prefix system is well-designed
- File naming convention (category prefix + number) is clean and deterministic
