"""Tests for priority-related models."""

import pytest
from pydantic import ValidationError

from vtic.models import PriorityBreakdown, PriorityLevel


class TestPriorityBreakdown:
    """Tests for PriorityBreakdown model."""

    def test_valid_data(self):
        """Test that valid data passes validation."""
        breakdown = PriorityBreakdown(
            base_score=75,
            base_label="high × medium",
            category="bug",
            category_multiplier=1.2,
            final_score=90,
            priority_level=PriorityLevel.P0,
        )
        assert breakdown.base_score == 75
        assert breakdown.base_label == "high × medium"
        assert breakdown.category == "bug"
        assert breakdown.category_multiplier == 1.2
        assert breakdown.final_score == 90
        assert breakdown.priority_level == PriorityLevel.P0

    def test_valid_data_with_string_priority_level(self):
        """Test that string priority level is coerced to enum."""
        breakdown = PriorityBreakdown(
            base_score=50,
            base_label="medium × medium",
            category="feature",
            category_multiplier=1.0,
            final_score=50,
            priority_level="p2",  # String instead of enum
        )
        assert breakdown.priority_level == PriorityLevel.P2

    def test_invalid_level_rejected(self):
        """Test that invalid PriorityLevel raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            PriorityBreakdown(
                base_score=50,
                base_label="medium × medium",
                category="feature",
                category_multiplier=1.0,
                final_score=50,
                priority_level="p9",  # Invalid level
            )
        assert "priority_level" in str(exc_info.value).lower()

    def test_base_score_bounds(self):
        """Test that base_score must be 0-100."""
        # Valid: minimum
        breakdown = PriorityBreakdown(
            base_score=0,
            base_label="low × low",
            category="general",
            category_multiplier=0.8,
            final_score=0,
            priority_level=PriorityLevel.P4,
        )
        assert breakdown.base_score == 0

        # Valid: maximum
        breakdown = PriorityBreakdown(
            base_score=100,
            base_label="critical × critical",
            category="security",
            category_multiplier=1.5,
            final_score=100,
            priority_level=PriorityLevel.P0,
        )
        assert breakdown.base_score == 100

        # Invalid: too high
        with pytest.raises(ValidationError):
            PriorityBreakdown(
                base_score=101,
                base_label="test",
                category="test",
                category_multiplier=1.0,
                final_score=100,
                priority_level=PriorityLevel.P0,
            )

        # Invalid: negative
        with pytest.raises(ValidationError):
            PriorityBreakdown(
                base_score=-1,
                base_label="test",
                category="test",
                category_multiplier=1.0,
                final_score=0,
                priority_level=PriorityLevel.P4,
            )

    def test_final_score_bounds(self):
        """Test that final_score must be 0-100."""
        # Valid
        breakdown = PriorityBreakdown(
            base_score=50,
            base_label="test",
            category="test",
            category_multiplier=1.0,
            final_score=100,
            priority_level=PriorityLevel.P0,
        )
        assert breakdown.final_score == 100

        # Invalid: too high
        with pytest.raises(ValidationError):
            PriorityBreakdown(
                base_score=50,
                base_label="test",
                category="test",
                category_multiplier=2.0,
                final_score=150,  # Over 100
                priority_level=PriorityLevel.P0,
            )

    def test_category_multiplier_non_negative(self):
        """Test that category_multiplier must be non-negative."""
        # Valid: zero
        breakdown = PriorityBreakdown(
            base_score=50,
            base_label="test",
            category="test",
            category_multiplier=0,
            final_score=0,
            priority_level=PriorityLevel.P4,
        )
        assert breakdown.category_multiplier == 0

        # Invalid: negative
        with pytest.raises(ValidationError):
            PriorityBreakdown(
                base_score=50,
                base_label="test",
                category="test",
                category_multiplier=-0.5,
                final_score=25,
                priority_level=PriorityLevel.P4,
            )

    def test_model_serialization(self):
        """Test that model can be serialized to dict/JSON."""
        breakdown = PriorityBreakdown(
            base_score=60,
            base_label="high × low",
            category="bug",
            category_multiplier=1.2,
            final_score=72,
            priority_level=PriorityLevel.P1,
        )
        data = breakdown.model_dump()
        assert data["base_score"] == 60
        assert data["priority_level"] == "p1"  # Enum serializes to string

    def test_all_priority_levels(self):
        """Test PriorityBreakdown with all priority levels."""
        for level in PriorityLevel:
            breakdown = PriorityBreakdown(
                base_score=50,
                base_label="test",
                category="test",
                category_multiplier=1.0,
                final_score=50,
                priority_level=level,
            )
            assert breakdown.priority_level == level
