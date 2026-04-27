# Marketing AI Agent Fleet

A brand-agnostic scaffold for a fleet of 6 specialized Claude AI agents that operate across the full marketing funnel as a 24/7 autonomous marketing engine. Each agent handles a distinct stage of the funnel, passes its output downstream, and gates any external action behind human approval until trust is established.

Drop in your brand voice, ICP, and integration credentials and the fleet runs end-to-end against your data.

> **Reference implementation:** a fully populated configuration for a real business (America Voice — B2C fintech/telecom) lives at [`examples/americavoice/`](examples/americavoice/README.md). Use it to see what a completed `brand_voice.yaml`, `icp.yaml`, `integrations.yaml`, and pipeline `input.json` look like when filled in from a real brand guide.

---

## Target KPIs

| Metric | Target |
|---|---|
| Lead Volume | +40% qualified leads / month |
| Conversion Rate | +25% lead-to-close improvement |
| Content Output | 10× faster production |
| CAC | −30% customer acquisition cost |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MarketingPipeline                            │
│                        (pipeline/orchestrator.py)                   │
└─────────┬───────────────────────────────────────────────────────────┘
          │  Sequential execution — each agent feeds the next
          ▼
┌─────────────────┐    intelligence_briefing
│ 01 · Market     │ ──────────────────────────────────────────┐
│ Intelligence    │                                            │
└─────────────────┘                                            ▼
                                                   ┌─────────────────┐    content_assets
                                                   │ 02 · Content    │ ─────────────────┐
                                                   │ Creation        │                   │
                                                   └─────────────────┘                   ▼
                                                                          ┌─────────────────┐
                                                                          │ 03 · Lead       │
                                                                          │ Generation      │
                                                                          └─────────────────┘
                                                                          ┌─────────────────┐
                                                                          │ 04 · Campaign   │
                                                                          │ Optimization    │
                                                                          └─────────────────┘
                                                                          ┌─────────────────┐
                                                                          │ 05 · Customer   │
                                                                          │ Engagement      │
                                                                          └─────────────────┘
          ▲  all_agent_results
          │
┌─────────────────┐
│ 06 · Strategy   │
│ Synthesis       │
└─────────────────┘
```

Agent 06 runs last and receives every other agent's output, synthesizing a unified weekly strategy brief.

---

## The 6 Agents

### Agent 01 — Market Intelligence
**File:** `agents/market_intelligence.py` | **Model:** `claude-opus-4-6` | **Schedule:** Weekly

Analyzes competitor activity, industry trends, and customer reviews. Produces a structured weekly intelligence briefing that feeds directly into Agent 02.

| Input | Description |
|---|---|
| `competitor_urls` | List of competitor website URLs to analyze |
| `industry_topics` | Topics to monitor for trend signals |
| `customer_reviews` | Raw customer review text for sentiment analysis |

**Prompt workflow:** `competitor_analysis` → `trend_monitoring` → `review_analysis` → `compile_briefing`

**Approval gate:** None (read-only agent)

---

### Agent 02 — Content Creation
**File:** `agents/content_creation.py` | **Model:** `claude-sonnet-4-6` | **Schedule:** Daily

Takes the intelligence briefing from Agent 01 and a content brief, then produces brand-compliant content across five formats.

| Input | Description |
|---|---|
| `brief` | The content objective or campaign brief |
| `formats` | One or more of: `blog`, `email_sequence`, `ad_copy`, `social_post`, `landing_page` |
| `persona_id` | Target persona from `config/icp.yaml` |
| `intelligence_briefing` | Auto-injected from Agent 01 output |

**Approval gate:** All drafts require human review before publishing

---

### Agent 03 — Lead Generation
**File:** `agents/lead_generation.py` | **Model:** `claude-sonnet-4-6` | **Schedule:** Daily

Scores a list of incoming leads against the ICP, filters qualified prospects, and drafts personalized outreach emails.

| Input | Description |
|---|---|
| `leads` | List of lead dicts (name, company, country, etc.) |
| `content_assets` | Auto-injected from Agent 02 output |

**Config:** `outreach_daily_limit: 50` — caps drafts per run

**Approval gate:** Each outreach email requires approval before sending

---

### Agent 04 — Campaign Optimization
**File:** `agents/campaign_optimization.py` | **Model:** `claude-sonnet-4-6` | **Schedule:** Daily

Reads live campaign performance data from Google Ads and Meta Ads, identifies winners and underperformers, and generates a prioritized recommendations report.

| Input | Description |
|---|---|
| `campaign_data` | Performance dict (impressions, clicks, CPC, ROAS, etc.) |

**Prompt workflow:** `analyze_performance` → `recommendations` → `weekly_report`

**Approval gate:** Bid adjustments and ad pausing require approval

---

### Agent 05 — Customer Engagement
**File:** `agents/customer_engagement.py` | **Model:** `claude-sonnet-4-6` | **Schedule:** Daily

Monitors customer health signals, flags churn risk, identifies upsell opportunities, generates onboarding sequences for new customers, and drafts responses to social mentions.

| Input | Description |
|---|---|
| `customers` | List of customer dicts with engagement and transaction data |
| `social_mentions` | Brand mentions from social monitoring tools |

**Behaviors:**
- Churn risk detected → Slack alert + flags account in CRM
- Upsell opportunity → drafts email, gates for approval
- Customer age < 14 days → generates onboarding sequence
- Social mention → drafts response, gates for approval

---

### Agent 06 — Strategy Synthesis
**File:** `agents/strategy_synthesis.py` | **Model:** `claude-sonnet-4-6` | **Schedule:** Weekly

Receives all five agent outputs and synthesizes a unified weekly strategy report covering digest, gap analysis, strategic recommendations, and brand audit.

> **Model choice:** Agent 06 runs on Sonnet, not Opus, because invoking Opus at the end of a full 5-agent run consistently hits Anthropic rate limits. Sonnet is sufficient for synthesis on the aggregated upstream outputs.

| Input | Description |
|---|---|
| `agent_results` | Auto-injected dict of all 5 upstream agent results |

**Prompt workflow:** `weekly_digest` → `gap_analysis` → `strategy_recommendations` → `brand_audit`

**Approval gate:** None (report only — no external actions)

---

## Project Structure

```
marketing-agents/
│
├── agents/                          # One file per agent
│   ├── base_agent.py                # BaseAgent (abstract) + AgentResult
│   ├── market_intelligence.py       # Agent 01
│   ├── content_creation.py          # Agent 02
│   ├── lead_generation.py           # Agent 03
│   ├── campaign_optimization.py     # Agent 04
│   ├── customer_engagement.py       # Agent 05
│   └── strategy_synthesis.py        # Agent 06
│
├── prompts/                         # Prompt library — never hardcode prompts in agent files
│   ├── market_intelligence/         # system.md + 4 task prompts
│   ├── content_creation/            # system.md + 5 format prompts
│   ├── lead_generation/             # system.md + 2 task prompts
│   ├── campaign_optimization/       # system.md + 3 task prompts
│   ├── customer_engagement/         # system.md + 4 task prompts
│   └── strategy_synthesis/          # system.md + 4 task prompts
│
├── integrations/                    # API connectors (stubbed, ready to implement)
│   ├── base_integration.py          # BaseIntegration (abstract)
│   ├── crm.py                       # HubSpot / Salesforce
│   ├── ads.py                       # Google Ads + Meta Ads Manager
│   └── content.py                   # Mailchimp / WordPress / Buffer
│
├── pipeline/                        # Orchestration layer
│   ├── orchestrator.py              # MarketingPipeline — runs all 6 agents in sequence
│   └── cli.py                       # Typer CLI entrypoint (marketing-agents command)
│
├── config/                          # Brand-agnostic templates — fill in for your brand
│   ├── settings.yaml                # Model tiers, approval gates, schedules
│   ├── integrations.yaml            # Data source registry (connected | not_started | blocked)
│   ├── brand_voice.yaml             # Tone, messaging, glossary, do/don't examples
│   └── icp.yaml                     # Ideal Customer Profile + lead scoring
│
├── examples/
│   ├── input.json                   # Generic B2B SaaS pipeline input — use this to kick the tires
│   └── americavoice/                # Fully populated reference implementation
│       ├── README.md                # How this reference is organized
│       ├── brand_voice.yaml         # Populated brand voice
│       ├── icp.yaml                 # Populated ICP
│       ├── integrations.yaml        # Populated integration registry (Phase 1 audit)
│       └── input.json               # Realistic pipeline input
│
├── tests/
│   └── test_agents.py               # Pytest tests for AgentResult and config loading
│
├── reports/                         # Agent output files (gitignored)
│
├── .env                             # Secrets — never committed
├── .env.example                     # Template — copy to .env to get started
└── pyproject.toml                   # Dependencies and CLI entrypoint
```

---

## Setup

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com)

### Installation

```bash
# Clone and enter the project
git clone <repo-url>
cd marketing-agents

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate     # macOS / Linux
# .venv\Scripts\activate      # Windows

# Install dependencies
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Open .env and add your ANTHROPIC_API_KEY at minimum
```

### Fill in your brand

The `config/*.yaml` files ship as templates with `{{PLACEHOLDER}}` fields. Before running the pipeline, populate:

1. **`config/brand_voice.yaml`** — brand name, tone pillars, glossary, do/don't examples
2. **`config/icp.yaml`** — primary persona, behavioral signals, lead-scoring weights
3. **`config/integrations.yaml`** — flip integrations from `not_started` to `connected` as you wire them up

See [`examples/americavoice/`](examples/americavoice/README.md) for a fully populated reference.

### Verify setup

```bash
# Run the test suite
pytest tests/

# Confirm the CLI is available
marketing-agents --help
```

---

## Running the Pipeline

### Dry-run mode (default — safe, no writes)

All agents run but no emails are sent, no ads are adjusted, and no CRM records are written. This is the default until you're ready to go live.

```bash
# Run the full pipeline with the generic example input
marketing-agents run --input examples/input.json

# Or run against the America Voice reference
marketing-agents run --input examples/americavoice/input.json

# Run a single agent by name
marketing-agents agent market_intelligence
marketing-agents agent content_creation
```

### Live mode

```bash
# Enable live writes (requires all integrations configured)
marketing-agents run --input examples/input.json --live
```

You can also override dry-run globally via environment variable:

```bash
export PIPELINE_DRY_RUN=false
```

### Input file format

The pipeline input is a single JSON document with the following top-level keys. See `examples/input.json` for a working version and `examples/americavoice/input.json` for a fully realistic one.

```json
{
  "competitor_urls": ["https://competitor-a.com", "https://competitor-b.com"],
  "industry_topics": ["AI marketing automation", "B2B lead generation 2026"],
  "customer_reviews": ["Great product but onboarding took forever...", "..."],
  "content_brief": "Write content explaining ... Target audience: ... CTA: ...",
  "content_formats": ["blog", "email_sequence", "ad_copy"],
  "leads": [
    {"id": "L001", "name": "Sarah Chen", "title": "VP Marketing", "company": "Acme SaaS"}
  ],
  "campaign_data": {
    "google_ads": {"impressions": 8500, "clicks": 340, "spend_usd": 1200},
    "meta_ads": {"impressions": 45000, "clicks": 420, "spend_usd": 600}
  },
  "customers": [
    {"id": "C001", "name": "Globex Corp", "days_since_signup": 5, "monthly_spend_usd": 299}
  ],
  "social_mentions": [
    {"platform": "twitter", "handle": "@jane_marketer", "text": "...", "sentiment": "positive"}
  ]
}
```

### Pipeline output

Each agent writes two files to `reports/` via `AgentResult.save()` in `agents/base_agent.py`:

- **`<agent>_<YYYYMMDD_HHMMSS>.json`** — full structured output (all fields returned by the agent, plus `success`, `timestamp`, and `summary`). Parse this for downstream tooling.
- **`<agent>_<YYYYMMDD_HHMMSS>.md`** — human-readable summary only. Good for Slack/Notion paste-ins.

Timestamps are UTC.

```
reports/
├── market_intelligence_agent_20260420_090000.json    # structured data
├── market_intelligence_agent_20260420_090000.md      # human-readable summary
├── content_creation_agent_20260420_090112.json
...
```

---

## Configuration

### `config/settings.yaml` — Runtime behavior

Controls model selection, approval gates, schedules, and pipeline flags. Safe to commit — no secrets.

```yaml
anthropic:
  model_primary: claude-opus-4-6           # Agents 01, 06 (complex reasoning)
  model_secondary: claude-sonnet-4-6       # Agents 02–05 (balanced)
  model_fast: claude-haiku-4-5-20251001    # High-volume tasks (enrichment, scoring)

pipeline:
  dry_run: true                            # Override with PIPELINE_DRY_RUN env var

agents:
  lead_generation:
    require_approval: true                 # Gate every outreach email
    outreach_daily_limit: 50               # Max drafts per run
```

### `config/brand_voice.yaml` — Brand voice template

Defines voice pillars, prohibited words, channel-specific tone guidance, and sample copy for each sales goal. All content agents read this file. Fill in the `{{PLACEHOLDER}}` fields for your brand, or copy a reference from `examples/americavoice/brand_voice.yaml`.

### `config/icp.yaml` — Ideal Customer Profile template

Defines primary (and optional secondary) personas, behavioral signals, and lead-scoring weights used by Agent 03. The template includes both B2B (firmographics) and B2C (demographics) blocks — delete whichever doesn't apply.

### `config/integrations.yaml` — Data source registry

Registry of all integrations with status, auth method, agent dependencies, and open action items. Flip `status: not_started` to `status: connected` as you wire each one up.

---

## Integration Status (template defaults)

| Status | Count |
|---|---|
| ✅ Connected | 1 — Anthropic API |
| ❌ Not Started | All others |

Flip integrations to `connected` in `config/integrations.yaml` as you wire them up. Each integration's `env_key` field points to the `.env` variable it reads from.

### Agent readiness — what each agent needs

| Agent | Required Integrations |
|---|---|
| 01 · Market Intelligence | App Store Reviews, Semrush/Ahrefs, Google Search Console, Slack, Notion |
| 02 · Content Creation | Notion, WordPress/Webflow, Mailchimp/Klaviyo, Buffer/Hootsuite, Semrush/Ahrefs |
| 03 · Lead Generation | HubSpot/Salesforce, Apollo.io, Outreach/Salesloft, LinkedIn Sales Nav |
| 04 · Campaign Optimization | Google Ads, Meta Ads, GA4, Looker/Tableau |
| 05 · Customer Engagement | Mailchimp/Klaviyo, HubSpot/Salesforce, Buffer/Hootsuite, internal customer data |
| 06 · Strategy Synthesis | Slack, Notion, Looker/Tableau, GA4 |

---

## Human-in-the-Loop Gates

The `_gate()` method on `BaseAgent` intercepts any action that writes to an external system. In dry-run or early phases, it prints what would happen instead of acting. In live mode with `require_approval: true`, it prompts for explicit confirmation before proceeding.

| Agent | Gated Actions |
|---|---|
| 02 · Content Creation | All content drafts before publishing |
| 03 · Lead Generation | Every outreach email before sending |
| 04 · Campaign Optimization | Bid adjustments and ad pausing |
| 05 · Customer Engagement | Upsell emails and social responses |

Agents 01 and 06 are read-only and have no gates.

---

## Adding a New Agent

1. Create `agents/<agent_name>.py` extending `BaseAgent`
2. Set `name` and `_config_key` class attributes
3. Implement `run(**kwargs) -> AgentResult`
4. Load prompts with `self._prompt("<prompt_name>")` — never hardcode prompt text
5. Call the Anthropic API with `self._call(system, user)`
6. Gate any write actions with `self._gate("<description>")`
7. Add the agent config block to `config/settings.yaml`
8. Create `prompts/<agent_name>/system.md` and task prompt files
9. Register any new integrations in `config/integrations.yaml`

---

## Adding a New Integration

All integrations live in `integrations/` and extend `BaseIntegration`:

```python
from integrations.base_integration import BaseIntegration

class MyIntegration(BaseIntegration):
    def health_check(self) -> bool:
        # verify the connection
        ...

    def my_method(self, ...) -> ...:
        if not self._guard("description of what this will do"):
            return None
        # make the real API call
        ...
```

`_guard()` returns `False` in dry-run mode and logs what would have happened — no changes required to the calling agent.

---

## Development

```bash
# Run tests
pytest tests/ -v

# Lint and format
ruff check .
ruff format .

# Run a single agent in dry-run (safe for development)
marketing-agents agent market_intelligence --dry-run
```

### Key conventions

- **Secrets:** Always in `.env`, never in code or config YAML files
- **Prompts:** Always in `prompts/<agent_key>/<name>.md`, never hardcoded in Python
- **Config:** `require_approval` defaults to `true` for any agent that writes externally
- **Models:** Use `model_primary` (`claude-opus-4-6`) only for complex reasoning agents; `model_secondary` (`claude-sonnet-4-6`) for everything else
- **Rate limits:** `BaseAgent._call()` retries `RateLimitError` with exponential backoff (60s → 120s → 180s, then fails). A full pipeline run can stall for several minutes if the account hits limits — check console for the `Rate limit hit — waiting Ns` message before assuming something else is wrong
- **Test coverage:** `tests/test_agents.py` covers `AgentResult` serialization and config loading only. No tests exercise prompts or end-to-end agent logic — treat pipeline runs against `examples/input.json` as the real integration test

---

## Rollout Phases

| Phase | Weeks | Milestone |
|---|---|---|
| **Phase 1 — Foundation** | 1–2 | Brand voice docs uploaded, API keys obtained, CRM fields mapped |
| **Phase 2 — Pilot** | 3–5 | Agents 01 & 02 live in read-only mode with human review on all outputs |
| **Phase 3 — Launch** | 6–9 | Agents 03–05 live, approval gates active, KPI baseline established |
| **Phase 4 — Full Autonomy** | 10–12 | Agent 06 live, manual approvals reduced, full KPI review vs. targets |

---

## Tech Stack

| Layer | Tools |
|---|---|
| AI Engine | Anthropic Claude API (`claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`) |
| CRM / Sales | HubSpot / Salesforce, Apollo.io, Outreach / Salesloft |
| Content / SEO | WordPress / Webflow, Semrush / Ahrefs, Mailchimp / Klaviyo |
| Ads / Analytics | Google Ads, Meta Ads Manager, Google Analytics 4, Mixpanel |
| Infrastructure | Zapier / Make.com (triggers), Slack (agent alerts), Notion (knowledge base) |
| Framework | Python 3.11+, `anthropic` SDK, `typer` (CLI), `rich` (terminal UI), `pyyaml`, `pydantic` |
