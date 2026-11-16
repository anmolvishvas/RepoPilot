"""CLI entry point for RepoPilot."""

from __future__ import annotations

import typer
import uvicorn
from rich.console import Console

from repopilot.mcp.server import main as run_mcp_server

app = typer.Typer(
    name="repopilot",
    help="Autonomous Codebase Modernization & Migration Agent.",
    add_completion=False,
)
console = Console()


@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """Start the RepoPilot FastAPI SSE Gateway server."""
    console.print(
        f"[bold green]Starting RepoPilot API Gateway[/bold green] on http://{host}:{port}"
    )
    uvicorn.run("repopilot.server.app:app", host=host, port=port, reload=reload)


@app.command()
def mcp() -> None:
    """Start the RepoPilot FastMCP Code Server over standard I/O."""
    console.print("[bold blue]Starting RepoPilot FastMCP Code Server over STDIO...[/bold blue]")
    run_mcp_server()


@app.command()
def version() -> None:
    """Show the RepoPilot version."""
    console.print(
        "[bold cyan]RepoPilot v0.1.0[/bold cyan] - Autonomous Codebase Modernization Agent"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
