"""Core priority scoring engine."""

from vtic.models.enums import Urgency, Impact, PriorityLevel
from vtic.models.ticket import PriorityBreakdown

# ITIL Urgency × Impact Matrix (base scores)
ITIL_MATRIX: dict[Urgency, dict[Impact, int]] = {
    Urgency.CRITICAL: {Impact.CRITICAL: 95, Impact.HIGH: 85, Impact.MEDIUM: 75, Impact.LOW: 60},
    Urgency.HIGH:     {Impact.CRITICAL: 85, Impact.HIGH: 70, Impact.MEDIUM: 60, Impact.LOW: 50},
    Urgency.MEDIUM:   {Impact.CRITICAL: 75, Impact.HIGH: 60, Impact.MEDIUM: 50, Impact.LOW: 35},
    Urgency.LOW:      {Impact.CRITICAL: 60, Impact.HIGH: 50, Impact.MEDIUM: 35, Impact.LOW: 20},
}

# Default category multipliers (must match config.py)
DEFAULT_CATEGORY_MULTIPLIERS: dict[str, float] = {
    "security": 1.5,
    "hotfix": 1.3,
    "bug": 1.2,
    "feature": 1.0,
    "enhancement": 0.9,
    "docs": 0.8,
    "chore": 0.7,
    "refactor": 0.7,
}


def derive_priority_level(score: int) -> PriorityLevel:
    """Derive PriorityLevel from a score (0-100)."""
    if score >= 90:
        return PriorityLevel.P0
    elif score >= 70:
        return PriorityLevel.P1
    elif score >= 50:
        return PriorityLevel.P2
    elif score >= 30:
        return PriorityLevel.P3
    else:
        return PriorityLevel.P4


def compute_priority(
    urgency: Urgency,
    impact: Impact,
    category: str,
    category_multipliers: dict[str, float] | None = None,
) -> PriorityBreakdown:
    """
    Compute priority breakdown from urgency, impact, and category.

    Args:
        urgency: Urgency level
        impact: Impact level
        category: Ticket category (e.g., "bug", "feature")
        category_multipliers: Optional dict of category → multiplier.
            Defaults to DEFAULT_CATEGORY_MULTIPLIERS if not provided.

    Returns:
        PriorityBreakdown with all scoring details.
    """
    if category_multipliers is None:
        category_multipliers = DEFAULT_CATEGORY_MULTIPLIERS

    base_score = ITIL_MATRIX[urgency][impact]
    multiplier = category_multipliers.get(category, 1.0)
    final_score = min(100, max(0, int(base_score * multiplier)))
    priority_level = derive_priority_level(final_score)

    return PriorityBreakdown(
        base_score=base_score,
        base_label=f"{urgency.value} × {impact.value}",
        category=category,
        category_multiplier=multiplier,
        final_score=final_score,
        priority_level=priority_level,
    )
