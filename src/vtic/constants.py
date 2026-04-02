"""Domain constants for vtic."""

from __future__ import annotations

from pathlib import Path

from .models import Category, Status

CATEGORY_PREFIXES: dict[Category, str] = {
    Category.CODE_QUALITY: "C",
    Category.SECURITY: "S",
    Category.AUTH: "A",
    Category.INFRASTRUCTURE: "I",
    Category.DOCUMENTATION: "D",
    Category.TESTING: "T",
    Category.PERFORMANCE: "P",
    Category.FRONTEND: "F",
    Category.CONFIGURATION: "N",
    Category.API: "X",
    Category.DATA: "M",
    Category.UI: "U",
    Category.DEPENDENCIES: "Y",
    Category.BUILD: "B",
    Category.OTHER: "O",
}

VALID_STATUSES: tuple[Status, ...] = (
    Status.OPEN,
    Status.IN_PROGRESS,
    Status.BLOCKED,
    Status.FIXED,
    Status.WONT_FIX,
    Status.CLOSED,
)

TERMINAL_STATUSES: frozenset[Status] = frozenset(
    {Status.FIXED, Status.WONT_FIX, Status.CLOSED}
)

STATUS_METADATA: dict[Status, dict[str, str]] = {
    Status.OPEN: {
        "name": Status.OPEN.value,
        "display_name": "Open",
        "description": "New ticket, not yet started",
        "color": "cyan",
    },
    Status.IN_PROGRESS: {
        "name": Status.IN_PROGRESS.value,
        "display_name": "In Progress",
        "description": "Currently being worked on",
        "color": "yellow",
    },
    Status.BLOCKED: {
        "name": Status.BLOCKED.value,
        "display_name": "Blocked",
        "description": "Waiting on external dependency",
        "color": "red",
    },
    Status.FIXED: {
        "name": Status.FIXED.value,
        "display_name": "Fixed",
        "description": "Issue resolved",
        "color": "green",
    },
    Status.WONT_FIX: {
        "name": Status.WONT_FIX.value,
        "display_name": "Won't Fix",
        "description": "Will not be resolved",
        "color": "gray",
    },
    Status.CLOSED: {
        "name": Status.CLOSED.value,
        "display_name": "Closed",
        "description": "Ticket closed",
        "color": "blue",
    },
}

DEFAULT_CONFIG_FILENAME = "vtic.toml"
DEFAULT_CONFIG_DIRNAME = ".vtic"
DEFAULT_GLOBAL_CONFIG_DIR = Path("~/.config/vtic").expanduser()
DEFAULT_GLOBAL_CONFIG_PATH = DEFAULT_GLOBAL_CONFIG_DIR / "config.toml"

