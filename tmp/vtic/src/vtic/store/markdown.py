"""Markdown serialization and parsing for tickets.

This module provides functions to convert between ticket dictionaries
and markdown files with YAML frontmatter.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import tempfile
import os

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def _ensure_yaml():
    """Ensure PyYAML is available."""
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML is required for markdown operations. Install with: pip install pyyaml")


# Fields that go into YAML frontmatter (in order)
FRONTMATTER_FIELDS = [
    "id", "title", "description", "repo", "category", "severity", 
    "status", "assignee", "fix", "tags", "references", "created", "updated"
]


def ticket_to_markdown(ticket: dict) -> str:
    """Serialize a ticket dictionary to markdown with YAML frontmatter.
    
    Args:
        ticket: Ticket dictionary with all fields
        
    Returns:
        Markdown string with YAML frontmatter and body sections
        
    Example:
        >>> ticket = {
        ...     "id": "C1",
        ...     "title": "CORS Wildcard Issue",
        ...     "description": "The API allows wildcard CORS origins",
        ...     "repo": "ejacklab/open-dsearch",
        ...     "category": "security",
        ...     "severity": "high",
        ...     "status": "open",
        ...     "assignee": None,
        ...     "fix": None,
        ...     "tags": ["cors", "security"],
        ...     "references": [],
        ...     "created": "2026-03-18T10:00:00Z",
        ...     "updated": "2026-03-18T10:00:00Z",
        ... }
        >>> md = ticket_to_markdown(ticket)
    """
    _ensure_yaml()
    
    # Build frontmatter dict in specified order
    frontmatter: Dict[str, Any] = {}
    for field in FRONTMATTER_FIELDS:
        if field in ticket:
            frontmatter[field] = ticket[field]
    
    # Serialize frontmatter to YAML
    yaml_content = yaml.dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        default_style=""
    )
    
    # Build body sections
    body_parts = []
    
    # Description section (always present)
    description = ticket.get("description", "")
    body_parts.append(f"## Description\n{description}")
    
    # Fix section (only when fix is set)
    fix = ticket.get("fix")
    if fix is not None:
        body_parts.append(f"## Fix\n{fix}")
    
    body = "\n\n".join(body_parts)
    
    return f"---\n{yaml_content}---\n\n{body}\n"


def markdown_to_ticket(content: str) -> dict:
    """Parse markdown with YAML frontmatter into a ticket dictionary.
    
    Args:
        content: Markdown string with YAML frontmatter
        
    Returns:
        Ticket dictionary with all fields from frontmatter and body
        
    Raises:
        ValueError: If content is not valid markdown with frontmatter
    """
    _ensure_yaml()
    
    # Parse frontmatter
    pattern = r"^---\s*\n(.*?)\n---\s*\n+(.*)$"
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        raise ValueError("Invalid markdown format: missing YAML frontmatter")
    
    yaml_content = match.group(1)
    body_content = match.group(2)
    
    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(yaml_content)
        if frontmatter is None:
            frontmatter = {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in frontmatter: {e}")
    
    # Start with frontmatter data
    ticket: Dict[str, Any] = dict(frontmatter)
    
    # Extract description from body (overrides frontmatter if present)
    description_match = re.search(
        r"## Description\s*\n(.*?)(?=\n## |$)", 
        body_content, 
        re.DOTALL
    )
    if description_match:
        ticket["description"] = description_match.group(1).strip()
    
    # Extract fix from body if present
    fix_match = re.search(
        r"## Fix\s*\n(.*?)(?=\n## |$)", 
        body_content, 
        re.DOTALL
    )
    if fix_match:
        ticket["fix"] = fix_match.group(1).strip()
    
    return ticket


def write_ticket(path: Path, ticket: dict) -> None:
    """Write a ticket to disk atomically.
    
    Uses temp file + fsync + rename pattern for atomic writes.
    
    Args:
        path: Destination path for the ticket file
        ticket: Ticket dictionary to serialize
        
    Raises:
        OSError: If file write fails
    """
    # Ensure parent directories exist
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Serialize ticket to markdown
    content = ticket_to_markdown(ticket)
    
    # Write to temp file in same directory (for atomic rename)
    temp_fd = None
    temp_path = None
    try:
        # Create temp file in same directory as target for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.stem}",
            suffix=".tmp"
        )
        
        # Write content
        os.write(temp_fd, content.encode("utf-8"))
        
        # Ensure data is written to disk (fsync)
        os.fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = None
        
        # Atomic rename
        os.replace(temp_path, path)
        
        # Sync parent directory to ensure rename is persisted
        dir_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
            
    except Exception:
        # Clean up temp file on failure
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise


def read_ticket(path: Path) -> Optional[dict]:
    """Read and parse a ticket from disk.
    
    Args:
        path: Path to the ticket markdown file
        
    Returns:
        Ticket dictionary or None if file doesn't exist
        
    Raises:
        ValueError: If file exists but has invalid format
    """
    if not path.exists():
        return None
    
    content = path.read_text(encoding="utf-8")
    return markdown_to_ticket(content)


def delete_ticket(path: Path, mode: str = "soft", trash_dir: Optional[Path] = None) -> None:
    """Delete a ticket file.
    
    Args:
        path: Path to the ticket file
        mode: "soft" (move to trash) or "hard" (permanent delete)
        trash_dir: Directory for soft-deleted tickets (required if mode="soft")
        
    Raises:
        FileNotFoundError: If ticket doesn't exist
        ValueError: If mode is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"Ticket not found: {path}")
    
    if mode == "hard":
        path.unlink()
    elif mode == "soft":
        if trash_dir is None:
            # Default trash dir at base level
            trash_dir = path.parent.parent.parent / ".trash"
        
        # Ensure trash directory exists
        trash_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate trash path with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        trashed_path = trash_dir / f"{path.stem}-{timestamp}.md"
        
        # Move to trash
        path.rename(trashed_path)
    else:
        raise ValueError(f"Invalid delete mode: {mode}. Use 'soft' or 'hard'.")


def list_tickets(base_dir: Path, repo: Optional[str] = None, category: Optional[str] = None) -> List[Path]:
    """List ticket files, optionally filtered by repo and/or category.
    
    Args:
        base_dir: Base directory for all ticket storage
        repo: Filter by repository (owner/repo format)
        category: Filter by category
        
    Returns:
        List of Path objects matching the filters
    """
    if not base_dir.exists():
        return []
    
    # Build search path
    search_path = base_dir
    if repo:
        search_path = search_path / repo
    if category:
        search_path = search_path / category
    
    if not search_path.exists():
        return []
    
    # Find all markdown files
    if category:
        # Category specified - search directly in that directory
        return list(search_path.glob("*.md"))
    elif repo:
        # Only repo specified - recursive search within repo
        return list(search_path.rglob("*.md"))
    else:
        # No filters - recursive search from base
        return list(base_dir.rglob("*.md"))


def scan_all_tickets(base_dir: Path) -> List[Tuple[Path, dict]]:
    """Scan all tickets and return paths with parsed content.
    
    Args:
        base_dir: Base directory for all ticket storage
        
    Returns:
        List of (path, ticket_dict) tuples
    """
    results: List[Tuple[Path, dict]] = []
    
    if not base_dir.exists():
        return results
    
    for path in base_dir.rglob("*.md"):
        # Skip trash directory and hidden files
        if ".trash" in path.parts or path.name.startswith("."):
            continue
        
        try:
            ticket = read_ticket(path)
            if ticket:
                results.append((path, ticket))
        except (ValueError, OSError):
            # Skip files that can't be parsed
            continue
    
    return results
