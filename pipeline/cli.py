"""CLI entrypoint — run `marketing-agents` after installing the package."""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console

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
app.add_typer(brand_app, name="brand")

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
