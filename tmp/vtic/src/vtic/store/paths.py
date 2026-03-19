"""Path utilities for ticket file storage.

This module provides functions for constructing ticket file paths,
resolving tickets by ID, and managing directory structures.
"""

from pathlib import Path
from typing import List
import re


def ticket_file_path(base_dir: Path, repo: str, category: str, id: str, slug: str) -> Path:
    """Generate the file path for a ticket.
    
    Args:
        base_dir: Base directory for all ticket storage
        repo: Repository in owner/repo format
        category: Ticket category (crash, hotfix, feature, security, general)
        id: Ticket ID (e.g., C1, S2, H3)
        slug: URL-safe slug derived from title
        
    Returns:
        Path in format: base_dir/{repo}/{category}/{id}-{slug}.md
        
    Example:
        >>> ticket_file_path(Path("/tickets"), "ejacklab/open-dsearch", "security", "C1", "cors-wildcard-issue")
        PosixPath('/tickets/ejacklab/open-dsearch/security/C1-cors-wildcard-issue.md')
    """
    # repo contains a slash, Path will create nested directories
    return base_dir / repo / category / f"{id}-{slug}.md"


def resolve_path(base_dir: Path, id: str) -> List[Path]:
    """Find all ticket files matching a given ID.
    
    Args:
        base_dir: Base directory for all ticket storage
        id: Ticket ID to search for (e.g., C1, S2)
        
    Returns:
        List of Path objects matching the ID (can be empty)
        
    Note:
        This searches recursively through the base_dir for files
        starting with the ticket ID followed by a hyphen.
    """
    if not base_dir.exists():
        return []
    
    pattern = f"{id}-*.md"
    return list(base_dir.rglob(pattern))


def trash_path(base_dir: Path, id: str, timestamp: str) -> Path:
    """Generate a path in the trash directory for soft-deleted tickets.
    
    Args:
        base_dir: Base directory for all ticket storage
        id: Ticket ID being deleted
        timestamp: Timestamp string for the trash filename
        
    Returns:
        Path in format: base_dir/.trash/{id}-{timestamp}.md
    """
    trash_dir = base_dir / ".trash"
    return trash_dir / f"{id}-{timestamp}.md"


def ensure_dirs(path: Path) -> None:
    """Create parent directories for a path if they don't exist.
    
    Args:
        path: File path whose parent directories should be created
        
    Raises:
        OSError: If directory creation fails
    """
    path.parent.mkdir(parents=True, exist_ok=True)
