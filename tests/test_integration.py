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
    assert "SEC-1" in create_result.output

    second_create_result = runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--category",
            "code_quality",
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
            "--category",
            "code_quality",
            "--title",
            "Document deployment checklist",
            "--description",
            "The staging deployment notes are incomplete.",
        ],
        env=_env(tmp_path),
    )
    assert third_create_result.exit_code == 0

    get_result = runner.invoke(app, ["get", "SEC-1"], env=_env(tmp_path))
    assert get_result.exit_code == 0
    assert "CORS wildcard in production" in get_result.output

    search_result = runner.invoke(app, ["search", "cors"], env=_env(tmp_path))
    assert search_result.exit_code == 0
    assert "SEC-1" in search_result.output

    update_result = runner.invoke(app, ["update", "--id", "SEC-1", "--status", "done"], env=_env(tmp_path))
    assert update_result.exit_code == 0
    assert "done" in update_result.output

    list_result = runner.invoke(app, ["list", "--status", "done"], env=_env(tmp_path))
    assert list_result.exit_code == 0
    assert "SEC-1" in list_result.output

    delete_result = runner.invoke(app, ["delete", "--id", "SEC-1", "--yes"], env=_env(tmp_path))
    assert delete_result.exit_code == 0
    assert "Deleted (moved to trash)" in delete_result.output
    store = TicketStore(tickets_dir)
    with pytest.raises(TicketNotFoundError):
        store.get("SEC-1")
    assert [ticket.id for ticket in store.list()] == ["CODE-1", "CODE-2"]


def test_full_lifecycle_with_search_update(tmp_path: Path) -> None:
    """Extended lifecycle: create, search, update, verify search changed, list, delete."""
    tickets_dir = tmp_path / "tickets"

    # Create tickets
    runner.invoke(app, ["init", "--dir", str(tickets_dir)], env=_env(tmp_path))
    runner.invoke(
        app,
        ["create", "--repo", "acme/platform", "--category", "code_quality", "--title", "Auth middleware refactor"],
        env=_env(tmp_path),
    )
    runner.invoke(
        app,
        ["create", "--repo", "acme/platform", "--category", "code_quality", "--title", "Database query optimization"],
        env=_env(tmp_path),
    )

    # Search for "auth" - should find CODE-1
    result = runner.invoke(app, ["search", "auth", "--format", "json"], env=_env(tmp_path))
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total"] == 1
    assert payload["results"][0]["id"] == "CODE-1"

    # Update CODE-2 title to include "auth"
    runner.invoke(
        app,
        ["update", "--id", "CODE-2", "--title", "Auth database connection pooling"],
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

    # Delete CODE-1
    runner.invoke(app, ["delete", "--id", "CODE-1", "--yes", "--force"], env=_env(tmp_path))

    # Verify only CODE-2 remains
    store = TicketStore(tickets_dir)
    assert [t.id for t in store.list()] == ["CODE-2"]


def test_concurrent_create_then_search(tmp_path: Path) -> None:
    """Create multiple tickets then search to verify all are indexed."""
    tickets_dir = tmp_path / "tickets"
    runner.invoke(app, ["init", "--dir", str(tickets_dir)], env=_env(tmp_path))

    # Create 5 tickets
    for i in range(5):
        runner.invoke(
            app,
            ["create", "--repo", "acme/platform", "--category", "code_quality", "--title", f"Ticket number {i}"],
            env=_env(tmp_path),
        )

    # List all
    result = runner.invoke(app, ["list", "--format", "json"], env=_env(tmp_path))
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload) == 5
    assert [t["id"] for t in payload] == ["CODE-1", "CODE-2", "CODE-3", "CODE-4", "CODE-5"]

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
    # "number 3" should rank CODE-3 highly (exact match for "3")
    result_ids = [r["id"] for r in payload["results"]]
    assert "CODE-3" in result_ids


def test_create_search_update_verify_search(tmp_path: Path) -> None:
    tickets_dir = tmp_path / "tickets"
    runner.invoke(app, ["init", "--dir", str(tickets_dir)], env=_env(tmp_path))

    create_result = runner.invoke(
        app,
        ["create", "--dir", str(tickets_dir), "--repo", "acme/platform", "--category", "code_quality", "--title", "Auth flow regression"],
        env=_env(tmp_path),
    )
    assert create_result.exit_code == 0

    first_search = runner.invoke(
        app,
        ["search", "auth", "--dir", str(tickets_dir), "--format", "json"],
        env=_env(tmp_path),
    )
    assert first_search.exit_code == 0
    first_payload = json.loads(first_search.output)
    assert first_payload["total"] == 1
    assert first_payload["results"][0]["id"] == "CODE-1"

    update_result = runner.invoke(
        app,
        ["update", "--dir", str(tickets_dir), "--id", "CODE-1", "--title", "Session flow regression"],
        env=_env(tmp_path),
    )
    assert update_result.exit_code == 0

    second_search = runner.invoke(
        app,
        ["search", "auth", "--dir", str(tickets_dir), "--format", "json"],
        env=_env(tmp_path),
    )
    assert second_search.exit_code == 0
    second_payload = json.loads(second_search.output)
    assert second_payload["total"] == 0