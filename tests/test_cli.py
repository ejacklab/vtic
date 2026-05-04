"""Tests for the vtic CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vtic.cli.main import app

runner = CliRunner()


@pytest.fixture()
def tickets_dir(tmp_path: Path) -> Path:
    """Provide an isolated tickets directory for each test."""
    d = tmp_path / "tickets"
    d.mkdir()
    return d


def _dir_args(tickets_dir: Path) -> list[str]:
    return ["--dir", str(tickets_dir)]


class TestInit:
    def test_init_creates_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "fresh"
        result = runner.invoke(app, ["init", "--dir", str(target)])
        assert result.exit_code == 0
        assert target.exists()
        assert "Initialized" in result.output

    def test_init_idempotent(self, tickets_dir: Path) -> None:
        runner.invoke(app, ["init", *_dir_args(tickets_dir)])
        result = runner.invoke(app, ["init", *_dir_args(tickets_dir)])
        assert result.exit_code == 0


class TestCreate:
    def _create_ticket(self, tickets_dir: Path, **overrides: str) -> str:
        """Create a ticket via CLI and return the output."""
        args = [
            *_dir_args(tickets_dir),
            "--repo", overrides.get("repo", "owner/repo"),
            "--title", overrides.get("title", "Test ticket"),
            "--category", overrides.get("category", "code_quality"),
        ]
        if "severity" in overrides:
            args += ["--severity", overrides["severity"]]
        if "description" in overrides:
            args += ["--description", overrides["description"]]
        if "file" in overrides:
            args += ["--file", overrides["file"]]
        result = runner.invoke(app, ["create", *args])
        return result

    def test_create_basic(self, tickets_dir: Path) -> None:
        result = self._create_ticket(tickets_dir)
        assert result.exit_code == 0
        assert "Created Ticket" in result.output
        assert "CODE-1" in result.output
        assert "Test ticket" in result.output

    def test_create_with_category_security(self, tickets_dir: Path) -> None:
        result = self._create_ticket(
            tickets_dir,
            category="security",
            severity="critical",
            title="SQL injection",
        )
        assert result.exit_code == 0
        assert "SEC-1" in result.output
        assert "security" in result.output

    def test_create_auto_increments_id(self, tickets_dir: Path) -> None:
        self._create_ticket(tickets_dir, title="First")
        result = self._create_ticket(tickets_dir, title="Second")
        assert result.exit_code == 0
        assert "CODE-2" in result.output

    def test_create_with_file_reference(self, tickets_dir: Path) -> None:
        result = self._create_ticket(
            tickets_dir,
            title="File bug",
            file="src/app.py:42",
        )
        assert result.exit_code == 0
        assert "src/app.py:42" in result.output

    def test_create_with_description(self, tickets_dir: Path) -> None:
        result = self._create_ticket(
            tickets_dir,
            title="Described",
            description="Detailed description here",
        )
        assert result.exit_code == 0
        assert "Detailed description here" in result.output

    def test_create_with_all_flags(self, tickets_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "create",
                *_dir_args(tickets_dir),
                "--repo", "acme/platform",
                "--title", "Auth middleware issue",
                "--category", "auth",
                "--severity", "high",
                "--description", "Authentication flow breaks on refresh.",
                "--fix", "Refresh the token before retrying.",
                "--file", "src/auth.py:12-20",
                "--tags", "auth,backend,token",
            ],
        )

        assert result.exit_code == 0
        assert "Auth middleware issue" in result.output
        assert "acme/platform" in result.output
        assert "auth" in result.output
        assert "high" in result.output
        assert "Authentication flow breaks on refresh." in result.output
        assert "Refresh the token before retrying." in result.output
        assert "src/auth.py:12-20" in result.output
        assert "auth, backend, token" in result.output

    def test_create_with_due_date(self, tickets_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "create",
                *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Due date ticket",
                "--due-date", "2026-12-31",
            ],
        )

        assert result.exit_code == 0
        assert "Due Date" in result.output
        assert "2026-12-31" in result.output

    def test_create_without_due_date(self, tickets_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "create",
                *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "No due date",
            ],
        )

        assert result.exit_code == 0
        assert "CODE-1" in result.output

    def test_create_rejects_missing_repo(self, tickets_dir: Path) -> None:
        args = [*_dir_args(tickets_dir), "--title", "No repo"]
        result = runner.invoke(app, ["create", *args])
        assert result.exit_code != 0

    def test_create_missing_title_raises(self, tickets_dir: Path) -> None:
        result = runner.invoke(
            app,
            ["create", *_dir_args(tickets_dir), "--repo", "owner/repo"],
        )
        assert result.exit_code != 0

    def test_create_rejects_bad_repo_format(self, tickets_dir: Path) -> None:
        result = self._create_ticket(tickets_dir, repo="badrepo")
        assert result.exit_code != 0

    def test_create_creates_directory_structure(self, tickets_dir: Path) -> None:
        self._create_ticket(tickets_dir, repo="myorg/myrepo", title="Structure test")
        expected_dir = tickets_dir / "myorg" / "myrepo" / "code_quality"
        assert expected_dir.exists()
        md_files = list(expected_dir.glob("*.md"))
        assert len(md_files) == 1


class TestGet:
    def test_get_existing_ticket(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--title", "Get me",
                "--severity", "high",
            ],
            input=None,
        )
        # Create first, then get
        create_result = runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Get me",
                "--severity", "high",
            ],
        )
        assert create_result.exit_code == 0

        result = runner.invoke(app, ["get", "CODE-1", *_dir_args(tickets_dir)])
        assert result.exit_code == 0
        assert "Get me" in result.output
        assert "high" in result.output

    def test_get_not_found(self, tickets_dir: Path) -> None:
        result = runner.invoke(app, ["get", "X99", *_dir_args(tickets_dir)])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "X99" in result.output

    def test_get_json_format(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "JSON ticket",
            ],
        )
        result = runner.invoke(
            app, ["get", "CODE-1", *_dir_args(tickets_dir), "--format", "json"]
        )
        assert result.exit_code == 0
        # Should be valid JSON
        import json
        data = json.loads(result.output)
        assert data["title"] == "JSON ticket"

    def test_get_security_ticket(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "security",
                "--title", "CORS issue",
            ],
        )
        result = runner.invoke(app, ["get", "SEC-1", *_dir_args(tickets_dir)])
        assert result.exit_code == 0
        assert "SEC-1" in result.output
        assert "CORS issue" in result.output


class TestList:
    def test_list_empty(self, tickets_dir: Path) -> None:
        result = runner.invoke(app, ["list", *_dir_args(tickets_dir)])
        assert result.exit_code == 0

    def test_list_shows_tickets(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "First ticket",
            ],
        )
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Second ticket",
            ],
        )
        result = runner.invoke(app, ["list", *_dir_args(tickets_dir)])
        assert result.exit_code == 0
        assert "CODE-1" in result.output
        assert "CODE-2" in result.output

    def test_list_filter_by_repo(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "orgA/repo1",
                "--category", "code_quality",
                "--title", "Ticket A",
            ],
        )
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "orgB/repo2",
                "--category", "code_quality",
                "--title", "Ticket B",
            ],
        )
        result = runner.invoke(
            app, ["list", *_dir_args(tickets_dir), "--repo", "orga/repo1"]
        )
        assert result.exit_code == 0
        assert "CODE-1" in result.output
        assert "CODE-2" not in result.output

    def test_list_filter_by_category(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "security",
                "--title", "Sec issue",
            ],
        )
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "testing",
                "--title", "Test issue",
            ],
        )
        result = runner.invoke(
            app, ["list", *_dir_args(tickets_dir), "--category", "security"]
        )
        assert result.exit_code == 0
        assert "SEC-1" in result.output
        assert "T1" not in result.output

    def test_list_filter_by_severity(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--severity", "critical",
                "--title", "Critical issue",
            ],
        )
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--severity", "low",
                "--title", "Low issue",
            ],
        )
        result = runner.invoke(
            app, ["list", *_dir_args(tickets_dir), "--severity", "critical"]
        )
        assert result.exit_code == 0
        assert "CODE-1" in result.output
        assert "CODE-2" not in result.output

    def test_list_filter_by_status(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Open ticket",
            ],
        )
        result = runner.invoke(
            app, ["list", *_dir_args(tickets_dir), "--status", "open"]
        )
        assert result.exit_code == 0
        assert "CODE-1" in result.output

        result_closed = runner.invoke(
            app, ["list", *_dir_args(tickets_dir), "--status", "done"]
        )
        assert result_closed.exit_code == 0
        assert "CODE-1" not in result_closed.output

    def test_list_json_format(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "JSON list",
            ],
        )
        result = runner.invoke(
            app, ["list", *_dir_args(tickets_dir), "--format", "json"]
        )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "JSON list"

    def test_list_with_multiple_filters(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "security",
                "--severity", "critical",
                "--title", "Critical security issue",
            ],
        )
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "security",
                "--severity", "low",
                "--title", "Low security issue",
            ],
        )
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "testing",
                "--severity", "critical",
                "--title", "Critical testing issue",
            ],
        )

        result = runner.invoke(
            app,
            [
                "list", *_dir_args(tickets_dir),
                "--category", "security",
                "--severity", "critical",
            ],
        )
        assert result.exit_code == 0
        assert "Critical security issue" in result.output
        assert "Low security issue" not in result.output
        assert "Critical testing issue" not in result.output

    def test_list_filter_by_due_date(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Due Jan",
                "--due-date", "2026-01-15",
            ],
        )
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Due Jun",
                "--due-date", "2026-06-15",
            ],
        )

        before_result = runner.invoke(
            app, ["list", *_dir_args(tickets_dir), "--due-before", "2026-06-01"]
        )
        assert before_result.exit_code == 0
        assert "CODE-1" in before_result.output
        assert "CODE-2" not in before_result.output

        after_result = runner.invoke(
            app, ["list", *_dir_args(tickets_dir), "--due-after", "2026-06-01"]
        )
        assert after_result.exit_code == 0
        assert "CODE-1" not in after_result.output
        assert "CODE-2" in after_result.output


class TestUpdate:
    def test_update_status(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "To update",
            ],
        )
        result = runner.invoke(
            app,
            [
                "update", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--status", "active",
            ],
        )
        assert result.exit_code == 0
        assert "active" in result.output

    def test_update_severity(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Severity change",
                "--severity", "low",
            ],
        )
        result = runner.invoke(
            app,
            [
                "update", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--severity", "critical",
            ],
        )
        assert result.exit_code == 0
        assert "critical" in result.output

    def test_update_description(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Update desc",
            ],
        )
        result = runner.invoke(
            app,
            [
                "update", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--description", "New description content",
            ],
        )
        assert result.exit_code == 0
        assert "New description content" in result.output

    def test_update_not_found(self, tickets_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "update", *_dir_args(tickets_dir),
                "--id", "X99",
                "--status", "done",
            ],
        )
        assert result.exit_code != 0

    def test_update_multiple_fields(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Multi update",
            ],
        )
        result = runner.invoke(
            app,
            [
                "update", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--status", "done",
                "--severity", "critical",
                "--fix", "Applied the fix",
            ],
        )
        assert result.exit_code == 0
        assert "done" in result.output
        assert "critical" in result.output

    def test_update_title_via_cli(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Old title",
            ],
        )
        result = runner.invoke(
            app,
            [
                "update", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--title", "Updated title",
            ],
        )
        assert result.exit_code == 0
        assert "Updated title" in result.output

    def test_update_set_due_date(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Set due",
            ],
        )

        result = runner.invoke(
            app,
            [
                "update", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--due-date", "2026-07-15",
            ],
        )

        assert result.exit_code == 0
        assert "2026-07-15" in result.output

    def test_update_clear_due_date(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Clear due",
                "--due-date", "2026-05-01",
            ],
        )

        result = runner.invoke(
            app,
            [
                "update", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--due-date", "none",
            ],
        )

        assert result.exit_code == 0
        assert "Due Date" in result.output
        assert "2026-05-01" not in result.output


class TestDelete:
    def test_delete_with_yes(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "To delete",
            ],
        )
        result = runner.invoke(
            app,
            [
                "delete", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--yes",
            ],
        )
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_confirmed(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Confirm delete",
            ],
        )
        result = runner.invoke(
            app,
            [
                "delete", *_dir_args(tickets_dir),
                "--id", "CODE-1",
            ],
            input="y\n",
        )
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_cancelled(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Cancel delete",
            ],
        )
        result = runner.invoke(
            app,
            [
                "delete", *_dir_args(tickets_dir),
                "--id", "CODE-1",
            ],
            input="n\n",
        )
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    def test_delete_not_found(self, tickets_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "delete", *_dir_args(tickets_dir),
                "--id", "X99",
                "--yes",
            ],
        )
        assert result.exit_code != 0

    def test_delete_force(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Force delete",
            ],
        )
        result = runner.invoke(
            app,
            [
                "delete", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--yes",
                "--force",
            ],
        )
        assert result.exit_code == 0
        assert "Permanently deleted" in result.output

    def test_delete_moves_to_trash_by_default(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Soft delete",
            ],
        )
        runner.invoke(
            app,
            [
                "delete", *_dir_args(tickets_dir),
                "--id", "CODE-1",
                "--yes",
            ],
        )
        # Ticket should be in trash, not gone completely
        trash_dir = tickets_dir / ".trash"
        assert trash_dir.exists()
        trash_files = list(trash_dir.rglob("*.md"))
        assert len(trash_files) == 1


class TestSearch:
    def test_search_command(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Auth middleware issue",
            ],
        )
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Database cleanup",
            ],
        )

        result = runner.invoke(app, ["search", "auth", *_dir_args(tickets_dir)])

        assert result.exit_code == 0
        assert "Auth middleware issue" in result.output
        assert "Database cleanup" not in result.output

    def test_search_json_format(self, tickets_dir: Path) -> None:
        runner.invoke(
            app,
            [
                "create", *_dir_args(tickets_dir),
                "--repo", "owner/repo",
                "--category", "code_quality",
                "--title", "Keyword auth result",
            ],
        )

        result = runner.invoke(
            app,
            ["search", "auth", *_dir_args(tickets_dir), "--format", "json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["total"] == 1
        assert payload["results"][0]["title"] == "Keyword auth result"