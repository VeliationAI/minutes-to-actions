"""Minutes to Actions command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from minutes import __version__
from minutes.extractor import extract
from minutes.models import MinutesResult

app = typer.Typer(
    name="minutes",
    help="Paste a meeting transcript → decisions, action items, owners.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _read_transcript(
    transcript: Optional[str],
    file: Optional[Path],
) -> str:
    if file is not None:
        return file.read_text(encoding="utf-8")
    if transcript:
        return transcript
    if not sys.stdin.isatty():
        return sys.stdin.read()
    console.print(
        "[red]No transcript.[/] Pass text, --file, or pipe via stdin."
    )
    raise typer.Exit(1)


def _print_result(result: MinutesResult) -> None:
    header = Text()
    header.append("Minutes to Actions", style="bold #E8A838")
    header.append(f"  ·  via {result.source}\n", style="dim")
    if result.summary:
        header.append(result.summary, style="white")
    console.print(Panel(header, border_style="#E8A838", padding=(1, 2)))

    if result.attendees:
        console.print(f"[dim]Attendees[/]  " + ", ".join(result.attendees))
        console.print()

    if result.decisions:
        dtable = Table(title="Decisions", title_style="bold #5B9FD4", show_lines=False)
        dtable.add_column("#", style="dim", width=3)
        dtable.add_column("Decision")
        dtable.add_column("Context", style="dim")
        for i, d in enumerate(result.decisions, 1):
            dtable.add_row(str(i), d.text, d.context or "—")
        console.print(dtable)
        console.print()
    else:
        console.print("[dim]No decisions detected.[/]\n")

    if result.action_items:
        atable = Table(title="Action items", title_style="bold #E8A838")
        atable.add_column("Owner", style="bold")
        atable.add_column("Task")
        atable.add_column("Due", style="dim")
        atable.add_column("Priority")
        for item in result.action_items:
            color = {"high": "red", "medium": "yellow", "low": "green"}.get(
                item.priority, "white"
            )
            atable.add_row(
                item.owner,
                item.task,
                item.due or "—",
                f"[{color}]{item.priority}[/]",
            )
        console.print(atable)
        console.print()
    else:
        console.print("[dim]No action items detected.[/]\n")

    if result.open_questions:
        console.print("[bold]Open questions[/]")
        for q in result.open_questions:
            console.print(f"  • {q}")
        console.print()


@app.command("extract")
def extract_cmd(
    transcript: Optional[str] = typer.Argument(
        None, help="Raw transcript text (or pipe via stdin)."
    ),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Path to a transcript file.", exists=True
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-F",
        help="Output format: table | json | markdown",
    ),
    out: Optional[Path] = typer.Option(
        None, "--out", "-o", help="Write result to a file."
    ),
    heuristic: bool = typer.Option(
        False,
        "--heuristic",
        help="Force offline extraction (no LLM).",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="LLM model (default gpt-4o-mini)."
    ),
) -> None:
    """Extract decisions, action items, and owners from a transcript."""
    text = _read_transcript(transcript, file)
    try:
        result = extract(text, model=model, force_heuristic=heuristic)
    except Exception as exc:  # noqa: BLE001 — surface clean CLI errors
        console.print(f"[red]Extraction failed:[/] {exc}")
        raise typer.Exit(1) from exc

    fmt = format.lower().strip()
    if fmt == "json":
        payload = json.dumps(result.to_dict(), indent=2, ensure_ascii=True)
        if out:
            out.write_text(payload, encoding="utf-8")
            console.print(f"[green]Wrote[/] {out}")
        else:
            # Plain stdout so redirects stay valid JSON (no Rich markup).
            print(payload)
        return

    if fmt == "markdown":
        md = result.to_markdown()
        if out:
            out.write_text(md, encoding="utf-8")
            console.print(f"[green]Wrote[/] {out}")
        else:
            console.print(Markdown(md))
        return

    _print_result(result)
    if out:
        out.write_text(result.to_markdown(), encoding="utf-8")
        console.print(f"[dim]Also wrote markdown →[/] {out}")


@app.command("demo")
def demo(
    format: str = typer.Option("table", "--format", "-F"),
) -> None:
    """Run extraction on the bundled sample transcript (offline)."""
    sample = Path(__file__).resolve().parent / "sample_transcript.txt"
    text = sample.read_text(encoding="utf-8")
    result = extract(text, force_heuristic=True)
    if format.lower() == "json":
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
    elif format.lower() == "markdown":
        console.print(Markdown(result.to_markdown()))
    else:
        _print_result(result)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: Optional[int] = typer.Option(None, "--port", "-p"),
) -> None:
    """Launch the Minutes to Actions web UI."""
    import os

    import uvicorn

    from minutes.server import create_app

    bind_port = port or int(os.getenv("PORT", "8766"))
    if os.getenv("PORT") and host == "127.0.0.1":
        host = "0.0.0.0"

    console.print(
        Panel(
            f"[bold #E8A838]Minutes to Actions[/]\n"
            f"http://{host}:{bind_port}\n\n"
            f"[dim]Set OPENAI_API_KEY for LLM extraction.\n"
            f"Without a key, offline heuristics are used.[/]",
            border_style="#E8A838",
        )
    )
    uvicorn.run(create_app(), host=host, port=bind_port, log_level="info")



@app.command()
def version() -> None:
    """Print version."""
    console.print(f"minutes {__version__}")


@app.callback()
def main() -> None:
    """Minutes to Actions — nobody extracts the actions. Until now."""


if __name__ == "__main__":
    app()
