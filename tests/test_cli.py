from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from vtic.cli.main import app
from vtic.storage import TicketStore

runner = CliRunner()


def _make_store(tmp_path: Path) -> TicketStore:
    return TicketStore(tmp_path / "tickets")


def _env(tmp_path: Path) -> dict[str, str]:
    return {"VTIC_TICKETS_DIR": str((tmp_path / "tickets").resolve())}


def test_create_ticket(tmp_path: Path) -> None:
    result = runner.invoke(
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
            "CORS Wildcard in Production",
            "--description",
            "All FastAPI services use allow_origins=['*'].",
            "--file",
            "backend/api-gateway/main.py:27-32",
            "--tags",
            "cors,security,fastapi",
        ],
        env=_env(tmp_path),
    )

    assert result.exit_code == 0
    ticket_path = (
        tmp_path
        / "tickets"
        / "ejacklab"
        / "open-dsearch"
        / "security"
        / "S1-cors-wildcard-in-production.md"
    )
    assert ticket_path.exists()


def test_init_command(tmp_path: Path) -> None:
    tickets_dir = tmp_path / "initialized-tickets"

    result = runner.invoke(app, ["init", "--dir", str(tickets_dir)], env=_env(tmp_path))

    assert result.exit_code == 0
    assert tickets_dir.exists()
    assert tickets_dir.is_dir()


def test_create_command_all_flags(tmp_path: Path) -> None:
    result = runner.invoke(
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
            "CORS Wildcard in Production",
            "--description",
            "All FastAPI services use allow_origins=['*'].",
            "--fix",
            "Restrict allowed origins to trusted domains.",
            "--file",
            "backend/api-gateway/main.py:27-32",
            "--tags",
            "cors,security,fastapi",
        ],
        env=_env(tmp_path),
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "tickets"
        / "ejacklab"
        / "open-dsearch"
        / "security"
        / "S1-cors-wildcard-in-production.md"
    ).exists()
    ticket = _make_store(tmp_path).get("S1")
    assert ticket.fix == "Restrict allowed origins to trusted domains."


def test_create_command_supports_owner_and_status(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--owner",
            "custom-owner",
            "--status",
            "blocked",
            "--title",
            "Created with owner and status",
        ],
        env=_env(tmp_path),
    )

    assert result.exit_code == 0
    ticket = _make_store(tmp_path).get("C1")
    assert ticket.owner == "custom-owner"
    assert ticket.status.value == "blocked"


def test_create_missing_required_field_raises(tmp_path: Path) -> None:
    result = runner.invoke(app, ["create", "--title", "Missing repo"], env=_env(tmp_path))

    assert result.exit_code != 0


def test_create_invalid_repo_returns_clean_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["create", "--repo", "nocolon", "--title", "Invalid repo"],
        env=_env(tmp_path),
    )

    assert result.exit_code == 1
    assert "Invalid repo format: nocolon. Expected: 'owner/repo'" in result.output
    assert "Traceback" not in result.output


def test_get_ticket(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--title", "Duplicated auth helpers"],
        env=_env(tmp_path),
    )

    result = runner.invoke(app, ["get", "c1"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "C1" in result.output
    assert "Duplicated auth helpers" in result.output


def test_list_tickets(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "First ticket"], env=_env(tmp_path))
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--category", "security", "--title", "Second ticket"],
        env=_env(tmp_path),
    )

    result = runner.invoke(app, ["list"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "First ticket" in result.output
    assert "Second ticket" in result.output


def test_list_with_filters(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Code quality ticket"], env=_env(tmp_path))
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--category", "security", "--title", "Security ticket"],
        env=_env(tmp_path),
    )

    result = runner.invoke(app, ["list", "--category", "security"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "Security ticket" in result.output
    assert "Code quality ticket" not in result.output


def test_list_with_owner_tags_and_date_filters(tmp_path: Path) -> None:
    runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--owner",
            "smoke01",
            "--tags",
            "auth,api",
            "--title",
            "Owned ticket",
        ],
        env=_env(tmp_path),
    )
    runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--owner",
            "alex",
            "--tags",
            "auth,api",
            "--title",
            "Wrong owner",
        ],
        env=_env(tmp_path),
    )

    result = runner.invoke(
        app,
        [
            "list",
            "--owner",
            "smoke01",
            "--tags",
            "auth,api",
            "--created-after",
            "2000-01-01T00:00:00Z",
            "--updated-before",
            "2100-01-01T00:00:00Z",
            "--format",
            "json",
        ],
        env=_env(tmp_path),
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert [ticket["id"] for ticket in payload] == ["C1"]


def test_get_ticket_json_format(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--title", "JSON ticket"],
        env=_env(tmp_path),
    )

    result = runner.invoke(app, ["get", "C1", "--format", "json"], env=_env(tmp_path))

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["id"] == "C1"
    assert payload["title"] == "JSON ticket"


def test_list_tickets_json_format_and_sort(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--severity", "low", "--title", "Low priority"],
        env=_env(tmp_path),
    )
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--severity", "critical", "--title", "Critical priority"],
        env=_env(tmp_path),
    )

    result = runner.invoke(app, ["list", "--sort", "severity", "--format", "json"], env=_env(tmp_path))

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert [ticket["id"] for ticket in payload] == ["C2", "C1"]


def test_update_ticket(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Needs fix"], env=_env(tmp_path))

    result = runner.invoke(app, ["update", "--id", "C1", "--status", "fixed"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "fixed" in result.output
    ticket = _make_store(tmp_path).get("C1")
    assert ticket.status.value == "fixed"


def test_update_ticket_all_new_flags(tmp_path: Path) -> None:
    runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--title",
            "Original title",
            "--description",
            "Original description",
        ],
        env=_env(tmp_path),
    )

    result = runner.invoke(
        app,
        [
            "update",
            "--id",
            "C1",
            "--status",
            "in_progress",
            "--severity",
            "high",
            "--fix",
            "Apply the shared abstraction.",
            "--owner",
            "smoke01",
            "--category",
            "security",
            "--file",
            "src/app.py:10-20",
            "--tags",
            "auth,security",
            "--title",
            "Updated title",
            "--description",
            "Updated description",
        ],
        env=_env(tmp_path),
    )

    assert result.exit_code == 0
    ticket = _make_store(tmp_path).get("C1")
    assert ticket.status.value == "in_progress"
    assert ticket.severity.value == "high"
    assert ticket.fix == "Apply the shared abstraction."
    assert ticket.owner == "smoke01"
    assert ticket.category.value == "security"
    assert ticket.file == "src/app.py:10-20"
    assert ticket.tags == ["auth", "security"]
    assert ticket.title == "Updated title"
    assert ticket.description == "Updated description"


def test_update_invalid_category_returns_clean_error(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Needs category"], env=_env(tmp_path))

    result = runner.invoke(app, ["update", "--id", "C1", "--category", "invalid"], env=_env(tmp_path))

    assert result.exit_code == 1
    assert "'invalid' is not a valid Category" in result.output
    assert "Traceback" not in result.output


def test_create_invalid_file_returns_clean_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--title",
            "Bad file reference",
            "--file",
            ":12",
        ],
        env=_env(tmp_path),
    )

    assert result.exit_code == 1
    assert "file" in result.output.lower()
    assert "Traceback" not in result.output


def test_create_invalid_tags_returns_clean_error(tmp_path: Path) -> None:
    tags = ",".join(f"tag{i}" for i in range(51))
    result = runner.invoke(
        app,
        [
            "create",
            "--repo",
            "ejacklab/open-dsearch",
            "--title",
            "Too many tags",
            "--tags",
            tags,
        ],
        env=_env(tmp_path),
    )

    assert result.exit_code == 1
    assert "Cannot have more than 50 tags" in result.output
    assert "Traceback" not in result.output


def test_delete_ticket(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Delete me"], env=_env(tmp_path))

    result = runner.invoke(app, ["delete", "--id", "C1", "--yes", "--force"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "Permanently deleted" in result.output
    assert not any((tmp_path / "tickets").rglob("*.md"))


def test_delete_ticket_soft_delete_moves_to_trash(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Trash me"], env=_env(tmp_path))

    result = runner.invoke(app, ["delete", "--id", "C1", "--yes"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "Deleted (moved to trash)" in result.output
    assert not (_make_store(tmp_path).base_dir / "ejacklab" / "open-dsearch" / "code_quality" / "C1-trash-me.md").exists()
    assert (_make_store(tmp_path).base_dir / ".trash" / "ejacklab" / "open-dsearch" / "code_quality" / "C1-trash-me.md").exists()


def test_get_nonexistent_ticket(tmp_path: Path) -> None:
    result = runner.invoke(app, ["get", "S99"], env=_env(tmp_path))

    assert result.exit_code == 1
    assert "Ticket S99 not found" in result.output


def test_delete_requires_confirmation(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Keep me"], env=_env(tmp_path))

    result = runner.invoke(app, ["delete", "--id", "C1"], input="n\n", env=_env(tmp_path))

    assert result.exit_code == 0
    assert "Deletion cancelled" in result.output
    assert _make_store(tmp_path).get("C1").id == "C1"


def test_delete_yes_skips_confirmation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Skip prompt"], env=_env(tmp_path))

    def _unexpected_confirm(*args: object, **kwargs: object) -> bool:
        raise AssertionError("typer.confirm should not be called when --yes is set")

    monkeypatch.setattr(typer, "confirm", _unexpected_confirm)

    result = runner.invoke(app, ["delete", "--id", "C1", "--yes"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "Delete ticket C1?" not in result.output
    assert "Deleted (moved to trash)" in result.output
    assert (_make_store(tmp_path).base_dir / ".trash" / "ejacklab" / "open-dsearch" / "code_quality" / "C1-skip-prompt.md").exists()


def test_list_empty_outputs_empty_table(tmp_path: Path) -> None:
    result = runner.invoke(app, ["list"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "Tickets" in result.output


def test_search_no_results_prints_empty_state(tmp_path: Path) -> None:
    result = runner.invoke(app, ["search", "missing-term"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "No results found." in result.output


def test_restore_ticket_from_trash(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Restore me"], env=_env(tmp_path))
    runner.invoke(app, ["delete", "--id", "C1", "--yes"], env=_env(tmp_path))

    result = runner.invoke(app, ["restore", "--id", "C1"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "Restored ticket:" in result.output
    assert _make_store(tmp_path).get("C1").title == "Restore me"


def test_list_invalid_sort_returns_clean_error(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Sortable"], env=_env(tmp_path))

    result = runner.invoke(app, ["list", "--sort", "invalid"], env=_env(tmp_path))

    assert result.exit_code == 1
    assert "Unsupported sort field: invalid" in result.output
    assert "Traceback" not in result.output


def test_search_json_format(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--title", "Searchable auth helper"],
        env=_env(tmp_path),
    )

    result = runner.invoke(app, ["search", "auth", "--format", "json"], env=_env(tmp_path))

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total"] == 1
    assert payload["results"][0]["id"] == "C1"


def test_reindex_command(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--title", "Indexed ticket"],
        env=_env(tmp_path),
    )
    result = runner.invoke(app, ["reindex"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "Rebuilt BM25 index" in result.output
    assert (tmp_path / "tickets" / ".vtic-search-index.json").exists()


def test_serve_uses_config_defaults_when_host_and_port_not_passed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "vtic.toml"
    config_path.write_text("[server]\nhost = \"127.0.0.9\"\nport = 9123\n", encoding="utf-8")
    called: dict[str, object] = {}

    def fake_run(app_instance, *, host: str, port: int) -> None:
        called["host"] = host
        called["port"] = port

    monkeypatch.setattr("uvicorn.run", fake_run)

    result = runner.invoke(
        app,
        ["serve"],
        env={**_env(tmp_path), "VTIC_CONFIG": str(config_path)},
    )

    assert result.exit_code == 0
    assert called == {"host": "127.0.0.9", "port": 9123}


def test_serve_rejects_out_of_range_port(tmp_path: Path) -> None:
    result = runner.invoke(app, ["serve", "--port", "70000"], env=_env(tmp_path))

    assert result.exit_code != 0
    assert "Invalid value for '--port'" in result.output


def test_search_with_filters_cli(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--category", "security", "--title", "Security ticket"],
        env=_env(tmp_path),
    )
    runner.invoke(
        app,
        ["create", "--repo", "ejacklab/open-dsearch", "--title", "Code quality ticket"],
        env=_env(tmp_path),
    )

    # Search with category filter
    result = runner.invoke(
        app,
        ["search", "ticket", "--category", "security", "--format", "json"],
        env=_env(tmp_path),
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total"] == 1
    assert payload["results"][0]["id"] == "S1"

    # Search with severity filter
    result = runner.invoke(
        app,
        ["search", "ticket", "--severity", "high", "--format", "json"],
        env=_env(tmp_path),
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    # Only S1 has critical severity, not high
    assert payload["total"] == 0

    # Search with repo filter
    result = runner.invoke(
        app,
        ["search", "ticket", "--repo", "ejacklab/open-dsearch", "--format", "json"],
        env=_env(tmp_path),
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total"] == 2

    # Search with status filter
    result = runner.invoke(
        app,
        ["search", "ticket", "--status", "open", "--format", "json"],
        env=_env(tmp_path),
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total"] == 2
