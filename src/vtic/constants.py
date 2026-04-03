"""Domain constants for vtic."""

from __future__ import annotations

from pathlib import Path

CATEGORY_PREFIXES: dict[str, str] = {
    "code_quality": "C",
    "security": "S",
    "auth": "A",
    "infrastructure": "I",
    "documentation": "D",
    "testing": "T",
    "performance": "P",
    "frontend": "F",
    "configuration": "N",
    "api": "X",
    "data": "M",
    "ui": "U",
    "dependencies": "Y",
    "build": "B",
    "other": "O",
}

VALID_STATUSES: tuple[str, ...] = (
    "open",
    "in_progress",
    "blocked",
    "fixed",
    "wont_fix",
    "closed",
)

TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"fixed", "wont_fix", "closed"}
)

STATUS_METADATA: dict[str, dict[str, str]] = {
    "open": {
        "name": "open",
        "display_name": "Open",
        "description": "New ticket, not yet started",
        "color": "cyan",
    },
    "in_progress": {
        "name": "in_progress",
        "display_name": "In Progress",
        "description": "Currently being worked on",
        "color": "yellow",
    },
    "blocked": {
        "name": "blocked",
        "display_name": "Blocked",
        "description": "Waiting on external dependency",
        "color": "red",
    },
    "fixed": {
        "name": "fixed",
        "display_name": "Fixed",
        "description": "Issue resolved",
        "color": "green",
    },
    "wont_fix": {
        "name": "wont_fix",
        "display_name": "Won't Fix",
        "description": "Will not be resolved",
        "color": "gray",
    },
    "closed": {
        "name": "closed",
        "display_name": "Closed",
        "description": "Ticket closed",
        "color": "blue",
    },
}

DEFAULT_CONFIG_FILENAME = "vtic.toml"
DEFAULT_CONFIG_DIRNAME = ".vtic"
DEFAULT_GLOBAL_CONFIG_DIR = Path("~/.config/vtic").expanduser()
DEFAULT_GLOBAL_CONFIG_PATH = DEFAULT_GLOBAL_CONFIG_DIR / "config.toml"
