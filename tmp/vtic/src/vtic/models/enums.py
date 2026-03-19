"""Core enums for the vtic ticket system."""

from __future__ import annotations

from enum import StrEnum
from typing import Dict, Set


class Category(StrEnum):
    """
    Ticket category with ID prefix mapping.
    
    Categories determine both the storage directory and the ID prefix.
    For example, crash tickets get IDs like C1, C2, C3.
    
    ID Prefix Mapping:
    - crash → C
    - hotfix → H
    - feature → F
    - security → S
    - general → G
    """
    CRASH = "crash"         # Prefix: C
    HOTFIX = "hotfix"       # Prefix: H
    FEATURE = "feature"     # Prefix: F
    SECURITY = "security"   # Prefix: S
    GENERAL = "general"     # Prefix: G

    @classmethod
    def get_prefix(cls, category: "Category | str") -> str:
        """Get the ID prefix for a category."""
        if category is None:
            return "G"  # None/invalid gets G (general)
        
        prefix_map: Dict[str, str] = {
            cls.CRASH.value: "C",
            cls.HOTFIX.value: "H",
            cls.FEATURE.value: "F",
            cls.SECURITY.value: "S",
            cls.GENERAL.value: "G",
        }
        value = category.value if isinstance(category, Category) else category
        return prefix_map.get(value, "G")  # Unknown categories get G (general)


class Severity(StrEnum):
    """Ticket severity levels with weight for sorting."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def weight(self) -> int:
        """Get numeric weight for sorting (higher = more severe)."""
        weights = {
            self.CRITICAL: 4,
            self.HIGH: 3,
            self.MEDIUM: 2,
            self.LOW: 1,
            self.INFO: 0,
        }
        return weights.get(self, 0)


class Status(StrEnum):
    """
    Ticket status values with workflow transitions.
    
    Terminal statuses are those that represent a final state (closed, wont_fix).
    Reopening from terminal status is allowed but should be intentional.
    """
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"
    CLOSED = "closed"

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal (completed) status."""
        return self in (Status.FIXED, Status.WONT_FIX, Status.CLOSED)

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        display_map: Dict[Status, str] = {
            Status.OPEN: "Open",
            Status.IN_PROGRESS: "In Progress",
            Status.BLOCKED: "Blocked",
            Status.FIXED: "Fixed",
            Status.WONT_FIX: "Won't Fix",
            Status.CLOSED: "Closed",
        }
        return display_map.get(self, self.value)

    def can_transition_to(self, target: "Status") -> bool:
        """Check if transition to target status is valid."""
        return target in VALID_STATUS_TRANSITIONS.get(self, set())


# Valid transitions - defines allowed state changes
VALID_STATUS_TRANSITIONS: Dict[Status, Set[Status]] = {
    Status.OPEN: {Status.IN_PROGRESS, Status.BLOCKED, Status.WONT_FIX, Status.CLOSED},
    Status.IN_PROGRESS: {Status.OPEN, Status.BLOCKED, Status.FIXED, Status.WONT_FIX, Status.CLOSED},
    Status.BLOCKED: {Status.OPEN, Status.IN_PROGRESS, Status.WONT_FIX, Status.CLOSED},
    Status.FIXED: {Status.OPEN, Status.CLOSED, Status.WONT_FIX},
    Status.WONT_FIX: {Status.OPEN, Status.CLOSED},
    Status.CLOSED: {Status.OPEN},  # Reopening only
}

# Terminal statuses - tickets that can't transition further without reopening
TERMINAL_STATUSES: Set[Status] = {Status.CLOSED, Status.WONT_FIX}


class EmbeddingProvider(StrEnum):
    """Embedding provider for semantic search."""
    LOCAL = "local"
    OPENAI = "openai"
    CUSTOM = "custom"
    NONE = "none"


class DeleteMode(StrEnum):
    """Deletion mode for tickets."""
    SOFT = "soft"
    HARD = "hard"
