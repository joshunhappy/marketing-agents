"""CLI entrypoint — run `marketing-agents` after installing the package."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
app = typer.Typer(help="Marketing Agent Fleet CLI")
console = Console()


@app.command()
def run(
    input_file: Path = typer.Option(
        ..., "--input", "-i", help="JSON file with pipeline inputs (see examples/sample_input.json)"
    ),
    dry_run: bool = typer.Option(True, "--dry-run/--live", help="Dry run (default) vs. live mode"),
):
    """Run the full marketing pipeline from a JSON input file."""
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
def agent(
    agent_name: str = typer.Argument(help="Agent slug: market_intelligence | content_creation | lead_generation | campaign_optimization | customer_engagement | strategy_synthesis"),
    dry_run: bool = typer.Option(True, "--dry-run/--live"),
):
    """Run a single agent by name."""
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
