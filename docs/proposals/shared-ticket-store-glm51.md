# Proposal: Shared Ticket Store v3 — Lean Coordination

**Author:** GLM-5.1 (hermes-agent subagent)
**Date:** 2026-04-09
**Status:** Draft
**Reviews:** shared-ticket-store.md (GLM-5), shared-ticket-store-gpt54.md (GPT-5.4)

---

## 0. What This Proposal Does Differently

After reading both prior proposals and the full vtic codebase, here's the executive summary:

**The GPT-5.4 proposal is the better architecture. Validate it with these changes:**
1. Cut the agent manifest — unnecessary complexity for 5 trusted agents on one machine
2. Cut the journal module for v1 — it's the right idea but we should prove the core works first
3. Fix a real bug both proposals missed: `_write_ticket` uses exclusive `open("x")` which will fail when two agents create tickets at the same path (the tempfile pattern used in `update()` is not used in `create_ticket()`)
4. Simplify the API surface — no new CLI commands in v1, just make existing commands work in shared mode
5. Correct both proposals on `_parse_frontmatter` — neither correctly describes how new optional fields flow through the YAML dict to the Ticket constructor

The core change is small: 4 new fields on Ticket, a config section, optimistic concurrency in update(), and a ConflictError. That's it for v1. Everything else (journal, status command, migrate) is additive later.

---

## 1. Critique of Existing Proposals

### 1.1 GLM-5 Proposal (shared-ticket-store.md)

**Good:**
- Correctly identifies the three core problems and their root cause
- Backward compatibility analysis is thorough and correct
- Recognizes that pointing agents at the same directory is 80% of the solution
- Right-sized migration phasing — Phase 0/1/2 are genuinely non-breaking
- Honest about what the existing lock mechanism already handles (Section 5.1)

**Bad:**
- Auto-merge is wrong for AI agents. The `_can_auto_merge()` logic (Section 2.2.5, code at Section 3.3) will silently discard one agent's `status` transition. If Apex sets `status=in_progress` and Orion sets `status=fixed` in the same version window, the merge accepts whichever write arrives second. The losing agent never knows. AI agents need conflicts surfaced so they can reason about them.
- Claim mechanism via `owner` field (Section 2.2.4) is incorrect. `owner` is the repo owner, validated as part of `owner/repo`. Setting `owner="apex"` would break `ticket_path()` resolution because `ticket.filepath` uses `self.repo` not `self.owner` for path construction, but the `owner` field is still validated and displayed. More importantly, the `parse_repo()` function in `utils.py` splits on `/`, and the CLI's `create` command does `owner or derived_owner.lower()`. Repurposing this field creates ambiguity.
- Activity log as "P3 Future" (Section 6) underestimates its importance. Without a log, agents have no efficient way to discover what changed since their last session.

**Missing:**
- Does not address that `_write_ticket()` in `create_ticket()` uses `path.open("x")` (exclusive create), NOT the `tempfile + os.replace()` pattern used in `update()`. Under the shared directory, two agents trying to create a ticket with the same ID (from `_next_id()` race) will get a `FileExistsError` that's caught and turned into `TicketAlreadyExistsError`. This is actually handled correctly by the existing lock, but the proposal doesn't analyze this code path.
- Does not address `_persist_index()` non-atomic write (`search.py:154` uses `write_text()`)
- No mention of the lock file deletion TOCTOU issue

### 1.2 GPT-5.4 Proposal (shared-ticket-store-gpt54.md)

**Good:**
- Correctly identifies all flaws in the GLM-5 proposal (C1-C6 in Section 1.3 are all valid)
- Explicit conflict rejection (Section 2.2.6) is the right call for AI agents
- `assignee` field as a proper first-class concept is correct — completely independent of `owner`
- Journal as JSONL (Section 2.2.4) is the right design — no new dependencies, human-readable, crash-safe
- Persistent lock file (Section 2.2.8) correctly fixes the TOCTOU race
- Atomic index writes (Section 2.2.7) fixes a real bug
- Agent manifest (Section 2.2.5) enables discovery
- Backward compatibility analysis includes the mixed-mode case (some agents shared, some not) — important practical detail
- `effective_tickets_dir` property on config is clean

**Bad:**
- **Over-scoped for v1.** The proposal includes journal.py (~120 lines), agent manifest, `vtic journal` CLI command, `vtic status` CLI command, `GET /journal` API endpoint, journal rotation, and auto-clear assignee on terminal status. That's ~470 lines of new/modified code for a first pass. The user explicitly asked for lean.
- Journal is listed as P1 but is not actually needed for the core coordination problem. The core problem is: agents can't see each other's tickets. Sharing a directory fixes that. Version counters fix lost updates. The journal is an optimization for "what happened since I last checked" — useful, but not blocking.
- Agent manifest (`.vtic-agents.json`) is premature. With 5 trusted agents on one machine, you can discover agents by reading tickets. A manifest that agents must update on every write adds failure modes (corrupted manifest, stale entries, version mismatches). Defer it.
- The `read_for_ticket()` method reads the entire journal into memory (`read_recent(n=10000)`) and then filters. This won't scale.
- The journal `append()` acquires the lock separately from the ticket write, creating a window where a journal entry exists but the ticket doesn't (or vice versa). The proposal acknowledges this in Section 5.3 ("harmless") but it's messy.

**Missing:**
- Does not address that `create_ticket()` uses `_write_ticket()` which opens with `"x"` (exclusive) mode, while `update()` uses `tempfile.NamedTemporaryFile + os.replace()`. These are different atomicity guarantees. The proposal's updated `create_ticket()` code (Section 3.3) still calls `self._write_ticket()` but doesn't show updating that method to use the tempfile pattern.
- Does not address that `TicketUpdate` has `extra="forbid"` — adding `expected_version` and `assignee` to `TicketUpdate` will work, but if the `assignee` field needs to be clearable (set to None), Pydantic's `exclude_unset` behavior means `None` is excluded. This is a real gotcha.
- The `from_env()` method in config.py currently handles each env var individually (lines 107-132). The proposal adds shared env vars to `_ENV_OVERRIDES` dict but also shows inline handling in `from_env()`. These would conflict. The actual code uses the `_ENV_OVERRIDES` loop in `load_config()` (lines 158-163), not `from_env()` for overrides. The proposal should be consistent with the existing pattern.

### 1.3 What Both Proposals Get Wrong

Both proposals describe the `_parse_frontmatter` change as needing `data.setdefault()` calls. This is wrong. Looking at the actual code:

```python
# storage.py:306-314
raw = path.read_text(encoding="utf-8")
frontmatter, body = self._split_frontmatter(raw)
data = self._parse_frontmatter(frontmatter)  # returns dict
description, fix = self._parse_body(body)
data["description"] = description
data["fix"] = fix
data["slug"] = self._slug_from_path(path, data["id"])
return Ticket(**data)  # Pydantic handles defaults
```

The `_parse_frontmatter` method returns a raw dict from `yaml.safe_load()`. It only validates required fields (`category`, `severity`, `status`, `created_at`, `updated_at`). Missing optional fields simply won't be in the dict. When `Ticket(**data)` is called, Pydantic applies its field defaults. So no `setdefault` calls are needed in `_parse_frontmatter` — the defaults on the Pydantic fields handle it. Both proposals overcomplicate this.

Both proposals also miss that `version` should NOT default to `1` in `_parse_frontmatter`. If a ticket file genuinely has no `version` field (old ticket), it should get the default `1`. But the existing code path through `Ticket(**data)` already handles this — the field default of `1` kicks in. The proposals are correct about the behavior but wrong about needing explicit code changes in `_parse_frontmatter`.

---

## 2. Proposed Solution

### 2.1 Design Principles

1. Shared filesystem, not a server
2. Explicit conflict rejection — never auto-merge
3. Proper `assignee` field, independent of `owner`
4. Backward compatible — zero changes needed for single-agent setups
5. Minimal v1 — prove the core works before adding journal/manifest

### 2.2 What Changes in v1

Four new fields on `Ticket`. One new field on `TicketUpdate`. One new config section. Optimistic concurrency in `update()`. One new error type. Atomic index writes. That's it.

What explicitly does NOT change in v1:
- No journal module
- No agent manifest
- No new CLI commands
- No new API endpoints
- No `vtic migrate` command
- No `vtic status` command

### 2.3 New Ticket Fields

```python
# models.py — add to Ticket class after line 132

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

All optional, all have defaults. Old tickets work unchanged. New tickets written by agents in shared mode get these fields populated.

### 2.4 New TicketUpdate Fields

```python
# models.py — add to TicketUpdate class

expected_version: int | None = Field(default=None, ge=1,
    description="Expected current version for optimistic concurrency")
assignee: str | None = Field(default=None, max_length=100,
    description="Agent to assign (null clears assignment)")
```

**Important gotcha:** `TicketUpdate` uses `exclude_unset=True` when dumping (in `storage.py:183`). This means if a caller passes `assignee=None`, Pydantic considers it "set" and includes it. If a caller omits `assignee`, it's excluded. This is the correct behavior for clearing an assignment.

### 2.5 TicketResponse Updates

```python
# models.py — add to TicketResponse class

agent_id: str | None = None
created_by: str | None = None
version: int = 1
assignee: str | None = None
```

Update `from_ticket()`:

```python
@classmethod
def from_ticket(cls, ticket: Ticket) -> "TicketResponse":
    return cls(
        # ... existing fields ...
        agent_id=ticket.agent_id,
        created_by=ticket.created_by,
        version=ticket.version,
        assignee=ticket.assignee,
    )
```

No `getattr` guard needed — these are real fields on Ticket with defaults.

### 2.6 SearchFilters Updates

```python
# models.py — add to SearchFilters class

assignee: str | None = Field(default=None,
    description="Filter by assigned agent")
```

`agent_id` and `created_by` filters are intentionally omitted from v1. If agents need to filter by creator, they can use the journal (v2) or grep the markdown files. Keep filters minimal.

### 2.7 Search Text Updates

```python
# models.py — update search_text property

@property
def search_text(self) -> str:
    parts = [
        self.id, self.title, self.description or "", self.file or "",
        self.fix or "", " ".join(self.tags),
        self.assignee or "",  # Assignee is searchable
    ]
    return " ".join(parts)
```

`agent_id` and `created_by` are NOT included in search text — they're metadata, not ticket content. An agent searching for "apex" shouldn't match every ticket apex touched.

### 2.8 SharedConfig

```python
# config.py — new class

class SharedConfig(BaseModel):
    """Multi-agent shared store configuration."""
    model_config = {"validate_default": True}

    enabled: bool = Field(default=False,
        description="Enable shared ticket store mode")
    store_dir: Path | None = Field(default=None,
        description="Shared store directory (overrides tickets.dir)")
    agent_id: str | None = Field(default=None, max_length=100,
        description="Agent identity for shared mode")

    @field_validator("store_dir")
    @classmethod
    def validate_store_dir(cls, v: Path | None) -> Path | None:
        if v is not None:
            return v.expanduser().resolve()
        return None
```

Add to `VticConfig`:

```python
shared: SharedConfig = Field(default_factory=SharedConfig)
```

Add to `_ENV_OVERRIDES`:

```python
"VTIC_SHARED_ENABLED": ("shared", "enabled"),
"VTIC_SHARED_STORE_DIR": ("shared", "store_dir"),
"VTIC_AGENT_ID": ("shared", "agent_id"),
```

Add property to `VticConfig`:

```python
@property
def effective_tickets_dir(self) -> Path:
    """Return the effective tickets directory."""
    if self.shared.enabled and self.shared.store_dir:
        return self.shared.store_dir
    return self.tickets.dir
```

No validation that `agent_id` is required when `enabled=true` at the model level. Why? Because the existing `load_config()` doesn't raise on partial configs — it returns what it finds. If `agent_id` is missing in shared mode, `TicketStore` just doesn't tag tickets with an agent. The CLI can warn at runtime if desired, but don't make it a config error. Silent defaults over rigid validation.

### 2.9 ConflictError

```python
# errors.py — new class

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

The `current_ticket` payload is critical — it gives the conflicted agent the full state it needs to make a merge decision. This is the GPT-5.4 proposal's best idea, adopted verbatim.

### 2.10 Storage Changes

#### 2.10.1 Constructor

```python
def __init__(self, base_dir: Path, *, agent_id: str | None = None) -> None:
    self.base_dir = Path(base_dir)
    self._agent_id = agent_id
    self._last_list_errors: list[ErrorDetail] = []
```

Single parameter addition. No journal, no manifest.

#### 2.10.2 Persistent Lock File

Replace the lock pattern everywhere. Currently, `create_ticket()` and `update()` both:
1. Open `.vtic.lock` with `open("a+")`
2. Lock with `fcntl.flock()`
3. Do work
4. Delete `.vtic.lock` in `finally`

Change to: don't delete the file. `fcntl.flock()` is released when the fd closes. The file is just an anchor.

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

Apply in `create_ticket()` and `update()` by replacing the inline lock logic.

#### 2.10.3 Serialize New Fields

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
    # ... rest unchanged ...
```

Note: `version` is always written (it always has a value). Agent fields are only written when non-None, to keep old ticket files clean.

**No changes to `_parse_frontmatter()`.** It returns a raw dict. `Ticket(**data)` applies Pydantic defaults for missing fields. This is simpler than what either prior proposal described.

#### 2.10.4 Create Ticket

```python
def create_ticket(self, *, ..., agent_id: str | None = None) -> Ticket:
    with self._with_lock():
        ticket_id = self._next_id(category)
        now = utc_now()
        ticket = Ticket(
            id=ticket_id,
            # ... existing fields ...
            agent_id=agent_id or self._agent_id,
            created_by=agent_id or self._agent_id,
            version=1,
        )
        self._write_ticket(ticket, ticket_path(self.base_dir, ticket))
        return ticket
```

The `_write_ticket()` method uses `open("x")` which is fine here — we're inside the lock, so no two agents can try to create the same file. The existing `FileExistsError -> TicketAlreadyExistsError` path is a valid safety net.

#### 2.10.5 Update — Optimistic Concurrency

```python
def update(self, ticket_id: str, updates: TicketUpdate,
           agent_id: str | None = None) -> Ticket:
    update_data = updates.model_dump(exclude_unset=True)
    if "repo" in update_data:
        raise ValidationError("Cannot change repo field on update")

    expected_version = update_data.pop("expected_version", None)
    resolved_agent = agent_id or self._agent_id

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
        data["agent_id"] = resolved_agent

        updated_ticket = Ticket(**data)
        # ... existing tempfile+replace write logic ...
```

Key design choice: if `expected_version` is `None` (caller doesn't care about concurrency), the update proceeds without a version check. This preserves backward compatibility for single-agent CLI usage where the caller doesn't pass a version.

#### 2.10.6 Filter Updates

```python
# In _matches_filters, add:
if filters.assignee is not None and ticket.assignee != filters.assignee:
    return False
```

One line. That's it for filters.

### 2.11 Atomic Index Writes

Fix the real bug in `search.py:142-154`:

```python
def _persist_index(self) -> None:
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

### 2.12 Search Signature Updates

```python
def _ticket_signature(self, ticket: Ticket) -> str:
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

Only `version` is added. Not `agent_id` or `assignee` — those don't change the ticket's searchable content.

### 2.13 API Changes

Minimal — wire up agent_id and handle ConflictError:

```python
def create_app(tickets_dir: str | None = None) -> FastAPI:
    config = load_config()
    base_dir = Path(tickets_dir) if tickets_dir else config.effective_tickets_dir
    agent_id = config.shared.agent_id if config.shared.enabled else None
    store = TicketStore(base_dir, agent_id=agent_id)
    search = TicketSearch(store)
    # ... rest unchanged ...
```

Update `create_ticket` endpoint to pass agent_id (already passed via store constructor).

Update `update_ticket` to handle ConflictError:

```python
try:
    return TicketResponse.from_ticket(store.update(ticket_id, payload))
except ConflictError as exc:
    raise HTTPException(status_code=409, detail={
        "error_code": exc.error_code,
        "message": exc.message,
        "current_ticket": (
            TicketResponse.from_ticket(exc.current_ticket).model_dump()
            if exc.current_ticket else None
        ),
    })
```

Update `list_tickets` to support `assignee` filter:

```python
assignee: str | None = Query(None),
# ... in SearchFilters construction:
assignee=assignee,
```

### 2.14 CLI Changes

Update `_resolve_store()`:

```python
def _resolve_store(tickets_dir: Path | None) -> TicketStore:
    config = load_config()
    base_dir = tickets_dir or config.effective_tickets_dir
    agent_id = config.shared.agent_id if config.shared.enabled else None
    return TicketStore(base_dir, agent_id=agent_id)
```

Update `create` command to pass agent_id:

```python
# No change needed — agent_id is on the store now.
# store.create_ticket(...) uses self._agent_id automatically.
```

Update `update` command — add `--assignee` option:

```python
@app.command()
def update(
    # ... existing options ...
    assignee: str | None = typer.Option(None, "--assignee", help="Assign ticket to agent"),
) -> None:
    # ... in update_data construction:
    if assignee is not None:
        update_data["assignee"] = assignee
    # ... rest unchanged ...
```

No new CLI commands in v1. The existing `list`, `get`, `create`, `update`, `search`, `delete` all work with shared mode automatically.

---

## 3. Migration Path

### Phase 0: Ship the model changes (non-breaking)

Add 4 fields to Ticket, 2 fields to TicketUpdate, 4 fields to TicketResponse, 1 field to SearchFilters. All have defaults. Old tickets read fine. New tickets written with old code are fine (extra frontmatter fields ignored by `extra="ignore"` on VticBaseModel... wait, actually Ticket inherits from VticBaseModel which has `extra="ignore"`, so yes, old code reading new tickets will ignore the new fields).

Actually, let me re-check: old code's `Ticket(**data)` where `data` has `agent_id`, `created_by`, `version`, `assignee` — these will be silently ignored because VticBaseModel has `extra="ignore"`. Confirmed safe.

### Phase 1: Ship the config and storage changes

Add SharedConfig, update storage with optimistic concurrency, atomic index writes, persistent lock file. All behind `shared.enabled=false` default. No existing user sees any change.

### Phase 2: Opt-in shared mode

Agents add to their vtic.toml:

```toml
[shared]
enabled = true
store_dir = "/home/smoke01/.shared-vtic"
agent_id = "apex"
```

First use creates the directory and `.vtic.lock` file.

### Phase 3 (future): Journal, manifest, migrate, status

Add these as separate PRs after v1 is validated in production.

### Backward Compatibility

| Scenario | Works? |
|----------|--------|
| Existing single-agent, no config change | Yes |
| Old ticket files with new code | Yes (Pydantic defaults) |
| New ticket files with old code | Yes (extra="ignore") |
| Two agents, both shared=false | Yes (isolated) |
| Two agents, both shared=true, same dir | Yes (coordinated) |
| One agent shared, one not | Yes (they see different stores) |

---

## 4. Edge Cases

### 4.1 Concurrent Creates

Two agents call `create_ticket()` simultaneously. Both enter `_with_lock()`. Serialized by `fcntl.flock()`. First gets C5, second gets C6. No collision. The existing `_next_id()` scans all files including trashed ones, so IDs are always unique within a store. This is already correct — no change needed.

### 4.2 Concurrent Updates

Agent A reads v1, Agent B reads v1. A writes with `expected_version=1` (succeeds, now v2). B writes with `expected_version=1` (ConflictError with current_ticket=v2).

If B doesn't pass `expected_version` (e.g., CLI usage without the flag), the update succeeds without version check. This is intentional — backward compatible.

### 4.3 Stale Lock After Crash

`fcntl.flock()` is released when the fd closes, which happens on process exit (including SIGKILL). The persistent lock file is just an anchor — no stale lock issue.

### 4.4 Index Corruption

Fixed by atomic writes in Phase 1. Two agents writing index simultaneously: last `os.replace()` wins, but the result is always valid JSON.

### 4.5 Deleted Tickets

Trash is per-store, shared in shared mode. `_iter_ticket_paths(include_trash=False)` excludes trashed tickets. All agents see the same trash. No journal needed for v1 — if Agent A deletes a ticket, Agent B discovers it's gone on next list/search.

### 4.6 Search Consistency Race

Agent A creates a ticket. Agent B searches immediately. B's search calls `_load_cached_tickets()` which checks file mtimes. New file has new mtime, gets re-read and included. If B's search starts before A's `os.replace()` completes (sub-millisecond race), B gets stale results. Next search picks it up. Acceptable.

---

## 5. Implementation Checklist

### P0 — Core (do first)
- [ ] Add `agent_id`, `created_by`, `version`, `assignee` to `Ticket`
- [ ] Add `expected_version`, `assignee` to `TicketUpdate`
- [ ] Add new fields to `TicketResponse` and update `from_ticket()`
- [ ] Add `assignee` to `SearchFilters` and `_matches_filters()`
- [ ] Update `search_text` property to include `assignee`
- [ ] Add `SharedConfig` to config with `effective_tickets_dir`
- [ ] Add shared env vars to `_ENV_OVERRIDES`
- [ ] Add `ConflictError` to errors.py
- [ ] Update `TicketStore.__init__()` to accept `agent_id`
- [ ] Extract `_with_lock()` context manager
- [ ] Update `_serialize_ticket()` for new fields
- [ ] Update `create_ticket()` to set agent fields
- [ ] Update `update()` for optimistic concurrency

### P1 — Wire-up (do second)
- [ ] Fix `_persist_index()` for atomic writes
- [ ] Update `_ticket_signature()` to include `version`
- [ ] Update API `create_app()` to use `effective_tickets_dir` and pass `agent_id`
- [ ] Update API `update_ticket` to handle ConflictError
- [ ] Update API `list_tickets` for `assignee` filter
- [ ] Update CLI `_resolve_store()` for shared config
- [ ] Add `--assignee` option to CLI `update` command

### P2 — Polish (do later)
- [ ] Journal module
- [ ] Agent manifest
- [ ] `vtic status` command
- [ ] `vtic migrate` command
- [ ] `vtic journal` command
- [ ] `GET /journal` API endpoint

---

## 6. Testing

### Unit Tests
- Ticket with new fields serializes/deserializes correctly
- Old frontmatter (no new fields) reads with Pydantic defaults
- `expected_version` match → update succeeds, version increments
- `expected_version` mismatch → ConflictError with current_ticket
- `expected_version=None` → no version check (backward compat)
- `assignee` filter in SearchFilters works
- SharedConfig defaults (enabled=false)
- effective_tickets_dir returns store_dir when shared, tickets.dir when not

### Integration Tests
- Two TicketStore instances on same dir see all tickets
- Concurrent creates don't collide
- Concurrent update → one succeeds, one gets ConflictError
- Search across agent-created tickets works
- Single-agent workflow unchanged

### No Migration Tests Needed
Migration is a config change, not a data change. No ticket files need modification.

---

## 7. What v2 Adds (Not This Proposal)

- **Journal** (JSONL activity log) — for "what happened since I last checked"
- **Agent manifest** — for discovery of participating agents
- **`vtic status`** — cross-agent dashboard
- **`vtic migrate`** — dedup existing ticket silos
- **`vtic journal`** — view activity log
- **Assignee auto-clear** — when status transitions to fixed/closed/wont_fix, clear assignee
- **`created_by` and `agent_id` filters** — after journal proves useful

These are all additive. v1 establishes the foundation (shared directory, identity, concurrency) that makes them possible.

---

## 8. Size Estimate

| Component | Lines Changed |
|-----------|--------------|
| models.py | ~40 |
| config.py | ~25 |
| storage.py | ~50 |
| errors.py | ~15 |
| search.py | ~15 |
| api.py | ~30 |
| cli/main.py | ~15 |
| **Total** | **~190** |

~190 lines of new/modified code. Zero new dependencies. Zero new files. Zero new CLI commands. Full backward compatibility.

---

## 9. Conclusion

The GPT-5.4 proposal has the right architecture. This proposal adopts its core ideas (explicit conflict rejection, `assignee` field, persistent lock file, atomic index writes) while cutting everything that isn't needed to solve the immediate problem. The result is ~190 lines that makes vtic work correctly when multiple agents share a ticket directory.

The journal is a good idea for v2 — it should be added after the core is validated in production, not before. The agent manifest is premature. New CLI commands can wait until the basic shared workflow is proven.

Ship the smallest thing that works. Measure. Then add more.
