"""CLI entrypoint — run `marketing-agents` after installing the package."""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from pipeline.brand import (
    BrandNotConfigured,
    active_brand,
    init_brand,
    list_brands,
    load_brand_env,
    set_active_brand,
)

# Load shared root .env then the active brand's .env (if any) at CLI startup.
load_brand_env()

app = typer.Typer(help="Marketing Agent Fleet CLI")
brand_app = typer.Typer(help="Manage brand directories under brands/")
integrations_app = typer.Typer(help="Inspect the active brand's integration registry")
app.add_typer(brand_app, name="brand")
app.add_typer(integrations_app, name="integrations")

console = Console()


def _apply_brand_override(slug: str | None) -> None:
    """If --brand was passed, set BRAND env var so downstream resolves to it."""
    if slug:
        os.environ["BRAND"] = slug
        # Reload brand-specific .env now that BRAND has changed.
        load_brand_env()


@app.command()
def run(
    input_file: Path = typer.Option(
        ..., "--input", "-i", help="JSON file with pipeline inputs"
    ),
    dry_run: bool = typer.Option(True, "--dry-run/--live", help="Dry run (default) vs. live mode"),
    brand: str | None = typer.Option(
        None, "--brand", "-b", help="Override active brand for this run"
    ),
):
    """Run the full marketing pipeline from a JSON input file."""
    _apply_brand_override(brand)
    from pipeline import MarketingPipeline

    with open(input_file) as f:
        inputs = json.load(f)

    pipeline = MarketingPipeline(dry_run=dry_run)
    pipeline.run(**inputs)


@app.command()
def setup():
    """Interactive wizard to fulfill the materials required to start the project."""
    from pipeline.setup_wizard import run_wizard

    run_wizard()


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
    all_: bool = typer.Option(
        False, "--all", help="Archive every brand + examples, not just the active brand"
    ),
    brand: str | None = typer.Option(
        None, "--brand", "-b", help="Archive a specific brand instead of the active one"
    ),
):
    """Archive brand data to _archive/<ts>/ for human review.

    Default: archives only the active brand (brands/<slug>/ + reports/<slug>/).
    Use --all to archive everything, or --brand <slug> to target a specific brand.
    """
    _apply_brand_override(brand)
    from pipeline.reset import reset_project_data

    reset_project_data(assume_yes=yes, scope="all" if all_ else "active")


@app.command()
def agent(
    agent_name: str = typer.Argument(
        help="Agent slug: market_intelligence | content_creation | lead_generation | "
        "campaign_optimization | customer_engagement | strategy_synthesis"
    ),
    dry_run: bool = typer.Option(True, "--dry-run/--live"),
    brand: str | None = typer.Option(None, "--brand", "-b", help="Override active brand"),
):
    """Run a single agent by name."""
    _apply_brand_override(brand)
    from agents import (
        CampaignOptimizationAgent,
        ContentCreationAgent,
        CustomerEngagementAgent,
        LeadGenerationAgent,
        MarketIntelligenceAgent,
        StrategySynthesisAgent,
    )

    mapping = {
        "market_intelligence": MarketIntelligenceAgent,
        "content_creation": ContentCreationAgent,
        "lead_generation": LeadGenerationAgent,
        "campaign_optimization": CampaignOptimizationAgent,
        "customer_engagement": CustomerEngagementAgent,
        "strategy_synthesis": StrategySynthesisAgent,
    }

    cls = mapping.get(agent_name)
    if not cls:
        console.print(f"[red]Unknown agent:[/red] {agent_name}")
        raise typer.Exit(1)

    console.print(f"Running [bold]{agent_name}[/bold] in {'DRY RUN' if dry_run else 'LIVE'} mode...")
    instance = cls(dry_run=dry_run)
    result = instance.run()
    result.save()
    console.print(result.summary)


# ── Brand management ────────────────────────────────────────────────────────


@brand_app.command("list")
def brand_list():
    """List all brand directories under brands/."""
    brands = list_brands()
    try:
        current = active_brand(allow_missing=True)
    except BrandNotConfigured:
        current = ""
    if not brands:
        console.print("[yellow]No brands yet.[/yellow] Create one with: marketing-agents brand new <slug>")
        return
    for b in brands:
        marker = " [green](active)[/green]" if b == current else ""
        console.print(f"  • {b}{marker}")


@brand_app.command("show")
def brand_show():
    """Print the active brand slug."""
    try:
        console.print(active_brand())
    except BrandNotConfigured as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(1) from None


@brand_app.command("status")
def brand_status(
    brand: str | None = typer.Option(
        None, "--brand", "-b", help="Check a specific brand instead of the active one"
    ),
):
    """Print the readiness check (materials + per-agent runnability) for the active brand.

    Exit code: 0 = all agents can run live, 1 = hard blocker, 2 = soft gaps only.
    """
    _apply_brand_override(brand)
    try:
        active_brand()
    except BrandNotConfigured as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(1) from None
    from pipeline.setup_wizard import readiness_report

    raise typer.Exit(readiness_report())


@brand_app.command("use")
def brand_use(slug: str = typer.Argument(help="Slug of the brand to activate")):
    """Set the active brand."""
    try:
        set_active_brand(slug)
    except BrandNotConfigured as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None
    console.print(f"[green]✓ Active brand: {slug}[/green]")


@brand_app.command("new")
def brand_new(
    slug: str = typer.Argument(help="Slug for the new brand (lowercase, alphanumeric)"),
    activate: bool = typer.Option(True, "--activate/--no-activate"),
):
    """Create a new brand directory from templates."""
    path = init_brand(slug, set_active=activate)
    console.print(f"[green]✓ Created {path.relative_to(Path.cwd())}/[/green]")
    if activate:
        console.print(f"[green]✓ Active brand: {slug}[/green]")
    console.print("Next: run `marketing-agents setup` to fill it in.")


# ── Integrations ────────────────────────────────────────────────────────────


_STATUS_STYLE = {
    "connected": "[green]connected[/green]",
    "not_started": "[red]not_started[/red]",
    "blocked": "[yellow]blocked[/yellow]",
}


@integrations_app.command("list")
def integrations_list(
    status: str | None = typer.Option(
        None, "--status", "-s",
        help="Filter by status: connected | not_started | blocked",
    ),
    used_by: str | None = typer.Option(
        None, "--used-by", "-u",
        help="Filter to integrations consumed by a specific agent slug",
    ),
    brand: str | None = typer.Option(
        None, "--brand", "-b", help="Inspect a specific brand instead of the active one"
    ),
    plain: bool = typer.Option(
        False, "--plain", help="TSV output (slug<TAB>status<TAB>used_by<TAB>auth<TAB>env_key) for scripting",
    ),
):
    """List the active brand's integrations with their connection status."""
    import yaml as _yaml
    from pipeline.brand import brand_file

    _apply_brand_override(brand)
    try:
        path = brand_file("integrations.yaml")
        active = active_brand()
    except BrandNotConfigured as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(1) from None

    if not path.exists():
        console.print(f"[red]No integrations.yaml under brands/{active}/[/red]")
        raise typer.Exit(1)

    data = _yaml.safe_load(path.read_text()) or {}
    items: dict = data.get("integrations", {}) or {}

    rows = []
    for slug, cfg in items.items():
        cfg = cfg or {}
        if status and cfg.get("status") != status:
            continue
        if used_by and used_by not in (cfg.get("used_by") or []):
            continue
        rows.append((slug, cfg))

    if plain:
        for slug, cfg in rows:
            print(
                "\t".join([
                    slug,
                    cfg.get("status", ""),
                    ",".join(cfg.get("used_by") or []),
                    cfg.get("auth", ""),
                    cfg.get("env_key", ""),
                ])
            )
        return

    title = f"Integrations — brand '{active}'"
    if status or used_by:
        bits = []
        if status:
            bits.append(f"status={status}")
        if used_by:
            bits.append(f"used_by={used_by}")
        title += f"  ({', '.join(bits)})"

    table = Table(title=title, show_lines=False)
    table.add_column("Slug", style="bold")
    table.add_column("Status")
    table.add_column("Used by", style="dim")
    table.add_column("Auth", style="dim")
    table.add_column("Env key", style="cyan")
    table.add_column("Label", style="dim")
    for slug, cfg in rows:
        st = cfg.get("status", "?")
        table.add_row(
            slug,
            _STATUS_STYLE.get(st, st),
            ", ".join(cfg.get("used_by") or []) or "—",
            cfg.get("auth", "—"),
            cfg.get("env_key", "—"),
            cfg.get("label", ""),
        )
    console.print(table)
    console.print(f"[dim]{len(rows)}/{len(items)} integration(s) shown[/dim]")
