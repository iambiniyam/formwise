"""Command line interface for formwise."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .audit import load_audit, totals
from .batch import fill_folder
from .fields import fill_pdf, inspect_pdf
from .profile import SAMPLE, ProfileLocked, load_profile, save_profile, value_for_field

app = typer.Typer(help="Fill PDF forms locally from a private profile.", no_args_is_help=True)
console = Console()


@app.callback(invoke_without_command=True)
def _root(
    version: bool = typer.Option(False, "--version", is_eager=True, help="Show the version and exit."),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()



@app.command()
def profile(
    out: Path = typer.Option(Path("profile.json"), "--out", "-o"),
    encrypt: bool = typer.Option(False, "--encrypt", help="Require a passphrase to read the profile."),
) -> None:
    """Write a sample profile with private file permissions."""
    password = None
    if encrypt:
        password = typer.prompt("Passphrase", hide_input=True, confirmation_prompt=True)
    path = save_profile(dict(SAMPLE), out, password=password)
    note = "encrypted" if password else "plain JSON"
    console.print(f"wrote {path} ({note}) with mode 0600. Edit it, then keep it private.")


@app.command()
def fields(pdf: Path = typer.Argument(..., exists=True)) -> None:
    """List the AcroForm fields in a PDF."""
    items, pages = inspect_pdf(pdf)
    console.print(f"{len(items)} fields across {pages} page(s)")
    if not items:
        console.print("[yellow]No AcroForm fields found. This is likely a scanned form; fill needs an AcroForm.[/yellow]")
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
    passphrase: str | None = typer.Option(None, "--passphrase", help="Passphrase for an encrypted profile."),
) -> None:
    """Fill a PDF from a profile."""
    try:
        data = load_profile(profile_path, password=passphrase)
    except ProfileLocked as exc:
        if passphrase is None:
            passphrase = typer.prompt("Profile passphrase", hide_input=True)
        try:
            data = load_profile(profile_path, password=passphrase)
        except ProfileLocked:
            console.print("[red]The profile could not be unlocked. Check the passphrase.[/red]")
            raise typer.Exit(code=2) from exc
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
def batch(
    folder: Path = typer.Argument(..., exists=True, file_okay=False),
    out: Path = typer.Option(Path("filled"), "--out", "-o"),
    profile_path: Path = typer.Option(Path("profile.json"), "--profile", "-p"),
    flatten: bool = typer.Option(False, "--flatten"),
    passphrase: str | None = typer.Option(None, "--passphrase"),
) -> None:
    """Fill every PDF in a folder and write an audit log."""
    try:
        data = load_profile(profile_path, password=passphrase)
    except ProfileLocked:
        data = load_profile(
            profile_path,
            password=passphrase or typer.prompt("Profile passphrase", hide_input=True),
        )
    result = fill_folder(folder, out, data, flatten=flatten)
    failed = [item for item in result["files"] if item.get("error")]
    console.print(f"wrote {len(result['files']) - len(failed)} files to {out}")
    console.print(f"audit: {result['audit']}")
    if failed:
        for item in failed:
            console.print(f"[red]{item['input']}: {item['error']}[/red]")
        raise typer.Exit(code=1)


@app.command()
def audit(path: Path = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    """Summarize a batch audit log."""
    try:
        payload = load_audit(path)
    except (ValueError, TypeError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    summary = totals(payload)
    console.print(
        f"{summary['files']} files · {summary['filled']} filled fields · "
        f"{summary['fields']} total fields · {summary['errors']} errors"
    )
    table = Table("Input", "Pages", "Filled", "Blank", "Status")
    for item in payload["files"]:
        table.add_row(
            str(item.get("input") or ""),
            str(item.get("pages") or "-"),
            f"{item.get('filled') or 0}/{item.get('fields') or 0}",
            str(len(item.get("blank") or [])),
            "error" if item.get("error") else "ok",
        )
    console.print(table)
    if summary["errors"]:
        for item in payload["files"]:
            if item.get("error"):
                console.print(f"[red]{item.get('input')}: {item['error']}[/red]")


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
