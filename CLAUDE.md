# Marketing Agents — Project Context

## What This Is
A fleet of 6 specialized Claude AI agents that operate across the full marketing funnel as a 24/7 autonomous marketing engine.

## Target KPIs
| Metric | Target |
|---|---|
| Lead Volume | +40% qualified leads/month |
| Conversion Rate | +25% lead-to-close improvement |
| Content Output | 10× faster production |
| CAC | −30% customer acquisition cost |

## The 6 Agents
| # | Agent | Role |
|---|---|---|
| 01 | Market Intelligence | Research & Insights |
| 02 | Content Creation | Content & Copywriting |
| 03 | Lead Generation | Prospecting & Outreach |
| 04 | Campaign Optimization | Performance & Analytics |
| 05 | Customer Engagement | Nurture & Retention |
| 06 | Strategy Synthesis | Coordination & Planning |

## Pipeline Flow
Market Intelligence → Content Creation → Lead Generation → Campaign Optimization → Customer Engagement → Strategy Synthesis

## Project Structure
```
agents/             # One file per agent + base class + requirements registry
brands/<slug>/      # Per-brand: .env, brand_voice.yaml, icp.yaml, integrations.yaml, input.json
config/             # Global runtime settings + brand-config templates (config/templates/)
prompts/            # Prompt library per agent
integrations/       # CRM, ads, content platform connectors
pipeline/           # Orchestrator + setup wizard + brand resolver + reset command
reports/<slug>/     # Agent output reports per brand (gitignored)
tests/              # Agent and integration tests
```

## Brand Model
The project is multi-tenant: each brand lives in `brands/<slug>/` with its own `.env` and YAMLs. Active brand is resolved by `pipeline/brand.py` in this order: `BRAND` env var → `.active-brand` file → single brand under `brands/`. Templates for new brands live in `config/templates/`. Settings shared across all brands stay in `config/settings.yaml`.

## Rollout Phases
- **Phase 1 (Wk 1–2):** Foundation — brand voice docs, API access, CRM connections
- **Phase 2 (Wk 3–5):** Pilot Agents 01 & 02 in read-only mode with human review
- **Phase 3 (Wk 6–9):** Launch Agents 03–05, enable approval gates, baseline KPIs
- **Phase 4 (Wk 10–12):** Launch Agent 06, reduce manual approvals, full KPI review

## Tech Stack
- **AI:** Anthropic Claude API (claude-opus-4-6 for complex reasoning, claude-haiku-4-5-20251001 for high-volume tasks)
- **CRM/Sales:** Salesforce / HubSpot, Apollo.io, Outreach / Salesloft
- **Content/SEO:** WordPress / Webflow, Semrush / Ahrefs, Mailchimp / Klaviyo
- **Ads/Analytics:** Google Ads & Analytics, Meta Ads Manager, Mixpanel
- **Infrastructure:** Zapier / Make.com for triggers, Slack for agent alerts, Notion for knowledge base

## Development Notes
- Each agent extends `BaseAgent` in `agents/base_agent.py`
- All prompts live in `prompts/<agent_name>/` as `.md` files — never hardcode prompts in agent files
- Secrets go in `.env` (never committed) — see `config/settings.yaml` for the key names
- Human-in-the-loop gates are controlled per agent via `config/settings.yaml → agents.<name>.require_approval`
- Per-agent integration & config requirements live in `agents/requirements.py` (`requires_any`, `optional`, `requires_config`). The orchestrator skips an agent in live mode if its requirements aren't met; the setup wizard reads the same registry to compute per-agent runnability
- Run `marketing-agents setup` for the interactive wizard. It scopes everything to the active brand and prompts to create a brand on first launch
- Brand commands: `marketing-agents brand list | show | use <slug> | new <slug>`. Per-run override: `marketing-agents run --brand <slug> --input ...`
- Reports write to `reports/<active-brand>/`; `AgentResult.save()` resolves the brand via `pipeline.brand.active_brand()`
