"""VTIC CLI - Command line interface for the vtic ticket system."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional

import httpx
import toml
import typer
from rich.console import Console
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vtic.models.config import Config, load_config
from vtic.models.enums import Category, Severity, Status

app = typer.Typer(
    name="vtic",
    help="VTIC - Vector Ticket System with BM25 search",
    no_args_is_help=True,
)
console = Console()

DEFAULT_CONFIG = """# VTIC Configuration File
# Documentation: https://vtic.ejai.ai/docs

[storage]
dir = "./tickets"

[api]
host = "127.0.0.1"
port = 8080

[search]
bm25_enabled = true
semantic_enabled = false
bm25_weight = 0.6
semantic_weight = 0.4

[embeddings]
provider = "local"
model = "all-MiniLM-L6-v2"
dimension = 384
"""

API_BASE_URL = "http://localhost:8080"


def get_api_url() -> str:
    """Get API base URL from config or default."""
    try:
        config = load_config()
        return f"http://{config.api.host}:{config.api.port}"
    except Exception:
        return API_BASE_URL


def handle_api_error(response: httpx.Response) -> None:
    """Handle API error responses."""
    try:
        data = response.json()
        if "error" in data:
            error = data["error"]
            console.print(f"[red]Error: {error.get('code', 'UNKNOWN')}[/red]")
            console.print(f"[red]{error.get('message', 'An error occurred')}[/red]")
            if "details" in error and error["details"]:
                for detail in error["details"]:
                    field = detail.get("field", "")
                    msg = detail.get("message", "")
                    console.print(f"[yellow]  - {field}: {msg}[/yellow]")
        else:
            console.print(f"[red]Error: HTTP {response.status_code}[/red]")
    except Exception:
        console.print(f"[red]Error: HTTP {response.status_code}[/red]")
        console.print(f"[red]{response.text}[/red]")
    raise typer.Exit(1)


@app.command()
def init(
    path: Annotated[Optional[Path], typer.Argument(help="Path to initialize the vtic project")] = None,
) -> None:
    """Initialize a new vtic project with directory structure and config."""
    target_path = path or Path(".")
    target_path = target_path.resolve()
    
    # Create tickets directory
    tickets_dir = target_path / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    
    # Write default config
    config_path = target_path / "vtic.toml"
    if config_path.exists():
        console.print(f"[yellow]Config already exists at {config_path}[/yellow]")
    else:
        config_path.write_text(DEFAULT_CONFIG)
        console.print(f"[green]Created config: {config_path}[/green]")
    
    # Initialize Zvec index placeholder (actual index creation happens on first server start)
    index_dir = target_path / ".vtic"
    index_dir.mkdir(exist_ok=True)
    
    console.print(f"[green]Initialized vtic project at {target_path}[/green]")
    console.print(f"[dim]  - Tickets directory: {tickets_dir}[/dim]")
    console.print(f"[dim]  - Config file: {config_path}[/dim]")
    console.print(f"[dim]  - Index directory: {index_dir}[/dim]")
    console.print("\n[blue]Run 'vtic serve' to start the server[/blue]")


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", help="Host to bind the server to")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind the server to")] = 8080,
    reload: Annotated[bool, typer.Option("--reload", help="Enable auto-reload on code changes")] = False,
) -> None:
    """Start the vtic API server with uvicorn."""
    # Try to load config for better UX
    try:
        config = load_config()
        # Override with CLI args if explicitly provided or use config values
        host = host or config.api.host
        port = port or config.api.port
    except Exception:
        pass
    
    console.print(f"[green]Starting vtic server at http://{host}:{port}[/green]")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "vtic.api.app:app",
        "--host", host,
        "--port", str(port),
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")


@app.command()
def create(
    title: Annotated[str, typer.Option("--title", "-t", help="Ticket title", prompt=True)],
    description: Annotated[str, typer.Option("--description", "-d", help="Ticket description")] = "",
    severity: Annotated[Optional[Severity], typer.Option("--severity", "-s", help="Ticket severity")] = None,
    category: Annotated[Optional[Category], typer.Option("--category", "-c", help="Ticket category")] = None,
    repo: Annotated[str, typer.Option("--repo", "-r", help="Repository (owner/repo format)")] = "",
    status: Annotated[Optional[Status], typer.Option("--status", help="Initial status")] = None,
    assignee: Annotated[Optional[str], typer.Option("--assignee", "-a", help="Assigned user")] = None,
    tags: Annotated[Optional[list[str]], typer.Option("--tag", help="Tags (can be used multiple times)")] = None,
) -> None:
    """Create a new ticket."""
    # Build request body
    body: dict = {"title": title}
    
    # Handle description - use title if not provided via option
    if description:
        body["description"] = description
    else:
        # If running interactively, prompt for description
        body["description"] = typer.prompt("Description", default=title)
    
    # Handle repo - prompt if not provided
    if repo:
        body["repo"] = repo
    else:
        body["repo"] = typer.prompt("Repository (owner/repo)")
    
    if severity:
        body["severity"] = severity.value
    if category:
        body["category"] = category.value
    if status:
        body["status"] = status.value
    if assignee:
        body["assignee"] = assignee
    if tags:
        body["tags"] = tags
    
    api_url = get_api_url()
    
    try:
        response = httpx.post(f"{api_url}/tickets", json=body, timeout=30.0)
        if response.status_code == 201:
            data = response.json()
            ticket = data.get("data", {})
            console.print(f"[green]Created ticket {ticket.get('id')}: {ticket.get('title')}[/green]")
            console.print(json.dumps(data, indent=2))
        else:
            handle_api_error(response)
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to server at {api_url}[/red]")
        console.print("[yellow]Make sure the server is running: vtic serve[/yellow]")
        raise typer.Exit(1)
    except httpx.TimeoutException:
        console.print("[red]Error: Request timed out[/red]")
        raise typer.Exit(1)


@app.command()
def get(
    ticket_id: Annotated[str, typer.Argument(help="Ticket ID (e.g., C1, F12)")],
) -> None:
    """Get a ticket by ID."""
    api_url = get_api_url()
    
    try:
        response = httpx.get(f"{api_url}/tickets/{ticket_id}", timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            console.print(json.dumps(data, indent=2, default=str))
        elif response.status_code == 404:
            console.print(f"[red]Error: Ticket '{ticket_id}' not found[/red]")
            raise typer.Exit(1)
        else:
            handle_api_error(response)
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to server at {api_url}[/red]")
        console.print("[yellow]Make sure the server is running: vtic serve[/yellow]")
        raise typer.Exit(1)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    severity: Annotated[Optional[list[Severity]], typer.Option("--severity", "-s", help="Filter by severity")] = None,
    category: Annotated[Optional[list[Category]], typer.Option("--category", "-c", help="Filter by category")] = None,
    status: Annotated[Optional[list[Status]], typer.Option("--status", help="Filter by status")] = None,
    repo: Annotated[Optional[list[str]], typer.Option("--repo", "-r", help="Filter by repo")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 10,
    offset: Annotated[int, typer.Option("--offset", help="Pagination offset")] = 0,
    semantic: Annotated[bool, typer.Option("--semantic", help="Enable semantic search")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON instead of table")] = False,
) -> None:
    """Search tickets using BM25 or hybrid search."""
    body: dict = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "semantic": semantic,
    }
    
    # Build filters
    filters: dict = {}
    if severity:
        filters["severity"] = [s.value for s in severity]
    if category:
        filters["category"] = [c.value for c in category]
    if status:
        filters["status"] = [s.value for s in status]
    if repo:
        filters["repo"] = repo
    
    if filters:
        body["filters"] = filters
    
    api_url = get_api_url()
    
    try:
        response = httpx.post(f"{api_url}/search", json=body, timeout=30.0)
        if response.status_code == 200:
            data = response.json()
            
            if json_output:
                console.print(json.dumps(data, indent=2, default=str))
                return
            
            # Display as table
            hits = data.get("hits", [])
            total = data.get("total", 0)
            
            if not hits:
                console.print(f"[yellow]No results found for '{query}'[/yellow]")
                return
            
            table = Table(title=f"Search Results: '{query}' ({total} total)")
            table.add_column("ID", style="cyan")
            table.add_column("Score", style="magenta")
            table.add_column("Source", style="green")
            table.add_column("Highlight")
            
            for hit in hits:
                table.add_row(
                    hit.get("ticket_id", "N/A"),
                    f"{hit.get('score', 0):.3f}",
                    hit.get("source", "bm25"),
                    hit.get("highlight", "")[:60] + "..." if hit.get("highlight") else "",
                )
            
            console.print(table)
            
            # Show meta info
            meta = data.get("meta", {})
            if meta:
                console.print(f"\n[dim]Latency: {meta.get('latency_ms', 'N/A')}ms | "
                            f"BM25 weight: {meta.get('bm25_weight', 'N/A')} | "
                            f"Semantic: {meta.get('semantic_used', False)}[/dim]")
        else:
            handle_api_error(response)
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to server at {api_url}[/red]")
        console.print("[yellow]Make sure the server is running: vtic serve[/yellow]")
        raise typer.Exit(1)
    except httpx.TimeoutException:
        console.print("[red]Error: Request timed out[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_tickets(
    status: Annotated[Optional[list[Status]], typer.Option("--status", "-s", help="Filter by status")] = None,
    severity: Annotated[Optional[list[Severity]], typer.Option("--severity", help="Filter by severity")] = None,
    category: Annotated[Optional[list[Category]], typer.Option("--category", "-c", help="Filter by category")] = None,
    repo: Annotated[Optional[list[str]], typer.Option("--repo", "-r", help="Filter by repo")] = None,
    assignee: Annotated[Optional[str], typer.Option("--assignee", "-a", help="Filter by assignee")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 20,
    offset: Annotated[int, typer.Option("--offset", help="Pagination offset")] = 0,
    sort: Annotated[str, typer.Option("--sort", help="Sort field (prefix - for desc)")] = "-created",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON instead of table")] = False,
) -> None:
    """List tickets with optional filtering."""
    # Build query params
    params: dict = {
        "limit": limit,
        "offset": offset,
        "sort": sort,
    }
    
    if status:
        params["status"] = ",".join(s.value for s in status)
    if severity:
        params["severity"] = ",".join(s.value for s in severity)
    if category:
        params["category"] = ",".join(c.value for c in category)
    if repo:
        params["repo"] = ",".join(repo)
    if assignee:
        params["assignee"] = assignee
    
    api_url = get_api_url()
    
    try:
        response = httpx.get(f"{api_url}/tickets", params=params, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            
            if json_output:
                console.print(json.dumps(data, indent=2, default=str))
                return
            
            # Display as table
            tickets = data.get("data", [])
            meta = data.get("meta", {})
            total = meta.get("total", 0)
            
            if not tickets:
                console.print("[yellow]No tickets found[/yellow]")
                return
            
            table = Table(title=f"Tickets ({len(tickets)} of {total})")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Severity", style="red")
            table.add_column("Status", style="green")
            table.add_column("Category", style="blue")
            table.add_column("Repo", style="dim")
            
            for ticket in tickets:
                sev_color = {
                    "critical": "red",
                    "high": "orange3",
                    "medium": "yellow",
                    "low": "green",
                    "info": "blue",
                }.get(ticket.get("severity", ""), "white")
                
                table.add_row(
                    ticket.get("id", "N/A"),
                    ticket.get("title", "")[:40],
                    f"[{sev_color}]{ticket.get('severity', 'N/A')}[/{sev_color}]",
                    ticket.get("status", "N/A"),
                    ticket.get("category", "N/A"),
                    ticket.get("repo", "")[:20],
                )
            
            console.print(table)
            
            if meta.get("has_more"):
                console.print(f"\n[dim]Use --offset {offset + limit} for more results[/dim]")
        else:
            handle_api_error(response)
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to server at {api_url}[/red]")
        console.print("[yellow]Make sure the server is running: vtic serve[/yellow]")
        raise typer.Exit(1)


@app.command()
def update(
    ticket_id: Annotated[str, typer.Argument(help="Ticket ID to update")],
    title: Annotated[Optional[str], typer.Option("--title", "-t", help="New title")] = None,
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="New description")] = None,
    status: Annotated[Optional[Status], typer.Option("--status", "-s", help="New status")] = None,
    severity: Annotated[Optional[Severity], typer.Option("--severity", help="New severity")] = None,
    category: Annotated[Optional[Category], typer.Option("--category", "-c", help="New category")] = None,
    assignee: Annotated[Optional[str], typer.Option("--assignee", "-a", help="New assignee (or null to clear)")] = None,
    fix: Annotated[Optional[str], typer.Option("--fix", "-f", help="Resolution details")] = None,
) -> None:
    """Update a ticket (partial update)."""
    body: dict = {}
    
    if title:
        body["title"] = title
    if description:
        body["description"] = description
    if status:
        body["status"] = status.value
    if severity:
        body["severity"] = severity.value
    if category:
        body["category"] = category.value
    if assignee is not None:
        body["assignee"] = assignee
    if fix:
        body["fix"] = fix
    
    if not body:
        console.print("[yellow]No fields to update. Provide at least one field.[/yellow]")
        raise typer.Exit(1)
    
    api_url = get_api_url()
    
    try:
        response = httpx.patch(f"{api_url}/tickets/{ticket_id}", json=body, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            ticket = data.get("data", {})
            console.print(f"[green]Updated ticket {ticket.get('id')}: {ticket.get('title')}[/green]")
            console.print(json.dumps(data, indent=2, default=str))
        elif response.status_code == 404:
            console.print(f"[red]Error: Ticket '{ticket_id}' not found[/red]")
            raise typer.Exit(1)
        else:
            handle_api_error(response)
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to server at {api_url}[/red]")
        console.print("[yellow]Make sure the server is running: vtic serve[/yellow]")
        raise typer.Exit(1)


@app.command()
def delete(
    ticket_id: Annotated[str, typer.Argument(help="Ticket ID to delete")],
    force: Annotated[bool, typer.Option("--force", help="Permanent deletion (skip trash)")] = False,
) -> None:
    """Delete a ticket (soft delete by default)."""
    api_url = get_api_url()
    
    params = {"force": "true"} if force else {}
    
    try:
        response = httpx.delete(f"{api_url}/tickets/{ticket_id}", params=params, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            if force:
                console.print(f"[green]Permanently deleted ticket {ticket_id}[/green]")
            else:
                console.print(f"[green]Moved ticket {ticket_id} to trash[/green]")
                console.print("[dim]Use --force for permanent deletion[/dim]")
        elif response.status_code == 404:
            console.print(f"[red]Error: Ticket '{ticket_id}' not found[/red]")
            raise typer.Exit(1)
        else:
            handle_api_error(response)
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to server at {api_url}[/red]")
        console.print("[yellow]Make sure the server is running: vtic serve[/yellow]")
        raise typer.Exit(1)


@app.command()
def health() -> None:
    """Check server health status."""
    api_url = get_api_url()
    
    try:
        response = httpx.get(f"{api_url}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            
            status_color = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
            }.get(status, "white")
            
            console.print(f"[green]Server status:[/green] [{status_color}]{status}[/{status_color}]")
            console.print(f"[dim]Version: {data.get('version', 'N/A')}[/dim]")
            
            index_status = data.get("index_status", {})
            console.print(f"[dim]Index: {index_status.get('zvec', 'N/A')} "
                        f"({index_status.get('ticket_count', 0)} tickets)[/dim]")
            
            embedding = data.get("embedding_provider", {})
            console.print(f"[dim]Embeddings: {embedding.get('name', 'none')} "
                        f"({embedding.get('model', 'N/A')})[/dim]")
        elif response.status_code == 503:
            data = response.json()
            console.print(f"[red]Server unhealthy: {data.get('status', 'unknown')}[/red]")
            raise typer.Exit(1)
        else:
            handle_api_error(response)
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to server at {api_url}[/red]")
        console.print("[yellow]Make sure the server is running: vtic serve[/yellow]")
        raise typer.Exit(1)


@app.command()
def doctor() -> None:
    """Run system diagnostics and health checks."""
    api_url = get_api_url()
    
    try:
        response = httpx.get(f"{api_url}/doctor", timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            overall = data.get("overall", "unknown")
            checks = data.get("checks", [])
            
            status_color = {
                "ok": "green",
                "warnings": "yellow",
                "errors": "red",
            }.get(overall, "white")
            
            console.print(f"[bold]Overall status:[/bold] [{status_color}]{overall}[/{status_color}]")
            console.print()
            
            for check in checks:
                check_status = check.get("status", "unknown")
                check_color = {
                    "ok": "green",
                    "warning": "yellow",
                    "error": "red",
                }.get(check_status, "white")
                
                console.print(f"  [{check_color}]{check_status.upper()}[/{check_color}] {check.get('name', 'unknown')}")
                if check.get("message"):
                    console.print(f"      {check['message']}")
                if check.get("fix"):
                    console.print(f"      [blue]Fix: {check['fix']}[/blue]")
            
            if overall == "errors":
                raise typer.Exit(1)
            elif overall == "warnings":
                raise typer.Exit(0)  # Warnings are OK for exit code
        else:
            handle_api_error(response)
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to server at {api_url}[/red]")
        console.print("[yellow]Make sure the server is running: vtic serve[/yellow]")
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
