"""
Marketing Pipeline Orchestrator

Runs all 6 agents in sequence, passing each agent's output
as context to the next agent in the chain.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from agents.requirements import AGENT_REQUIREMENTS, agent_runnability, connected_integrations
from pipeline.brand import (
    BrandNotConfigured,
    active_brand,
    brand_dir,
    brand_file,
    load_brand_env,
)

load_brand_env()

console = Console()

ROOT = Path(__file__).parent.parent
PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")


def _load_settings() -> dict:
    path = ROOT / "config" / "settings.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _load_integrations() -> dict:
    """Load the active brand's integrations.yaml. Returns {} if no brand or file missing."""
    try:
        path = brand_file("integrations.yaml")
    except BrandNotConfigured:
        return {}
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _filled_configs() -> set[str]:
    """Brand-config slugs whose YAML has no template placeholders, for the active brand."""
    out: set[str] = set()
    try:
        bdir = brand_dir()
    except BrandNotConfigured:
        return out
    for name in ("brand_voice", "icp"):
        path = bdir / f"{name}.yaml"
        if path.exists() and not PLACEHOLDER_RE.search(path.read_text()):
            out.add(name)
    return out


class MarketingPipeline:
    """
    Runs the full 6-agent marketing fleet in sequence.

    Usage:
        pipeline = MarketingPipeline()
        results = pipeline.run(
            competitor_urls=["https://competitor.com"],
            content_brief="Write about AI in marketing...",
            leads=[{"name": "Jane Smith", "company": "Acme", ...}],
            campaign_data={...},
            customers=[...],
            social_mentions=[...],
        )
    """

    def __init__(self, dry_run: bool | None = None):
        self.settings = _load_settings()
        self.dry_run = dry_run if dry_run is not None else self._env_dry_run()
        self.enabled = self.settings["pipeline"]["enabled_agents"]
        self._connected = connected_integrations(_load_integrations())
        self._configs = _filled_configs()

    def _can_run(self, agent_slug: str) -> bool:
        """Check requirements; in live mode skip on miss, in dry-run warn but proceed."""
        if agent_slug not in self.enabled:
            return False
        report = agent_runnability(agent_slug, self._connected, self._configs)
        if report["can_run"]:
            if report["missing_optional"]:
                console.print(
                    f"[dim]· {agent_slug}: optional integrations not connected — "
                    f"{', '.join(report['missing_optional'])}[/dim]"
                )
            return True
        # Cannot run.
        reasons = []
        if report["missing_required_any"]:
            reasons.append(
                "needs ≥1 of: " + ", ".join(report["missing_required_any"])
            )
        if report["missing_required_configs"]:
            reasons.append(
                "config not filled: " + ", ".join(report["missing_required_configs"])
            )
        reason_text = "; ".join(reasons)
        if self.dry_run:
            console.print(
                f"[yellow]⚠ {agent_slug}: {reason_text} — running anyway in DRY RUN.[/yellow]"
            )
            return True
        console.print(f"[red]✗ {agent_slug}: skipped — {reason_text}.[/red]")
        return False

    def run(
        self,
        # Agent 01 inputs
        competitor_urls: list[str] | None = None,
        industry_topics: list[str] | None = None,
        customer_reviews: list[str] | None = None,
        # Agent 02 inputs
        content_brief: str = "",
        content_formats: list[str] | None = None,
        # Agent 03 inputs
        leads: list[dict] | None = None,
        # Agent 04 inputs
        campaign_data: dict | None = None,
        # Agent 05 inputs
        customers: list[dict] | None = None,
        social_mentions: list[dict] | None = None,
    ) -> dict:
        """Run the full pipeline and return all agent results."""

        try:
            slug = active_brand()
        except BrandNotConfigured as e:
            raise RuntimeError(str(e)) from None

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                f"ANTHROPIC_API_KEY is not set for brand '{slug}'. Run "
                "`marketing-agents setup` or add it to brands/<slug>/.env."
            )

        # Lazy import to avoid loading anthropic until keys are confirmed present
        from agents import (
            CampaignOptimizationAgent,
            ContentCreationAgent,
            CustomerEngagementAgent,
            LeadGenerationAgent,
            MarketIntelligenceAgent,
            StrategySynthesisAgent,
        )

        results: dict = {}

        console.print(Panel.fit(
            "[bold green]Marketing Agent Pipeline[/bold green]\n"
            f"Brand: [cyan]{slug}[/cyan]\n"
            f"Mode: {'[yellow]DRY RUN[/yellow]' if self.dry_run else '[red]LIVE[/red]'}\n"
            f"Agents: {len(self.enabled)}",
            border_style="green",
        ))

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:

            # ── Agent 01: Market Intelligence ─────────────────────────────────
            if self._can_run("market_intelligence"):
                task = progress.add_task("Agent 01 — Market Intelligence...", total=None)
                agent = MarketIntelligenceAgent(dry_run=self.dry_run)
                result = agent.run(
                    competitor_urls=competitor_urls,
                    industry_topics=industry_topics,
                    customer_reviews=customer_reviews,
                )
                results["market_intelligence"] = result.to_dict()
                result.save()
                progress.remove_task(task)
                console.print("[green]✓[/green] Agent 01 complete")

            # ── Agent 02: Content Creation ────────────────────────────────────
            if self._can_run("content_creation") and content_brief:
                task = progress.add_task("Agent 02 — Content Creation...", total=None)
                agent = ContentCreationAgent(dry_run=self.dry_run)
                briefing = results.get("market_intelligence", {}).get("data", {}).get("weekly_briefing")
                result = agent.run(
                    brief=content_brief,
                    formats=content_formats,
                    intelligence_briefing=briefing,
                )
                results["content_creation"] = result.to_dict()
                result.save()
                progress.remove_task(task)
                console.print("[green]✓[/green] Agent 02 complete")

            # ── Agent 03: Lead Generation ─────────────────────────────────────
            if self._can_run("lead_generation") and leads:
                task = progress.add_task("Agent 03 — Lead Generation...", total=None)
                agent = LeadGenerationAgent(dry_run=self.dry_run)
                content_assets = results.get("content_creation", {}).get("data", {})
                result = agent.run(leads=leads, content_assets=content_assets)
                results["lead_generation"] = result.to_dict()
                result.save()
                progress.remove_task(task)
                console.print("[green]✓[/green] Agent 03 complete")

            # ── Agent 04: Campaign Optimization ──────────────────────────────
            if self._can_run("campaign_optimization") and campaign_data:
                task = progress.add_task("Agent 04 — Campaign Optimization...", total=None)
                agent = CampaignOptimizationAgent(dry_run=self.dry_run)
                result = agent.run(campaign_data=campaign_data)
                results["campaign_optimization"] = result.to_dict()
                result.save()
                progress.remove_task(task)
                console.print("[green]✓[/green] Agent 04 complete")

            # ── Agent 05: Customer Engagement ─────────────────────────────────
            if self._can_run("customer_engagement") and customers:
                task = progress.add_task("Agent 05 — Customer Engagement...", total=None)
                agent = CustomerEngagementAgent(dry_run=self.dry_run)
                result = agent.run(customers=customers, social_mentions=social_mentions)
                results["customer_engagement"] = result.to_dict()
                result.save()
                progress.remove_task(task)
                console.print("[green]✓[/green] Agent 05 complete")

            # ── Agent 06: Strategy Synthesis ──────────────────────────────────
            if self._can_run("strategy_synthesis") and len(results) > 0:
                task = progress.add_task("Agent 06 — Strategy Synthesis...", total=None)
                agent = StrategySynthesisAgent(dry_run=self.dry_run)
                result = agent.run(agent_results=results)
                results["strategy_synthesis"] = result.to_dict()
                result.save()
                progress.remove_task(task)
                console.print("[green]✓[/green] Agent 06 complete")

        console.print(Panel.fit(
            f"[bold green]Pipeline complete.[/bold green] {len(results)} agent(s) ran.\n"
            "Reports saved to [cyan]reports/[/cyan]",
            border_style="green",
        ))

        return results

    @staticmethod
    def _env_dry_run() -> bool:
        return os.environ.get("PIPELINE_DRY_RUN", "true").lower() in ("1", "true", "yes")
