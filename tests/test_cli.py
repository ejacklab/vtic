from __future__ import annotations

from pathlib import Path

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


def test_create_missing_required_field_raises(tmp_path: Path) -> None:
    result = runner.invoke(app, ["create", "--title", "Missing repo"], env=_env(tmp_path))

    assert result.exit_code != 0


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


def test_update_ticket(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Needs fix"], env=_env(tmp_path))

    result = runner.invoke(app, ["update", "--id", "C1", "--status", "fixed"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "fixed" in result.output
    ticket = _make_store(tmp_path).get("C1")
    assert ticket.status.value == "fixed"


def test_delete_ticket(tmp_path: Path) -> None:
    runner.invoke(app, ["create", "--repo", "ejacklab/open-dsearch", "--title", "Delete me"], env=_env(tmp_path))

    result = runner.invoke(app, ["delete", "--id", "C1", "--yes"], env=_env(tmp_path))

    assert result.exit_code == 0
    assert "Deleted ticket" in result.output
    assert not any((tmp_path / "tickets").rglob("*.md"))


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
