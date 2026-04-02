"""Command-line interface for vtic."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vtic.config import load_config
from vtic.errors import VticError
from vtic.models import Category, SearchFilters, Severity, Status, Ticket, TicketUpdate
from vtic.search import TicketSearch
from vtic.storage import TicketStore
from vtic.utils import normalize_tags, parse_repo, slugify, utc_now

app = typer.Typer(help="vtic CLI")
console = Console()


def _resolve_store(tickets_dir: Path | None) -> TicketStore:
    config = load_config()
    base_dir = tickets_dir or config.tickets.dir
    return TicketStore(base_dir)


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
            "",
            ticket.description or "",
        ]
    ).rstrip()
    if ticket.fix:
        body = f"{body}\n\n[bold]Fix[/bold]\n{ticket.fix}"
    console.print(Panel(body, title=title, expand=False))


def _exit_with_error(exc: VticError) -> None:
    console.print(f"[red]{exc.message}[/red]")
    raise typer.Exit(code=1) from exc


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
    category: Category = typer.Option(Category.CODE_QUALITY, "--category", help="Ticket category"),
    severity: Severity = typer.Option(Severity.MEDIUM, "--severity", help="Ticket severity"),
    title: str = typer.Option(..., "--title", help="Ticket title"),
    description: str | None = typer.Option(None, "--description", help="Ticket description"),
    file: str | None = typer.Option(None, "--file", help="File reference"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Create a ticket."""

    try:
        store = _resolve_store(dir)
        now = utc_now()
        owner, _ = parse_repo(repo)
        ticket = Ticket(
            id=store.next_id(category),
            title=title,
            description=description,
            repo=repo,
            owner=owner,
            category=category,
            severity=severity,
            status=Status.OPEN,
            file=file,
            tags=normalize_tags(tags.split(",")) if tags else [],
            created_at=now,
            updated_at=now,
            slug=slugify(title),
        )
        store.create(ticket)
        _print_ticket(ticket, "Created Ticket")
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def get(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Get a ticket."""

    try:
        ticket = _resolve_store(dir).get(ticket_id)
        _print_ticket(ticket, "Ticket")
    except VticError as exc:
        _exit_with_error(exc)


@app.command(name="list")
def list_tickets(
    repo: str | None = typer.Option(None, "--repo", help="Filter by repo"),
    category: Category | None = typer.Option(None, "--category", help="Filter by category"),
    severity: Severity | None = typer.Option(None, "--severity", help="Filter by severity"),
    status: Status | None = typer.Option(None, "--status", help="Filter by status"),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """List tickets."""

    try:
        filters = SearchFilters(
            repo=[repo] if repo else None,
            category=[category] if category else None,
            severity=[severity] if severity else None,
            status=[status] if status else None,
        )
        tickets = _resolve_store(dir).list(filters)

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
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query text"),
    severity: Severity | None = typer.Option(None, "--severity", help="Filter by severity"),
    repo: str | None = typer.Option(None, "--repo", help="Filter by repo"),
    category: Category | None = typer.Option(None, "--category", help="Filter by category"),
    status: Status | None = typer.Option(None, "--status", help="Filter by status"),
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

        if not response.results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f"Search Results ({response.total} matches, {response.took_ms}ms)")
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
    severity: Severity | None = typer.Option(None, "--severity", help="New severity"),
    description: str | None = typer.Option(None, "--description", help="New description"),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Update a ticket."""

    try:
        updates = TicketUpdate(
            status=status,
            severity=severity,
            description=description,
        )
        ticket = _resolve_store(dir).update(id, updates)
        _print_ticket(ticket, "Updated Ticket")
    except VticError as exc:
        _exit_with_error(exc)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind address"),
    port: int = typer.Option(8900, "--port", help="Server port"),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Start the HTTP API server."""

    import uvicorn
    from vtic.api import create_app

    config = load_config()
    tickets_dir = dir or config.tickets.dir
    app_instance = create_app(str(tickets_dir))
    uvicorn.run(app_instance, host=host, port=port)


@app.command()
def delete(
    id: str = typer.Option(..., "--id", help="Ticket ID"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
    dir: Path | None = typer.Option(None, "--dir", help="Tickets directory"),
) -> None:
    """Delete a ticket."""

    try:
        if not yes and not typer.confirm(f"Delete ticket {id}?"):
            console.print("[yellow]Deletion cancelled[/yellow]")
            raise typer.Exit(code=0)
        _resolve_store(dir).delete(id)
        console.print(f"[green]Deleted ticket:[/green] {id.upper()}")
    except VticError as exc:
        _exit_with_error(exc)


@app.callback()
def main() -> None:
    """vtic CLI."""
