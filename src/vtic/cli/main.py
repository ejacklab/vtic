"""Command-line interface for vtic."""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

import typer
from pydantic import ValidationError as PydanticValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vtic.config import load_config
from vtic.errors import ValidationError as VticValidationError
from vtic.errors import VticError
from vtic.models import (
    Category,
    SearchFilters,
    SearchResponse,
    Severity,
    Status,
    Ticket,
    TicketResponse,
    TicketUpdate,
)
from vtic.search import TicketSearch
from vtic.storage import TicketStore
from vtic.utils import parse_repo, slugify

app = typer.Typer(help="vtic CLI")
console = Console()


class OutputFormat(StrEnum):
    TABLE = "table"
    JSON = "json"


def _resolve_store(tickets_dir: Path | None) -> TicketStore:
    config = load_config()
    base_dir = tickets_dir or config.effective_tickets_dir
    agent_id = config.shared.agent_id if config.shared.enabled else None
    return TicketStore(base_dir, agent_id=agent_id)


def _print_ticket(ticket: Ticket, title: str) -> None:
    tags = ", ".join(ticket.tags) if ticket.tags else "-"
    body = "\n".join(
        [
            f"[bold]ID:[/bold] {ticket.id}",
            f"[bold]Title:[/bold] {ticket.title}",
            f"[bold]Repo:[/bold] {ticket.repo}",
            f"[bold]Category:[/bold] {ticket.category.value}",
            f"[bold]Severity:[/bold] {ticket.severity.value}",
            f"[bold]Status:[/bold] {ticket.status.value}",
            f"[bold]Owner:[/bold] {ticket.owner or '-'}",
            f"[bold]File:[/bold] {ticket.file or '-'}",
            f"[bold]Tags:[/bold] {tags}",
            f"[bold]Due Date:[/bold] {ticket.due_date.isoformat() if ticket.due_date else '-'}",
            "",
            ticket.description or "",
        ]
    ).rstrip()
    if ticket.fix:
        body = f"{body}\n\n[bold]Fix[/bold]\n{ticket.fix}"
    console.print(Panel(body, title=title, expand=False))


def _write_json(payload: str) -> None:
    typer.echo(payload)


def _ticket_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse.from_ticket(ticket)


def _print_ticket_json(ticket: Ticket) -> None:
    _write_json(_ticket_response(ticket).model_dump_json())


def _print_ticket_list_json(tickets: list[Ticket]) -> None:
    payload = [_ticket_response(ticket).model_dump(mode="json") for ticket in tickets]
    _write_json(json.dumps(payload))


def _print_search_json(response: SearchResponse) -> None:
    _write_json(response.model_dump_json())


def _parse_datetime_option(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        _exit_with_validation_error(f"Invalid datetime value: {value}")
        raise AssertionError("unreachable") from exc


def _exit_with_error(exc: VticError) -> None:
    console.print(f"[red]{exc.message}[/red]")
    raise typer.Exit(code=1) from exc


def _exit_with_validation_error(message: str) -> None:
    _exit_with_error(VticValidationError(message))


@app.command()
def init(
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Initialize the tickets directory."""

    try:
        store = _resolve_store(dir)
        store.base_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]Initialized tickets directory:[/green] {store.base_dir}")
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def create(
    repo: str = typer.Option(..., "--repo", help="Repository in owner/repo format"),
    owner: str | None = typer.Option(None, "--owner", help="Ticket owner"),
    category: Category = typer.Option(
        Category.CODE_QUALITY, "--category", help="Ticket category"
    ),
    severity: Severity = typer.Option(
        Severity.MEDIUM, "--severity", help="Ticket severity"
    ),
    status: Status = typer.Option(
        Status.OPEN, "--status", help="Initial ticket status"
    ),
    title: str = typer.Option(..., "--title", help="Ticket title"),
    description: str | None = typer.Option(
        None, "--description", help="Ticket description"
    ),
    fix: str | None = typer.Option(None, "--fix", help="Fix description"),
    file: str | None = typer.Option(None, "--file", help="File reference"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    due_date: str | None = typer.Option(
        None, "--due-date", help="Due date (YYYY-MM-DD)"
    ),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Create a ticket."""

    try:
        store = _resolve_store(dir)
        derived_owner, _ = parse_repo(repo)
        parsed_due_date: date | None = None
        if due_date:
            parsed_due_date = date.fromisoformat(due_date)
        ticket = store.create_ticket(
            title=title,
            repo=repo,
            owner=owner or derived_owner.lower(),
            category=category,
            severity=severity,
            status=status,
            description=description,
            fix=fix,
            file=file,
            tags=tags.split(",") if tags else [],
            slug=slugify(title),
            due_date=parsed_due_date,
        )
        _print_ticket(ticket, "Created Ticket")
    except (ValueError, PydanticValidationError) as exc:
        _exit_with_validation_error(str(exc))
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def get(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE, "--format", help="Output format"
    ),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Get a ticket."""

    try:
        ticket = _resolve_store(dir).get(ticket_id)
        if format is OutputFormat.JSON:
            _print_ticket_json(ticket)
        else:
            _print_ticket(ticket, "Ticket")
    except VticError as exc:
        _exit_with_error(exc)


@app.command(name="list")
def list_tickets(
    repo: str | None = typer.Option(None, "--repo", help="Filter by repo"),
    owner: str | None = typer.Option(None, "--owner", help="Filter by owner"),
    tags: str | None = typer.Option(
        None, "--tags", help="Filter by comma-separated tags"
    ),
    category: Category | None = typer.Option(
        None, "--category", help="Filter by category"
    ),
    severity: Severity | None = typer.Option(
        None, "--severity", help="Filter by severity"
    ),
    status: Status | None = typer.Option(None, "--status", help="Filter by status"),
    created_after: str | None = typer.Option(
        None, "--created-after", help="Filter by created_at >= timestamp"
    ),
    created_before: str | None = typer.Option(
        None, "--created-before", help="Filter by created_at <= timestamp"
    ),
    updated_after: str | None = typer.Option(
        None, "--updated-after", help="Filter by updated_at >= timestamp"
    ),
    updated_before: str | None = typer.Option(
        None, "--updated-before", help="Filter by updated_at <= timestamp"
    ),
    due_before: str | None = typer.Option(
        None, "--due-before", help="Filter by due_date <= YYYY-MM-DD"
    ),
    due_after: str | None = typer.Option(
        None, "--due-after", help="Filter by due_date >= YYYY-MM-DD"
    ),
    sort: str | None = typer.Option(
        None,
        "--sort",
        help="Sort by severity, status, created_at, updated_at, due_date, title",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE, "--format", help="Output format"
    ),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """List tickets."""

    try:
        filters = SearchFilters(
            repo=[repo] if repo else None,
            owner=owner,
            tags=tags.split(",") if tags else None,
            category=[category] if category else None,
            severity=[severity] if severity else None,
            status=[status] if status else None,
            created_after=_parse_datetime_option(created_after),
            created_before=_parse_datetime_option(created_before),
            updated_after=_parse_datetime_option(updated_after),
            updated_before=_parse_datetime_option(updated_before),
            due_before=date.fromisoformat(due_before) if due_before else None,
            due_after=date.fromisoformat(due_after) if due_after else None,
        )
        tickets = _resolve_store(dir).list(filters, sort_by=sort)

        if format is OutputFormat.JSON:
            _print_ticket_list_json(tickets)
            return

        table = Table(title="Tickets")
        for column in ("ID", "Title", "Category", "Severity", "Status", "Repo"):
            table.add_column(column)
        for ticket in tickets:
            table.add_row(
                ticket.id,
                ticket.title,
                ticket.category.value,
                ticket.severity.value,
                ticket.status.value,
                ticket.repo,
            )
        console.print(table)
    except (ValueError, PydanticValidationError) as exc:
        _exit_with_validation_error(str(exc))
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query text"),
    severity: Severity | None = typer.Option(
        None, "--severity", help="Filter by severity"
    ),
    repo: str | None = typer.Option(None, "--repo", help="Filter by repo"),
    category: Category | None = typer.Option(
        None, "--category", help="Filter by category"
    ),
    status: Status | None = typer.Option(None, "--status", help="Filter by status"),
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE, "--format", help="Output format"
    ),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Search tickets by keyword."""
    try:
        store = _resolve_store(dir)
        filters = SearchFilters(
            severity=[severity] if severity else None,
            repo=[repo] if repo else None,
            category=[category] if category else None,
            status=[status] if status else None,
        )
        engine = TicketSearch(store)
        response = engine.search(query, filters=filters)

        if format is OutputFormat.JSON:
            _print_search_json(response)
            return

        if not response.results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(
            title=f"Search Results ({response.total} matches, {response.took_ms}ms)"
        )
        for column in ("Score", "ID", "Title", "Severity", "Status", "Repo"):
            table.add_column(column)
        for result in response.results:
            table.add_row(
                f"{result.score:.2f}",
                result.id,
                result.title,
                result.severity,
                result.status,
                result.repo,
            )
        console.print(table)
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def update(
    id: str = typer.Option(..., "--id", help="Ticket ID"),
    status: Status | None = typer.Option(None, "--status", help="New status"),
    severity: Severity | None = typer.Option(
        None, "--severity", help="New severity"
    ),
    fix: str | None = typer.Option(None, "--fix", help="New fix description"),
    owner: str | None = typer.Option(None, "--owner", help="New owner"),
    category: str | None = typer.Option(None, "--category", help="New category"),
    file: str | None = typer.Option(None, "--file", help="New file reference"),
    tags: str | None = typer.Option(None, "--tags", help="New comma-separated tags"),
    title: str | None = typer.Option(None, "--title", help="New title"),
    description: str | None = typer.Option(
        None, "--description", help="New description"
    ),
    assignee: str | None = typer.Option(None, "--assignee", help="Assign ticket to agent"),
    due_date: str | None = typer.Option(
        None, "--due-date", help="Due date (YYYY-MM-DD, or 'none' to clear)"
    ),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Update a ticket."""

    try:
        update_data: dict[str, object] = {}
        if status is not None:
            update_data["status"] = status
        if severity is not None:
            update_data["severity"] = severity
        if fix is not None:
            update_data["fix"] = fix
        if owner is not None:
            update_data["owner"] = owner
        if category is not None:
            update_data["category"] = Category(category)
        if file is not None:
            update_data["file"] = file
        if tags is not None:
            update_data["tags"] = tags.split(",")
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if assignee is not None:
            update_data["assignee"] = assignee
        if due_date is not None:
            if due_date.lower() == "none":
                update_data["due_date"] = None
            else:
                update_data["due_date"] = date.fromisoformat(due_date)

        updates = TicketUpdate(**update_data)
        ticket = _resolve_store(dir).update(id, updates)
        _print_ticket(ticket, "Updated Ticket")
    except (ValueError, PydanticValidationError) as exc:
        _exit_with_validation_error(str(exc))
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def serve(
    host: str | None = typer.Option(None, "--host", help="Bind address"),
    port: int | None = typer.Option(
        None, "--port", min=1, max=65535, help="Server port"
    ),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Start the HTTP API server."""

    import uvicorn
    from vtic.api import create_app

    config = load_config()
    tickets_dir = dir or config.effective_tickets_dir
    app_instance = create_app(str(tickets_dir))
    uvicorn.run(
        app_instance,
        host=host or config.server.host,
        port=port or config.server.port,
    )


@app.command()
def delete(
    id: str = typer.Option(..., "--id", help="Ticket ID"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
    force: bool = typer.Option(
        False, "--force", help="Permanently delete instead of moving to trash"
    ),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Delete a ticket."""

    try:
        if not yes and not typer.confirm(f"Delete ticket {id}?"):
            console.print("[yellow]Deletion cancelled[/yellow]")
            raise typer.Exit(code=0)
        _resolve_store(dir).delete(id, force=force)
        if force:
            console.print(f"[green]Permanently deleted:[/green] {id.upper()}")
        else:
            console.print(f"[green]Deleted (moved to trash):[/green] {id.upper()}")
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def reindex(
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Rebuild the search index."""

    try:
        store = _resolve_store(dir)
        engine = TicketSearch(store)
        engine.build_index(persist=True)
        console.print(f"[green]Rebuilt BM25 index for:[/green] {store.base_dir}")
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def restore(
    id: str = typer.Option(..., "--id", help="Ticket ID to restore from trash"),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Restore a soft-deleted ticket from trash."""

    try:
        ticket = _resolve_store(dir).restore_from_trash(id)
        console.print(f"[green]Restored ticket:[/green] {ticket.id}")
        _print_ticket(ticket, "Restored Ticket")
    except VticError as exc:
        _exit_with_error(exc)


@app.callback()
def main() -> None:
    """vtic CLI."""
