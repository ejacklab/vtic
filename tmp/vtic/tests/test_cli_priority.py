"""Tests for priority CLI commands."""

import pytest
from typer.testing import CliRunner
from vtic.cli.main import app

runner = CliRunner()


class TestPriorityCommand:
    def test_priority_command_help(self):
        result = runner.invoke(app, ["priority", "--help"])
        assert result.exit_code == 0


class TestListSortPriority:
    def test_list_sort_priority_option(self):
        result = runner.invoke(app, ["list", "--sort", "priority", "--help"])
        assert result.exit_code == 0


class TestUpdatePriorityFields:
    def test_update_urgency_option(self):
        result = runner.invoke(app, ["update", "--help"])
        assert "--urgency" in result.stdout
    
    def test_update_impact_option(self):
        result = runner.invoke(app, ["update", "--help"])
        assert "--impact" in result.stdout
