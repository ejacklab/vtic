"""Tests for priority engine."""

import pytest
from vtic.models.enums import Urgency, Impact, PriorityLevel
from vtic.priority.engine import (
    ITIL_MATRIX,
    DEFAULT_CATEGORY_MULTIPLIERS,
    compute_priority,
    derive_priority_level,
)


class TestITILMatrix:
    def test_all_urgency_impact_combinations(self):
        """All 16 combinations should have scores."""
        for urgency in Urgency:
            for impact in Impact:
                score = ITIL_MATRIX[urgency][impact]
                assert 0 <= score <= 100


class TestDerivePriorityLevel:
    def test_p0_range(self):
        assert derive_priority_level(90) == PriorityLevel.P0
        assert derive_priority_level(100) == PriorityLevel.P0

    def test_p1_range(self):
        assert derive_priority_level(70) == PriorityLevel.P1
        assert derive_priority_level(89) == PriorityLevel.P1

    def test_p2_range(self):
        assert derive_priority_level(50) == PriorityLevel.P2
        assert derive_priority_level(69) == PriorityLevel.P2

    def test_p3_range(self):
        assert derive_priority_level(30) == PriorityLevel.P3
        assert derive_priority_level(49) == PriorityLevel.P3

    def test_p4_range(self):
        assert derive_priority_level(0) == PriorityLevel.P4
        assert derive_priority_level(29) == PriorityLevel.P4


class TestComputePriority:
    def test_basic_computation(self):
        result = compute_priority(Urgency.HIGH, Impact.MEDIUM, "bug")
        assert result.base_score == 60
        assert result.category == "bug"
        assert result.category_multiplier == 1.2
        assert result.final_score == 72  # 60 * 1.2
        assert result.priority_level == PriorityLevel.P1

    def test_security_multiplier(self):
        result = compute_priority(Urgency.HIGH, Impact.MEDIUM, "security")
        assert result.category_multiplier == 1.5
        assert result.final_score == 90  # 60 * 1.5

    def test_chore_multiplier(self):
        result = compute_priority(Urgency.HIGH, Impact.MEDIUM, "chore")
        assert result.category_multiplier == 0.7
        assert result.final_score == 42  # 60 * 0.7

    def test_unknown_category(self):
        result = compute_priority(Urgency.HIGH, Impact.MEDIUM, "unknown")
        assert result.category_multiplier == 1.0
        assert result.final_score == 60

    def test_score_clamps_to_100(self):
        result = compute_priority(Urgency.CRITICAL, Impact.CRITICAL, "security")
        # 95 * 1.5 = 142.5 → clamped to 100
        assert result.final_score == 100

    def test_base_label_format(self):
        result = compute_priority(Urgency.HIGH, Impact.MEDIUM, "bug")
        assert result.base_label == "high × medium"
