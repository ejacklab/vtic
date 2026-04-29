#!/usr/bin/env python3
"""One-shot migration: add `due_date: null` to all ticket markdown files
that don't already have a `due_date` field in their frontmatter.

Usage:
    python scripts/migrate_add_due_date.py [--dir TICKETS_DIR] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def migrate_file(path: Path, *, dry_run: bool = False) -> bool:
    """Add due_date: null to a single ticket file if missing. Returns True if modified."""
    raw = path.read_text(encoding="utf-8")

    # Parse frontmatter
    normalized = raw.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        print(f"  SKIP (no frontmatter): {path}", file=sys.stderr)
        return False

    closing_marker = "\n---\n"
    end_idx = normalized.find(closing_marker, 4)
    if end_idx == -1:
        print(f"  SKIP (invalid frontmatter): {path}", file=sys.stderr)
        return False

    frontmatter_str = normalized[4:end_idx]

    loaded = yaml.safe_load(frontmatter_str) or {}
    if not isinstance(loaded, dict):
        print(f"  SKIP (non-mapping frontmatter): {path}", file=sys.stderr)
        return False

    if "due_date" in loaded:
        return False  # Already has due_date

    # Re-serialize with due_date inserted.
    # Use a simple approach: find the last key before the closing ---
    # and append due_date: null on the next line.
    lines = normalized.split("\n")
    # Find closing --- line
    closing_line_idx = None
    for i in range(4, len(lines)):
        if lines[i] == "---":
            closing_line_idx = i
            break

    if closing_line_idx is None:
        return False

    # Insert due_date: null just before the closing ---
    new_lines = lines[:closing_line_idx] + ["due_date: null"] + lines[closing_line_idx:]

    new_content = "\n".join(new_lines)

    if dry_run:
        print(f"  WOULD MODIFY: {path}")
        return True

    path.write_text(new_content, encoding="utf-8")
    print(f"  MODIFIED: {path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add missing due_date: null to vtic ticket files"
    )
    parser.add_argument(
        "--dir",
        default="tickets",
        help="Tickets directory (default: tickets)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    args = parser.parse_args()

    tickets_dir = Path(args.dir)
    if not tickets_dir.exists():
        print(f"Error: directory not found: {tickets_dir}", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(tickets_dir.rglob("*.md"))
    # Exclude .trash directory
    md_files = [f for f in md_files if ".trash" not in str(f)]

    modified = 0
    skipped = 0
    for path in md_files:
        was_modified = migrate_file(path, dry_run=args.dry_run)
        if was_modified:
            modified += 1
        else:
            skipped += 1

    print(f"\nDone. {modified} files modified, {skipped} files unchanged.")
    if args.dry_run:
        print("(dry run - no changes were made)")


if __name__ == "__main__":
    main()
