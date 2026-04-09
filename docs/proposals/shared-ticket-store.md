# Proposal: Shared Ticket Store for Multi-Agent Coordination

**Author:** Apex (hermes-agent subagent)
**Date:** 2026-04-09
**Status:** Draft
**Version:** 1.0

---

## 1. Problem Analysis

### 1.1 Current Architecture

vtic stores tickets as markdown files on disk. The storage path is:

```
{tickets_dir}/{owner}/{repo}/{category}/{id}-{slug}.md
```

Each agent (Apex, Lux, Orion, cclow, dave, finan) runs from its own profile/workspace and configures vtic with a `tickets.dir` pointing to its own local directory. The key architectural facts:

- `TicketStore.__init__(base_dir)` takes a single directory path — all tickets live under it
- `_iter_ticket_paths()` walks `base_dir` recursively via `rglob("*.md")`
- `create_ticket()` allocates IDs by scanning existing files (no cross-agent coordination)
- `update()` uses `fcntl.flock()` for intra-process locking but has no cross-agent awareness
- The `owner` field on tickets refers to the GitHub/repo owner, NOT the agent identity
- There is no concept of "who created this ticket" separate from the repo owner
- Search indexes are per-store, not shared

### 1.2 The Multi-Agent Gap

This is the root cause of all three stated problems:

**Problem 1 — Invisible silos:** Each agent's `tickets.dir` is a separate directory tree. Apex has tickets under `~/.hermes/profiles/apex/workspace/ctxgraph4agent/tickets/`, Orion under `~/.hermes/profiles/orion/workspace/ctxgraph4agent/tickets/`. These are completely separate filesystems. Neither agent sees the other's work.

**Problem 2 — Fragmented status reports:** When asked "what's the status of ctxgraph4agent?", each agent only lists its own tickets. This was confirmed by inspecting the actual ticket directories — Apex and Orion both have copies of the same tickets (C3, C8, T1-T3) in separate trees, likely created independently because neither could see the other's.

**Problem 3 — No coordination protocol:** Two agents can:
- Create duplicate tickets for the same issue (confirmed: identical ticket IDs in Apex and Orion trees)
- Both mark different status on "their" copy while the other remains unchanged
- One agent closes a ticket that another agent is actively working on
- There is no lock, claim, or assignment mechanism

### 1.3 Why Simple "Shared Directory" Isn't Enough

Pointing all agents at the same `tickets.dir` solves the visibility problem but introduces new issues:
- **ID collisions:** Two agents calling `_next_id()` simultaneously get the same ID → `FileExistsError`
- **Lost updates:** Agent A reads ticket, Agent B updates it, Agent A writes stale data → last-write-wins silently
- **No provenance:** No way to know which agent created or last modified a ticket
- **No claiming:** No way for an agent to "claim" a ticket to signal intent to work on it

---

## 2. Proposed Solution

### 2.1 Design Principles

1. **Shared filesystem, not a server** — Keep vtic's markdown-on-disk philosophy
2. **Agent identity as first-class concept** — Every write is tagged with who did it
3. **Optimistic concurrency** — Use version counters instead of heavy locking
4. **Backward compatible** — Single-agent setups work unchanged
5. **Migration, not migration** — Existing tickets just work; new fields are optional

### 2.2 New Concepts

#### 2.2.1 Agent Identity (`agent_id`)

A new field on every ticket: the identity of the agent that last modified it.

```python
# In Ticket model
agent_id: str | None = Field(default=None, max_length=100,
    description="Identity of the agent that created/last modified this ticket")
```

- Set automatically on create and update
- Populated from config or environment variable `VTIC_AGENT_ID`
- Visible in search, list, and API responses
- `None` for backward compatibility with existing tickets

#### 2.2.2 Version Counter (`version`)

An integer field that increments on every update, used for optimistic concurrency control.

```python
# In Ticket model
version: int = Field(default=1, ge=1,
    description="Monotonically increasing version for conflict detection")
```

#### 2.2.3 Created-By Tracking (`created_by`)

Separate from `agent_id` — records who originally created the ticket, even if another agent later updates it.

```python
# In Ticket model
created_by: str | None = Field(default=None, max_length=100,
    description="Identity of the agent that originally created this ticket")
```

#### 2.2.4 Claim Mechanism (via tags + owner field)

Rather than adding a complex "claim" primitive, use the existing `owner` field plus a convention:
- When an agent starts working on a ticket, they set `owner` to their agent identity
- Add a reserved tag `claimed-by:{agent_id}` for filtering
- The existing `status` field (`in_progress`) combined with `owner` provides sufficient signaling

This requires no schema changes — just convention and a filter helper.

#### 2.2.5 Conflict Resolution Policy

When an agent tries to update a ticket whose `version` has changed since they read it:
- **Status/status transitions:** Last-write-wins (agents should read-before-write)
- **Non-conflicting field updates:** Merge — each field independently takes the latest value
- **Description/fix content:** Append conflicting edits with a separator rather than overwrite

The primary mechanism is **optimistic concurrency with auto-merge**:
1. Agent reads ticket (gets version N)
2. Agent computes update
3. Agent writes update with `expected_version=N`
4. If current version > N, attempt field-level merge
5. If merge fails (conflicting text edits), return a `ConflictError` with both versions

### 2.3 Shared Store Configuration

#### 2.3.1 New Config Section

```toml
# vtic.toml
[shared]
enabled = true
store_dir = "/home/smoke01/.shared-vtic/projects"  # optional, overrides tickets.dir for shared mode
agent_id = "apex"                                    # required when enabled

[tickets]
dir = "./tickets"  # still works for local-only mode
```

#### 2.3.2 Environment Variables

```
VTIC_SHARED_ENABLED=true
VTIC_SHARED_STORE_DIR=/home/smoke01/.shared-vtic/projects
VTIC_AGENT_ID=apex
```

#### 2.3.3 Shared Directory Structure

```
~/.shared-vtic/
  projects/
    ctxgraph4agent/
      661818yijack/          # repo owner
        ctxgraph4agent/      # repo name
          code_quality/
            C1-some-ticket.md
            C8-async-reqwest.md
          testing/
            T1-mcp-init.md
    vtic/
      661818yijack/
        vtic/
          code_quality/
            C1-shared-store.md
  .vtic-lock/                # directory for per-project lock files
    ctxgraph4agent.lock
    vtic.lock
```

The key difference from current: the `owner/{repo}` structure is preserved, but the top-level directory is shared across all agents. Each agent's `agent_id` is recorded in the ticket metadata.

### 2.4 How the Pieces Fit Together

```
Agent Apex                  Agent Orion                  Shared Store
    |                            |                            |
    |--- create_ticket() ------> |                            |
    |                            |                            |
    |                 agent_id="apex"                          |
    |                 version=1                                |
    |                 created_by="apex"                        |
    |                            |                            |
    |                    reads ticket (v1)                     |
    |                            |                            |
    |--- update_ticket() ------> |                            |
    |   expected_version=1       |                            |
    |                            |                            |
    |                 agent_id="orion"                         |
    |                 version=2                                |
    |                            |                            |
    |                    reads ticket (v2)                     |
    |                            |                            |
    |--- update_ticket() ------> |                            |
    |   expected_version=2       |                            |
    |   (succeeds)               |                            |
```

---

## 3. Specific Code Changes

### 3.1 File: `src/vtic/models.py`

**Add fields to `Ticket` class (after line 132):**
```python
agent_id: str | None = Field(default=None, max_length=100,
    description="Agent identity that last modified this ticket")
created_by: str | None = Field(default=None, max_length=100,
    description="Agent identity that originally created this ticket")
version: int = Field(default=1, ge=1,
    description="Optimistic concurrency version counter")
```

**Add field to `TicketUpdate` class:**
```python
expected_version: int | None = Field(default=None, ge=1,
    description="Expected current version for optimistic concurrency")
```

**Add to `TicketResponse`:**
```python
agent_id: str | None = None
created_by: str | None = None
version: int = 1
```

**Update `TicketResponse.from_ticket()` to include the new fields.**

**Add `created_by` filter to `SearchFilters`:**
```python
created_by: str | None = Field(default=None,
    description="Filter by the agent that created the ticket")
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
        description="Shared store directory (overrides tickets.dir when set)")
    agent_id: str | None = Field(default=None, max_length=100,
        description="Agent identity for shared mode")
```

**Add to `VticConfig`:**
```python
shared: SharedConfig = Field(default_factory=SharedConfig)
```

**Add environment overrides:**
```python
"VTIC_SHARED_ENABLED": ("shared", "enabled"),
"VTIC_SHARED_STORE_DIR": ("shared", "store_dir"),
"VTIC_AGENT_ID": ("shared", "agent_id"),
```

**Update `load_config()`** to resolve the effective tickets directory:
- If `shared.enabled` and `shared.store_dir` is set → use `shared.store_dir`
- Otherwise → use `tickets.dir` (backward compatible)

### 3.3 File: `src/vtic/storage.py`

**Update `_serialize_ticket()`** to include new frontmatter fields:
```python
if ticket.agent_id:
    frontmatter["agent_id"] = ticket.agent_id
if ticket.created_by:
    frontmatter["created_by"] = ticket.created_by
frontmatter["version"] = ticket.version
```

**Update `_parse_frontmatter()`** to read new fields (with backward-compatible defaults):
```python
data.setdefault("agent_id", None)
data.setdefault("created_by", None)
data.setdefault("version", 1)
```

**Update `create_ticket()`** to accept and set `agent_id` and `created_by`:
```python
def create_ticket(self, *, ..., agent_id: str | None = None) -> Ticket:
    # ... existing code ...
    ticket = Ticket(
        # ... existing fields ...
        agent_id=agent_id,
        created_by=agent_id,
        version=1,
    )
```

**Update `update()`** to implement optimistic concurrency:
```python
def update(self, ticket_id: str, updates: TicketUpdate,
           agent_id: str | None = None) -> Ticket:
    update_data = updates.model_dump(exclude_unset=True)
    expected_version = update_data.pop("expected_version", None)

    # ... inside lock ...
    current, current_path = self._find_ticket_path(ticket_id)

    if expected_version is not None and current.version != expected_version:
        if self._can_auto_merge(current, update_data):
            return self._merge_update(current, update_data, agent_id)
        raise ConflictError(ticket_id, expected_version, current.version)

    # ... rest of update logic ...
    data["version"] = current.version + 1
    data["agent_id"] = agent_id
```

**Add new error class in `src/vtic/errors.py`:**
```python
class ConflictError(VticError):
    """Raised when optimistic concurrency check fails."""
    def __init__(self, ticket_id: str, expected: int, actual: int) -> None:
        super().__init__(
            error_code="CONFLICT",
            message=f"Ticket {ticket_id} version conflict: expected {expected}, actual {actual}",
            status_code=409,
        )
```

**Add `_can_auto_merge()` helper:**
```python
def _can_auto_merge(self, current: Ticket, update_data: dict) -> bool:
    """Check if fields being updated don't conflict with the current version."""
    # Non-text fields can always be auto-merged
    text_fields = {"description", "fix", "title"}
    conflicting_updates = text_fields & set(update_data.keys())
    return len(conflicting_updates) == 0 or len(conflicting_updates) == len(update_data)
```

**Add `_merge_update()` helper:**
```python
def _merge_update(self, current: Ticket, update_data: dict,
                  agent_id: str | None) -> Ticket:
    """Perform field-level merge with version bump."""
    data = current.model_dump()
    data.update(update_data)
    data["version"] = current.version + 1
    data["updated_at"] = utc_now()
    data["agent_id"] = agent_id
    updated_ticket = Ticket(**data)
    # write to disk...
    return updated_ticket
```

### 3.4 File: `src/vtic/api.py`

**Update `create_app()`** to pass agent_id from config:
```python
config = load_config()
agent_id = config.shared.agent_id if config.shared.enabled else None
```

**Update `create_ticket` endpoint** to set agent_id:
```python
ticket = store.create_ticket(
    # ... existing args ...
    agent_id=agent_id,
)
```

**Update `update_ticket` endpoint** to pass agent_id and handle ConflictError:
```python
try:
    return TicketResponse.from_ticket(store.update(ticket_id, payload, agent_id=agent_id))
except ConflictError as exc:
    raise HTTPException(status_code=409, detail=exc.to_response().model_dump())
```

**Update `list_tickets` endpoint** to support `created_by` filter:
```python
created_by: str | None = Query(None, alias="created-by"),
# ...
filters = SearchFilters(
    # ... existing ...
    created_by=created_by,
)
```

### 3.5 File: `src/vtic/cli/main.py`

**Update `_resolve_store()`** to also return agent_id:
```python
def _resolve_store(tickets_dir: Path | None) -> tuple[TicketStore, str | None]:
    config = load_config()
    base_dir = tickets_dir or config.tickets.dir
    if config.shared.enabled and config.shared.store_dir:
        base_dir = config.shared.store_dir
    agent_id = config.shared.agent_id if config.shared.enabled else None
    return TicketStore(base_dir), agent_id
```

**Update all commands** that create/update tickets to pass `agent_id`.

**Add new CLI command `status`:**
```python
@app.command()
def status(
    repo: str = typer.Option(..., "--repo"),
    dir: Path | None = typer.Option(None, "--dir"),
) -> None:
    """Show project status across all agents."""
    store, _ = _resolve_store(dir)
    filters = SearchFilters(repo=[repo])
    tickets = store.list(filters)
    # Group by agent_id, show counts by status
    # Show claimed vs unclaimed
    # Show recently updated
```

### 3.6 File: `src/vtic/search.py`

**No structural changes needed.** The search engine already reads all tickets from the store's `base_dir`. When multiple agents point at the same shared directory, the search index automatically includes all agents' tickets.

**Enhancement:** Update `_ticket_signature()` to include `version` and `agent_id` so the index invalidates correctly when another agent updates a ticket:
```python
def _ticket_signature(self, ticket: Ticket) -> str:
    payload = {
        # ... existing fields ...
        "version": getattr(ticket, "version", 1),
        "agent_id": getattr(ticket, "agent_id", None),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
```

### 3.7 File: `src/vtic/constants.py`

**No changes needed.** The existing constants work as-is.

---

## 4. Migration Path

### 4.1 Phase 0: No Changes (Current State)

Single-agent setups continue working. Nothing breaks.

### 4.2 Phase 1: Schema Extension (Non-Breaking)

Add the three new fields (`agent_id`, `created_by`, `version`) to the `Ticket` model with `default=None` / `default=1`. Old ticket files that lack these fields in frontmatter will:
- `agent_id` → `None` (backward compatible default)
- `created_by` → `None`
- `version` → defaults to `1` via `setdefault()`

All existing tickets read and work without modification.

### 4.3 Phase 2: Config Addition (Non-Breaking)

Add `SharedConfig` to `VticConfig`. Default is `enabled=false`. No existing config files need changes. If `vtic.toml` doesn't have a `[shared]` section, everything works as before.

### 4.4 Phase 3: Opt-In Shared Mode

Agents that want shared tickets add to their `vtic.toml`:
```toml
[shared]
enabled = true
store_dir = "/home/smoke01/.shared-vtic/projects"
agent_id = "apex"
```

The shared directory is created on first use (existing `mkdir(parents=True, exist_ok=True)` pattern).

### 4.5 Phase 4: Migration of Existing Tickets (Optional)

For agents that already have duplicate tickets across workspaces:
1. Run a one-time `vtic migrate --from ./local-tickets --to /shared-dir` command
2. Deduplication: tickets with same `id` and similar title are merged (keep newest)
3. Set `created_by` to the agent whose ticket was kept
4. Delete the old local ticket directory

This is a separate utility, not part of the core change.

### 4.6 Backward Compatibility Summary

| Scenario | Works? | Notes |
|----------|--------|-------|
| Existing single-agent, no config changes | Yes | New fields default to None/1 |
| Old ticket files, new code | Yes | Missing frontmatter fields get defaults |
| New ticket files, old code | Yes | Extra frontmatter fields are ignored (extra="ignore") |
| Multiple agents, shared=false | Yes | Same as current behavior |
| Multiple agents, shared=true, same dir | Yes | New coordinated behavior |

---

## 5. Edge Cases and Handling

### 5.1 Two Agents Create the Same Ticket Simultaneously

**Scenario:** Apex and Orion both call `create_ticket()` for the same category within milliseconds.

**Current behavior:** Both agents call `_next_id()` under `fcntl.flock()`. The lock serializes access, so one gets ID C5 and the other gets C6. No collision.

**With shared store:** Same — the lock file is in the shared directory, so `fcntl.flock()` works across processes on the same machine. First agent gets C5, second gets C6. Both succeed, but the content may be duplicates.

**Mitigation:** Agents should search before creating. Additionally, `created_by` makes duplicates easy to detect (two tickets with similar titles and different `created_by`).

### 5.2 Two Agents Update the Same Ticket Simultaneously

**Scenario:** Agent A reads ticket (v1), Agent B reads ticket (v1), both update.

**Handling:**
1. Agent A writes with `expected_version=1` → succeeds, ticket becomes v2
2. Agent B writes with `expected_version=1` → CONFLICT (current is v2)
3. Auto-merge attempt:
   - If B only changed `status` (non-text field) → merge succeeds, ticket becomes v3 with A's text + B's status
   - If both changed `description` → conflict returned to Agent B
4. Agent B can re-read v2 and retry, or manually resolve

### 5.3 Agent Crashes Mid-Write

**Scenario:** Agent starts writing a ticket file but crashes before completion.

**Current behavior:** The temp file (from `NamedTemporaryFile`) remains but the `os.replace()` never happened. The partial file is in the directory but doesn't match the `{id}-{slug}.md` pattern expected by `_iter_ticket_paths()`.

**With shared store:** Same behavior. The existing `tempfile` + `os.replace` pattern is already crash-safe. No change needed.

### 5.4 Stale Lock Files

**Scenario:** Agent crashes while holding the lock, leaving `.vtic.lock` behind.

**Current behavior:** `fcntl.flock()` is advisory and released when the file descriptor closes (process exit). The `lock_path.unlink(missing_ok=True)` in the `finally` block handles cleanup.

**With shared store:** Same behavior. `fcntl.flock()` works correctly across processes. If the process is killed hard (SIGKILL), the OS releases the flock on FD close. The lock file cleanup in `finally` is defensive.

**Additional hardening:** Add a stale lock detection: if `.vtic.lock` exists and its mtime is older than 30 seconds, attempt to acquire the lock anyway (the original holder is likely dead).

### 5.5 Agent Identity Spoofing

**Scenario:** An agent sets `agent_id` to another agent's identity.

**Handling:** This is a trust boundary issue, not a technical one. All agents on this machine are trusted (they're all the user's agents). No authentication needed for local-first tooling. The `agent_id` is self-reported.

**Future:** If untrusted agents are introduced, a shared secret or filesystem permissions could gate the shared directory.

### 5.6 Search Index Consistency

**Scenario:** Agent A creates a ticket, Agent B searches before the index is rebuilt.

**Handling:** The search engine already handles this via:
1. `_load_cached_tickets()` checks file mtimes on each search
2. `_ensure_index()` rebuilds if signatures don't match
3. The persisted index includes signatures for invalidation

**With shared store:** Works correctly. Agent B's search will detect the new file (mtime changed), re-read it, rebuild the index, and include it in results. The persisted index at `{base_dir}/.vtic-search-index.json` is in the shared directory, so both agents share it.

**Race condition:** If Agent A writes the ticket and Agent B reads the index in the same millisecond, Agent B might get stale results. This is acceptable — the next search will pick it up.

### 5.7 Ticket ID Exhaustion

**Scenario:** A shared project accumulates thousands of tickets per category.

**Handling:** Current ID scheme is `{PREFIX}{N}` where N is an integer (C1, C2, ... C9999). At N=99999 the ID exceeds the 20-char `max_length` constraint.

**Mitigation:** This is a pre-existing limitation, not introduced by sharing. But sharing makes it more likely to hit. The `_next_id()` method should be updated to use zero-padded formatting when N > 9 (C01, C02...) and raise a clear error near the limit. This is a separate enhancement.

### 5.8 Deleted Tickets and Visibility

**Scenario:** Agent A deletes (trashes) a ticket. Agent B still sees it.

**Handling:** The trash directory (`.trash/`) is per-store. With a shared store, the trash is shared. `_iter_ticket_paths(include_trash=False)` excludes trashed tickets from normal listing. Agent B won't see trashed tickets in normal operations. Agent B can still restore them if needed.

---

## 6. Implementation Priority

### P0 (Core — Do First)
1. Add `agent_id`, `created_by`, `version` fields to `Ticket` model
2. Update `_serialize_ticket()` and `_parse_frontmatter()` for new fields
3. Add `SharedConfig` to config
4. Update `create_ticket()` and `update()` to accept/pass agent_id
5. Add `ConflictError` and optimistic concurrency to `update()`

### P1 (Important — Do Second)
6. Update API endpoints to pass agent_id from config
7. Add `created_by` filter to `SearchFilters`
8. Update CLI commands to use agent_id
9. Add `vtic status` command for cross-agent visibility

### P2 (Nice to Have)
10. Add `vtic migrate` command for deduplicating existing tickets
11. Add stale lock detection with timeout
12. Add `--agent` filter to CLI `list` and `search` commands
13. Update health endpoint to report shared mode status and participating agents

### P3 (Future)
14. Per-agent notification system (inotify watch on shared directory)
15. Activity log (append-only log of all agent actions for audit trail)
16. Claim protocol with automatic timeout (release claim after N hours of inactivity)

---

## 7. Testing Strategy

### 7.1 Unit Tests

- `test_ticket_model_with_agent_fields` — New fields serialize/deserialize correctly
- `test_ticket_backward_compat_no_new_fields` — Old frontmatter reads with defaults
- `test_optimistic_concurrency_success` — Update with correct version succeeds
- `test_optimistic_concurrency_conflict` — Update with stale version raises ConflictError
- `test_auto_merge_non_text_fields` — Non-conflicting field merge succeeds
- `test_auto_merge_conflict_text` — Conflicting text edits raise ConflictError
- `test_shared_config_defaults` — Default config has shared.enabled=false

### 7.2 Integration Tests

- `test_multi_agent_shared_store` — Two TicketStore instances on same dir, both see all tickets
- `test_multi_agent_concurrent_create` — Two agents create tickets simultaneously, no ID collision
- `test_multi_agent_concurrent_update` — Two agents update same ticket, one gets conflict
- `test_search_across_agents` — Tickets created by different agents are all searchable
- `test_single_agent_backward_compat` — Existing single-agent workflow works unchanged

### 7.3 Migration Tests

- `test_migrate_old_tickets` — Read tickets without new fields, verify defaults applied
- `test_new_code_old_tickets` — Create Ticket from frontmatter missing agent_id/version

---

## 8. Conclusion

This proposal solves the multi-agent coordination problem with minimal architectural changes to vtic. The key insight is that the current filesystem-based storage already provides most of what's needed — what's missing is agent identity, concurrency control, and a configuration path to share a directory.

The solution adds 3 fields to the ticket model, 1 config section, optimistic concurrency to the update path, and a conflict error type. No database, no server, no new dependencies. Existing single-agent setups are completely unaffected.

Total estimated code changes: ~200 lines of new/modified code across 5 files.
