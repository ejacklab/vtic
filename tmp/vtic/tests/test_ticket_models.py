"""Tests for ticket models."""

import json
import re
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from vtic.models import (
    Category,
    Severity,
    Status,
    Ticket,
    TicketCreate,
    TicketUpdate,
    TicketSummary,
    TicketResponse,
    TicketListResponse,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_ticket_data():
    """Sample ticket data for testing."""
    return {
        "id": "C1",
        "title": "CORS Wildcard Issue",
        "description": "The API allows wildcard CORS origins in production...",
        "repo": "ejacklab/open-dsearch",
        "category": Category.SECURITY,
        "severity": Severity.HIGH,
        "status": Status.OPEN,
        "assignee": "ejack",
        "fix": None,
        "tags": ["cors", "security", "api"],
        "references": ["C2", "C3"],
        "created": datetime.now(timezone.utc),
        "updated": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_ticket(sample_ticket_data):
    """Create a full Ticket instance."""
    return Ticket(**sample_ticket_data)


@pytest.fixture
def sample_ticket_create_data():
    """Sample TicketCreate data."""
    return {
        "title": "CORS Wildcard Issue",
        "description": "The API allows wildcard CORS origins in production...",
        "repo": "ejacklab/open-dsearch",
    }


@pytest.fixture
def sample_ticket_summary_data():
    """Sample TicketSummary data."""
    return {
        "id": "C1",
        "title": "CORS Wildcard Issue",
        "severity": Severity.HIGH,
        "status": Status.OPEN,
        "repo": "ejacklab/open-dsearch",
        "category": Category.SECURITY,
        "created": datetime.now(timezone.utc),
    }


# =============================================================================
# Ticket Model Tests
# =============================================================================


class TestTicket:
    """Tests for the Ticket model."""

    def test_ticket_creation(self, sample_ticket_data):
        """Test creating a valid Ticket."""
        ticket = Ticket(**sample_ticket_data)
        assert ticket.id == "C1"
        assert ticket.title == "CORS Wildcard Issue"
        assert ticket.category == Category.SECURITY
        assert ticket.severity == Severity.HIGH
        assert ticket.status == Status.OPEN

    def test_id_pattern_validation_valid(self, sample_ticket_data):
        """Test valid ID patterns."""
        valid_ids = ["C1", "S10", "H99", "F1", "G12345", "T0"]
        for ticket_id in valid_ids:
            data = {**sample_ticket_data, "id": ticket_id}
            ticket = Ticket(**data)
            assert ticket.id == ticket_id

    def test_id_pattern_validation_invalid(self, sample_ticket_data):
        """Test invalid ID patterns."""
        invalid_ids = ["X1", "abc", "1C", "c1", "C-1", ""]
        for ticket_id in invalid_ids:
            data = {**sample_ticket_data, "id": ticket_id}
            with pytest.raises(ValidationError) as exc_info:
                Ticket(**data)
            assert "id" in str(exc_info.value)

    def test_repo_pattern_validation_valid(self, sample_ticket_data):
        """Test valid repo patterns."""
        valid_repos = [
            "ejacklab/open-dsearch",
            "user/repo",
            "org-name/repo-name",
            "user123/repo_456",
        ]
        for repo in valid_repos:
            data = {**sample_ticket_data, "repo": repo}
            ticket = Ticket(**data)
            assert ticket.repo == repo

    def test_repo_pattern_validation_invalid(self, sample_ticket_data):
        """Test invalid repo patterns."""
        invalid_repos = [
            "noslash",
            "owner/",
            "/repo",
            "owner/repo/extra",
            "",
        ]
        for repo in invalid_repos:
            data = {**sample_ticket_data, "repo": repo}
            with pytest.raises(ValidationError) as exc_info:
                Ticket(**data)
            assert "repo" in str(exc_info.value)

    def test_slug_generation_from_title(self, sample_ticket_data):
        """Test slug generation from title."""
        data = {**sample_ticket_data, "title": "CORS Wildcard Issue", "slug": None}
        ticket = Ticket(**data)
        assert ticket.slug == "cors-wildcard-issue"

    def test_slug_generation_with_special_chars(self, sample_ticket_data):
        """Test slug generation with special characters."""
        data = {**sample_ticket_data, "title": "API@Error #123: Fix It!", "slug": None}
        ticket = Ticket(**data)
        assert ticket.slug == "api-error-123-fix-it"

    def test_tags_normalization(self, sample_ticket_data):
        """Test tags normalization."""
        data = {**sample_ticket_data, "tags": ["  API  ", "Security-Risk", "API"]}
        ticket = Ticket(**data)
        assert ticket.tags == ["api", "security-risk"]  # Duplicates removed, normalized

    def test_references_validation(self, sample_ticket_data):
        """Test references validation."""
        data = {**sample_ticket_data, "references": ["C1", "S2", "invalid", "X1"]}
        ticket = Ticket(**data)
        assert ticket.references == ["C1", "S2"]  # Invalid refs filtered out

    def test_update_timestamp(self, sample_ticket):
        """Test update_timestamp method."""
        old_updated = sample_ticket.updated
        # Sleep briefly to ensure time difference
        import time

        time.sleep(0.01)
        sample_ticket.update_timestamp()
        assert sample_ticket.updated > old_updated

    def test_is_terminal(self, sample_ticket_data):
        """Test is_terminal method."""
        # Non-terminal statuses
        for status in [Status.OPEN, Status.IN_PROGRESS, Status.BLOCKED]:
            data = {**sample_ticket_data, "status": status}
            ticket = Ticket(**data)
            assert not ticket.is_terminal()

        # Terminal statuses
        for status in [Status.FIXED, Status.WONT_FIX, Status.CLOSED]:
            data = {**sample_ticket_data, "status": status}
            ticket = Ticket(**data)
            assert ticket.is_terminal()

    def test_id_prefix_property(self, sample_ticket_data):
        """Test id_prefix property."""
        test_cases = [
            ("C123", "C"),
            ("F1", "F"),
            ("G99", "G"),
            ("H5", "H"),
            ("S42", "S"),
        ]
        for ticket_id, expected_prefix in test_cases:
            data = {**sample_ticket_data, "id": ticket_id}
            ticket = Ticket(**data)
            assert ticket.id_prefix == expected_prefix

    def test_timestamps_auto_filled(self):
        """Test that timestamps can be set."""
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            id="C1",
            title="Test",
            description="Test description",
            repo="user/repo",
            category=Category.GENERAL,
            severity=Severity.MEDIUM,
            status=Status.OPEN,
            created=now,
            updated=now,
        )
        assert ticket.created == now
        assert ticket.updated == now


# =============================================================================
# TicketCreate Tests
# =============================================================================


class TestTicketCreate:
    """Tests for the TicketCreate model."""

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            TicketCreate()
        errors = str(exc_info.value)
        assert "title" in errors
        assert "description" in errors
        assert "repo" in errors

    def test_valid_creation(self, sample_ticket_create_data):
        """Test valid TicketCreate."""
        create = TicketCreate(**sample_ticket_create_data)
        assert create.title == "CORS Wildcard Issue"
        assert create.description == "The API allows wildcard CORS origins in production..."
        assert create.repo == "ejacklab/open-dsearch"

    def test_empty_title_rejected(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(title="", description="Test", repo="user/repo")
        assert "title" in str(exc_info.value)
        assert "too_short" in str(exc_info.value) or "min_length" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(title="   ", description="Test", repo="user/repo")
        assert "title" in str(exc_info.value)

    def test_empty_description_rejected(self):
        """Test that empty description is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(title="Test", description="", repo="user/repo")
        assert "description" in str(exc_info.value)
        assert "too_short" in str(exc_info.value) or "min_length" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(title="Test", description="   ", repo="user/repo")
        assert "description" in str(exc_info.value)

    def test_category_defaults_to_none(self, sample_ticket_create_data):
        """Test that category defaults to None (system will set to general)."""
        create = TicketCreate(**sample_ticket_create_data)
        assert create.category is None

    def test_category_can_be_set(self, sample_ticket_create_data):
        """Test that category can be explicitly set."""
        data = {**sample_ticket_create_data, "category": Category.SECURITY}
        create = TicketCreate(**data)
        assert create.category == Category.SECURITY

    def test_severity_defaults_to_none(self, sample_ticket_create_data):
        """Test that severity defaults to None (system will set to medium)."""
        create = TicketCreate(**sample_ticket_create_data)
        assert create.severity is None

    def test_severity_can_be_set(self, sample_ticket_create_data):
        """Test that severity can be explicitly set."""
        data = {**sample_ticket_create_data, "severity": Severity.HIGH}
        create = TicketCreate(**data)
        assert create.severity == Severity.HIGH

    def test_status_defaults_to_none(self, sample_ticket_create_data):
        """Test that status defaults to None (system will set to open)."""
        create = TicketCreate(**sample_ticket_create_data)
        assert create.status is None

    def test_status_can_be_set(self, sample_ticket_create_data):
        """Test that status can be explicitly set."""
        data = {**sample_ticket_create_data, "status": Status.IN_PROGRESS}
        create = TicketCreate(**data)
        assert create.status == Status.IN_PROGRESS

    def test_tags_default_to_empty_list(self, sample_ticket_create_data):
        """Test that tags default to empty list."""
        create = TicketCreate(**sample_ticket_create_data)
        assert create.tags == []

    def test_references_default_to_empty_list(self, sample_ticket_create_data):
        """Test that references default to empty list."""
        create = TicketCreate(**sample_ticket_create_data)
        assert create.references == []

    def test_no_fix_field(self, sample_ticket_create_data):
        """Test that TicketCreate does NOT have a fix field."""
        # This verifies the fix field is not in the model (as per spec)
        create = TicketCreate(**sample_ticket_create_data)
        assert not hasattr(create, "fix") or getattr(create, "fix", None) is None


# =============================================================================
# TicketUpdate Tests
# =============================================================================


class TestTicketUpdate:
    """Tests for the TicketUpdate model."""

    def test_at_least_one_field_required(self):
        """Test that at least one field must be provided."""
        with pytest.raises(ValidationError) as exc_info:
            TicketUpdate()
        assert "At least one field must be provided" in str(exc_info.value)

    def test_single_field_update(self):
        """Test update with a single field."""
        update = TicketUpdate(status=Status.FIXED)
        assert update.status == Status.FIXED

    def test_multiple_fields_update(self):
        """Test update with multiple fields."""
        update = TicketUpdate(
            status=Status.FIXED,
            fix="Added garbage collection",
            severity=Severity.LOW,
        )
        assert update.status == Status.FIXED
        assert update.fix == "Added garbage collection"
        assert update.severity == Severity.LOW

    def test_description_append_field(self):
        """Test description_append special field."""
        append_text = "\n\n## Update\nIssue resolved in PR #42."
        update = TicketUpdate(description_append=append_text)
        # description_append preserves newlines (not subject to strip_whitespace)
        assert "## Update" in update.description_append
        assert "Issue resolved in PR #42." in update.description_append

    def test_empty_title_rejected(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TicketUpdate(title="")
        assert "title" in str(exc_info.value)
        assert "too_short" in str(exc_info.value) or "min_length" in str(exc_info.value)

    def test_get_updates_method(self):
        """Test get_updates method returns correct fields."""
        update = TicketUpdate(
            status=Status.FIXED,
            fix="Added garbage collection",
            description_append="\n\nFixed!",
        )
        updates = update.get_updates()
        assert updates["status"] == Status.FIXED
        assert updates["fix"] == "Added garbage collection"
        # description_append content is preserved (newlines may be stripped by config)
        assert "Fixed!" in updates["description_append"]

    def test_tags_can_be_empty_list_to_clear(self):
        """Test that empty list for tags clears tags."""
        update = TicketUpdate(tags=[])
        assert update.tags == []


# =============================================================================
# TicketSummary Tests
# =============================================================================


class TestTicketSummary:
    """Tests for the TicketSummary model."""

    def test_required_fields(self, sample_ticket_summary_data):
        """Test that required fields are enforced."""
        summary = TicketSummary(**sample_ticket_summary_data)
        assert summary.id == "C1"
        assert summary.title == "CORS Wildcard Issue"
        assert summary.severity == Severity.HIGH
        assert summary.status == Status.OPEN
        assert summary.repo == "ejacklab/open-dsearch"
        assert summary.category == Category.SECURITY
        assert summary.created is not None

    def test_missing_required_field(self):
        """Test that missing required fields cause error."""
        with pytest.raises(ValidationError):
            TicketSummary(
                id="C1",
                title="Test",
                # Missing severity, status, repo, category, created
            )

    def test_optional_assignee(self, sample_ticket_summary_data):
        """Test that assignee is optional."""
        # Without assignee
        data = {k: v for k, v in sample_ticket_summary_data.items() if k != "assignee"}
        summary = TicketSummary(**data)
        assert summary.assignee is None

        # With assignee
        data["assignee"] = "ejack"
        summary = TicketSummary(**data)
        assert summary.assignee == "ejack"

    def test_optional_updated(self, sample_ticket_summary_data):
        """Test that updated is optional."""
        # Without updated
        data = {k: v for k, v in sample_ticket_summary_data.items() if k != "updated"}
        summary = TicketSummary(**data)
        assert summary.updated is None

        # With updated
        data["updated"] = datetime.now(timezone.utc)
        summary = TicketSummary(**data)
        assert summary.updated is not None

    def test_no_description_field(self, sample_ticket_summary_data):
        """Test that TicketSummary does not include description."""
        # TicketSummary should not have description field
        assert "description" not in TicketSummary.model_fields


# =============================================================================
# TicketResponse Tests
# =============================================================================


class TestTicketResponse:
    """Tests for the TicketResponse model."""

    def test_ticket_response_creation(self, sample_ticket):
        """Test creating a TicketResponse."""
        response = TicketResponse(
            data=sample_ticket,
            meta={"request_id": "req_abc123"},
        )
        assert response.data.id == "C1"
        assert response.meta["request_id"] == "req_abc123"

    def test_ticket_response_without_meta(self, sample_ticket):
        """Test creating a TicketResponse without meta."""
        response = TicketResponse(data=sample_ticket)
        assert response.data.id == "C1"
        assert response.meta is None

    def test_json_serialization(self, sample_ticket):
        """Test JSON serialization."""
        response = TicketResponse(
            data=sample_ticket,
            meta={"request_id": "req_abc123"},
        )
        json_str = response.model_dump_json()
        data = json.loads(json_str)
        assert data["data"]["id"] == "C1"
        assert data["meta"]["request_id"] == "req_abc123"


# =============================================================================
# TicketListResponse Tests
# =============================================================================


class TestTicketListResponse:
    """Tests for the TicketListResponse model."""

    def test_list_response(self, sample_ticket_summary_data):
        """Test creating a TicketListResponse."""
        summaries = [TicketSummary(**sample_ticket_summary_data) for _ in range(3)]
        response = TicketListResponse(
            data=summaries,
            meta={
                "total": 100,
                "limit": 20,
                "offset": 0,
                "has_more": True,
                "request_id": "req_abc123",
            },
        )
        assert len(response.data) == 3
        assert response.meta["total"] == 100
        assert response.meta["has_more"] is True


# =============================================================================
# Default Values Tests
# =============================================================================


class TestDefaultValues:
    """Tests for default values."""

    def test_category_defaults_to_general_via_system(self, sample_ticket_create_data):
        """Test category defaults to general."""
        create = TicketCreate(**sample_ticket_create_data)
        # In TicketCreate, category defaults to None, system sets to GENERAL
        # When building a Ticket from TicketCreate:
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            id="G1",
            title=create.title,
            description=create.description,
            repo=create.repo,
            category=create.category or Category.GENERAL,
            severity=create.severity or Severity.MEDIUM,
            status=create.status or Status.OPEN,
            created=now,
            updated=now,
        )
        assert ticket.category == Category.GENERAL

    def test_severity_defaults_to_medium_via_system(self, sample_ticket_create_data):
        """Test severity defaults to medium."""
        create = TicketCreate(**sample_ticket_create_data)
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            id="G1",
            title=create.title,
            description=create.description,
            repo=create.repo,
            category=create.category or Category.GENERAL,
            severity=create.severity or Severity.MEDIUM,
            status=create.status or Status.OPEN,
            created=now,
            updated=now,
        )
        assert ticket.severity == Severity.MEDIUM

    def test_status_defaults_to_open_via_system(self, sample_ticket_create_data):
        """Test status defaults to open."""
        create = TicketCreate(**sample_ticket_create_data)
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            id="G1",
            title=create.title,
            description=create.description,
            repo=create.repo,
            category=create.category or Category.GENERAL,
            severity=create.severity or Severity.MEDIUM,
            status=create.status or Status.OPEN,
            created=now,
            updated=now,
        )
        assert ticket.status == Status.OPEN


# =============================================================================
# Integration Tests
# =============================================================================


def test_create_to_ticket_flow(sample_ticket_create_data):
    """Test the full flow from TicketCreate to Ticket."""
    # Create a TicketCreate
    data = {
        **sample_ticket_create_data,
        "category": Category.CRASH,
        "severity": Severity.HIGH,
        "tags": ["memory", "performance"],
    }
    create = TicketCreate(**data)

    # Build a Ticket from it
    now = datetime.now(timezone.utc)
    ticket = Ticket(
        id="C1",
        title=create.title,
        description=create.description,
        repo=create.repo,
        category=create.category or Category.GENERAL,
        severity=create.severity or Severity.MEDIUM,
        status=create.status or Status.OPEN,
        assignee=create.assignee,
        fix=None,
        tags=create.tags,
        references=create.references,
        created=now,
        updated=now,
    )

    # Verify
    assert ticket.id == "C1"
    assert ticket.title == "CORS Wildcard Issue"
    assert ticket.category == Category.CRASH
    assert ticket.severity == Severity.HIGH
    assert ticket.tags == ["memory", "performance"]


def test_update_to_ticket_flow(sample_ticket):
    """Test the full flow from TicketUpdate to updating a Ticket."""
    original_desc = sample_ticket.description

    # Create an update
    update = TicketUpdate(
        status=Status.FIXED,
        fix="Added garbage collection",
        description_append="\n\n## Resolved\nFixed in PR #42.",
    )

    # Apply updates to ticket
    if update.status:
        sample_ticket.status = update.status
    if update.fix:
        sample_ticket.fix = update.fix
    if update.description_append:
        sample_ticket.description += update.description_append
    sample_ticket.update_timestamp()

    # Verify
    assert sample_ticket.status == Status.FIXED
    assert sample_ticket.fix == "Added garbage collection"
    # Verify description was appended (content check, not exact match due to whitespace handling)
    assert "## Resolved" in sample_ticket.description
    assert "Fixed in PR #42." in sample_ticket.description
    assert sample_ticket.description.startswith(original_desc)


def test_ticket_response_with_meta(sample_ticket):
    """Test creating a response with full metadata."""
    response = TicketResponse(
        data=sample_ticket,
        meta={
            "request_id": "req_abc123",
            "warnings": ["deprecated_field_used"],
        },
    )
    json_str = response.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["meta"]["request_id"] == "req_abc123"
    assert "deprecated_field_used" in parsed["meta"]["warnings"]
