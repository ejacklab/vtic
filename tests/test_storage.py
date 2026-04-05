from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor

import pytest

from vtic.errors import TicketAlreadyExistsError, TicketNotFoundError
from vtic.models import Category, SearchFilters, Severity, Status, Ticket, TicketUpdate
from vtic.storage import TRASH_DIRNAME, TicketStore
from vtic.utils import slugify, ticket_path


FIXED_TIMESTAMP = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)


def _make_ticket(
    ticket_id: str,
    *,
    title: str,
    repo: str = "owner/repo",
    category: Category = Category.CODE_QUALITY,
    severity: Severity = Severity.MEDIUM,
    status: Status = Status.OPEN,
    description: str | None = None,
    fix: str | None = None,
    owner: str | None = "owner",
    file: str | None = None,
    tags: list[str] | None = None,
) -> Ticket:
    return Ticket(
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
        tags=tags or [],
        created_at=FIXED_TIMESTAMP,
        updated_at=FIXED_TIMESTAMP,
        slug=slugify(title),
    )


def test_init_creates_directory(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")

    store.base_dir.mkdir(parents=True, exist_ok=True)

    assert store.base_dir.exists()
    assert store.base_dir.is_dir()


def test_create_writes_markdown_file(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket(
        "C1",
        title="Consolidate duplicate helpers",
        repo="owner/repo",
        category=Category.CODE_QUALITY,
        description="Refactor duplicate helper implementations.",
        fix="Extract a shared helper module.",
        file="src/helpers.py:10-40",
        tags=["refactor", "helpers"],
    )

    store.create(ticket)

    path = ticket_path(store.base_dir, ticket)
    content = path.read_text(encoding="utf-8")
    assert path.exists()
    assert "---" in content
    assert "id: C1" in content
    assert "title: Consolidate duplicate helpers" in content
    assert "repo: owner/repo" in content
    assert "category: code_quality" in content
    assert "Refactor duplicate helper implementations." in content
    assert "<!-- FIX -->" in content
    assert "Extract a shared helper module." in content


def test_get_returns_ticket(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    created = _make_ticket("S1", title="CORS wildcard", category=Category.SECURITY, repo="owner/repo")
    store.create(created)

    loaded = store.get("S1")

    assert loaded == created


def test_get_not_found(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")

    with pytest.raises(TicketNotFoundError, match="Ticket Z99 not found"):
        store.get("Z99")


def test_list_filters(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    code_ticket = _make_ticket("C1", title="Code cleanup", category=Category.CODE_QUALITY)
    security_ticket = _make_ticket("S1", title="Fix TLS", category=Category.SECURITY)
    store.create(code_ticket)
    store.create(security_ticket)

    results = store.list(SearchFilters(category=[Category.SECURITY]))

    assert [ticket.id for ticket in results] == ["S1"]


def test_update_modifies_file(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Needs fix", status=Status.OPEN)
    store.create(ticket)

    updated = store.update("C1", TicketUpdate(status=Status.FIXED))
    content = ticket_path(store.base_dir, updated).read_text(encoding="utf-8")

    assert updated.status is Status.FIXED
    assert "status: fixed" in content


def test_delete_removes_file(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Delete me")
    path = ticket_path(store.base_dir, ticket)
    store.create(ticket)

    store.delete("C1", force=True)

    assert not path.exists()
    with pytest.raises(TicketNotFoundError):
        store.get("C1")


def test_concurrent_id_generation(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    store.create(_make_ticket("C1", title="Existing cleanup"))

    first = store._next_id(Category.CODE_QUALITY)
    store.create(_make_ticket(first, title="Queued cleanup"))
    second = store._next_id(Category.CODE_QUALITY)

    assert first == "C2"
    assert second == "C3"
    assert first != second


def test_create_ticket_is_atomic_under_concurrency(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    barrier = Barrier(8)

    def create_one(index: int) -> str:
        barrier.wait()
        ticket = store.create_ticket(
            title=f"Concurrent ticket {index}",
            repo="owner/repo",
            owner="owner",
            category=Category.CODE_QUALITY,
            severity=Severity.MEDIUM,
            status=Status.OPEN,
            description=None,
            fix=None,
            file=None,
            tags=[],
            slug=f"concurrent-ticket-{index}",
        )
        return ticket.id

    with ThreadPoolExecutor(max_workers=8) as executor:
        ids = list(executor.map(create_one, range(8)))

    assert sorted(ids) == [f"C{i}" for i in range(1, 9)]
    assert len({*ids}) == 8
    assert len(list((tmp_path / "tickets").rglob("*.md"))) == 8


def test_list_empty(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")

    assert store.list() == []


def test_next_id_starts_at_1(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")

    assert store._next_id(Category.CODE_QUALITY) == "C1"


def test_count_counts_markdown_files_without_parsing(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket_dir = store.base_dir / "owner" / "repo" / "code-quality"
    ticket_dir.mkdir(parents=True)
    (ticket_dir / "C1-valid.md").write_text("---\nid: C1\n---\n", encoding="utf-8")
    (ticket_dir / "C2-invalid.md").write_text("not frontmatter", encoding="utf-8")
    (ticket_dir / "notes.txt").write_text("ignore", encoding="utf-8")

    assert store.count() == 2


def test_next_id_uses_filename_scan_without_parsing(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket_dir = store.base_dir / "owner" / "repo" / "code-quality"
    ticket_dir.mkdir(parents=True)
    (ticket_dir / "C2-valid.md").write_text("---\nid: C2\n---\n", encoding="utf-8")
    (ticket_dir / "C10-invalid.md").write_text("not frontmatter", encoding="utf-8")
    (ticket_dir / "S99-security.md").write_text("not frontmatter", encoding="utf-8")

    assert store._next_id(Category.CODE_QUALITY) == "C11"


def test_create_uses_expected_nested_path(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("S1", title="Nested path", repo="acme/platform", category=Category.SECURITY)

    store.create(ticket)

    assert ticket_path(store.base_dir, ticket) == (
        tmp_path / "tickets" / "acme" / "platform" / "security" / "S1-nested-path.md"
    )


def test_ticket_path_rejects_repo_path_escape(tmp_path: Path, sample_timestamp: datetime) -> None:
    ticket = Ticket.model_construct(
        id="C1",
        title="Escape",
        description=None,
        fix=None,
        repo="../repo",
        owner="owner",
        category=Category.CODE_QUALITY,
        severity=Severity.MEDIUM,
        status=Status.OPEN,
        file=None,
        tags=[],
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        slug="escape",
    )

    with pytest.raises(ValueError, match="Repo path segments cannot be '.' or '..'"):
        ticket_path(tmp_path / "tickets", ticket)


def test_create_without_fix_omits_fix_section(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Plain body", description="Only description text.")

    store.create(ticket)

    content = ticket_path(store.base_dir, ticket).read_text(encoding="utf-8")
    assert "Only description text." in content
    assert "<!-- FIX -->" not in content


def test_get_is_case_insensitive_for_id_lookup(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Lookup")
    store.create(ticket)

    loaded = store.get("c1")

    assert loaded.id == "C1"


def test_list_returns_sorted_by_ticket_id(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    store.create(_make_ticket("S2", title="Second security", category=Category.SECURITY))
    store.create(_make_ticket("C3", title="Third code"))
    store.create(_make_ticket("C1", title="First code"))

    results = store.list()

    assert [ticket.id for ticket in results] == ["C1", "C3", "S2"]


def test_update_can_change_description_and_fix(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Needs more detail", description="Old", fix=None)
    store.create(ticket)

    updated = store.update(
        "C1",
        TicketUpdate(description="New description", fix="Apply a shared abstraction."),
    )

    content = ticket_path(store.base_dir, updated).read_text(encoding="utf-8")
    assert updated.description == "New description"
    assert updated.fix == "Apply a shared abstraction."
    assert "New description" in content
    assert "Apply a shared abstraction." in content


def test_description_preserves_literal_fix_heading(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket(
        "C1",
        title="Literal heading",
        description="Keep this heading:\n## Fix\ninside the description.",
        fix="Actual fix body.",
    )
    store.create(ticket)

    loaded = store.get("C1")

    assert loaded.description == "Keep this heading:\n## Fix\ninside the description."
    assert loaded.fix == "Actual fix body."


def test_update_can_change_category_and_move_file(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Reclassify ticket", category=Category.CODE_QUALITY)
    old_path = ticket_path(store.base_dir, ticket)
    store.create(ticket)

    updated = store.update("C1", TicketUpdate(category=Category.SECURITY))
    new_path = ticket_path(store.base_dir, updated)

    assert updated.category is Category.SECURITY
    assert not old_path.exists()
    assert new_path.exists()


def test_update_is_atomic(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Original title", category=Category.CODE_QUALITY)
    old_path = ticket_path(store.base_dir, ticket)
    store.create(ticket)

    updated = store.update(
        "C1",
        TicketUpdate(
            category=Category.SECURITY,
            title="Updated title",
            status=Status.FIXED,
            description="Updated description",
        ),
    )
    new_path = ticket_path(store.base_dir, updated)
    files = list(store.base_dir.rglob("*.md"))

    assert len(files) == 1
    assert files == [new_path]
    assert not old_path.exists()
    assert new_path.exists()
    content = new_path.read_text(encoding="utf-8")
    assert "title: Updated title" in content
    assert "status: fixed" in content
    assert "Updated description" in content


def test_delete_not_found_raises(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")

    with pytest.raises(TicketNotFoundError):
        store.delete("C404")


def test_create_duplicate_id_raises(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Duplicate")
    store.create(ticket)

    with pytest.raises(TicketAlreadyExistsError, match="Ticket C1 already exists"):
        store.create(ticket)


def test_list_filters_by_repo_status_and_tags(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    matching = _make_ticket(
        "C1",
        title="Match all filters",
        repo="acme/app",
        status=Status.BLOCKED,
        tags=["auth", "api"],
    )
    store.create(matching)
    store.create(_make_ticket("C2", title="Wrong repo", repo="other/app", status=Status.BLOCKED, tags=["auth", "api"]))
    store.create(_make_ticket("C3", title="Wrong status", repo="acme/app", status=Status.OPEN, tags=["auth", "api"]))
    store.create(_make_ticket("C4", title="Missing tag", repo="acme/app", status=Status.BLOCKED, tags=["auth"]))

    results = store.list(
        SearchFilters(
            repo=["acme/app"],
            status=[Status.BLOCKED],
            tags=["auth", "api"],
        )
    )

    assert [ticket.id for ticket in results] == ["C1"]


def test_list_filters_repo_wildcards(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    store.create(_make_ticket("C1", title="Match wildcard", repo="ejacklab/core"))
    store.create(_make_ticket("C2", title="No match", repo="other/core"))

    results = store.list(SearchFilters(repo=["ejacklab/*"]))

    assert [ticket.id for ticket in results] == ["C1"]


def test_list_filters_by_has_fix_and_owner(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    store.create(_make_ticket("C1", title="Owned fix", owner="smoke01", description="Has a fix", fix="Do it"))
    store.create(_make_ticket("C2", title="Owned no fix", owner="smoke01", description="No fix", fix=None))
    store.create(_make_ticket("C3", title="Other owner", owner="alex", description="Other owner", fix="Do it"))

    results = store.list(SearchFilters(has_fix=True, owner="smoke01"))

    assert [ticket.id for ticket in results] == ["C1"]


def test_list_skips_corrupt_files_and_collects_errors(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    store.create(_make_ticket("C1", title="Healthy ticket", repo="acme/app"))
    broken_path = (
        store.base_dir / "acme" / "app" / "code_quality" / "C2-broken-ticket.md"
    )
    broken_path.parent.mkdir(parents=True, exist_ok=True)
    broken_path.write_text("---\nid: C2\ntitle: Broken\n---\n", encoding="utf-8")

    results = store.list()

    assert [ticket.id for ticket in results] == ["C1"]
    assert len(store.last_list_errors) == 1
    assert store.last_list_errors[0].field == "acme/app/code_quality/C2-broken-ticket.md"


def test_soft_delete_moves_file_to_trash(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Trash me", repo="acme/app")
    active_path = ticket_path(store.base_dir, ticket)
    store.create(ticket)

    trash_path = store.move_to_trash("C1")

    assert not active_path.exists()
    assert trash_path == store.base_dir / TRASH_DIRNAME / "acme" / "app" / "code_quality" / "C1-trash-me.md"
    assert trash_path.exists()


def test_soft_delete_creates_trash_directory(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Create trash dir")
    store.create(ticket)

    store.delete("C1")

    assert (store.base_dir / TRASH_DIRNAME).is_dir()


def test_force_delete_permanently_removes(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Hard delete")
    store.create(ticket)

    store.delete("C1", force=True)

    assert not any(store.base_dir.rglob("*.md"))
    assert not (store.base_dir / TRASH_DIRNAME).exists()


def test_restore_from_trash(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("S1", title="Restore me", category=Category.SECURITY, repo="acme/app")
    original_path = ticket_path(store.base_dir, ticket)
    store.create(ticket)
    store.delete("S1")

    restored = store.restore_from_trash("S1")

    assert restored == ticket
    assert original_path.exists()
    assert not any((store.base_dir / TRASH_DIRNAME).rglob("S1-restore-me.md"))


def test_list_excludes_trash_directory(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    active = _make_ticket("C1", title="Active ticket")
    trashed = _make_ticket("C2", title="Trashed ticket")
    store.create(active)
    store.create(trashed)
    store.delete("C2")

    results = store.list()

    assert [ticket.id for ticket in results] == ["C1"]


def test_find_ticket_excludes_trash_directory(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket("C1", title="Hidden in trash")
    store.create(ticket)
    store.delete("C1")

    with pytest.raises(TicketNotFoundError):
        store.get("C1")


def test_soft_delete_preserves_file_content(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    ticket = _make_ticket(
        "C1",
        title="Preserve content",
        description="Original description.",
        fix="Original fix.",
        tags=["alpha", "beta"],
    )
    store.create(ticket)
    original_content = ticket_path(store.base_dir, ticket).read_text(encoding="utf-8")

    trash_path = store.move_to_trash("C1")

    assert trash_path.read_text(encoding="utf-8") == original_content


def test_list_supports_sort_by_severity(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    store.create(_make_ticket("C1", title="Medium priority", severity=Severity.MEDIUM))
    store.create(_make_ticket("C2", title="Critical priority", severity=Severity.CRITICAL))
    store.create(_make_ticket("C3", title="Low priority", severity=Severity.LOW))

    results = store.list(sort_by="severity")

    assert [ticket.id for ticket in results] == ["C2", "C1", "C3"]


def test_list_supports_descending_created_at_sort(tmp_path: Path) -> None:
    store = TicketStore(tmp_path / "tickets")
    older = _make_ticket("C1", title="Older")
    newer = _make_ticket("C2", title="Newer")
    older_timestamp = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)
    newer_timestamp = datetime(2026, 3, 16, 11, 0, 0, tzinfo=UTC)
    older = older.model_copy(update={"created_at": older_timestamp, "updated_at": older_timestamp})
    newer = newer.model_copy(update={"created_at": newer_timestamp, "updated_at": newer_timestamp})
    store.create(older)
    store.create(newer)

    results = store.list(sort_by="-created_at")

    assert [ticket.id for ticket in results] == ["C2", "C1"]
