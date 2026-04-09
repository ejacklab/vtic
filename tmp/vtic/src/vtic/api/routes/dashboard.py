"""Dashboard route for vtic — serves the web UI and scans tickets."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from ..deps import get_config

router = APIRouter(tags=["Dashboard"])

# Pattern to extract ticket ID from filename (generous matching)
_ID_PATTERNS = [
    # STORY-010, TASK-P0-S1-T1, META-001, SUB-001, F1, S01-S02-analysis
    re.compile(r"^(STORY-\d+|TASK-[A-Z0-9-]+|META-\d+|SUB-\d+|[A-Z]\d+)", re.IGNORECASE),
    # S01-S02-analysis, S10-build-summary, etc
    re.compile(r"^(S\d+-S\d+)", re.IGNORECASE),
    # CODEBASE-MAP, UNIFIED-DESIGN, api-frontend-libs-design
    re.compile(r"^([A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)+)", re.IGNORECASE),
]


def _extract_id(filename: str) -> Optional[str]:
    """Extract a ticket ID from a filename."""
    for pattern in _ID_PATTERNS:
        m = pattern.match(filename)
        if m:
            return m.group(0)
    return None


def _parse_ticket_file(content: str, filename: str, rel_path: str) -> Optional[dict]:
    """Parse a ticket markdown file (with or without YAML frontmatter)."""
    repo = ""
    repo_match = re.match(r"tickets/([^/]+/[^/]+)/", rel_path)
    if repo_match:
        repo = repo_match.group(1)

    # Try YAML frontmatter
    fm_match = re.match(r"^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$", content)
    if fm_match:
        return _parse_frontmatter(fm_match.group(1), fm_match.group(2), filename, repo)

    # Fallback: inline headers
    return _parse_inline(content, filename, repo)


def _parse_frontmatter(yaml_str: str, body: str, filename: str, repo: str) -> Optional[dict]:
    """Parse ticket with YAML frontmatter."""
    import yaml

    try:
        meta = yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError:
        meta = {}

    id_val = meta.get("id")
    if not id_val:
        id_val = _extract_id(filename)
    if not id_val:
        return None

    title = meta.get("title", "")
    if not title:
        h1 = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = h1.group(1) if h1 else id_val

    title = re.sub(r"^\[(Story|Task|Meta|Sub)\]\s*", "", title, flags=re.IGNORECASE)

    tags = meta.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    references = meta.get("references", [])
    if not isinstance(references, list):
        references = []

    return {
        "id": id_val,
        "title": title,
        "description": body.strip()[:50000],
        "repo": meta.get("repo", repo),
        "category": str(meta.get("category", "general")).lower(),
        "severity": str(meta.get("severity", "medium")).lower(),
        "status": str(meta.get("status", "open")).lower(),
        "assignee": meta.get("assignee") or meta.get("assigned_to"),
        "fix": meta.get("fix"),
        "tags": tags,
        "references": references,
        "created": meta.get("created") or meta.get("date"),
        "updated": meta.get("updated"),
    }


def _parse_inline(content: str, filename: str, repo: str) -> Optional[dict]:
    """Parse ticket with inline **Key:** Value headers."""
    id_val = _extract_id(filename)
    if not id_val:
        return None

    meta = {}
    for m in re.finditer(r"^\*\*(\w[\w\s]*?)\*\*:\s*(.+)$", content, re.MULTILINE):
        key = m.group(1).strip().lower().replace(" ", "_")
        meta[key] = m.group(2).strip()

    h1 = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = h1.group(1) if h1 else id_val
    title = re.sub(r"^\[(Story|Task|Meta|Sub)\]\s*", "", title, flags=re.IGNORECASE)

    tags = []
    id_upper = id_val.upper()
    if id_upper.startswith("STORY"):
        tags.append("story")
    if id_upper.startswith("TASK"):
        tags.append("task")
    if id_upper.startswith("META"):
        tags.append("meta")
    if id_upper.startswith("SUB"):
        tags.append("sub-task")
    if "analysis" in filename.lower():
        tags.append("analysis")
    if "architecture" in filename.lower():
        tags.append("architecture")
    if "review" in filename.lower():
        tags.append("review")
    if "design" in filename.lower():
        tags.append("design")

    return {
        "id": id_val,
        "title": title,
        "description": content[:50000],
        "repo": meta.get("repo", repo),
        "category": meta.get("category", "general").lower(),
        "severity": meta.get("severity", "medium").lower(),
        "status": meta.get("status", "open").lower(),
        "assignee": meta.get("assigned_to"),
        "fix": None,
        "tags": tags,
        "references": [],
        "created": meta.get("created"),
        "updated": meta.get("updated"),
    }


@router.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML."""
    dashboard_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "dashboard" / "index.html"
    if not dashboard_path.exists():
        return HTMLResponse(
            "<h1>Dashboard not found</h1><p>dashboard/index.html missing</p>",
            status_code=404,
        )
    return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))


@router.get("/dashboard/tickets")
async def dashboard_tickets(
    request: Request,
    repo: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Scan tickets directory and return all tickets.

    Handles both YAML-frontmatter format and inline-header format.
    """
    config = get_config()
    tickets_dir = Path(config.storage.dir)

    if not tickets_dir.exists():
        return {
            "data": [],
            "meta": {"total": 0, "limit": limit, "offset": offset, "has_more": False},
        }

    all_tickets = []
    for md_file in sorted(tickets_dir.rglob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
            rel_path = str(md_file.relative_to(tickets_dir.parent))
            ticket = _parse_ticket_file(content, md_file.name, rel_path)
            if ticket:
                all_tickets.append(ticket)
        except Exception:
            continue

    # Apply filters
    filtered = all_tickets
    if repo:
        filtered = [t for t in filtered if t["repo"] == repo]
    if status:
        filtered = [t for t in filtered if t["status"] == status.lower()]
    if severity:
        filtered = [t for t in filtered if t["severity"] == severity.lower()]
    if category:
        filtered = [t for t in filtered if t["category"] == category.lower()]
    if tag:
        filtered = [t for t in filtered if tag.lower() in [tg.lower() for tg in (t.get("tags") or [])]]
    if search:
        q = search.lower()
        filtered = [
            t for t in filtered
            if q in (t["title"] or "").lower()
            or q in (t["id"] or "").lower()
            or q in (t["description"] or "").lower()[:500]
            or q in (t["repo"] or "").lower()
            or any(q in tg for tg in (t.get("tags") or []))
        ]

    total = len(filtered)
    page = filtered[offset : offset + limit]

    return {
        "data": page,
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        },
    }


@router.get("/dashboard/stats")
async def dashboard_stats(request: Request):
    """Compute ticket statistics from disk scan."""
    config = get_config()
    tickets_dir = Path(config.storage.dir)

    if not tickets_dir.exists():
        return {"total": 0, "by_status": {}, "by_severity": {}, "by_category": {}, "by_repo": {}}

    by_status = {}
    by_severity = {}
    by_category = {}
    by_repo = {}
    by_tag = {}

    for md_file in tickets_dir.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            rel_path = str(md_file.relative_to(tickets_dir.parent))
            ticket = _parse_ticket_file(content, md_file.name, rel_path)
            if not ticket:
                continue

            s = (ticket.get("status") or "open").lower()
            sv = (ticket.get("severity") or "medium").lower()
            cat = (ticket.get("category") or "general").lower()
            r = ticket.get("repo") or "unknown"

            by_status[s] = by_status.get(s, 0) + 1
            by_severity[sv] = by_severity.get(sv, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1
            by_repo[r] = by_repo.get(r, 0) + 1

            for tg in ticket.get("tags") or []:
                by_tag[tg.lower()] = by_tag.get(tg.lower(), 0) + 1
        except Exception:
            continue

    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "by_severity": by_severity,
        "by_category": by_category,
        "by_repo": by_repo,
        "by_tag": by_tag,
    }
