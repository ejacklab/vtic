"""File-backed ticket storage for markdown tickets."""

from __future__ import annotations

import fcntl
import fnmatch
from datetime import datetime
from pathlib import Path

import yaml

from .errors import (
    TicketAlreadyExistsError,
    TicketDeleteError,
    TicketNotFoundError,
    TicketReadError,
    TicketWriteError,
)
from .models import CATEGORY_PREFIXES, Category, SearchFilters, Severity, Status, Ticket, TicketUpdate
from .utils import isoformat_z, normalize_tags, ticket_path, utc_now


DESCRIPTION_DELIMITER = "<!-- DESCRIPTION -->"
FIX_DELIMITER = "<!-- FIX -->"


class TicketStore:
    """Persist tickets as markdown files with YAML-like frontmatter."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)

    def create(self, ticket: Ticket) -> Ticket:
        path = ticket_path(self.base_dir, ticket)
        self._write_ticket(ticket, path)
        return ticket

    def create_ticket(
        self,
        *,
        title: str,
        repo: str,
        owner: str | None,
        category: Category,
        severity: Severity,
        status: Status,
        description: str | None,
        fix: str | None,
        file: str | None,
        tags: list[str],
        slug: str,
    ) -> Ticket:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.base_dir / ".vtic.lock"
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            ticket_id = self.next_id(category)
            now = utc_now()
            ticket = Ticket(
                id=ticket_id,
                title=title,
                description=description,
                fix=fix,
                repo=repo,
                owner=owner,
                category=category,
                severity=severity,
                status=status,
                file=file,
                tags=tags,
                created_at=now,
                updated_at=now,
                slug=slug,
            )
            self._write_ticket(ticket, ticket_path(self.base_dir, ticket))
            return ticket

    def get(self, ticket_id: str) -> Ticket:
        _, path = self._find_ticket_path(ticket_id)
        return self._read_ticket(path, ticket_id=ticket_id)

    def list(self, filters: SearchFilters | None = None) -> list[Ticket]:
        tickets: list[Ticket] = []
        if not self.base_dir.exists():
            return tickets

        for path in sorted(self.base_dir.rglob("*.md")):
            if not path.is_file():
                continue
            ticket = self._read_ticket(path)
            if self._matches_filters(ticket, filters):
                tickets.append(ticket)

        return sorted(tickets, key=lambda ticket: (ticket.id[0], int(ticket.id[1:])))

    def update(self, ticket_id: str, updates: TicketUpdate) -> Ticket:
        current, current_path = self._find_ticket_path(ticket_id)
        data = current.model_dump()
        update_data = updates.model_dump(exclude_none=True)
        data.update(update_data)
        data["updated_at"] = utc_now()
        updated_ticket = Ticket(**data)
        new_path = ticket_path(self.base_dir, updated_ticket)

        try:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.write_text(self._serialize_ticket(updated_ticket), encoding="utf-8")
            if new_path != current_path and current_path.exists():
                current_path.unlink()
        except OSError as exc:
            raise TicketWriteError(updated_ticket.id, str(exc)) from exc

        return updated_ticket

    def delete(self, ticket_id: str) -> None:
        _, path = self._find_ticket_path(ticket_id)
        try:
            path.unlink()
        except FileNotFoundError as exc:
            raise TicketNotFoundError(ticket_id) from exc
        except OSError as exc:
            raise TicketDeleteError(ticket_id, str(exc)) from exc

    def next_id(self, category: Category) -> str:
        prefix = CATEGORY_PREFIXES[category]
        highest = 0
        for ticket in self.list():
            if ticket.category is category and ticket.id.startswith(prefix):
                highest = max(highest, int(ticket.id[1:]))
        return f"{prefix}{highest + 1}"

    def _find_ticket_path(self, ticket_id: str) -> tuple[Ticket, Path]:
        normalized = ticket_id.upper()
        for path in sorted(self.base_dir.rglob("*.md")):
            if not path.is_file():
                continue
            stem_prefix = path.stem.split("-", 1)[0].upper()
            if stem_prefix == normalized:
                ticket = self._read_ticket(path, ticket_id=normalized)
                return ticket, path
        raise TicketNotFoundError(ticket_id)

    def _read_ticket(self, path: Path, *, ticket_id: str | None = None) -> Ticket:
        try:
            raw = path.read_text(encoding="utf-8")
            frontmatter, body = self._split_frontmatter(raw)
            data = self._parse_frontmatter(frontmatter)
            description, fix = self._parse_body(body)
            data["description"] = description
            data["fix"] = fix
            data["slug"] = self._slug_from_path(path, data["id"])
            return Ticket(**data)
        except TicketNotFoundError:
            raise
        except Exception as exc:
            raise TicketReadError(ticket_id or path.stem, str(exc)) from exc

    @staticmethod
    def _split_frontmatter(raw: str) -> tuple[str, str]:
        if not raw.startswith("---\n"):
            raise ValueError("Missing frontmatter")

        closing_marker = "\n---\n"
        end_index = raw.find(closing_marker, 4)
        if end_index == -1:
            raise ValueError("Invalid frontmatter")

        frontmatter = raw[4:end_index]
        body = raw[end_index + len(closing_marker) :]
        return frontmatter, body

    @staticmethod
    def _parse_frontmatter(frontmatter: str) -> dict[str, object]:
        loaded = yaml.safe_load(frontmatter) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Frontmatter must be a mapping")

        data = dict(loaded)
        data["tags"] = normalize_tags([str(tag) for tag in data.get("tags", []) or []])
        for field in ("category", "severity", "status"):
            if data.get(field) is None:
                raise ValueError(f"Missing required field: {field}")
        for field in ("created_at", "updated_at"):
            value = data.get(field)
            if value is None:
                raise ValueError(f"Missing required field: {field}")
            data[field] = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

        return data

    @staticmethod
    def _parse_body(body: str) -> tuple[str | None, str | None]:
        stripped = body.strip()
        if not stripped:
            return None, None

        lines = stripped.splitlines()
        description: list[str] = []
        fix: list[str] = []
        current: list[str] | None = None
        saw_marker = False

        for line in lines:
            if line == DESCRIPTION_DELIMITER:
                current = description
                saw_marker = True
                continue
            if line == FIX_DELIMITER:
                current = fix
                saw_marker = True
                continue
            if current is None:
                continue
            current.append(line)

        description_text = "\n".join(description).strip() or None
        fix_text = "\n".join(fix).strip() or None
        if description_text is None and fix_text is None:
            if saw_marker:
                return None, None
            return stripped or None, None
        return description_text, fix_text

    @staticmethod
    def _slug_from_path(path: Path, ticket_id: str) -> str:
        prefix = f"{ticket_id}-"
        if not path.stem.startswith(prefix):
            raise ValueError("Filename does not match ticket ID")
        return path.stem[len(prefix) :]

    def _serialize_ticket(self, ticket: Ticket) -> str:
        frontmatter = {
            "id": ticket.id,
            "title": ticket.title,
            "repo": ticket.repo,
            "category": ticket.category.value,
            "severity": ticket.severity.value,
            "status": ticket.status.value,
            "owner": ticket.owner,
            "file": ticket.file,
            "created_at": isoformat_z(ticket.created_at),
            "updated_at": isoformat_z(ticket.updated_at),
            "tags": ticket.tags,
        }
        lines = ["---", yaml.safe_dump(frontmatter, sort_keys=False).strip(), "---", ""]
        lines.append(DESCRIPTION_DELIMITER)
        if ticket.description:
            lines.append(ticket.description.strip())
        if ticket.fix:
            lines.append("")
            lines.append(FIX_DELIMITER)
            lines.append(ticket.fix.strip())
        return "\n".join(lines).rstrip() + "\n"

    def _write_ticket(self, ticket: Ticket, path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as handle:
                handle.write(self._serialize_ticket(ticket))
        except FileExistsError as exc:
            raise TicketAlreadyExistsError(ticket.id) from exc
        except OSError as exc:
            raise TicketWriteError(ticket.id, str(exc)) from exc

    @staticmethod
    def _matches_filters(ticket: Ticket, filters: SearchFilters | None) -> bool:
        if filters is None:
            return True
        if filters.repo and not any(fnmatch.fnmatch(ticket.repo, pattern) for pattern in filters.repo):
            return False
        if filters.category and ticket.category not in filters.category:
            return False
        if filters.severity and ticket.severity not in filters.severity:
            return False
        if filters.status and ticket.status not in filters.status:
            return False
        if filters.created_after and ticket.created_at < filters.created_after:
            return False
        if filters.created_before and ticket.created_at > filters.created_before:
            return False
        if filters.updated_after and ticket.updated_at < filters.updated_after:
            return False
        if filters.updated_before and ticket.updated_at > filters.updated_before:
            return False
        if filters.tags and not all(tag in ticket.tags for tag in filters.tags):
            return False
        if filters.has_fix is not None and bool(ticket.fix) is not filters.has_fix:
            return False
        if filters.owner and ticket.owner != filters.owner:
            return False
        return True
