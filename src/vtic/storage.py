"""File-backed ticket storage for markdown tickets."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .constants import CATEGORY_PREFIXES
from .errors import (
    TicketAlreadyExistsError,
    TicketDeleteError,
    TicketNotFoundError,
    TicketReadError,
    TicketWriteError,
)
from .models import Category, SearchFilters, Ticket, TicketUpdate
from .utils import isoformat_z, normalize_tags, ticket_path, utc_now


class TicketStore:
    """Persist tickets as markdown files with YAML-like frontmatter."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)

    def create(self, ticket: Ticket) -> Ticket:
        path = ticket_path(self.base_dir, ticket)
        if path.exists():
            raise TicketAlreadyExistsError(ticket.id)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._serialize_ticket(ticket), encoding="utf-8")
        except OSError as exc:
            raise TicketWriteError(ticket.id, str(exc)) from exc

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
        data: dict[str, object] = {}
        current_key: str | None = None
        tags: list[str] = []

        for line in frontmatter.splitlines():
            if not line.strip():
                continue
            if line.startswith("  - "):
                if current_key != "tags":
                    raise ValueError("Unexpected list entry in frontmatter")
                tags.append(line[4:].strip())
                continue
            if ":" not in line:
                raise ValueError(f"Invalid frontmatter line: {line}")

            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if key == "tags":
                tags = []
                data[key] = tags
            else:
                data[key] = value or None

        data["tags"] = normalize_tags(tags)
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

        fix_marker = "\n## Fix\n"
        if fix_marker in stripped:
            description, fix = stripped.split(fix_marker, 1)
            return description.strip() or None, fix.strip() or None

        return stripped, None

    @staticmethod
    def _slug_from_path(path: Path, ticket_id: str) -> str:
        prefix = f"{ticket_id}-"
        if not path.stem.startswith(prefix):
            raise ValueError("Filename does not match ticket ID")
        return path.stem[len(prefix) :]

    def _serialize_ticket(self, ticket: Ticket) -> str:
        lines = [
            "---",
            f"id: {ticket.id}",
            f"title: {ticket.title}",
            f"repo: {ticket.repo}",
            f"category: {ticket.category.value}",
            f"severity: {ticket.severity.value}",
            f"status: {ticket.status.value}",
            f"owner: {ticket.owner}" if ticket.owner else "owner:",
            f"file: {ticket.file}" if ticket.file else "file:",
            f"created_at: {isoformat_z(ticket.created_at)}",
            f"updated_at: {isoformat_z(ticket.updated_at)}",
            "tags:",
        ]
        lines.extend(f"  - {tag}" for tag in ticket.tags)
        lines.extend(["---", ""])
        if ticket.description:
            lines.append(ticket.description.strip())
            lines.append("")
        if ticket.fix:
            lines.append("## Fix")
            lines.append("")
            lines.append(ticket.fix.strip())
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _matches_filters(ticket: Ticket, filters: SearchFilters | None) -> bool:
        if filters is None:
            return True
        if filters.repo and ticket.repo not in filters.repo:
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
