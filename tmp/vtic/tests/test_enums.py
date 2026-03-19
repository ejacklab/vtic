"""Tests for vtic enums."""

import pytest

from vtic.models.enums import (
    Category,
    Severity,
    Status,
    EmbeddingProvider,
    DeleteMode,
    VALID_STATUS_TRANSITIONS,
    TERMINAL_STATUSES,
)


class TestCategory:
    """Tests for Category enum."""

    def test_all_values_exist(self):
        """Test all category values are defined."""
        assert Category.CRASH == "crash"
        assert Category.HOTFIX == "hotfix"
        assert Category.FEATURE == "feature"
        assert Category.SECURITY == "security"
        assert Category.GENERAL == "general"

    def test_category_values_list(self):
        """Test that we can get all category values."""
        values = list(Category)
        assert len(values) == 5
        assert "crash" in [v.value for v in values]
        assert "hotfix" in [v.value for v in values]
        assert "feature" in [v.value for v in values]
        assert "security" in [v.value for v in values]
        assert "general" in [v.value for v in values]

    def test_category_prefix_mapping(self):
        """Test category to ID prefix mapping."""
        assert Category.get_prefix(Category.CRASH) == "C"
        assert Category.get_prefix(Category.HOTFIX) == "H"
        assert Category.get_prefix(Category.FEATURE) == "F"
        assert Category.get_prefix(Category.SECURITY) == "S"
        assert Category.get_prefix(Category.GENERAL) == "G"

    def test_category_prefix_mapping_with_string(self):
        """Test category prefix mapping with string values."""
        assert Category.get_prefix("crash") == "C"
        assert Category.get_prefix("hotfix") == "H"
        assert Category.get_prefix("feature") == "F"
        assert Category.get_prefix("security") == "S"
        assert Category.get_prefix("general") == "G"

    def test_category_prefix_mapping_unknown(self):
        """Test that unknown categories get 'G' prefix."""
        assert Category.get_prefix("unknown") == "G"
        assert Category.get_prefix("invalid") == "G"

    def test_category_prefix_mapping_none(self):
        """Test that None input gets 'G' prefix (safe fallback)."""
        assert Category.get_prefix(None) == "G"

    def test_default_is_general(self):
        """Test that GENERAL is the default category."""
        # GENERAL should be the safe fallback
        assert Category.GENERAL.value == "general"
        assert Category.get_prefix("nonexistent") == "G"


class TestSeverity:
    """Tests for Severity enum."""

    def test_all_values_exist(self):
        """Test all severity values are defined."""
        assert Severity.CRITICAL == "critical"
        assert Severity.HIGH == "high"
        assert Severity.MEDIUM == "medium"
        assert Severity.LOW == "low"
        assert Severity.INFO == "info"

    def test_severity_values_list(self):
        """Test that we can get all severity values."""
        values = list(Severity)
        assert len(values) == 5

    def test_severity_weights(self):
        """Test severity weight property for sorting."""
        assert Severity.CRITICAL.weight == 4
        assert Severity.HIGH.weight == 3
        assert Severity.MEDIUM.weight == 2
        assert Severity.LOW.weight == 1
        assert Severity.INFO.weight == 0

    def test_severity_weight_ordering(self):
        """Test that severity weights are in correct order."""
        severities = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        weights = [s.weight for s in severities]
        assert weights == [0, 1, 2, 3, 4]
        assert weights == sorted(weights)

    def test_default_is_medium(self):
        """Test that MEDIUM is the common default severity."""
        assert Severity.MEDIUM.value == "medium"


class TestStatus:
    """Tests for Status enum."""

    def test_all_values_exist(self):
        """Test all status values are defined."""
        assert Status.OPEN == "open"
        assert Status.IN_PROGRESS == "in_progress"
        assert Status.BLOCKED == "blocked"
        assert Status.FIXED == "fixed"
        assert Status.WONT_FIX == "wont_fix"
        assert Status.CLOSED == "closed"

    def test_status_values_list(self):
        """Test that we can get all status values."""
        values = list(Status)
        assert len(values) == 6

    def test_terminal_statuses(self):
        """Test terminal status detection."""
        assert Status.CLOSED.is_terminal is True
        assert Status.WONT_FIX.is_terminal is True
        assert Status.FIXED.is_terminal is True
        assert Status.OPEN.is_terminal is False
        assert Status.IN_PROGRESS.is_terminal is False
        assert Status.BLOCKED.is_terminal is False

    def test_terminal_statuses_constant(self):
        """Test TERMINAL_STATUSES constant."""
        assert Status.CLOSED in TERMINAL_STATUSES
        assert Status.WONT_FIX in TERMINAL_STATUSES
        assert Status.FIXED not in TERMINAL_STATUSES  # FIXED is not in the constant

    def test_display_names(self):
        """Test human-readable display names."""
        assert Status.OPEN.display_name == "Open"
        assert Status.IN_PROGRESS.display_name == "In Progress"
        assert Status.BLOCKED.display_name == "Blocked"
        assert Status.FIXED.display_name == "Fixed"
        assert Status.WONT_FIX.display_name == "Won't Fix"
        assert Status.CLOSED.display_name == "Closed"

    def test_default_is_open(self):
        """Test that OPEN is the default status."""
        assert Status.OPEN.value == "open"


class TestStatusTransitions:
    """Tests for status workflow transitions."""

    def test_open_transitions(self):
        """Test valid transitions from OPEN."""
        assert Status.OPEN.can_transition_to(Status.IN_PROGRESS) is True
        assert Status.OPEN.can_transition_to(Status.BLOCKED) is True
        assert Status.OPEN.can_transition_to(Status.WONT_FIX) is True
        assert Status.OPEN.can_transition_to(Status.CLOSED) is True
        # Invalid transitions
        assert Status.OPEN.can_transition_to(Status.OPEN) is False
        assert Status.OPEN.can_transition_to(Status.FIXED) is False

    def test_in_progress_transitions(self):
        """Test valid transitions from IN_PROGRESS."""
        assert Status.IN_PROGRESS.can_transition_to(Status.OPEN) is True
        assert Status.IN_PROGRESS.can_transition_to(Status.BLOCKED) is True
        assert Status.IN_PROGRESS.can_transition_to(Status.FIXED) is True
        assert Status.IN_PROGRESS.can_transition_to(Status.WONT_FIX) is True
        assert Status.IN_PROGRESS.can_transition_to(Status.CLOSED) is True
        # Invalid
        assert Status.IN_PROGRESS.can_transition_to(Status.IN_PROGRESS) is False

    def test_blocked_transitions(self):
        """Test valid transitions from BLOCKED."""
        assert Status.BLOCKED.can_transition_to(Status.OPEN) is True
        assert Status.BLOCKED.can_transition_to(Status.IN_PROGRESS) is True
        assert Status.BLOCKED.can_transition_to(Status.WONT_FIX) is True
        assert Status.BLOCKED.can_transition_to(Status.CLOSED) is True
        # Invalid
        assert Status.BLOCKED.can_transition_to(Status.BLOCKED) is False
        assert Status.BLOCKED.can_transition_to(Status.FIXED) is False

    def test_fixed_transitions(self):
        """Test valid transitions from FIXED."""
        assert Status.FIXED.can_transition_to(Status.OPEN) is True
        assert Status.FIXED.can_transition_to(Status.CLOSED) is True
        assert Status.FIXED.can_transition_to(Status.WONT_FIX) is True
        # Invalid
        assert Status.FIXED.can_transition_to(Status.FIXED) is False
        assert Status.FIXED.can_transition_to(Status.IN_PROGRESS) is False
        assert Status.FIXED.can_transition_to(Status.BLOCKED) is False

    def test_wont_fix_transitions(self):
        """Test valid transitions from WONT_FIX."""
        assert Status.WONT_FIX.can_transition_to(Status.OPEN) is True
        assert Status.WONT_FIX.can_transition_to(Status.CLOSED) is True
        # Invalid
        assert Status.WONT_FIX.can_transition_to(Status.WONT_FIX) is False
        assert Status.WONT_FIX.can_transition_to(Status.IN_PROGRESS) is False

    def test_closed_transitions(self):
        """Test valid transitions from CLOSED (only reopening)."""
        assert Status.CLOSED.can_transition_to(Status.OPEN) is True
        # Invalid - closed can only reopen
        assert Status.CLOSED.can_transition_to(Status.CLOSED) is False
        assert Status.CLOSED.can_transition_to(Status.IN_PROGRESS) is False
        assert Status.CLOSED.can_transition_to(Status.FIXED) is False
        assert Status.CLOSED.can_transition_to(Status.BLOCKED) is False
        assert Status.CLOSED.can_transition_to(Status.WONT_FIX) is False

    def test_valid_transitions_constant(self):
        """Test that VALID_STATUS_TRANSITIONS contains expected mappings."""
        assert Status.OPEN in VALID_STATUS_TRANSITIONS
        assert Status.IN_PROGRESS in VALID_STATUS_TRANSITIONS
        assert len(VALID_STATUS_TRANSITIONS[Status.OPEN]) == 4
        assert len(VALID_STATUS_TRANSITIONS[Status.IN_PROGRESS]) == 5
        assert len(VALID_STATUS_TRANSITIONS[Status.CLOSED]) == 1


class TestEmbeddingProvider:
    """Tests for EmbeddingProvider enum."""

    def test_all_values_exist(self):
        """Test all provider values are defined."""
        assert EmbeddingProvider.LOCAL == "local"
        assert EmbeddingProvider.OPENAI == "openai"
        assert EmbeddingProvider.CUSTOM == "custom"
        assert EmbeddingProvider.NONE == "none"

    def test_default_is_none(self):
        """Test that NONE is the zero-config default."""
        # NONE enables pure BM25 without any embedding setup
        assert EmbeddingProvider.NONE.value == "none"


class TestDeleteMode:
    """Tests for DeleteMode enum."""

    def test_all_values_exist(self):
        """Test all delete mode values are defined."""
        assert DeleteMode.SOFT == "soft"
        assert DeleteMode.HARD == "hard"

    def test_soft_vs_hard(self):
        """Test soft and hard delete modes."""
        # Soft delete marks as deleted but keeps data
        assert DeleteMode.SOFT.value == "soft"
        # Hard delete permanently removes data
        assert DeleteMode.HARD.value == "hard"


class TestEnumSerialization:
    """Tests for enum serialization behavior."""

    def test_enum_string_values(self):
        """Test that enums serialize to their string values."""
        assert str(Category.CRASH) == "crash"
        assert str(Severity.HIGH) == "high"
        assert str(Status.OPEN) == "open"

    def test_enum_equality_with_strings(self):
        """Test that enums can be compared with strings."""
        assert Category.CRASH == "crash"
        assert Severity.HIGH == "high"
        assert Status.OPEN == "open"

    def test_enum_in_container(self):
        """Test that enums work in containers."""
        categories = {Category.CRASH, Category.HOTFIX}
        assert "crash" in [c.value for c in categories]
        assert Category.CRASH in categories
