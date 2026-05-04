"""Domain constants for vtic."""

from __future__ import annotations

from pathlib import Path

VALID_STATUSES: tuple[str, ...] = (
    "open",
    "active",
    "done",
    "cancelled",
)

TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"done", "cancelled"}
)

STATUS_METADATA: dict[str, dict[str, str]] = {
    "open": {
        "name": "open",
        "display_name": "Open",
        "description": "New ticket, not yet started",
        "color": "cyan",
    },
    "active": {
        "name": "active",
        "display_name": "Active",
        "description": "Currently being worked on",
        "color": "yellow",
    },
    "done": {
        "name": "done",
        "display_name": "Done",
        "description": "Ticket completed",
        "color": "green",
    },
    "cancelled": {
        "name": "cancelled",
        "display_name": "Cancelled",
        "description": "Ticket cancelled",
        "color": "gray",
    },
}

DEFAULT_CONFIG_FILENAME = "vtic.toml"
DEFAULT_CONFIG_DIRNAME = ".vtic"
DEFAULT_GLOBAL_CONFIG_DIR = Path("~/.config/vtic").expanduser()
DEFAULT_GLOBAL_CONFIG_PATH = DEFAULT_GLOBAL_CONFIG_DIR / "config.toml"
