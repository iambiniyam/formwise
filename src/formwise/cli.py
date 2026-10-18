"""Command line interface for formwise."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .fields import fill_pdf, inspect_pdf
from .profile import SAMPLE, load_profile, save_profile, value_for_field

app = typer.Typer(help="Fill PDF forms locally from a private profile.", no_args_is_help=True)
console = Console()


@app.command()
def profile(out: Path = typer.Option(Path("profile.json"), "--out", "-o")) -> None:
    """Write a sample profile with private file permissions."""
    path = save_profile(dict(SAMPLE), out)
    console.print(f"wrote {path} with mode 0600. Edit it, then keep it private.")


@app.command()
def fields(pdf: Path = typer.Argument(..., exists=True)) -> None:
    """List the AcroForm fields in a PDF."""
    items, pages = inspect_pdf(pdf)
    console.print(f"{len(items)} fields across {pages} page(s)")
    table = Table("Field", "Type", "Value")
    for item in items:
        table.add_row(item.name, item.field_type, item.value)
    console.print(table)


@app.command()
def fill(
    pdf: Path = typer.Argument(..., exists=True),
    out: Path = typer.Option(Path("filled.pdf"), "--out", "-o"),
    profile_path: Path = typer.Option(Path("profile.json"), "--profile", "-p"),
    flatten: bool = typer.Option(False, "--flatten", help="Rasterize the filled PDF."),
    set_value: list[str] = typer.Option([], "--set", help="Override a field: name=value"),
) -> None:
    """Fill a PDF from a profile."""
    data = load_profile(profile_path)
    items, _pages = inspect_pdf(pdf)
    values = {item.name: value_for_field(item.name, data) for item in items}
    for raw in set_value:
        if "=" not in raw:
            raise typer.BadParameter("--set must be name=value")
        name, value = raw.split("=", 1)
        values[name] = value
    result = fill_pdf(pdf, out, values, flatten=flatten)
    console.print(f"wrote {result['output']} with {len(result['filled'])} fields")
    empty = [item.name for item in items if not values.get(item.name)]
    if empty:
        console.print(f"[yellow]left blank:[/yellow] {', '.join(empty)}")


@app.command()
def serve(port: int = typer.Option(8793, "--port")) -> None:
    """Start the local web UI."""
    import uvicorn

    uvicorn.run("formwise.server:app", host="127.0.0.1", port=port, log_level="warning")


@app.command()
def doctor() -> None:
    """Check the runtime and profile."""
    from .config import profile_path

    path = profile_path()
    console.print(f"profile: {path} ({'found' if path.exists() else 'not created'})")
    console.print("[green]ready[/green]")


if __name__ == "__main__":
    app()
