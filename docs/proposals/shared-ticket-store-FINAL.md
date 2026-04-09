# Shared Ticket Store — FINAL Proposal

**Status:** Definitive
**Date:** 2026-04-09
**Supersedes:** All prior drafts (GLM-5, GPT-5.4, GLM-5.1)

---

## 1. Proposal Scores

| Criterion | GLM-5 (P1) | GPT-5.4 (P2) | GLM-5.1 (P3) |
|---|---|---|---|
| Correctness | 2 — auto-merge silently loses data; claim via `owner` breaks repo path | 4 — right architecture, wrong scope for v1 | 5 — catches every bug |
| Completeness | 3 — misses index atomicity, lock TOCTOU | 5 — comprehensive but over-scoped | 4 — deliberately cuts features |
| Simplicity | 3 — ~200 LOC but has hidden complexity | 2 — ~470 LOC, 1 new file, 2 new CLI commands | 5 — ~190 LOC, 0 new files, 0 new commands |
| User-Value Alignment | 3 — lean but wrong conflict policy | 3 — user asked for lean, got a framework | 5 — ships smallest thing that works |

**Winner:** GLM-5.1's architecture, with selective adoption of GPT-5.4's best ideas.

---

## 2. Idea-by-Idea Verdict

| Idea | Source | Verdict | Reason |
|---|---|---|---|
| `agent_id` field on Ticket | P1,P2,P3 | KEEP | Core provenance |
| `created_by` field on Ticket | P1,P2,P3 | KEEP | Separate from `agent_id`, tracks origin |
| `version` field on Ticket | P1,P2,P3 | KEEP | Enables optimistic concurrency |
| `assignee` field on Ticket | P2,P3 | KEEP | Proper claim mechanism, independent of `owner` |
| `expected_version` on TicketUpdate | P1,P2,P3 | KEEP | Trigger for conflict check |
| Explicit conflict rejection (no auto-merge) | P2,P3 | KEEP | AI agents need conflicts surfaced, not silently resolved |
| `ConflictError` with `current_ticket` payload | P2,P3 | KEEP | Agent needs full state to decide retry vs defer |
| `SharedConfig` in config.py | P1,P2,P3 | KEEP | Opt-in config, `enabled=false` default |
| `effective_tickets_dir` property | P2,P3 | KEEP | Clean abstraction |
| `_with_lock()` context manager (persistent lock) | P2,P3 | KEEP | Eliminates TOCTOU, drops lock-file-deletion dance |
| Atomic index writes (`_persist_index`) | P2,P3 | KEEP | Real bug fix — `write_text()` corrupts under concurrent writes |
| `version` in `_ticket_signature()` | P1,P2,P3 | KEEP | Invalidates cache when another agent updates |
| `assignee` in `search_text` property | P3 | KEEP | Assignee is ticket content, agents search for their assignments |
| `assignee` filter on SearchFilters | P3 | KEEP | Primary coordination filter |
| Auto-merge on conflict | P1 | CUT | Silently discards agent intent; AI agents must decide |
| Claim via `owner` field | P1 | CUT | `owner` is repo owner validated by `parse_repo()` |
| Journal module (`journal.py`) | P2 | DEFER | Right idea, wrong phase. Ship v1 first, measure, then add |
| Agent manifest (`.vtic-agents.json`) | P2 | DEFER | 5 trusted agents on one machine. Discover from tickets. |
| `vtic journal` CLI command | P2 | DEFER | Depends on journal module |
| `vtic status` CLI command | P1,P2 | DEFER | Can be built from existing `list --repo` output |
| `vtic migrate` CLI command | P1,P2 | DEFER | One-time utility, not core |
| `GET /journal` API endpoint | P2 | DEFER | Depends on journal module |
| `created_by` filter on SearchFilters | P1,P2 | DEFER | Low value in v1; agents discover via list, not filter |
| `agent_id` filter on SearchFilters | P2 | DEFER | Same rationale |
| `agent_id`/`created_by` in `_ticket_signature()` | P2 | CUT | These are metadata, not ticket content. Including them would invalidate index whenever a different agent touches a ticket — causing unnecessary rebuilds |
| `setdefault()` in `_parse_frontmatter()` | P1,P2 | CUT | Wrong. Pydantic field defaults handle missing keys automatically via `Ticket(**data)` |
| Config validation: require `agent_id` when `enabled=true` | P2 | CUT | Silent defaults. Let it degrade gracefully |
| `from_env()` inline handling for shared vars | P2 | CUT | Existing `_ENV_OVERRIDES` dict loop in `load_config()` handles this |

---

## 3. Exact Code Changes

### 3.1 `src/vtic/models.py`

**Add to `Ticket` class, after line 132 (after `slug` field, before validators):**

```python
    # Multi-agent coordination fields
    agent_id: str | None = Field(default=None, max_length=100,
        description="Agent that last modified this ticket")
    created_by: str | None = Field(default=None, max_length=100,
        description="Agent that created this ticket")
    version: int = Field(default=1, ge=1,
        description="Optimistic concurrency version counter")
    assignee: str | None = Field(default=None, max_length=100,
        description="Agent currently assigned to work on this ticket")
```

**Add to `TicketUpdate` class, after line 273 (after `tags` field):**

```python
    expected_version: int | None = Field(default=None, ge=1,
        description="Expected current version for optimistic concurrency check")
    assignee: str | None = Field(default=None, max_length=100,
        description="Agent to assign this ticket to (null clears assignment)")
```

**Update `search_text` property (line 203-205):**

```python
    @property
    def search_text(self) -> str:
        parts = [
            self.id, self.title, self.description or "", self.file or "",
            self.fix or "", " ".join(self.tags), self.assignee or "",
        ]
        return " ".join(parts)
```

**Add to `TicketResponse` class, after line 326 (after `filepath` field):**

```python
    agent_id: str | None = None
    created_by: str | None = None
    version: int = 1
    assignee: str | None = None
```

**Update `from_ticket()` method (line 328-348):**

```python
    @classmethod
    def from_ticket(cls, ticket: Ticket) -> "TicketResponse":
        return cls(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            fix=ticket.fix,
            repo=ticket.repo,
            owner=ticket.owner,
            category=ticket.category.value,
            severity=ticket.severity.value,
            status=ticket.status.value,
            file=ticket.file,
            tags=ticket.tags,
            created_at=ticket.created_at.isoformat(),
            updated_at=ticket.updated_at.isoformat(),
            slug=ticket.slug,
            is_terminal=ticket.is_terminal,
            filename=ticket.filename,
            filepath=ticket.filepath,
            agent_id=ticket.agent_id,
            created_by=ticket.created_by,
            version=ticket.version,
            assignee=ticket.assignee,
        )
```

**Add to `SearchFilters` class, after line 366 (after `owner` field):**

```python
    assignee: str | None = Field(default=None,
        description="Filter by assigned agent")
```

### 3.2 `src/vtic/config.py`

**Add after `SearchConfig` class (after line 82):**

```python
class SharedConfig(BaseModel):
    """Multi-agent shared store configuration."""

    model_config = {"validate_default": True}

    enabled: bool = Field(default=False,
        description="Enable shared ticket store mode")
    store_dir: Path | None = Field(default=None,
        description="Shared store directory (overrides tickets.dir when set)")
    agent_id: str | None = Field(default=None, max_length=100,
        description="Agent identity for shared mode")

    @field_validator("store_dir")
    @classmethod
    def validate_store_dir(cls, v: Path | None) -> Path | None:
        if v is not None:
            return v.expanduser().resolve()
        return None
```

**Add to `VticConfig` class, after line 91 (after `search` field):**

```python
    shared: SharedConfig = Field(default_factory=SharedConfig)
```

**Add to `_ENV_OVERRIDES` dict (after line 31):**

```python
    "VTIC_SHARED_ENABLED": ("shared", "enabled"),
    "VTIC_SHARED_STORE_DIR": ("shared", "store_dir"),
    "VTIC_AGENT_ID": ("shared", "agent_id"),
```

**Add property to `VticConfig`, after `from_env()` method:**

```python
    @property
    def effective_tickets_dir(self) -> Path:
        """Return the effective tickets directory, accounting for shared mode."""
        if self.shared.enabled and self.shared.store_dir:
            return self.shared.store_dir
        return self.tickets.dir
```

### 3.3 `src/vtic/errors.py`

**Add after `TicketDeleteError` class (after line 109):**

```python
class ConflictError(VticError):
    """Raised when optimistic concurrency check fails."""

    def __init__(
        self,
        ticket_id: str,
        expected: int,
        actual: int,
        current_ticket: Any = None,
    ) -> None:
        self.ticket_id = ticket_id
        self.expected = expected
        self.actual = actual
        self.current_ticket = current_ticket
        super().__init__(
            error_code="CONFLICT",
            message=(
                f"Ticket {ticket_id} version conflict: "
                f"expected {expected}, actual {actual}. "
                f"Re-read the ticket and retry."
            ),
            status_code=409,
        )
```

**Add `from typing import Any` to the imports at the top of errors.py:**

```python
from __future__ import annotations

from typing import Any
```

### 3.4 `src/vtic/storage.py`

**Update import (line 20-27) to include `ConflictError`:**

```python
from .errors import (
    ConflictError,
    TicketAlreadyExistsError,
    TicketDeleteError,
    TicketNotFoundError,
    TicketReadError,
    TicketWriteError,
    ValidationError,
)
```

**Update `__init__` (line 58-60):**

```python
    def __init__(self, base_dir: Path, *, agent_id: str | None = None) -> None:
        self.base_dir = Path(base_dir)
        self._agent_id = agent_id
        self._last_list_errors: list[ErrorDetail] = []
```

**Add `_with_lock` context manager after `_lock_exclusive` (after line 68):**

```python
    @contextmanager
    def _with_lock(self):
        """Acquire exclusive lock. File persists after release."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.base_dir / ".vtic.lock"
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            self._lock_exclusive(lock_file)
            try:
                yield
            finally:
                pass  # lock released on fd close; file persists
```

**Add `from contextlib import contextmanager` to the imports at top of file.**

**Update `create_ticket` (line 80-128):**

```python
    def create_ticket(
        self,
        *,
        title: str,
        repo: str,
        owner: str | None,
        category: Category,
        severity: Severity,
        status: Status,
        description: str | None,
        fix: str | None,
        file: str | None,
        tags: list[str],
        slug: str,
    ) -> Ticket:
        """Create a ticket with locked, atomic ID allocation.

        This is the only safe public API for creating new tickets concurrently.
        """
        with self._with_lock():
            ticket_id = self._next_id(category)
            now = utc_now()
            ticket = Ticket(
                id=ticket_id,
                title=title,
                description=description,
                fix=fix,
                repo=repo,
                owner=owner,
                category=category,
                severity=severity,
                status=status,
                file=file,
                tags=tags,
                created_at=now,
                updated_at=now,
                slug=slug,
                agent_id=self._agent_id,
                created_by=self._agent_id,
                version=1,
            )
            self._write_ticket(ticket, ticket_path(self.base_dir, ticket))
            return ticket
```

**Update `update` (line 182-229):**

```python
    def update(self, ticket_id: str, updates: TicketUpdate) -> Ticket:
        update_data = updates.model_dump(exclude_unset=True)
        if "repo" in update_data:
            raise ValidationError("Cannot change repo field on update")

        expected_version = update_data.pop("expected_version", None)

        with self._with_lock():
            current, current_path = self._find_ticket_path(ticket_id)

            if expected_version is not None and current.version != expected_version:
                raise ConflictError(
                    ticket_id=ticket_id,
                    expected=expected_version,
                    actual=current.version,
                    current_ticket=current,
                )

            data = current.model_dump()
            data.update(update_data)
            if "title" in update_data:
                data["slug"] = slugify(str(update_data["title"]))
            data["updated_at"] = utc_now()
            data["version"] = current.version + 1
            data["agent_id"] = self._agent_id

            updated_ticket = Ticket(**data)
            new_path = ticket_path(self.base_dir, updated_ticket)
            temp_path: Path | None = None
            try:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=new_path.parent,
                    delete=False,
                ) as temp_file:
                    temp_file.write(self._serialize_ticket(updated_ticket))
                    temp_path = Path(temp_file.name)
                os.replace(temp_path, new_path)
                temp_path = None
                if new_path != current_path and current_path.exists():
                    current_path.unlink()
            except OSError as exc:
                if temp_path is not None:
                    try:
                        temp_path.unlink()
                    except FileNotFoundError:
                        pass
                    except OSError:
                        pass
                raise TicketWriteError(updated_ticket.id, str(exc)) from exc

        return updated_ticket
```

**Update `_serialize_ticket` (line 395-417):**

```python
    def _serialize_ticket(self, ticket: Ticket) -> str:
        frontmatter = {
            "id": ticket.id,
            "title": ticket.title,
            "repo": ticket.repo,
            "category": ticket.category.value,
            "severity": ticket.severity.value,
            "status": ticket.status.value,
            "owner": ticket.owner,
            "file": ticket.file,
            "created_at": isoformat_z(ticket.created_at),
            "updated_at": isoformat_z(ticket.updated_at),
            "tags": ticket.tags,
            "version": ticket.version,
        }
        if ticket.agent_id:
            frontmatter["agent_id"] = ticket.agent_id
        if ticket.created_by:
            frontmatter["created_by"] = ticket.created_by
        if ticket.assignee:
            frontmatter["assignee"] = ticket.assignee
        lines = ["---", yaml.safe_dump(frontmatter, sort_keys=False).strip(), "---", ""]
        lines.append(DESCRIPTION_DELIMITER)
        if ticket.description:
            lines.append(ticket.description.strip())
        if ticket.fix:
            lines.append("")
            lines.append(FIX_DELIMITER)
            lines.append(ticket.fix.strip())
        return "\n".join(lines).rstrip() + "\n"
```

**Update `_matches_filters` (add after the `owner` check at line 464-465):**

```python
        if filters.assignee is not None and ticket.assignee != filters.assignee:
            return False
```

**No changes to `_parse_frontmatter`.** It returns a raw dict; `Ticket(**data)` applies Pydantic field defaults for missing keys. Both prior proposals were wrong about needing `setdefault()` calls.

### 3.5 `src/vtic/search.py`

**Update `_ticket_signature` (line 110-122):**

```python
    def _ticket_signature(self, ticket: Ticket) -> str:
        """Return a stable signature for cache invalidation."""

        payload = {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "fix": ticket.fix,
            "file": ticket.file,
            "tags": ticket.tags,
            "updated_at": ticket.updated_at.isoformat(),
            "version": ticket.version,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
```

Only `version` is added. Not `agent_id` or `assignee` — those are metadata, not searchable content. Including them would cause unnecessary index rebuilds when any agent touches a ticket.

**Update `_persist_index` (line 142-154) for atomic writes:**

```python
    def _persist_index(self) -> None:
        """Persist the current index to disk for future processes."""

        if not self.store.base_dir.exists():
            return

        payload = {
            "version": 1,
            "ticket_signatures": list(self._ticket_signatures),
            "tokenized_documents": self._tokenized_documents,
        }
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        import tempfile as _tf
        with _tf.NamedTemporaryFile(
            mode="w", encoding="utf-8",
            dir=self._index_path.parent, delete=False,
        ) as tmp:
            tmp.write(json.dumps(payload))
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, self._index_path)
```

**Add `import os` to search.py imports** (it's not currently imported — `tempfile` and `Path` are used but `os` is needed for `os.replace`).

### 3.6 `src/vtic/api.py`

**Update `create_app` (line 76-87):**

```python
def create_app(tickets_dir: str | None = None) -> FastAPI:
    """Create the vtic FastAPI application."""

    config = load_config()
    base_dir = Path(tickets_dir) if tickets_dir is not None else config.effective_tickets_dir
    agent_id = config.shared.agent_id if config.shared.enabled else None
    store = TicketStore(base_dir, agent_id=agent_id)
    search = TicketSearch(store)

    app = FastAPI(title="vtic API", version=__version__)
    app.state.store = store
    app.state.search = search
```

**Update `update_ticket` endpoint (line 183-185) to handle ConflictError:**

```python
    @app.patch(
        "/tickets/{ticket_id}",
        response_model=TicketResponse,
        responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    async def update_ticket(ticket_id: str, payload: TicketUpdate) -> TicketResponse:
        from vtic.errors import ConflictError
        ticket_id = _validate_ticket_id(ticket_id)
        try:
            return TicketResponse.from_ticket(store.update(ticket_id, payload))
        except ConflictError as exc:
            raise _error_json(ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
                status_code=409,
                details=[ErrorDetail(
                    field=ticket_id,
                    message=f"Current version is {exc.actual}, expected {exc.expected}. "
                           "Re-read the ticket and retry with the updated version.",
                    code="VERSION_MISMATCH",
                )],
            ))
```

**Update `list_tickets` endpoint (add `assignee` query parameter):**

Add to the function signature (after line 138, after `owner`):

```python
        assignee: str | None = Query(None),
```

Add to the `SearchFilters` construction (after line 153):

```python
            assignee=assignee,
```

### 3.7 `src/vtic/cli/main.py`

**Update `_resolve_store` (line 42-45):**

```python
def _resolve_store(tickets_dir: Path | None) -> TicketStore:
    config = load_config()
    base_dir = tickets_dir or config.effective_tickets_dir
    agent_id = config.shared.agent_id if config.shared.enabled else None
    return TicketStore(base_dir, agent_id=agent_id)
```

**Update `update` command (line 322-369) — add `--assignee` option:**

Add parameter after `description` (after line 337):

```python
    assignee: str | None = typer.Option(None, "--assignee", help="Assign ticket to agent"),
```

Add to the update_data dict (after line 361):

```python
        if assignee is not None:
            update_data["assignee"] = assignee
```

**No new CLI commands.** All existing commands (`create`, `update`, `list`, `get`, `delete`, `search`) work unchanged in shared mode. `create` and `update` automatically use `agent_id` from the store constructor. `list` and `search` include all agents' tickets because the store's `base_dir` is shared.

---

## 4. Migration Path

### Phase 0: Model + Config (non-breaking, zero user impact)
- Add 4 fields to Ticket, 2 to TicketUpdate, 4 to TicketResponse, 1 to SearchFilters
- Add SharedConfig to VticConfig
- All defaults; all existing tickets, configs, and code paths work unchanged
- Old ticket files without new fields: Pydantic field defaults apply (`None`/`1`)
- New ticket files with old code: `extra="ignore"` on VticBaseModel silently accepts unknown frontmatter keys

### Phase 1: Storage + Search (non-breaking, behind feature flag)
- Update TicketStore with `_with_lock()`, optimistic concurrency, `ConflictError`
- Fix `_persist_index()` for atomic writes
- All behind `shared.enabled=false` default
- Single-agent setups see zero behavioral change
- `expected_version=None` (no version passed) means no version check — backward compatible with all existing callers

### Phase 2: Opt-in shared mode
Each agent adds to its `vtic.toml`:
```toml
[shared]
enabled = true
store_dir = "/home/smoke01/.shared-vtic"
agent_id = "apex"
```
Or via environment:
```
VTIC_SHARED_ENABLED=true VTIC_SHARED_STORE_DIR=/home/smoke01/.shared-vtic VTIC_AGENT_ID=apex vtic list
```

First use creates the directory and persistent `.vtic.lock` file. No migration of existing ticket files needed — agents start fresh in the shared directory. Existing local tickets stay where they are.

### Compatibility matrix

| Scenario | Works? |
|---|---|
| Single-agent, no config change | Yes |
| Old ticket files, new code | Yes (Pydantic defaults) |
| New ticket files, old code | Yes (`extra="ignore"`) |
| Two agents, both `shared=false` | Yes (isolated) |
| Two agents, both `shared=true`, same dir | Yes (coordinated) |
| One agent `shared=true`, one not | Yes (different stores) |

---

## 5. Edge Cases

**Concurrent creates:** Both agents enter `_with_lock()`, serialized by `fcntl.flock()`. First gets C5, second gets C6. Content may be duplicates, but IDs are unique. Agents should search before creating.

**Concurrent updates:** Agent A reads v1, Agent B reads v1. A updates with `expected_version=1` → succeeds (v2). B updates with `expected_version=1` → `ConflictError(actual=2, current_ticket=v2)`. B reads v2 and retries. If neither passes `expected_version` (CLI usage), both succeed — last write wins, same as current behavior.

**Stale lock after crash:** `fcntl.flock()` releases on fd close (process exit, including SIGKILL). The persistent lock file is just an anchor — no stale lock issue.

**Index corruption:** Fixed by atomic writes. Two agents writing index simultaneously: last `os.replace()` wins, result is always valid JSON.

**Deleted tickets:** Trash is per-store. In shared mode, trash is shared. `_iter_ticket_paths(include_trash=False)` excludes trashed tickets from all agents.

**Search consistency race:** Agent A creates a ticket. Agent B searches immediately. B's `_load_cached_tickets()` checks file mtimes, re-reads the new file. Sub-millisecond race possible but acceptable — next search picks it up.

**Assignee vs owner:** Completely independent fields. `owner` = repo owner (validated by `parse_repo()`, used in path). `assignee` = agent working on ticket (used for coordination). `owner="661818yijack"` and `assignee="apex"` coexist without conflict.

**`assignee` clearing:** Pass `--assignee ""` via CLI or `{"assignee": null}` via API. Pydantic includes it in `model_dump(exclude_unset=True)` since it was explicitly set.

---

## 6. Implementation Order

### P0 — Core (ship first, ~150 LOC across 5 files)

1. `models.py`: Add 4 fields to Ticket, 2 to TicketUpdate, 4 to TicketResponse, 1 to SearchFilters. Update `search_text` and `from_ticket()`.
2. `errors.py`: Add `ConflictError` class.
3. `config.py`: Add `SharedConfig`, `effective_tickets_dir` property, env overrides.
4. `storage.py`: Update `__init__`, add `_with_lock()`, update `create_ticket()`, `update()`, `_serialize_ticket()`, `_matches_filters()`.
5. Write tests: model roundtrip, backward compat, concurrency conflict.

### P1 — Wire-up (~40 LOC across 3 files)

6. `search.py`: Add `version` to `_ticket_signature()`, fix `_persist_index()`.
7. `api.py`: Update `create_app()`, `update_ticket()`, `list_tickets()`.
8. `cli/main.py`: Update `_resolve_store()`, add `--assignee` to update command.
9. Write integration tests: two stores on same dir, concurrent operations.

### P2 — Measure, then iterate

10. Deploy to agents. Validate shared workflow works.
11. If agents need activity history → add journal module.
12. If agents need cross-agent dashboard → add `vtic status`.
13. If duplicates are a problem → add `vtic migrate`.

---

## 7. Summary

**What this ships:** ~190 lines of new/modified code. Zero new files. Zero new dependencies. Zero new CLI commands. Full backward compatibility. Every existing ticket, config, and code path works unchanged.

**What it enables:** Multiple agents point at the same ticket directory. They see each other's tickets. They get version counters for optimistic concurrency. They get a proper `assignee` field for coordination. Conflicts are surfaced, not silently resolved. The search index doesn't corrupt under concurrent writes.

**What it explicitly does not do:** No journal (defer to v2). No agent manifest (defer). No new CLI commands (defer). No migration utility (defer). No auto-merge (wrong for AI agents).

Ship the smallest thing that works. Measure. Then add more.
