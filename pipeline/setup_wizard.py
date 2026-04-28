"""Interactive setup wizard for the Marketing Agents project.

Run via `marketing-agents setup` (or `python -m pipeline.setup_wizard`).
Walks the user through every material required to start the project:

  1. API keys              (.env)
  2. Brand voice           (config/brand_voice.yaml)
  3. ICP                   (config/icp.yaml)
  4. Integrations          (config/integrations.yaml — connection statuses)
  5. Pipeline input        (examples/input.json — copy of starter payload)

Each step detects whether the file is template/blank/filled and only re-prompts
the parts that still need attention. Existing values are never silently overwritten.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
BRAND_VOICE_PATH = ROOT / "config" / "brand_voice.yaml"
ICP_PATH = ROOT / "config" / "icp.yaml"
INTEGRATIONS_PATH = ROOT / "config" / "integrations.yaml"
PIPELINE_INPUT_PATH = ROOT / "examples" / "input.json"
PIPELINE_INPUT_TARGET = ROOT / "input.json"

PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")

console = Console()


# ── Status detection ────────────────────────────────────────────────────────


@dataclass
class MaterialStatus:
    key: str
    label: str
    state: str  # "filled" | "partial" | "missing"
    detail: str


def env_status() -> MaterialStatus:
    if not ENV_PATH.exists():
        return MaterialStatus("env", "API Keys (.env)", "missing", ".env file does not exist")
    values = _parse_env(ENV_PATH)
    anthropic = values.get("ANTHROPIC_API_KEY", "").strip()
    if not anthropic or anthropic.startswith("sk-ant-...") or anthropic == "":
        return MaterialStatus("env", "API Keys (.env)", "missing", "ANTHROPIC_API_KEY not set")
    blanks = [k for k, v in values.items() if not v.strip()]
    if blanks:
        return MaterialStatus(
            "env",
            "API Keys (.env)",
            "partial",
            f"Anthropic OK; {len(blanks)} other key(s) blank",
        )
    return MaterialStatus("env", "API Keys (.env)", "filled", "all keys populated")


def _yaml_status(path: Path, label: str, key: str) -> MaterialStatus:
    if not path.exists():
        return MaterialStatus(key, label, "missing", "file missing")
    text = path.read_text()
    matches = PLACEHOLDER_RE.findall(text)
    if matches:
        return MaterialStatus(key, label, "missing", f"{len(matches)} placeholder(s) remain")
    return MaterialStatus(key, label, "filled", "no template placeholders left")


def integrations_status() -> MaterialStatus:
    if not INTEGRATIONS_PATH.exists():
        return MaterialStatus("integrations", "Integrations", "missing", "file missing")
    data = yaml.safe_load(INTEGRATIONS_PATH.read_text()) or {}
    items = data.get("integrations", {}) or {}
    total = len(items)
    connected = sum(1 for v in items.values() if (v or {}).get("status") == "connected")
    if connected == 0:
        return MaterialStatus(
            "integrations", "Integrations", "missing", f"0/{total} connected"
        )
    if connected < total:
        return MaterialStatus(
            "integrations", "Integrations", "partial", f"{connected}/{total} connected"
        )
    return MaterialStatus("integrations", "Integrations", "filled", "all connected")


def pipeline_input_status() -> MaterialStatus:
    if PIPELINE_INPUT_TARGET.exists():
        return MaterialStatus(
            "input", "Pipeline Input", "filled", f"{PIPELINE_INPUT_TARGET.name} ready"
        )
    if PIPELINE_INPUT_PATH.exists():
        return MaterialStatus(
            "input",
            "Pipeline Input",
            "partial",
            "example available, not yet copied to project root",
        )
    return MaterialStatus("input", "Pipeline Input", "missing", "no input file found")


def all_statuses() -> list[MaterialStatus]:
    return [
        env_status(),
        _yaml_status(BRAND_VOICE_PATH, "Brand Voice", "brand_voice"),
        _yaml_status(ICP_PATH, "Ideal Customer Profile", "icp"),
        integrations_status(),
        pipeline_input_status(),
    ]


# ── Rendering ───────────────────────────────────────────────────────────────


STATE_GLYPH = {"filled": "[green]✓[/green]", "partial": "[yellow]~[/yellow]", "missing": "[red]✗[/red]"}


def render_status_table(statuses: list[MaterialStatus]) -> Table:
    table = Table(title="Required Materials", show_lines=False, expand=False)
    table.add_column("#", style="bold cyan", width=3)
    table.add_column("Status", width=8)
    table.add_column("Material", style="bold")
    table.add_column("Detail", style="dim")
    for i, s in enumerate(statuses, 1):
        table.add_row(str(i), STATE_GLYPH[s.state], s.label, s.detail)
    return table


def render_menu() -> None:
    console.print()
    console.print(
        Panel.fit(
            "[bold]Marketing Agents — Setup Wizard[/bold]\n"
            "Work through each material until every row is [green]✓[/green].",
            border_style="cyan",
        )
    )
    console.print(render_status_table(all_statuses()))
    console.print(
        "\nChoose a material to set up, or [bold]r[/bold] for readiness check, [bold]q[/bold] to quit."
    )


# ── .env helpers ────────────────────────────────────────────────────────────


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        out[k.strip()] = v.strip()
    return out


def _write_env(values: dict[str, str], path: Path) -> None:
    """Write values back, preserving comments and ordering from .env.example as the template."""
    template = ENV_EXAMPLE_PATH.read_text() if ENV_EXAMPLE_PATH.exists() else ""
    lines: list[str] = []
    seen: set[str] = set()
    for line in template.splitlines():
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            k, _, _ = stripped.partition("=")
            k = k.strip()
            seen.add(k)
            lines.append(f"{k}={values.get(k, '')}")
        else:
            lines.append(line)
    # Append any keys present in values but not in template.
    extras = [k for k in values if k not in seen]
    if extras:
        lines.append("")
        lines.append("# Additional keys (not in .env.example)")
        for k in extras:
            lines.append(f"{k}={values[k]}")
    path.write_text("\n".join(lines) + "\n")


# ── Step 1: API keys ────────────────────────────────────────────────────────

ENV_KEY_HELP = {
    "ANTHROPIC_API_KEY": "Required. Get one at console.anthropic.com.",
    "HUBSPOT_API_KEY": "Optional. CRM integration for lead_generation + customer_engagement.",
    "SALESFORCE_CLIENT_ID": "Optional. Salesforce OAuth client ID (alternative to HubSpot).",
    "SALESFORCE_CLIENT_SECRET": "Optional. Salesforce OAuth client secret.",
    "SALESFORCE_INSTANCE_URL": "Optional. e.g. https://acme.my.salesforce.com",
    "APOLLO_API_KEY": "Optional. Prospecting/enrichment for lead_generation.",
    "SEMRUSH_API_KEY": "Optional. SEO data for market_intelligence.",
    "MAILCHIMP_API_KEY": "Optional. Email sends from content_creation + customer_engagement.",
    "MAILCHIMP_LIST_ID": "Optional. Default list/audience ID.",
    "GOOGLE_ADS_DEVELOPER_TOKEN": "Optional. Required to read Google Ads via API.",
    "GOOGLE_ADS_CUSTOMER_ID": "Optional. Customer ID (no dashes).",
    "META_ADS_ACCESS_TOKEN": "Optional. Long-lived Meta access token.",
    "META_ADS_ACCOUNT_ID": "Optional. Ads account ID.",
    "SLACK_WEBHOOK_URL": "Optional. For agent alerts and weekly digests.",
    "PIPELINE_ENV": "development | staging | production. Controls dry_run defaults.",
    "PIPELINE_DRY_RUN": "true (read-only) | false (live). Override per run with --live.",
}


def step_env() -> None:
    console.rule("[bold]Step 1 · API Keys (.env)[/bold]")
    if not ENV_PATH.exists() and ENV_EXAMPLE_PATH.exists():
        shutil.copy(ENV_EXAMPLE_PATH, ENV_PATH)
        console.print(f"[dim]Created {ENV_PATH.name} from .env.example[/dim]")

    values = _parse_env(ENV_PATH)
    template_keys = list(_parse_env(ENV_EXAMPLE_PATH).keys()) or list(values.keys())

    only_required = Confirm.ask(
        "Only prompt for the [bold]required[/bold] key (ANTHROPIC_API_KEY)?",
        default=True,
    )

    target_keys = ["ANTHROPIC_API_KEY"] if only_required else template_keys

    for key in target_keys:
        current = values.get(key, "")
        masked = _mask(current)
        help_text = ENV_KEY_HELP.get(key, "")
        if current and not current.startswith("sk-ant-..."):
            keep = Confirm.ask(
                f"  {key} = {masked}  · keep existing?", default=True
            )
            if keep:
                continue
        if help_text:
            console.print(f"  [dim]{help_text}[/dim]")
        new_val = Prompt.ask(f"  {key}", default=current, password=key.endswith(("KEY", "TOKEN", "SECRET")))
        values[key] = new_val.strip()

    _write_env(values, ENV_PATH)
    console.print(f"[green]✓ Saved {ENV_PATH.name}[/green]")


def _mask(value: str) -> str:
    if not value:
        return "[dim]<blank>[/dim]"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}…{value[-4:]}"


# ── Step 2: Brand voice ─────────────────────────────────────────────────────


def step_brand_voice() -> None:
    console.rule("[bold]Step 2 · Brand Voice[/bold]")
    console.print(
        "[dim]Used by Content Creation and Customer Engagement agents. "
        "Reference example at examples/americavoice/brand_voice.yaml.[/dim]\n"
    )

    if not _confirm_overwrite(BRAND_VOICE_PATH):
        return

    name = Prompt.ask("Brand name")
    tagline = Prompt.ask("One-line tagline")
    founded = Prompt.ask("Founded (year or 'N years ago')", default="")
    description = Prompt.ask("One- or two-sentence description of what the brand does")
    distribution = _prompt_list(
        "Distribution channels (comma-separated, e.g. Website, iOS app, retail)"
    )

    primary_tone = Prompt.ask(
        "Primary tone adjective (e.g. warm, authoritative, playful, technical)"
    )
    secondary_tone = _prompt_list("2–5 supporting tone adjectives (comma-separated)")
    avoid_tone = _prompt_list(
        "Tones to avoid (comma-separated)",
        default="corporate_jargon, formal_stiff, fear_based, guilt_based",
    )

    pillars: dict[str, str] = {}
    console.print("\n[dim]Pillars: 2–4 short principles describing how the brand speaks.[/dim]")
    while len(pillars) < 4:
        if pillars and not Confirm.ask(f"  Add another pillar? (have {len(pillars)})", default=len(pillars) < 2):
            break
        p_name = Prompt.ask(f"  Pillar #{len(pillars) + 1} name (one word)").strip()
        if not p_name:
            break
        p_meaning = Prompt.ask("    What it means in practice")
        pillars[p_name] = p_meaning

    sentence_length = Prompt.ask(
        "Sentence length", choices=["short", "medium", "long"], default="short"
    )
    reading_level = Prompt.ask(
        "Reading level",
        choices=["accessible", "professional", "technical"],
        default="accessible",
    )
    point_of_view = Prompt.ask(
        "Point of view",
        choices=["first_person", "second_person", "third_person"],
        default="second_person",
    )
    oxford = Confirm.ask("Use the Oxford comma?", default=True)
    language_default = Prompt.ask("Default language", default="english")
    localization_note = Prompt.ask(
        "Localization note (optional, e.g. 'Spanish: neutral Latin American')",
        default="",
    )

    principles = _prompt_list(
        "Top 3–5 content principles (one per comma)",
        min_items=2,
    )

    prohibited_words = _prompt_list(
        "Words the agents should never use (comma-separated)",
        default="leverage, synergy, utilize",
    )
    prohibited_tactics = _prompt_list(
        "Persuasion tactics that violate brand values (comma-separated)",
        default="fear, guilt, shame",
    )

    do_examples = _prompt_list("2–3 on-brand example sentences (comma-separated)", min_items=1)
    dont_examples = _prompt_list("1–2 off-brand examples (comma-separated)", min_items=1)

    data = {
        "brand": {
            "name": name,
            "tagline": tagline,
            "founded": founded,
            "description": description,
            "distribution": distribution,
        },
        "tone": {
            "primary": primary_tone,
            "secondary": secondary_tone,
            "avoid": avoid_tone,
            "pillars": pillars,
        },
        "style": {
            "sentence_length": sentence_length,
            "reading_level": reading_level,
            "point_of_view": point_of_view,
            "oxford_comma": oxford,
            "language_default": language_default,
            "localization_note": localization_note,
        },
        "content_principles": principles,
        "prohibited": {"words": prohibited_words, "claims": [], "tactics": prohibited_tactics},
        "do_examples": do_examples,
        "dont_examples": dont_examples,
    }

    _write_yaml(
        BRAND_VOICE_PATH,
        data,
        header=(
            "# Brand Voice Guidelines\n"
            "# Generated by `marketing-agents setup`. Edit freely.\n"
            "# Used by Content Creation and Customer Engagement agents.\n"
        ),
    )
    console.print(f"[green]✓ Saved {BRAND_VOICE_PATH.relative_to(ROOT)}[/green]")


# ── Step 3: ICP ─────────────────────────────────────────────────────────────


def step_icp() -> None:
    console.rule("[bold]Step 3 · Ideal Customer Profile[/bold]")
    console.print(
        "[dim]Used by Lead Generation and Market Intelligence agents. "
        "Reference example at examples/americavoice/icp.yaml.[/dim]\n"
    )

    if not _confirm_overwrite(ICP_PATH):
        return

    audience = Prompt.ask("Audience type", choices=["b2b", "b2c"], default="b2b")

    label = Prompt.ask("Primary persona label (e.g. 'Growth-Stage VP of Marketing')")
    description = Prompt.ask("2–3 sentence description of this persona")

    primary: dict = {"label": label, "description": description}

    if audience == "b2b":
        primary["firmographics"] = {
            "company_size": Prompt.ask("  Company size (e.g. 50–500 employees)"),
            "industry": _prompt_list("  Target industries (comma-separated)"),
            "revenue_range": Prompt.ask("  Revenue range (e.g. $5M–$50M ARR)", default=""),
            "role_titles": _prompt_list("  Role titles (comma-separated)"),
            "geography": Prompt.ask("  Geography (e.g. North America, EMEA)", default="Global"),
        }
    else:
        primary["demographics"] = {
            "age_range": Prompt.ask("  Age range (e.g. 25–55)"),
            "location": Prompt.ask("  Location (e.g. US urban markets)"),
            "language": Prompt.ask("  Primary language(s)", default="English"),
            "income": Prompt.ask("  Income band", default=""),
        }

    primary["psychographics"] = _prompt_list(
        "  Psychographics — values, frustrations, aspirations (comma-separated)",
        min_items=2,
    )

    data: dict = {"icp": {"primary": primary}}

    if Confirm.ask("\nDefine a secondary persona?", default=False):
        data["icp"]["secondary"] = {
            "label": Prompt.ask("  Secondary persona label"),
            "description": Prompt.ask("  Description"),
            "messaging_approach": Prompt.ask("  How the pitch shifts for this persona"),
        }

    data["behavioral_signals"] = {
        "high_intent": _prompt_list(
            "High-intent signals (comma-separated)",
            default="Visited pricing page 2+ times in 7 days, Requested a demo or trial",
        ),
        "low_intent": _prompt_list(
            "Low-intent signals (comma-separated)",
            default="Bounced homepage in under 10 seconds, Inactive 60+ days after signup",
        ),
    }

    data["disqualifiers"] = _prompt_list(
        "Disqualifiers — traits that rule out a lead (comma-separated)",
        default="Outside target geography, Competitor or vendor",
    )

    console.print("\n[dim]Lead-scoring weights must sum to 100.[/dim]")
    fit = IntPrompt.ask("  Fit weight (demographic/firmographic match)", default=40)
    behavioral = IntPrompt.ask("  Behavioral weight (intent signals)", default=40)
    recency = IntPrompt.ask("  Recency weight (how recently engaged)", default=20)
    if fit + behavioral + recency != 100:
        console.print(
            f"[yellow]Weights sum to {fit + behavioral + recency} (not 100). Saving anyway — fix in YAML if needed.[/yellow]"
        )
    threshold = IntPrompt.ask("  Qualified threshold (score >= this is MQL)", default=65)

    data["lead_scoring"] = {
        "weights": {"fit": fit, "behavioral": behavioral, "recency": recency},
        "qualified_threshold": threshold,
    }

    primary_market = Prompt.ask("Primary market focus (e.g. 'US SaaS')", default="")
    supported_regions = Prompt.ask(
        "Supported regions (e.g. 'Global, US-only, EU+UK')", default="Global"
    )
    data["markets"] = {
        "primary_focus": [primary_market] if primary_market else [],
        "supported_regions": supported_regions,
    }

    _write_yaml(
        ICP_PATH,
        data,
        header=(
            "# Ideal Customer Profile (ICP)\n"
            "# Generated by `marketing-agents setup`. Edit freely.\n"
            "# Used by Lead Generation and Market Intelligence agents.\n"
        ),
    )
    console.print(f"[green]✓ Saved {ICP_PATH.relative_to(ROOT)}[/green]")


# ── Step 4: Integrations ────────────────────────────────────────────────────


def step_integrations() -> None:
    console.rule("[bold]Step 4 · Integrations[/bold]")
    console.print(
        "[dim]Mark each external tool as connected once its API key is in .env "
        "and you've verified the connection. anthropic must be connected for any agent to run.[/dim]\n"
    )

    text = INTEGRATIONS_PATH.read_text()
    data = yaml.safe_load(text) or {}
    items = data.get("integrations", {}) or {}

    table = Table(title="Integrations", show_lines=False)
    table.add_column("#", width=3)
    table.add_column("Status", width=14)
    table.add_column("Key")
    table.add_column("Label", style="dim")
    keys = list(items.keys())
    for i, key in enumerate(keys, 1):
        st = (items[key] or {}).get("status", "?")
        color = {"connected": "green", "not_started": "red", "blocked": "yellow"}.get(st, "white")
        table.add_row(str(i), f"[{color}]{st}[/{color}]", key, (items[key] or {}).get("label", ""))
    console.print(table)

    while True:
        choice = Prompt.ask(
            "\nEnter # to toggle (or 'all-connected', 'done')",
            default="done",
        ).strip()
        if choice == "done":
            break
        if choice == "all-connected":
            if Confirm.ask("Mark every integration as connected?", default=False):
                for key in keys:
                    text = _replace_status(text, key, "connected")
            break
        if not choice.isdigit() or not (1 <= int(choice) <= len(keys)):
            console.print("[red]Invalid choice.[/red]")
            continue
        key = keys[int(choice) - 1]
        new_status = Prompt.ask(
            f"  New status for [bold]{key}[/bold]",
            choices=["connected", "not_started", "blocked"],
            default="connected",
        )
        text = _replace_status(text, key, new_status)
        # refresh local view
        data = yaml.safe_load(text) or {}
        items = data.get("integrations", {}) or {}
        st = (items[key] or {}).get("status", "?")
        console.print(f"  [green]Updated[/green] {key} → {st}")

    INTEGRATIONS_PATH.write_text(text)
    console.print(f"[green]✓ Saved {INTEGRATIONS_PATH.relative_to(ROOT)}[/green]")


def _replace_status(text: str, key: str, new_status: str) -> str:
    """Replace the status: line under a given top-level key while preserving comments."""
    pattern = re.compile(
        rf"(^  {re.escape(key)}:.*?\n(?:.*\n)*?)(    status:\s*)(\S+)",
        re.MULTILINE,
    )
    return pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{new_status}", text, count=1)


# ── Step 5: Pipeline input ──────────────────────────────────────────────────


def step_pipeline_input() -> None:
    console.rule("[bold]Step 5 · Pipeline Input[/bold]")
    console.print(
        "[dim]The pipeline reads its inputs from a JSON file. Start from the example "
        "and tailor competitor URLs, leads, campaign data, etc.[/dim]\n"
    )

    if PIPELINE_INPUT_TARGET.exists():
        console.print(f"[green]✓ {PIPELINE_INPUT_TARGET.name} already exists at project root.[/green]")
        if not Confirm.ask("Overwrite it from the example?", default=False):
            return

    if not PIPELINE_INPUT_PATH.exists():
        console.print(f"[red]Example file missing at {PIPELINE_INPUT_PATH}[/red]")
        return

    shutil.copy(PIPELINE_INPUT_PATH, PIPELINE_INPUT_TARGET)
    console.print(
        f"[green]✓ Copied example to {PIPELINE_INPUT_TARGET.relative_to(ROOT)}[/green]"
    )
    console.print("  Edit it to swap in your real competitors, leads, campaign data.")
    console.print("  Then run: [bold]marketing-agents run --input input.json[/bold]")


# ── Readiness check ─────────────────────────────────────────────────────────


def step_readiness() -> None:
    console.rule("[bold]Readiness Check[/bold]")
    statuses = all_statuses()
    console.print(render_status_table(statuses))
    blockers = [s for s in statuses if s.state == "missing"]
    soft = [s for s in statuses if s.state == "partial"]
    if not blockers and not soft:
        console.print("\n[bold green]All set. The pipeline can run live.[/bold green]")
        return
    if blockers:
        console.print("\n[bold red]Blockers — must resolve before running:[/bold red]")
        for s in blockers:
            console.print(f"  • {s.label} — {s.detail}")
    if soft:
        console.print("\n[bold yellow]Soft gaps — pipeline can run in dry-run, fill before going live:[/bold yellow]")
        for s in soft:
            console.print(f"  • {s.label} — {s.detail}")


# ── Helpers ─────────────────────────────────────────────────────────────────


def _confirm_overwrite(path: Path) -> bool:
    if path.exists():
        text = path.read_text()
        if not PLACEHOLDER_RE.search(text):
            return Confirm.ask(
                f"{path.relative_to(ROOT)} appears already filled. Overwrite?",
                default=False,
            )
    return True


def _prompt_list(question: str, default: str = "", min_items: int = 1) -> list[str]:
    while True:
        raw = Prompt.ask(question, default=default)
        items = [x.strip() for x in raw.split(",") if x.strip()]
        if len(items) >= min_items:
            return items
        console.print(f"[red]Need at least {min_items} item(s).[/red]")


def _write_yaml(path: Path, data: dict, header: str = "") -> None:
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    path.write_text(header + body)


# ── Main loop ───────────────────────────────────────────────────────────────


STEPS: dict[str, tuple[str, Callable[[], None]]] = {
    "1": ("API Keys (.env)", step_env),
    "2": ("Brand Voice", step_brand_voice),
    "3": ("Ideal Customer Profile", step_icp),
    "4": ("Integrations", step_integrations),
    "5": ("Pipeline Input", step_pipeline_input),
}


def run_wizard() -> None:
    while True:
        render_menu()
        choice = Prompt.ask(
            "Select",
            choices=[*STEPS.keys(), "r", "q"],
            default="1",
        )
        if choice == "q":
            console.print("[dim]Bye.[/dim]")
            return
        if choice == "r":
            step_readiness()
            continue
        _, fn = STEPS[choice]
        try:
            fn()
        except KeyboardInterrupt:
            console.print("\n[yellow]Step cancelled. Returning to menu.[/yellow]")


if __name__ == "__main__":
    run_wizard()
