"""File-backed ticket storage for markdown tickets."""

from __future__ import annotations

import fnmatch
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows does not provide fcntl.
    fcntl = None

from .constants import VALID_STATUSES
from .errors import (
    TicketAlreadyExistsError,
    TicketDeleteError,
    TicketNotFoundError,
    TicketReadError,
    TicketWriteError,
    ValidationError,
)
from .models import (
    CATEGORY_PREFIXES,
    Category,
    ErrorDetail,
    SearchFilters,
    Severity,
    Status,
    Ticket,
    TicketUpdate,
)
from .utils import isoformat_z, normalize_tags, slugify, ticket_path, utc_now


DESCRIPTION_DELIMITER = "<!-- DESCRIPTION -->"
FIX_DELIMITER = "<!-- FIX -->"
TRASH_DIRNAME = ".trash"
SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}
STATUS_ORDER = {
    Status(status): index for index, status in enumerate(VALID_STATUSES)
}


class TicketStore:
    """Persist tickets as markdown files with YAML-like frontmatter."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self._last_list_errors: list[ErrorDetail] = []

    @staticmethod
    def _lock_exclusive(lock_file: Any) -> None:
        """Acquire an advisory exclusive lock when the platform supports it."""

        if fcntl is None:
            return
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

    def _create(self, ticket: Ticket) -> Ticket:
        """Write a pre-validated ticket directly.

        This is a low-level helper and does not provide atomic ID allocation.
        Callers that need safe concurrent creation should use `create_ticket()`.
        """
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
        """Create a ticket with locked, atomic ID allocation.

        This is the only safe public API for creating new tickets concurrently.
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.base_dir / ".vtic.lock"
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            try:
                self._lock_exclusive(lock_file)
                ticket_id = self._next_id(category)
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
            finally:
                try:
                    lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def get(self, ticket_id: str) -> Ticket:
        _, path = self._find_ticket_path(ticket_id)
        return self._read_ticket(path, ticket_id=ticket_id)

    def list(self, filters: SearchFilters | None = None, sort_by: str | None = None) -> list[Ticket]:
        tickets, _ = self.list_with_errors(filters=filters, sort_by=sort_by)
        return tickets

    def list_with_errors(
        self,
        filters: SearchFilters | None = None,
        sort_by: str | None = None,
        *,
        limit: int | None = None,
    ) -> tuple[list[Ticket], list[ErrorDetail]]:
        tickets: list[Ticket] = []
        errors: list[ErrorDetail] = []
        if not self.base_dir.exists():
            self._last_list_errors = []
            return tickets, errors

        for path in self._iter_ticket_paths():
            try:
                ticket = self._read_ticket(path)
            except TicketReadError as exc:
                errors.append(
                    ErrorDetail(
                        field=str(path.relative_to(self.base_dir)),
                        message=exc.message,
                        code=exc.error_code,
                    )
                )
                continue

            if self._matches_filters(ticket, filters) and (
                limit is None or len(tickets) < limit
            ):
                tickets.append(ticket)

        sorted_tickets = self._sort_tickets(tickets, sort_by)
        self._last_list_errors = list(errors)
        return sorted_tickets, errors

    @property
    def last_list_errors(self) -> list[ErrorDetail]:
        return list(self._last_list_errors)

    def count(self) -> int:
        if not self.base_dir.exists():
            return 0
        return sum(1 for _ in self._iter_ticket_paths())

    def update(self, ticket_id: str, updates: TicketUpdate) -> Ticket:
        update_data = updates.model_dump(exclude_unset=True)
        if "repo" in update_data:
            raise ValidationError("Cannot change repo field on update")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.base_dir / ".vtic.lock"
        temp_path: Path | None = None
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            try:
                self._lock_exclusive(lock_file)
                current, current_path = self._find_ticket_path(ticket_id)
                data = current.model_dump()
                data.update(update_data)
                if "title" in update_data:
                    data["slug"] = slugify(str(update_data["title"]))
                data["updated_at"] = utc_now()
                updated_ticket = Ticket(**data)
                new_path = ticket_path(self.base_dir, updated_ticket)
                try:
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(
                        mode="w",
                        encoding="utf-8",
                        dir=new_path.parent,
                        delete=False,
                    ) as temp_file:
                        temp_file.write(self._serialize_ticket(updated_ticket))
                        temp_path = Path(temp_file.name)
                    os.replace(temp_path, new_path)
                    temp_path = None
                    if new_path != current_path and current_path.exists():
                        current_path.unlink()
                except OSError as exc:
                    if temp_path is not None:
                        try:
                            temp_path.unlink()
                        except FileNotFoundError:
                            pass
                        except OSError:
                            pass
                    raise TicketWriteError(updated_ticket.id, str(exc)) from exc
            finally:
                try:
                    lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

        return updated_ticket

    def move_to_trash(self, ticket_id: str) -> Path:
        _, path = self._find_ticket_path(ticket_id)
        trash_path = self._trash_path_for_ticket_path(path)
        try:
            trash_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(path, trash_path)
            return trash_path
        except FileNotFoundError as exc:
            raise TicketNotFoundError(ticket_id) from exc
        except OSError as exc:
            raise TicketDeleteError(ticket_id, str(exc)) from exc

    def restore_from_trash(self, ticket_id: str) -> Ticket:
        ticket, trash_path = self._find_trashed_ticket_path(ticket_id)
        restored_path = ticket_path(self.base_dir, ticket)
        try:
            if restored_path.exists():
                raise TicketAlreadyExistsError(ticket.id)
            restored_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(trash_path, restored_path)
        except FileNotFoundError as exc:
            raise TicketNotFoundError(ticket_id) from exc
        except TicketAlreadyExistsError:
            raise
        except OSError as exc:
            raise TicketDeleteError(ticket_id, str(exc)) from exc
        return self._read_ticket(restored_path, ticket_id=ticket.id)

    def delete(self, ticket_id: str, force: bool = False) -> None:
        if not force:
            self.move_to_trash(ticket_id)
            return

        _, path = self._find_ticket_path(ticket_id)
        try:
            path.unlink()
        except FileNotFoundError as exc:
            raise TicketNotFoundError(ticket_id) from exc
        except OSError as exc:
            raise TicketDeleteError(ticket_id, str(exc)) from exc

    def _next_id(self, category: Category) -> str:
        prefix = CATEGORY_PREFIXES[category]
        highest = 0
        if not self.base_dir.exists():
            return f"{prefix}1"

        for path in self._iter_ticket_paths(include_trash=True):
            stem_prefix = path.stem.split("-", 1)[0].upper()
            if not stem_prefix.startswith(prefix):
                continue
            suffix = stem_prefix[len(prefix) :]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        return f"{prefix}{highest + 1}"

    def _find_ticket_path(self, ticket_id: str) -> tuple[Ticket, Path]:
        normalized = ticket_id.upper()
        for path in self._iter_ticket_paths():
            stem_prefix = path.stem.split("-", 1)[0].upper()
            if stem_prefix == normalized:
                ticket = self._read_ticket(path, ticket_id=normalized)
                return ticket, path
        raise TicketNotFoundError(ticket_id)

    def _find_trashed_ticket_path(self, ticket_id: str) -> tuple[Ticket, Path]:
        normalized = ticket_id.upper()
        for path in self._iter_ticket_paths(include_trash=True, trash_only=True):
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
        # Normalize CRLF -> LF for cross-platform markdown file compatibility
        normalized = raw.replace("\r\n", "\n")
        if not normalized.startswith("---\n"):
            raise ValueError("Missing frontmatter")

        closing_marker = "\n---\n"
        end_index = normalized.find(closing_marker, 4)
        if end_index == -1:
            raise ValueError("Invalid frontmatter")

        frontmatter = normalized[4:end_index]
        body = normalized[end_index + len(closing_marker) :]
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
    def _ensure_utc(dt: datetime) -> datetime:
        """Ensure a datetime is timezone-aware (assume UTC if naive)."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

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
        created_after = filters.created_after
        if created_after is not None and ticket.created_at < (TicketStore._ensure_utc(created_after)):
            return False
        created_before = filters.created_before
        if created_before is not None and ticket.created_at > (TicketStore._ensure_utc(created_before)):
            return False
        updated_after = filters.updated_after
        if updated_after is not None and ticket.updated_at < (TicketStore._ensure_utc(updated_after)):
            return False
        updated_before = filters.updated_before
        if updated_before is not None and ticket.updated_at > (TicketStore._ensure_utc(updated_before)):
            return False
        if filters.tags and not all(tag in ticket.tags for tag in filters.tags):
            return False
        if filters.has_fix is not None and bool(ticket.fix) is not filters.has_fix:
            return False
        if filters.owner and ticket.owner != filters.owner:
            return False
        return True

    def _iter_ticket_paths(self, *, include_trash: bool = False, trash_only: bool = False) -> list[Path]:
        paths: list[Path] = []
        if not self.base_dir.exists():
            return paths

        for path in sorted(self.base_dir.rglob("*.md")):
            if not path.is_file():
                continue
            is_trash = self._is_trash_path(path)
            if trash_only and not is_trash:
                continue
            if not include_trash and is_trash:
                continue
            paths.append(path)
        return paths

    def _trash_path_for_ticket_path(self, path: Path) -> Path:
        relative_path = path.relative_to(self.base_dir)
        return self.base_dir / TRASH_DIRNAME / relative_path

    def _is_trash_path(self, path: Path) -> bool:
        try:
            relative_path = path.relative_to(self.base_dir)
        except ValueError:
            return False
        return bool(relative_path.parts) and relative_path.parts[0] == TRASH_DIRNAME

    def _sort_tickets(self, tickets: list[Ticket], sort_by: str | None) -> list[Ticket]:
        if not sort_by:
            return sorted(tickets, key=self._ticket_id_sort_key)

        reverse = sort_by.startswith("-")
        field = sort_by[1:] if reverse else sort_by
        key_func = self._sort_key_for_field(field)
        return sorted(tickets, key=key_func, reverse=reverse)

    @staticmethod
    def _ticket_id_sort_key(ticket: Ticket) -> tuple[str, int]:
        return (ticket.id[0], int(ticket.id[1:]))

    def _sort_key_for_field(self, field: str) -> Any:
        if field == "severity":
            return lambda ticket: (SEVERITY_ORDER[ticket.severity], self._ticket_id_sort_key(ticket))
        if field == "status":
            return lambda ticket: (STATUS_ORDER[ticket.status], self._ticket_id_sort_key(ticket))
        if field == "created_at":
            return lambda ticket: (ticket.created_at, self._ticket_id_sort_key(ticket))
        if field == "updated_at":
            return lambda ticket: (ticket.updated_at, self._ticket_id_sort_key(ticket))
        if field == "title":
            return lambda ticket: (ticket.title.lower(), self._ticket_id_sort_key(ticket))
        raise ValueError(f"Unsupported sort field: {field}")
