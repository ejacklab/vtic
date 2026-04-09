# Proposal: Shared Ticket Store v2 — Activity-Journal Architecture

**Author:** Apex (GPT-5.4 subagent)
**Date:** 2026-04-09
**Status:** Draft
**Supersedes:** shared-ticket-store.md (GLM-5 draft, v1.0)

---

## 0. Executive Summary

This proposal solves multi-agent ticket coordination for vtic through three
cooperative mechanisms: (1) a shared filesystem directory that all agents
read and write, (2) an append-only activity journal that gives every agent a
durable, ordered log of all mutations, and (3) optimistic concurrency with
explicit conflict rejection so AI agents can make informed merge decisions.

It builds on the GLM-5 draft but fixes several problems identified in that
document (detailed in Section 1.4).

**Estimated code changes:** ~350 lines across 6 files (models, config,
storage, errors, api, cli) plus ~120 lines for a new `journal.py` module.

---

## 1. Problem Analysis

### 1.1 Current Architecture (unchanged from GLM-5 draft)

vtic stores tickets as markdown files on disk:

```
{tickets_dir}/{owner}/{repo}/{category}/{id}-{slug}.md
```

Key facts after reading the full codebase (`storage.py`, `models.py`,
`config.py`, `search.py`, `api.py`, `cli/main.py`):

- `TicketStore.__init__(base_dir)` takes a single directory — all state lives under it
- `_iter_ticket_paths()` walks `base_dir` recursively via `rglob("*.md")`
- `create_ticket()` allocates IDs by scanning existing files under `fcntl.flock()`
- `update()` uses `fcntl.flock()` + `tempfile.NamedTemporaryFile` + `os.replace()` for atomic writes
- Lock file `.vtic.lock` is **deleted** in the `finally` block after each operation — `fcntl.flock()` is the real lock, the file is just an fd anchor
- Search index persisted at `{base_dir}/.vtic-search-index.json` via plain `write_text()` (NOT atomic)
- `_parse_frontmatter()` uses `yaml.safe_load()` with `extra="ignore"` on VticBaseModel
- No concept of "who created/modified" exists in the schema
- `owner` field means "repo owner" (validated as part of `owner/repo`), NOT ticket assignee

### 1.2 The Multi-Agent Gap

The same three problems identified by GLM-5, confirmed by code inspection:

1. **Invisible silos** — Each agent has its own `tickets.dir`. Apex's vtic config at `~/.hermes/profiles/apex/workspace/vtic/tmp/vtic/vtic.toml` uses `dir = "./tickets"`, resolving to Apex's workspace. Other agents have separate paths.
2. **Fragmented reporting** — Each agent only sees its own `base_dir` tree
3. **No coordination** — Duplicate IDs, conflicting updates, no claiming

### 1.3 Critique of the GLM-5 Draft

The GLM-5 proposal (`shared-ticket-store.md`) identifies the right problems
and proposes the right general direction (shared directory + version counter).
However, it has several architectural weaknesses that would cause problems in
production with AI agents:

**C1 — Auto-merge silently loses intent.** Section 2.2.5 proposes
`_can_auto_merge()` which silently merges non-text field updates when a version
conflict is detected. Consider: Agent A sets `status=in_progress`, Agent B sets
`status=fixed`. The auto-merge accepts whichever write arrives last, discarding
the other. AI agents make decisions based on their view of state — silently
accepting a stale write masks coordination failures. Agents need the conflict
reported so they can reason about it.

**C2 — No activity log means agents are blind to each other.** The proposal
relies entirely on agents re-reading files to discover changes. But agents
don't continuously poll — they read on-demand. There's no efficient way to answer
"what happened since I last checked?" Reading every `.md` file's mtime is O(n)
and fragile. This is listed as "P3 Future" but is actually the core coordination
primitive.

**C3 — Claim mechanism repurposes `owner` field incorrectly.** The proposal
suggests using `owner` for claiming (Section 2.2.4). But `owner` is validated as
part of the `owner/repo` pattern and currently means "GitHub repo owner." The
`parse_repo()` function splits on `/`. Setting `owner="apex"` would break
`repo` validation and `ticket_path()` resolution which calls `parse_repo(ticket.repo)`.

**C4 — Search index write is not atomic.** The proposal notes the index is
shared but doesn't address that `_persist_index()` uses plain `write_text()`.
Two agents rebuilding the index simultaneously will corrupt it. The ticket files
use `tempfile + os.replace()` for atomicity — the index should too.

**C5 — Lock file deletion pattern is fragile.** The current code does
`lock_path.unlink(missing_ok=True)` in the `finally` block. This works because
`fcntl.flock()` is the actual lock mechanism, not the file's existence. But
it creates a TOCTOU race between unlink and the next open+lock. The proposal
doesn't fix this.

**C6 — Agent manifest is missing.** There's no way to discover which agents
are participating in a shared store, or their identities. The proposal assumes
all agents independently configure the same path and agent_id, with no
validation or discovery.

---

## 2. Proposed Solution

### 2.1 Design Principles

1. **Shared filesystem, not a server** — Keep vtic's markdown-on-disk philosophy
2. **Journal-first coordination** — An append-only activity log is the source of truth for "what happened"; files are the source of truth for "what's the current state"
3. **Explicit conflict rejection** — Version conflicts are always surfaced; never silently merged. AI agents are smart enough to merge deliberately.
4. **Proper assignee field** — A new `assignee` field for ticket claiming, completely separate from `owner` (repo owner)
5. **Backward compatible** — Single-agent setups work unchanged, all new fields optional
6. **Atomic index writes** — Search index uses same tempfile+replace pattern as ticket files

### 2.2 New Concepts

#### 2.2.1 Agent Identity (`agent_id` and `created_by`)

Same as GLM-5 draft — two new fields on Ticket:

```python
agent_id: str | None = Field(default=None, max_length=100,
    description="Identity of the agent that last modified this ticket")
created_by: str | None = Field(default=None, max_length=100,
    description="Identity of the agent that originally created this ticket")
```

Populated from config `shared.agent_id` or `VTIC_AGENT_ID` env var.

#### 2.2.2 Version Counter (`version`)

Same as GLM-5 draft:

```python
version: int = Field(default=1, ge=1,
    description="Monotonically increasing version for conflict detection")
```

#### 2.2.3 Ticket Assignee (`assignee`) — NEW

A proper field for claiming/assignment, distinct from `owner` (repo owner):

```python
assignee: str | None = Field(default=None, max_length=100,
    description="Agent currently assigned to work on this ticket")
```

- Set when an agent begins work (`update(ticket_id, TicketUpdate(assignee="apex"))`)
- Cleared when work completes or agent releases the ticket
- Filterable via `SearchFilters.assignee`
- Displayed in `vtic list` and API responses
- Does NOT interact with `owner` or `repo` validation in any way

#### 2.2.4 Activity Journal — NEW (core innovation)

An append-only JSONL (JSON Lines) file in the shared directory that records
every mutation:

**Location:** `{shared_dir}/.vtic-journal.jsonl`

**Format:** One JSON object per line:

```jsonl
{"ts":"2026-04-09T16:00:00Z","agent":"apex","action":"create","ticket_id":"C5","repo":"ctxgraph4agent/ctxgraph4agent","version":1}
{"ts":"2026-04-09T16:05:00Z","agent":"orion","action":"update","ticket_id":"C5","changes":{"status":"in_progress","assignee":"orion"},"version":2}
{"ts":"2026-04-09T16:10:00Z","agent":"apex","action":"update","ticket_id":"C5","changes":{"status":"fixed","fix":"Updated the handler"},"version":3}
{"ts":"2026-04-09T16:15:00Z","agent":"lux","action":"delete","ticket_id":"C3","version":3}
```

**Properties:**
- **Append-only** — written with `open("a")`, never modified or deleted in place
- **Crash-safe** — Each line is flushed to disk via `file.flush(); os.fsync(file.fileno())`
- **Globally ordered** — All agents append to the same file under `fcntl.flock()`
- **Queryable** — Agents can `tail -n 50` or parse from a known byte offset to see recent activity
- **Rotatable** — A `vtic journal rotate` command compacts old entries (keeps last state per ticket, discards intermediate updates for deleted/closed tickets older than N days)
- **Discoverable** — Any agent can read the journal to see full activity history

**Why JSONL, not a database:**
- No new dependencies (just `json` and `os`)
- Human-readable (agents can read it directly with `cat`)
- Works with standard Unix tools (`grep`, `tail`, `jq`)
- Append-only is naturally crash-safe
- Single file = single lock = simple coordination

**New module:** `src/vtic/journal.py` (~120 lines)

```python
@dataclass
class JournalEntry:
    ts: str                    # ISO 8601 UTC
    agent: str                 # agent_id
    action: Literal["create", "update", "delete", "restore"]
    ticket_id: str
    repo: str | None = None
    changes: dict[str, Any] | None = None  # for update actions
    version: int | None = None
    previous_version: int | None = None    # for conflict detection context

class ActivityJournal:
    def __init__(self, journal_path: Path) -> None: ...
    def append(self, entry: JournalEntry) -> None: ...
    def read_since(self, offset: int) -> list[JournalEntry]: ...
    def read_recent(self, n: int = 50) -> list[JournalEntry]: ...
    def read_for_ticket(self, ticket_id: str) -> list[JournalEntry]: ...
    def rotate(self, keep_days: int = 30) -> int: ...
```

#### 2.2.5 Agent Manifest — NEW

A small JSON file in the shared directory that tracks participating agents:

**Location:** `{shared_dir}/.vtic-agents.json`

```json
{
  "agents": {
    "apex": {"last_seen": "2026-04-09T16:30:00Z", "version": "0.9.0"},
    "orion": {"last_seen": "2026-04-09T16:28:00Z", "version": "0.9.0"},
    "lux": {"last_seen": "2026-04-09T16:25:00Z", "version": "0.9.0"}
  }
}
```

Updated by each agent on every write operation (create/update/delete). Enables:
- Discovery of participating agents
- Stale agent detection (last_seen > 24h ago = possibly offline)
- Version compatibility checks

#### 2.2.6 Conflict Resolution — EXPLICIT REJECTION (improved from GLM-5)

**Policy:** When `expected_version` doesn't match the current version, always raise
`ConflictError`. Never auto-merge.

```python
def update(self, ticket_id: str, updates: TicketUpdate,
           agent_id: str | None = None) -> Ticket:
    # ... inside lock ...
    current, current_path = self._find_ticket_path(ticket_id)
    expected_version = update_data.pop("expected_version", None)

    if expected_version is not None and current.version != expected_version:
        raise ConflictError(
            ticket_id=ticket_id,
            expected=expected_version,
            actual=current.version,
            current_ticket=current,  # Return the full current state
        )
    # ... proceed with update ...
```

**Rationale:** AI agents can read the returned `current_ticket` from the
`ConflictError`, compare it with their intended changes, and decide whether
to retry, merge manually, or defer. This is better than opaque auto-merge
because:
- The agent knows *why* the conflict happened (what changed between versions)
- The agent can make a semantic decision (e.g., "I see Orion already fixed this, I'll close my PR")
- The journal provides the full history of what happened (who changed what, when)

#### 2.2.7 Atomic Index Writes — FIX

The search index write in `_persist_index()` must use the same atomic
write pattern as ticket files:

```python
def _persist_index(self) -> None:
    # ... build payload ...
    self._index_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8",
        dir=self._index_path.parent, delete=False,
    ) as tmp:
        tmp.write(json.dumps(payload))
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, self._index_path)
```

#### 2.2.8 Persistent Lock File — IMPROVEMENT

Stop deleting `.vtic.lock` after every operation. Instead:

```python
def __init__(self, base_dir: Path) -> None:
    self.base_dir = Path(base_dir)
    self._lock_path = self.base_dir / ".vtic.lock"
    self._last_list_errors: list[ErrorDetail] = []

def _with_lock(self, fn: Callable[..., T]) -> T:
    """Execute fn while holding the exclusive lock."""
    self._lock_path.parent.mkdir(parents=True, exist_ok=True)
    with self._lock_path.open("a+", encoding="utf-8") as lock_file:
        self._lock_exclusive(lock_file)
        try:
            return fn()
        finally:
            pass  # fcntl.flock released on fd close; keep the file
```

This eliminates the TOCTOU race in the current pattern (create lock file,
lock it, delete it, next caller creates it again). The file becomes a
permanent anchor for `fcntl.flock()`.

### 2.3 Shared Store Configuration

#### 2.3.1 New Config Section

```toml
# vtic.toml
[shared]
enabled = true
store_dir = "/home/smoke01/.shared-vtic"   # shared directory root
agent_id = "apex"                          # this agent's identity
```

#### 2.3.2 Environment Variables

```
VTIC_SHARED_ENABLED=true
VTIC_SHARED_STORE_DIR=/home/smoke01/.shared-vtic
VTIC_AGENT_ID=apex
```

#### 2.3.3 Shared Directory Structure

```
~/.shared-vtic/
  ctxgraph4agent/              # repo owner
    ctxgraph4agent/            # repo name
      code_quality/
        C1-some-ticket.md
        C5-async-reqwest.md
      testing/
        T1-mcp-init.md
  vtic/
    661818yijack/
      vtic/
        code_quality/
          C1-shared-store.md
  .vtic-journal.jsonl          # append-only activity log
  .vtic-agents.json            # agent manifest
  .vtic.lock                   # persistent lock file (never deleted)
  .vtic-search-index.json      # shared BM25 index (atomic writes)
```

### 2.4 How the Pieces Fit Together

```
Agent Apex                  Agent Orion                  Shared Store
    |                            |                            |
    |--- create_ticket() ------> |                            |
    |   [lock acquired]          |                            |
    |   writes C5-*.md          |                            |
    |   appends journal entry   |                            |
    |   updates agent manifest  |                            |
    |   [lock released]         |                            |
    |                            |                            |
    |                    journal read: "apex created C5"     |
    |                    reads C5 (v1)                        |
    |                            |                            |
    |--- update_ticket() ------> |                            |
    |   expected_version=1       |                            |
    |   [lock acquired]          |                            |
    |   CONFLICT (current=v2)   |                            |
    |   ConflictError returned  |                            |
    |   with current_ticket=v2  |                            |
    |   [lock released]         |                            |
    |                            |                            |
    |  Agent reads v2, decides   |                            |
    |  to add a comment to fix   |                            |
    |  retries with version=2   |                            |
```

---

## 3. Specific Code Changes

### 3.1 File: `src/vtic/models.py`

**Add fields to `Ticket` class (after line 132, before validators):**

```python
# Multi-agent fields (all optional for backward compatibility)
agent_id: str | None = Field(default=None, max_length=100,
    description="Identity of the agent that last modified this ticket")
created_by: str | None = Field(default=None, max_length=100,
    description="Identity of the agent that originally created this ticket")
version: int = Field(default=1, ge=1,
    description="Optimistic concurrency version counter")
assignee: str | None = Field(default=None, max_length=100,
    description="Agent currently assigned to work on this ticket")
```

**Add field to `TicketUpdate` class:**

```python
expected_version: int | None = Field(default=None, ge=1,
    description="Expected current version for optimistic concurrency check")
assignee: str | None = Field(default=None, max_length=100,
    description="Agent to assign this ticket to (null to unassign)")
```

**Add fields to `TicketResponse`:**

```python
agent_id: str | None = None
created_by: str | None = None
version: int = 1
assignee: str | None = None
```

**Update `TicketResponse.from_ticket()`:**

```python
@classmethod
def from_ticket(cls, ticket: Ticket) -> "TicketResponse":
    return cls(
        # ... existing fields ...
        agent_id=getattr(ticket, "agent_id", None),
        created_by=getattr(ticket, "created_by", None),
        version=getattr(ticket, "version", 1),
        assignee=getattr(ticket, "assignee", None),
    )
```

**Add filters to `SearchFilters`:**

```python
created_by: str | None = Field(default=None,
    description="Filter by the agent that created the ticket")
assignee: str | None = Field(default=None,
    description="Filter by the assigned agent")
agent_id: str | None = Field(default=None,
    description="Filter by the agent that last modified the ticket")
```

**Add to `search_text` property of `Ticket`:**

```python
@property
def search_text(self) -> str:
    parts = [
        self.id, self.title, self.description or "", self.file or "",
        self.fix or "", " ".join(self.tags),
        self.agent_id or "", self.created_by or "", self.assignee or "",
    ]
    return " ".join(parts)
```

### 3.2 File: `src/vtic/config.py`

**Add new config model:**

```python
class SharedConfig(BaseModel):
    """Multi-agent shared store configuration."""
    model_config = {"validate_default": True}

    enabled: bool = Field(default=False,
        description="Enable shared ticket store mode")
    store_dir: Path | None = Field(default=None,
        description="Shared store root directory")
    agent_id: str | None = Field(default=None, max_length=100,
        description="Agent identity for shared mode")

    @field_validator("store_dir")
    @classmethod
    def validate_store_dir(cls, v: Path | None) -> Path | None:
        if v is not None:
            return v.expanduser().resolve()
        return None

    @model_validator(mode="after")
    def validate_shared_config(self) -> Self:
        if self.enabled and not self.agent_id:
            raise ValueError("shared.agent_id is required when shared.enabled=true")
        if self.enabled and not self.store_dir:
            raise ValueError("shared.store_dir is required when shared.enabled=true")
        return self
```

**Add to `VticConfig`:**

```python
shared: SharedConfig = Field(default_factory=SharedConfig)
```

**Add environment overrides to `_ENV_OVERRIDES`:**

```python
"VTIC_SHARED_ENABLED": ("shared", "enabled"),
"VTIC_SHARED_STORE_DIR": ("shared", "store_dir"),
"VTIC_AGENT_ID": ("shared", "agent_id"),
```

**Add to `VticConfig.from_env()`:**

```python
if shared_enabled := os.getenv("VTIC_SHARED_ENABLED"):
    config.shared.enabled = shared_enabled.lower() in ("true", "1", "yes")
if shared_dir := os.getenv("VTIC_SHARED_STORE_DIR"):
    config.shared.store_dir = Path(shared_dir)
if agent_id := os.getenv("VTIC_AGENT_ID"):
    config.shared.agent_id = agent_id
```

**Update `load_config()` — add property method to `VticConfig`:**

```python
@property
def effective_tickets_dir(self) -> Path:
    """Return the effective tickets directory, accounting for shared mode."""
    if self.shared.enabled and self.shared.store_dir:
        return self.shared.store_dir
    return self.tickets.dir
```

### 3.3 File: `src/vtic/storage.py`

**Modify `__init__` to accept optional agent_id and journal:**

```python
def __init__(
    self,
    base_dir: Path,
    *,
    agent_id: str | None = None,
    journal: ActivityJournal | None = None,
) -> None:
    self.base_dir = Path(base_dir)
    self._agent_id = agent_id
    self._journal = journal
    self._lock_path = self.base_dir / ".vtic.lock"
    self._last_list_errors: list[ErrorDetail] = []
```

**Replace lock pattern with `_with_lock` context manager:**

```python
from contextlib import contextmanager

@contextmanager
def _with_lock(self):
    """Acquire exclusive lock, execute block, release lock (keep file)."""
    self.base_dir.mkdir(parents=True, exist_ok=True)
    with self._lock_path.open("a+", encoding="utf-8") as lock_file:
        self._lock_exclusive(lock_file)
        try:
            yield
        finally:
            pass  # lock released on fd close; file persists
```

**Update `_serialize_ticket()` to include new frontmatter fields:**

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
        # New multi-agent fields
        "version": getattr(ticket, "version", 1),
    }
    if getattr(ticket, "agent_id", None):
        frontmatter["agent_id"] = ticket.agent_id
    if getattr(ticket, "created_by", None):
        frontmatter["created_by"] = ticket.created_by
    if getattr(ticket, "assignee", None):
        frontmatter["assignee"] = ticket.assignee
    # ... rest unchanged ...
```

**Update `_parse_frontmatter()` — no changes needed** because:
- `extra="ignore"` on VticBaseModel silently accepts unknown fields
- Missing new fields will get Pydantic defaults (None/1)
- Actually, `_parse_frontmatter` returns a raw dict that's passed to `Ticket(**data)`, so Pydantic handles the defaults

**Update `create_ticket()` to set agent_id and append journal:**

```python
def create_ticket(self, *, ..., agent_id: str | None = None) -> Ticket:
    with self._with_lock():
        ticket_id = self._next_id(category)
        now = utc_now()
        ticket = Ticket(
            id=ticket_id,
            # ... existing fields ...
            agent_id=agent_id,
            created_by=agent_id,
            version=1,
        )
        self._write_ticket(ticket, ticket_path(self.base_dir, ticket))
        if self._journal:
            self._journal.append(JournalEntry(
                ts=now.isoformat(),
                agent=agent_id or "unknown",
                action="create",
                ticket_id=ticket_id,
                repo=ticket.repo,
                version=1,
            ))
        return ticket
```

**Update `update()` to implement optimistic concurrency (explicit rejection):**

```python
def update(self, ticket_id: str, updates: TicketUpdate,
           agent_id: str | None = None) -> Ticket:
    update_data = updates.model_dump(exclude_unset=True)
    if "repo" in update_data:
        raise ValidationError("Cannot change repo field on update")

    expected_version = update_data.pop("expected_version", None)

    with self._with_lock():
        current, current_path = self._find_ticket_path(ticket_id)

        # Optimistic concurrency check
        if expected_version is not None:
            current_version = getattr(current, "version", 1)
            if expected_version != current_version:
                raise ConflictError(
                    ticket_id=ticket_id,
                    expected=expected_version,
                    actual=current_version,
                    current_ticket=current,
                )

        data = current.model_dump()
        data.update(update_data)
        if "title" in update_data:
            data["slug"] = slugify(str(update_data["title"]))
        data["updated_at"] = utc_now()
        data["version"] = getattr(current, "version", 1) + 1
        data["agent_id"] = agent_id or self._agent_id

        updated_ticket = Ticket(**data)
        new_path = ticket_path(self.base_dir, updated_ticket)
        try:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8",
                dir=new_path.parent, delete=False,
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
                except OSError:
                    pass
            raise TicketWriteError(updated_ticket.id, str(exc)) from exc

        # Journal the update
        if self._journal:
            changes = {k: v for k, v in update_data.items()
                       if k not in ("expected_version",)}
            self._journal.append(JournalEntry(
                ts=updated_ticket.updated_at.isoformat(),
                agent=agent_id or self._agent_id or "unknown",
                action="update",
                ticket_id=ticket_id,
                repo=updated_ticket.repo,
                changes=changes or None,
                version=data["version"],
                previous_version=getattr(current, "version", 1),
            ))

    return updated_ticket
```

**Update `delete()` and `move_to_trash()` to journal:**

Similar pattern — append a `JournalEntry(action="delete", ...)` inside the
lock, after the successful delete.

**Update `restore_from_trash()` to journal:**

Append `JournalEntry(action="restore", ...)` after successful restore.

**Update `_matches_filters()` to handle new filter fields:**

```python
if filters.agent_id and getattr(ticket, "agent_id", None) != filters.agent_id:
    return False
if filters.created_by and getattr(ticket, "created_by", None) != filters.created_by:
    return False
if filters.assignee and getattr(ticket, "assignee", None) != filters.assignee:
    return False
```

### 3.4 File: `src/vtic/journal.py` (NEW)

```python
"""Append-only activity journal for multi-agent coordination."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

Action = Literal["create", "update", "delete", "restore"]


@dataclass
class JournalEntry:
    ts: str
    agent: str
    action: Action
    ticket_id: str
    repo: str | None = None
    changes: dict[str, Any] | None = None
    version: int | None = None
    previous_version: int | None = None


class ActivityJournal:
    """Append-only JSONL journal for tracking agent activity on shared stores."""

    def __init__(self, journal_path: Path) -> None:
        self._path = journal_path

    def append(self, entry: JournalEntry) -> None:
        """Append a journal entry atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({
            "ts": entry.ts,
            "agent": entry.agent,
            "action": entry.action,
            "ticket_id": entry.ticket_id,
            "repo": entry.repo,
            "changes": entry.changes,
            "version": entry.version,
            "previous_version": entry.previous_version,
        }, sort_keys=True, default=str)
        # Append under flock to prevent interleaved writes
        lock_path = self._path.parent / ".vtic.lock"
        with lock_path.open("a", encoding="utf-8") as lock_file:
            try:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            except (ImportError, AttributeError):
                pass
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())

    def read_recent(self, n: int = 50) -> list[JournalEntry]:
        """Read the last n entries from the journal."""
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in lines[-n:]:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(JournalEntry(
                    ts=data["ts"],
                    agent=data["agent"],
                    action=data["action"],
                    ticket_id=data["ticket_id"],
                    repo=data.get("repo"),
                    changes=data.get("changes"),
                    version=data.get("version"),
                    previous_version=data.get("previous_version"),
                ))
            except (json.JSONDecodeError, KeyError):
                continue
        return entries

    def read_for_ticket(self, ticket_id: str) -> list[JournalEntry]:
        """Read all entries for a specific ticket."""
        return [
            e for e in self.read_recent(n=10000)  # read all
            if e.ticket_id.upper() == ticket_id.upper()
        ]

    def rotate(self, keep_days: int = 30) -> int:
        """Remove entries older than keep_days for closed/deleted tickets."""
        if not self._path.exists():
            return 0
        cutoff = datetime.now(timezone.utc).timestamp() - (keep_days * 86400)
        lines = self._path.read_text(encoding="utf-8").strip().split("\n")
        kept = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ts = datetime.fromisoformat(data["ts"].replace("Z", "+00:00"))
                if ts.timestamp() >= cutoff:
                    kept.append(line)
                elif data.get("action") not in ("delete", "restore"):
                    # Keep non-terminal entries within window
                    kept.append(line)
            except (json.JSONDecodeError, KeyError, ValueError):
                kept.append(line)  # keep unparseable lines
        removed = len(lines) - len(kept)
        with self._path.open("w", encoding="utf-8") as f:
            f.write("\n".join(kept) + "\n" if kept else "")
        return removed
```

### 3.5 File: `src/vtic/errors.py`

**Add `ConflictError` with richer context:**

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

### 3.6 File: `src/vtic/api.py`

**Update `create_app()` to use shared config and create journal:**

```python
def create_app(tickets_dir: str | None = None) -> FastAPI:
    config = load_config()
    base_dir = Path(tickets_dir) if tickets_dir else config.effective_tickets_dir
    agent_id = config.shared.agent_id if config.shared.enabled else None

    journal = None
    if config.shared.enabled and config.shared.store_dir:
        from vtic.journal import ActivityJournal
        journal = ActivityJournal(config.shared.store_dir / ".vtic-journal.jsonl")

    store = TicketStore(base_dir, agent_id=agent_id, journal=journal)
    search = TicketSearch(store)
    # ... rest unchanged ...
```

**Update `create_ticket` endpoint:**

```python
ticket = store.create_ticket(
    # ... existing args ...
    agent_id=agent_id,
)
```

**Update `update_ticket` endpoint:**

```python
async def update_ticket(ticket_id: str, payload: TicketUpdate) -> TicketResponse:
    ticket_id = _validate_ticket_id(ticket_id)
    try:
        return TicketResponse.from_ticket(
            store.update(ticket_id, payload, agent_id=agent_id)
        )
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

**Update `list_tickets` endpoint** with new filters:

```python
agent_id: str | None = Query(None, alias="agent-id"),
created_by: str | None = Query(None, alias="created-by"),
assignee: str | None = Query(None),
# ...
filters = SearchFilters(
    # ... existing ...
    agent_id=agent_id,
    created_by=created_by,
    assignee=assignee,
)
```

**Add `GET /journal` endpoint:**

```python
@app.get("/journal", response_model=list[dict])
async def get_journal(n: int = Query(50, ge=1, le=500)):
    """Read recent activity from the shared journal."""
    if journal is None:
        return []
    entries = journal.read_recent(n)
    return [
        {
            "ts": e.ts,
            "agent": e.agent,
            "action": e.action,
            "ticket_id": e.ticket_id,
            "repo": e.repo,
            "changes": e.changes,
            "version": e.version,
        }
        for e in entries
    ]
```

### 3.7 File: `src/vtic/cli/main.py`

**Update `_resolve_store()` to return agent_id and journal:**

```python
def _resolve_store(tickets_dir: Path | None) -> tuple[TicketStore, str | None]:
    config = load_config()
    base_dir = tickets_dir or config.effective_tickets_dir
    agent_id = config.shared.agent_id if config.shared.enabled else None

    journal = None
    if config.shared.enabled and config.shared.store_dir:
        from vtic.journal import ActivityJournal
        journal = ActivityJournal(config.shared.store_dir / ".vtic-journal.jsonl")

    store = TicketStore(base_dir, agent_id=agent_id, journal=journal)
    return store, agent_id
```

**Update `create` command** to pass agent_id:

```python
store, agent_id = _resolve_store(dir)
ticket = store.create_ticket(
    # ... existing args ...
    agent_id=agent_id,
)
```

**Update `update` command** to pass agent_id:

```python
store, agent_id = _resolve_store(dir)
ticket = store.update(id, updates, agent_id=agent_id)
```

**Add `vtic journal` command:**

```python
@app.command()
def journal(
    n: int = typer.Option(20, "--n", help="Number of recent entries"),
    ticket_id: str | None = typer.Option(None, "--ticket", help="Filter by ticket ID"),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Show recent activity from the shared journal."""
    config = load_config()
    if not config.shared.enabled:
        console.print("[yellow]Shared mode not enabled.[/yellow]")
        raise typer.Exit(code=1)

    from vtic.journal import ActivityJournal
    jpath = config.shared.store_dir / ".vtic-journal.jsonl"
    journal = ActivityJournal(jpath)

    if ticket_id:
        entries = journal.read_for_ticket(ticket_id)
    else:
        entries = journal.read_recent(n)

    if not entries:
        console.print("[yellow]No journal entries found.[/yellow]")
        return

    table = Table(title="Activity Journal")
    for col in ("Time", "Agent", "Action", "Ticket", "Details"):
        table.add_column(col)
    for entry in entries:
        details = ""
        if entry.changes:
            details = ", ".join(f"{k}={v}" for k, v in entry.changes.items())
        table.add_row(
            entry.ts[:19],  # truncate to date+time
            entry.agent,
            entry.action,
            entry.ticket_id,
            details or "-",
        )
    console.print(table)
```

**Add `vtic status` command:**

```python
@app.command()
def status(
    repo: str = typer.Option(..., "--repo", help="Repository filter"),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Show project status across all agents."""
    store, _ = _resolve_store(dir)
    filters = SearchFilters(repo=[repo])
    tickets = store.list(filters)

    if not tickets:
        console.print(f"[yellow]No tickets found for {repo}.[/yellow]")
        return

    # Group by status
    by_status: dict[str, list[Ticket]] = {}
    for t in tickets:
        by_status.setdefault(t.status.value, []).append(t)

    table = Table(title=f"Project Status: {repo}")
    table.add_column("Status")
    table.add_column("Count")
    table.add_column("Assigned")
    for status_val in ("open", "in_progress", "blocked", "fixed", "wont_fix", "closed"):
        group = by_status.get(status_val, [])
        if not group:
            continue
        assigned = [t for t in group if getattr(t, "assignee", None)]
        table.add_row(
            status_val,
            str(len(group)),
            ", ".join(getattr(t, "assignee", "?") for t in assigned) or "-",
        )
    console.print(table)

    # Show agent participation
    agents = set()
    for t in tickets:
        for field in ("created_by", "agent_id", "assignee"):
            val = getattr(t, field, None)
            if val:
                agents.add(val)
    if agents:
        console.print(f"\n[bold]Participating agents:[/bold] {', '.join(sorted(agents))}")
```

**Update `list_tickets` table** to include Agent column when in shared mode:

```python
store, agent_id = _resolve_store(dir)
# ... if shared mode, add "Agent" column to table ...
```

### 3.8 File: `src/vtic/search.py`

**Fix `_persist_index()` for atomic writes:**

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

**Update `_ticket_signature()` to include new fields:**

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
        "version": getattr(ticket, "version", 1),
        "agent_id": getattr(ticket, "agent_id", None),
        "assignee": getattr(ticket, "assignee", None),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
```

---

## 4. Migration Path

### 4.1 Phase 0: Schema Extension (Non-Breaking)

Add the four new fields to the `Ticket` model. All have defaults:
- `agent_id`: `None`
- `created_by`: `None`
- `version`: `1`
- `assignee`: `None`

Old ticket files without these frontmatter fields are read with Pydantic
defaults. The `extra="ignore"` config on `VticBaseModel` means extra fields in
new ticket files are silently accepted by old code.

### 4.2 Phase 2: Config Addition (Non-Breaking)

Add `SharedConfig` with `enabled=false` default. Existing configs are unaffected.
No `vtic.toml` changes needed for single-agent users.

### 4.3 Phase 3: Journal Module (Non-Breaking)

`ActivityJournal` is a standalone module. It's only instantiated when
`shared.enabled=true`. Single-agent setups never create or read the journal.

### 4.4 Phase 4: Opt-In Shared Mode

Agents add to their `vtic.toml`:

```toml
[shared]
enabled = true
store_dir = "/home/smoke01/.shared-vtic"
agent_id = "apex"
```

The shared directory and `.vtic-journal.jsonl` are created on first use.

### 4.5 Phase 5: Ticket Migration Utility

A standalone `vtic migrate` command for consolidating duplicate tickets:

```bash
# Run from Apex's workspace
vtic migrate --from ./tickets --to /home/smoke01/.shared-vtic --agent apex

# Then from Orion's workspace
vtic migrate --from ./tickets --to /home/smoke01/.shared-vtic --agent orion
```

Deduplication logic:
1. Group tickets by (repo, category, id)
2. If duplicate IDs exist, keep the one with the most recent `updated_at`
3. Set `created_by` to the agent whose ticket was kept
4. Log all merges to the journal

### 4.6 Backward Compatibility Summary

| Scenario | Works? | Notes |
|----------|--------|-------|
| Existing single-agent, no config changes | Yes | New fields default to None/1 |
| Old ticket files, new code | Yes | Missing frontmatter → Pydantic defaults |
| New ticket files, old code | Yes | `extra="ignore"` on VticBaseModel |
| Multiple agents, shared=false | Yes | Same as current, isolated stores |
| Multiple agents, shared=true | Yes | Coordinated via journal + versioning |
| Mixed: some agents shared, some not | Yes | Non-shared agents see their local store only |

---

## 5. Edge Cases and Handling

### 5.1 Two Agents Create the Same Ticket Simultaneously

`fcntl.flock()` on the shared `.vtic.lock` serializes `create_ticket()` calls.
One agent gets C5, the other gets C6. Both succeed — but content may be
duplicates. The journal records both creations, making duplicates easy to
detect. A future dedup command can merge them.

### 5.2 Two Agents Update the Same Ticket Simultaneously

1. Agent A reads ticket (v1), Agent B reads ticket (v1)
2. Agent A writes with expected_version=1 -> succeeds, ticket becomes v2
3. Agent B writes with expected_version=1 -> ConflictError(actual=2, current_ticket=...)
4. Agent B receives the full current ticket state and can:
   - Re-read, decide to retry (increment version to 2, re-apply changes)
   - Decide the other agent's changes obviate their own work (e.g., ticket already fixed)
   - Create a follow-up ticket if their work is orthogonal

**No silent data loss.** The agent always has enough information to decide.

### 5.3 Agent Crashes Mid-Write

Existing `tempfile.NamedTemporaryFile` + `os.replace()` pattern is crash-safe.
Partial writes leave a temp file that doesn't match the `{id}-{slug}.md` glob
pattern and is ignored by `_iter_ticket_paths()`.

Journal entries are fsync'd after each append. If the agent crashes after
writing the journal but before writing the ticket file, the journal will have
a spurious "create" or "update" entry. This is harmless — the ticket simply
won't exist on disk. Agents should treat journal entries as hints, not
authoritative state. The actual `.md` files are authoritative.

### 5.4 Lock File Handling

With the persistent lock file approach:
- The file `.vtic.lock` is created once and never deleted
- `fcntl.flock()` provides the actual mutual exclusion
- If a process is SIGKILL'd, the OS releases the flock when the fd closes
- The next process opens the same file and acquires the lock
- No TOCTOU race between file creation/deletion and lock acquisition

**Stale lock detection (optional hardening):**
If `fcntl.flock()` blocks for more than 10 seconds, log a warning. After 30
seconds, break the lock (the holder is likely dead). This is defensive — in
practice, `fcntl.flock()` is released immediately on process exit.

### 5.5 Agent Identity Spoofing

Self-reported `agent_id` is trusted (all agents on this machine are the user's).
No authentication needed for local-first tooling. If untrusted agents are added
later, filesystem permissions on the shared directory can restrict access.

### 5.6 Search Index Consistency with Multiple Agents

Fixed by atomic index writes (Section 2.2.7). If two agents rebuild
simultaneously, the last `os.replace()` wins — but the result is always a valid
index file, never corrupted. The next search by either agent will re-validate
signatures and rebuild if needed.

### 5.7 Journal Growth and Rotation

The journal grows linearly with activity. For a busy project with 5 agents,
expect ~50-200 entries/day. At 200 bytes/entry, that's ~40KB/day or ~15MB/year.

The `vtic journal rotate` command compacts old entries:
- Entries older than `keep_days` (default 30) for closed/deleted tickets are removed
- Entries for open/active tickets are always kept
- Can be run as a cron job: `0 3 * * * vtic journal rotate`

### 5.8 Deleted Tickets and Agent Visibility

Trash is per-store, and with a shared store, the trash directory is shared.
Agent A trashing a ticket is visible to Agent B (via journal entry). Agent B
can restore it if needed. `_iter_ticket_paths(include_trash=False)` excludes
trashed tickets from normal listing.

### 5.9 Assignee vs Owner Confusion

The new `assignee` field is completely independent of `owner`:
- `owner` = repo owner (used in path construction via `parse_repo()`)
- `assignee` = agent working on this ticket (used for coordination)

They can coexist without conflict. A ticket can have `owner="661818yijack"` and
`assignee="apex"` simultaneously.

### 5.10 Network Filesystem (NFS)

`fcntl.flock()` behavior on NFS is implementation-dependent. On Linux NFSv4,
it works correctly. On older NFS or SMB mounts, locking may not work. This is
acceptable because vtic's shared store is designed for local multi-agent use
(all agents on the same machine). Remote coordination should use a different
mechanism.

---

## 6. Implementation Priority

### P0 (Core — Do First)
1. Add `agent_id`, `created_by`, `version`, `assignee` fields to `Ticket` model
2. Add `expected_version` and `assignee` to `TicketUpdate`
3. Update `_serialize_ticket()` and frontmatter parsing for new fields
4. Add `SharedConfig` to config with `effective_tickets_dir` property
5. Add `ConflictError` to errors.py (with `current_ticket` payload)
6. Update `update()` for optimistic concurrency (explicit rejection)

### P1 (Coordination — Do Second)
7. Create `src/vtic/journal.py` module
8. Update `create_ticket()`, `update()`, `delete()`, `restore_from_trash()` to journal
9. Update `_with_lock()` pattern (persistent lock file)
10. Update API endpoints for shared mode, agent_id, and ConflictError handling
11. Update CLI commands to pass agent_id

### P2 (Discovery & Visibility — Do Third)
12. Add `vtic journal` CLI command
13. Add `vtic status` CLI command
14. Add `GET /journal` API endpoint
15. Add `agent_id`, `created_by`, `assignee` filters to SearchFilters and API
16. Update search `_ticket_signature()` for new fields

### P3 (Hardening & Polish)
17. Fix `_persist_index()` for atomic writes
18. Add `vtic migrate` command for deduplication
19. Add stale lock detection with timeout
20. Update health endpoint to report shared mode + participating agents
21. Add `JournalEntry` to `assignee` auto-clear on terminal status transitions

---

## 7. Testing Strategy

### 7.1 Unit Tests

- `test_ticket_model_new_fields` — Agent fields serialize/deserialize correctly
- `test_ticket_backward_compat_no_new_fields` — Old frontmatter reads with defaults
- `test_ticket_new_frontmatter_old_code` — `extra="ignore"` accepts unknown fields
- `test_optimistic_concurrency_success` — Update with correct version succeeds
- `test_optimistic_concurrency_conflict` — Update with stale version raises ConflictError
- `test_conflict_error_contains_current_ticket` — ConflictError has full ticket state
- `test_shared_config_defaults` — Default config has shared.enabled=false
- `test_shared_config_requires_agent_id` — Validation error when enabled but no agent_id
- `test_journal_append_and_read` — Journal round-trips correctly
- `test_journal_concurrent_append` — Two agents appending don't interleave
- `test_assignee_field_independent_of_owner` — assignee doesn't affect owner/repo

### 7.2 Integration Tests

- `test_multi_agent_shared_store` — Two TicketStore instances on same dir see all tickets
- `test_multi_agent_concurrent_create` — Two agents create simultaneously, no ID collision
- `test_multi_agent_concurrent_update` — Two agents update same ticket, one gets ConflictError
- `test_multi_agent_journal_consistency` — All mutations appear in journal in order
- `test_search_across_agents` — Tickets from different agents are all searchable
- `test_single_agent_backward_compat` — Existing single-agent workflow works unchanged
- `test_journal_survives_crash` — Journal entry is durable after fsync
- `test_persistent_lock_file` — Lock file not deleted between operations

### 7.3 Migration Tests

- `test_migrate_old_tickets` — Read tickets without new fields, defaults applied
- `test_migrate_duplicate_tickets` — Two stores with same IDs merged correctly

---

## 8. Comparison with GLM-5 Draft

| Aspect | GLM-5 Draft | This Proposal |
|--------|-------------|---------------|
| Conflict resolution | Auto-merge (silent) | Explicit rejection (agent decides) |
| Activity tracking | None (reads files) | Append-only journal (JSONL) |
| Claim mechanism | Repurpose `owner` field | New `assignee` field |
| Agent discovery | None | `.vtic-agents.json` manifest |
| Search index writes | Not addressed | Atomic (tempfile+replace) |
| Lock file handling | Delete after each op | Persistent (never deleted) |
| Journal API | Listed as P3 future | Part of P1 core |
| Agent ID in search | In signature only | In search text + filters |
| New files needed | 0 | 1 (`journal.py`) |
| Estimated LOC | ~200 | ~350 + ~120 (journal) |

---

## 9. Conclusion

The GLM-5 draft correctly identified the problem space but underspecified the
coordination mechanism. Simply sharing a directory with version counters solves
the *visibility* problem but not the *coordination* problem.

This proposal adds an activity journal as the coordination primitive. The journal
gives every agent a durable, ordered log of all mutations — the minimal
information needed for coordination. Combined with explicit conflict rejection
(never auto-merge), agents always have enough context to make good decisions
about retrying, deferring, or escalating.

The `assignee` field provides proper ticket claiming without breaking the
existing `owner` (repo owner) semantics. The agent manifest enables discovery.
The persistent lock file eliminates a TOCTOU race. Atomic index writes prevent
corruption.

All of this is achieved with ~470 lines of new/modified code, zero new
dependencies, and full backward compatibility.
