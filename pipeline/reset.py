"""Archive (don't delete) brand, example, report, and pipeline-input data.

Run via `marketing-agents reset`. Moves project data into a timestamped
`_archive/<UTC-stamp>/` directory at the project root for human review and
manual deletion. Code, prompts, config/, root .env, README, and CLAUDE.md
are never touched.

By default, archives the active brand only:
  - brands/<slug>/      (full brand directory incl. its .env and YAMLs)
  - reports/<slug>/     (this brand's outputs)

Pass `scope="all"` (or `--all` from the CLI) to also archive shared targets:
  - brands/             (every brand)
  - reports/            (every brand's reports)
  - examples/           (reference brand)
  - input.json          (legacy root input file, if present)

The point is reversibility: a real human reviews the archive directory and
deletes it (or restores from it) themselves.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from pipeline.brand import ACTIVE_BRAND_FILE, BrandNotConfigured, active_brand

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_ROOT = ROOT / "_archive"

console = Console()


def _targets(scope: str) -> list[tuple[str, Path, str]]:
    """Build the (label, path, kind) target list. kind is 'tree' or 'file'."""
    if scope == "all":
        return [
            ("All brands", ROOT / "brands", "tree"),
            ("All reports", ROOT / "reports", "tree"),
            ("Examples (incl. reference brand)", ROOT / "examples", "tree"),
            ("Legacy root input.json", ROOT / "input.json", "file"),
        ]
    # scope == "active"
    try:
        slug = active_brand()
    except BrandNotConfigured:
        console.print("[yellow]No active brand to reset. Use --all to archive everything.[/yellow]")
        return []
    return [
        (f"Brand '{slug}' directory", ROOT / "brands" / slug, "tree"),
        (f"Reports for '{slug}'", ROOT / "reports" / slug, "tree"),
    ]


def _scan(scope: str) -> list[tuple[str, Path, str, int]]:
    """Return existing targets with item counts for the preview table."""
    out = []
    for label, path, kind in _targets(scope):
        if not path.exists():
            continue
        if kind == "tree":
            count = sum(1 for _ in path.rglob("*") if _.is_file())
        else:
            count = 1
        out.append((label, path, kind, count))
    return out


def _archive_dir() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return ARCHIVE_ROOT / stamp


def reset_project_data(assume_yes: bool = False, scope: str = "active") -> Path | None:
    """Move project data to _archive/<ts>/. scope='active' (default) or 'all'."""
    if scope == "all":
        intro = (
            "[bold]Reset ALL project data[/bold]\n"
            "Moves every brand, every report, examples/, and any root input.json into a "
            "timestamped [cyan]_archive/[/cyan] directory.\n"
            "[dim]Code, prompts, config/, root .env are NOT touched.[/dim]"
        )
    else:
        try:
            slug = active_brand()
            intro = (
                f"[bold]Reset brand '{slug}'[/bold]\n"
                f"Moves [cyan]brands/{slug}/[/cyan] and [cyan]reports/{slug}/[/cyan] into "
                f"a timestamped [cyan]_archive/[/cyan] directory.\n"
                "[dim]Other brands, code, prompts, config/, root .env are NOT touched.[/dim]"
            )
        except BrandNotConfigured:
            intro = "[bold]Reset brand[/bold]\n[red]No active brand to reset.[/red]"

    console.print(Panel.fit(intro, border_style="yellow"))

    found = _scan(scope)
    if not found:
        console.print("[dim]Nothing to archive.[/dim]")
        return None

    table = Table(title="Will be moved", show_lines=False)
    table.add_column("Item")
    table.add_column("Path", style="cyan")
    table.add_column("Files", justify="right")
    for label, path, _, count in found:
        table.add_row(label, str(path.relative_to(ROOT)), str(count))
    console.print(table)

    archive = _archive_dir()
    console.print(f"\nDestination: [bold]{archive.relative_to(ROOT)}/[/bold]")
    console.print(
        "[dim]Nothing is deleted — a human reviews the archive directory and removes it manually.[/dim]\n"
    )

    if not assume_yes:
        if not Confirm.ask("Proceed with archive?", default=False):
            console.print("[yellow]Cancelled.[/yellow]")
            return None

    archive.mkdir(parents=True, exist_ok=True)
    for _, path, _, _ in found:
        # Preserve relative location under the archive (e.g. brands/acme → brands/acme).
        rel = path.relative_to(ROOT)
        dest = archive / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))
        console.print(f"  [green]→[/green] moved {rel} → {dest.relative_to(ROOT)}")

    # If we just archived the active brand, clear the pointer so future commands
    # don't try to use a brand directory that no longer exists.
    if scope == "active" and ACTIVE_BRAND_FILE.exists():
        ACTIVE_BRAND_FILE.unlink()
        console.print("[dim]· Cleared .active-brand pointer (brand directory was archived).[/dim]")

    # Recreate an empty reports/ so the next agent run doesn't fail.
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / ".gitkeep").touch()

    restore_hint = ""
    if scope == "all":
        restore_hint = "To restore committed dirs from git: [dim]git checkout examples/ config/[/dim]\n"

    console.print(
        Panel.fit(
            f"[bold green]Done.[/bold green]  Archived to [cyan]{archive.relative_to(ROOT)}/[/cyan]\n"
            f"Review the directory, then delete it when you're sure:\n"
            f"  [dim]rm -rf {archive.relative_to(ROOT)}/[/dim]\n"
            f"{restore_hint}",
            border_style="green",
        )
    )
    return archive


if __name__ == "__main__":
    reset_project_data()
