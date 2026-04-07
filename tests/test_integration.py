from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vtic.cli.main import app
from vtic.errors import TicketNotFoundError
from vtic.storage import TicketStore


runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"VTIC_TICKETS_DIR": str((tmp_path / "tickets").resolve())}


def test_full_lifecycle(tmp_path: Path) -> None:
    tickets_dir = tmp_path / "tickets"

    init_result = runner.invoke(app, ["init", "--dir", str(tickets_dir)], env=_env(tmp_path))
    assert init_result.exit_code == 0
    assert tickets_dir.exists()

    create_result = runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--category",
            "security",
            "--severity",
            "critical",
            "--title",
            "CORS wildcard in production",
            "--description",
            "All FastAPI services use allow_origins=['*'].",
            "--file",
            "backend/api-gateway/main.py:27-32",
            "--tags",
            "cors,security,fastapi",
        ],
        env=_env(tmp_path),
    )
    assert create_result.exit_code == 0
    assert "S1" in create_result.output

    second_create_result = runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--title",
            "Shared auth helpers cleanup",
            "--description",
            "Helper logic is duplicated across services.",
        ],
        env=_env(tmp_path),
    )
    assert second_create_result.exit_code == 0

    third_create_result = runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--title",
            "Document deployment checklist",
            "--description",
            "The staging deployment notes are incomplete.",
        ],
        env=_env(tmp_path),
    )
    assert third_create_result.exit_code == 0

    get_result = runner.invoke(app, ["get", "S1"], env=_env(tmp_path))
    assert get_result.exit_code == 0
    assert "CORS wildcard in production" in get_result.output

    search_result = runner.invoke(app, ["search", "cors"], env=_env(tmp_path))
    assert search_result.exit_code == 0
    assert "S1" in search_result.output

    update_result = runner.invoke(app, ["update", "--id", "S1", "--status", "fixed"], env=_env(tmp_path))
    assert update_result.exit_code == 0
    assert "fixed" in update_result.output

    list_result = runner.invoke(app, ["list", "--status", "fixed"], env=_env(tmp_path))
    assert list_result.exit_code == 0
    assert "S1" in list_result.output

    delete_result = runner.invoke(app, ["delete", "--id", "S1", "--yes"], env=_env(tmp_path))
    assert delete_result.exit_code == 0
    assert "Deleted (moved to trash)" in delete_result.output
    store = TicketStore(tickets_dir)
    with pytest.raises(TicketNotFoundError):
        store.get("S1")
    assert [ticket.id for ticket in store.list()] == ["C1", "C2"]


def test_full_lifecycle_with_search_update(tmp_path: Path) -> None:
    """Extended lifecycle: create, search, update, verify search changed, list, delete."""
    tickets_dir = tmp_path / "tickets"

    # Create tickets
    runner.invoke(app, ["init", "--dir", str(tickets_dir)], env=_env(tmp_path))
    runner.invoke(
        app,
        ["create", "--repo", "acme/platform", "--title", "Auth middleware refactor"],
        env=_env(tmp_path),
    )
    runner.invoke(
        app,
        ["create", "--repo", "acme/platform", "--title", "Database query optimization"],
        env=_env(tmp_path),
    )

    # Search for "auth" - should find C1
    result = runner.invoke(app, ["search", "auth", "--format", "json"], env=_env(tmp_path))
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total"] == 1
    assert payload["results"][0]["id"] == "C1"

    # Update C2 title to include "auth"
    runner.invoke(
        app,
        ["update", "--id", "C2", "--title", "Auth database connection pooling"],
        env=_env(tmp_path),
    )

    # Search for "auth" again - should find both now
    result = runner.invoke(app, ["search", "auth", "--format", "json"], env=_env(tmp_path))
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total"] == 2

    # List with status filter
    result = runner.invoke(app, ["list", "--status", "open", "--format", "json"], env=_env(tmp_path))
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload) == 2

    # Delete C1
    runner.invoke(app, ["delete", "--id", "C1", "--yes", "--force"], env=_env(tmp_path))

    # Verify only C2 remains
    store = TicketStore(tickets_dir)
    assert [t.id for t in store.list()] == ["C2"]


def test_concurrent_create_then_search(tmp_path: Path) -> None:
    """Create multiple tickets then search to verify all are indexed."""
    tickets_dir = tmp_path / "tickets"
    runner.invoke(app, ["init", "--dir", str(tickets_dir)], env=_env(tmp_path))

    # Create 5 tickets
    for i in range(5):
        runner.invoke(
            app,
            ["create", "--repo", "acme/platform", "--title", f"Ticket number {i}"],
            env=_env(tmp_path),
        )

    # List all
    result = runner.invoke(app, ["list", "--format", "json"], env=_env(tmp_path))
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload) == 5
    assert [t["id"] for t in payload] == ["C1", "C2", "C3", "C4", "C5"]

    # Search for "ticket"
    result = runner.invoke(app, ["search", "ticket", "--format", "json"], env=_env(tmp_path))
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total"] == 5

    # Search for specific ticket number
    result = runner.invoke(app, ["search", "number 3", "--format", "json"], env=_env(tmp_path))
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total"] >= 1
    # "number 3" should rank C3 highly (exact match for "3")
    result_ids = [r["id"] for r in payload["results"]]
    assert "C3" in result_ids
